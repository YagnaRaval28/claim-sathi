"""Escalation endpoints (system-design §5: /cases/{id}/escalation, /events, /deadlines.ics, /notifications)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.api.deps import consented_user, csrf, ctx, current_user, db, owned_case
from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.escalation import service as esc_svc
from claimsathi.guards import idempotent_replay, idempotent_store
from claimsathi.models import Case, Deadline, Document, User

router = APIRouter(prefix="/api/v1", dependencies=[Depends(csrf)])


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class S1Meta(_In):
    method: Literal["email", "post", "portal"]


class ReplyMeta(_In):
    satisfied: bool


class S2Meta(_In):
    token: str | None = Field(default=None, max_length=40)


class S3Meta(_In):
    reference: str | None = Field(default=None, max_length=40)


class OutcomeMeta(_In):
    result: Literal["award", "dismissed", "settled", "withdrawn", "other"]


class PaymentMeta(_In):
    amount_paise: int | None = Field(default=None, ge=0)


class EmptyMeta(_In):
    pass


META: dict[str, type[_In]] = {
    "s1_sent": S1Meta,
    "insurer_reply": ReplyMeta,
    "s2_filed": S2Meta,
    "s3_filed": S3Meta,
    "ombudsman_outcome": OutcomeMeta,
    "payment_received": PaymentMeta,
    "closed": EmptyMeta,
}


class EventIn(_In):
    kind: Literal["s1_sent", "insurer_reply", "s2_filed", "s3_filed", "ombudsman_outcome", "payment_received", "closed"]
    event_date: date
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _meta_matches_kind(self) -> EventIn:
        self.metadata = META[self.kind].model_validate(self.metadata).model_dump(exclude_none=True)
        return self


@router.get("/cases/{case_id}/escalation")
def get_escalation(
    case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    return esc_svc.escalation_view(c, s, case)


@router.get("/cases/{case_id}/events")
def list_events(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    return {"items": [esc_svc.event_view(e) for e in esc_svc.event_rows(s, case)]}


@router.post("/cases/{case_id}/events", status_code=201)
def post_event(
    body: EventIn,
    case: Case = Depends(owned_case),
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = {"case": str(case.id), **body.model_dump(mode="json")}
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    if (
        body.document_id is not None
        and s.scalar(select(Document.id).where(Document.id == body.document_id, Document.case_id == case.id)) is None
    ):
        raise AppError("validation_error", 422, "That document isn't part of this case.")
    ev = esc_svc.add_event(
        s, case, kind=body.kind, event_date=body.event_date, meta=body.metadata, document_id=body.document_id
    )
    out = esc_svc.event_view(ev)
    idempotent_store(s, user.id, idem or "", payload, 201, out)
    s.commit()
    return JSONResponse(out, status_code=201)


@router.delete("/cases/{case_id}/events/{event_id}", status_code=204)
def delete_event(event_id: uuid.UUID, case: Case = Depends(owned_case), s: Session = Depends(db)) -> Response:
    esc_svc.delete_event(s, case, event_id)
    s.commit()
    return Response(status_code=204)


class AckIn(_In):
    rule_keys: list[str] = Field(min_length=1, max_length=6)


@router.post("/cases/{case_id}/escalation/acknowledgements", status_code=204)
def acknowledge(body: AckIn, case: Case = Depends(owned_case), s: Session = Depends(db)) -> Response:
    esc_svc.acknowledge(s, case, body.rule_keys)
    s.commit()
    return Response(status_code=204)


class PackIn(_In):
    language: Literal["en"] = "en"


@router.get("/cases/{case_id}/packs/ombudsman")
def get_pack(
    case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    return esc_svc.pack_view(c, s, case)


@router.post("/cases/{case_id}/packs/ombudsman", status_code=202)
def post_pack(
    body: PackIn,
    case: Case = Depends(owned_case),
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    """FR-026 AC1: generation is impossible while any Block rule fails (checked here, not only in the UI)."""
    from claimsathi.letters.service import create_ombudsman_letter

    payload = {"case": str(case.id), "op": "ombudsman_pack", **body.model_dump()}
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    esc_svc.pack_guard(c, s, case)
    letter = create_ombudsman_letter(c, s, case)
    out = {"letter_id": str(letter.id)}
    idempotent_store(s, user.id, idem or "", payload, 202, out)
    s.commit()
    return JSONResponse(out, status_code=202)


ICS_ACTIONS = {
    "insurer_response_expected": "Check if your insurer replied",
    "ombudsman_eligible_from": "You can go to the Insurance Ombudsman from today",
    "ombudsman_limitation": "Last day to go to the Insurance Ombudsman",
    "ombudsman_award_expected": "Ombudsman decision usually expected by today",
}


def _ics_text(v: str) -> str:
    return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/cases/{case_id}/deadlines.ics")
def deadlines_ics(case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)) -> Response:
    """FR-022 calendar export [P1]: events hold the case nickname and the action only."""
    nickname = c.cipher.decrypt(case.nickname_enc)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ClaimSathi//Deadlines//EN", "CALSCALE:GREGORIAN"]
    for d in s.scalars(select(Deadline).where(Deadline.case_id == case.id, Deadline.status == "active")):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{d.id}@claimsathi",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d.due_date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(d.due_date + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_text(f'{nickname}: {ICS_ACTIONS[d.kind]}')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return Response(
        "\r\n".join(lines) + "\r\n",
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="claimsathi-deadlines.ics"', "Cache-Control": "no-store"},
    )


@router.get("/notifications")
def get_notifications(
    user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    return {"items": esc_svc.notifications(c, s, user)}


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(
    notification_id: uuid.UUID, user: User = Depends(current_user), s: Session = Depends(db)
) -> Response:
    esc_svc.mark_read(s, user, notification_id)
    s.commit()
    return Response(status_code=204)
