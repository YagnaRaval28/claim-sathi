"""Data-control endpoints (system-design §5): delete case/account, exports, retention, outcome, reports, settings."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.api.deps import csrf, ctx, current_user, db, owned_case
from claimsathi.cases.service import case_summary
from claimsathi.context import AppContext
from claimsathi.core.errors import AppError, not_found
from claimsathi.datacontrols import service as dc
from claimsathi.guards import idempotent_replay, idempotent_store
from claimsathi.models import Case, User

router = APIRouter(prefix="/api/v1", dependencies=[Depends(csrf)])


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfirmIn(_In):
    confirm_code: str = Field(pattern=r"^\d{4}$")


def _after_commit(bg: BackgroundTasks, c: AppContext) -> None:
    if c.settings.task_queue == "inprocess":
        bg.add_task(c.dispatcher.run_pending)


# --- Delete a case (FR-031) and the account (FR-032) -----------------------------------------------


@router.post("/cases/{case_id}/delete-challenge")
def case_delete_challenge(case: Case = Depends(owned_case), c: AppContext = Depends(ctx)) -> dict[str, str]:
    return dc.new_challenge(c, "delete_case", case.id)


@router.delete("/cases/{case_id}", status_code=202)
def delete_case(
    body: ConfirmIn,
    case: Case = Depends(owned_case),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    challenge: Annotated[str | None, Header(alias="X-Confirm-Challenge")] = None,
) -> Response:
    dc.check_challenge(c, challenge, body.confirm_code, "delete_case", case.id)
    dc.purge_case(c, s, case)
    s.commit()
    return Response(status_code=202)


@router.post("/me/delete-challenge")
def account_delete_challenge(user: User = Depends(current_user), c: AppContext = Depends(ctx)) -> dict[str, str]:
    return dc.new_challenge(c, "delete_account", user.id)


@router.delete("/me", status_code=202)
def delete_me(
    body: ConfirmIn,
    response: Response,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    challenge: Annotated[str | None, Header(alias="X-Confirm-Challenge")] = None,
) -> Response:
    dc.check_challenge(c, challenge, body.confirm_code, "delete_account", user.id)
    dc.delete_account(c, s, user)
    response.delete_cookie(c.settings.session_cookie_name, path="/")
    response.status_code = 202
    return response


# --- Export my data (FR-030) -----------------------------------------------------------------------


class ExportIn(_In):
    scope: Literal["case", "account"]
    case_id: uuid.UUID | None = None


@router.post("/exports", status_code=202)
def post_export(
    body: ExportIn,
    bg: BackgroundTasks,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = body.model_dump(mode="json")
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    case = None
    if body.scope == "case":
        if body.case_id is None:
            raise AppError("validation_error", 422, "Choose a case to export.")
        case = s.scalar(select(Case).where(Case.id == body.case_id, Case.user_id == user.id, Case.deleted_at.is_(None)))
        if case is None:
            raise not_found()
    exp = dc.request_export(s, user, body.scope, case)
    out = {"id": str(exp.id)}
    idempotent_store(s, user.id, idem or "", payload, 202, out)
    s.commit()
    _after_commit(bg, c)
    return JSONResponse(out, status_code=202)


@router.get("/exports/{export_id}")
def get_export(export_id: uuid.UUID, user: User = Depends(current_user), s: Session = Depends(db)) -> dict[str, Any]:
    return dc.export_view(dc.owned_export(s, user, export_id))


@router.get("/exports/{export_id}/file")
def download_export(
    export_id: uuid.UUID, user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> Response:
    exp = dc.owned_export(s, user, export_id)
    if dc.export_view(exp)["status"] != "ready" or not exp.storage_key:
        raise not_found()
    return Response(
        c.store.get(exp.storage_key),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="claimsathi-export.zip"', "Cache-Control": "no-store"},
    )


# --- Retention (FR-033) and outcome (FR-034) -------------------------------------------------------


@router.post("/cases/{case_id}/retention/extend")
def extend_retention(
    case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    dc.extend_retention(case)
    s.commit()
    return case_summary(c, s, case)


class OutcomeIn(_In):
    outcome: Literal["paid_in_full", "partly_paid", "not_paid", "withdrew"] | None = None
    amount_received_paise: int | None = Field(default=None, ge=0)
    ombudsman_accepted: Literal["accepted", "dismissed_not_admissible", "dont_know"] | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


@router.put("/cases/{case_id}/outcome")
def put_outcome(
    body: OutcomeIn, case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    dc.set_outcome(s, case, body.model_dump())
    s.commit()
    return case_summary(c, s, case)


# --- Report a problem (FR-035) ---------------------------------------------------------------------


class ReportIn(_In):
    case_id: uuid.UUID
    target_type: Literal["counter_point", "citation", "letter_block"]
    target_id: uuid.UUID
    block_index: int | None = Field(default=None, ge=0)
    reason: Literal["wrong_fact", "wrong_rule", "bad_translation", "other"]
    comment: str | None = Field(default=None, max_length=1000)
    grant_access: bool = False


@router.post("/reports", status_code=201)
def post_report(
    body: ReportIn,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = body.model_dump(mode="json")
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    case = s.scalar(select(Case).where(Case.id == body.case_id, Case.user_id == user.id, Case.deleted_at.is_(None)))
    if case is None:
        raise not_found()
    item = dc.create_report(
        s,
        case,
        target_type=body.target_type,
        target_id=body.target_id,
        block_index=body.block_index,
        reason=body.reason,
        comment=body.comment,
        grant_access=body.grant_access,
        language=user.display_language,
    )
    s.flush()
    out = {"id": str(item.id), "status": item.status}
    idempotent_store(s, user.id, idem or "", payload, 201, out)
    s.commit()
    return JSONResponse(out, status_code=201)


# --- Support access (FR-042) -----------------------------------------------------------------------


@router.get("/cases/{case_id}/support-grant")
def get_support_grant(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    g = dc.active_grant(s, case.id)
    return {"active": g is not None, "expires_at": g.expires_at.isoformat() if g else None}


@router.post("/cases/{case_id}/support-grant")
def post_support_grant(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    g = dc.grant_support_access(s, case)
    s.commit()
    return {"active": True, "expires_at": g.expires_at.isoformat()}


@router.delete("/cases/{case_id}/support-grant", status_code=204)
def delete_support_grant(case: Case = Depends(owned_case), s: Session = Depends(db)) -> Response:
    dc.revoke_support_access(s, case)
    s.commit()
    return Response(status_code=204)


# --- Settings (FR-036) -----------------------------------------------------------------------------


class EmailIn(_In):
    new_email: EmailStr


@router.post("/me/email", status_code=204)
def change_email(
    body: EmailIn, user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> Response:
    dc.request_email_change(c, s, user, str(body.new_email))
    return Response(status_code=204)


class CodeIn(_In):
    code: str = Field(pattern=r"^\d{6}$")


@router.post("/me/email/verify", status_code=204)
def verify_email(
    body: CodeIn, user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> Response:
    dc.verify_email_change(c, s, user, body.code)
    return Response(status_code=204)


@router.get("/me/consents")
def my_consents(user: User = Depends(current_user), s: Session = Depends(db)) -> dict[str, Any]:
    return {"items": dc.consent_history(s, user)}
