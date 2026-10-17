"""Consent (FR-005), eligibility and cases (FR-006/007), progress view."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.models import Case, Consent, Document, JobStep, User


class Eligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")
    health_india: Literal["yes", "no", "not_sure"]
    situation: Literal["rejected", "partly_paid", "delayed", "other"]
    policy_type: Literal["individual", "floater", "group", "unknown"]
    complainant_name: str = Field(min_length=1, max_length=120)
    relation: Literal["self", "spouse", "parent", "child", "other"]
    in_litigation: Literal["yes", "no", "not_sure"]


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: str | None = Field(default=None, max_length=80)
    eligibility: Eligibility


def give_consent(s: Session, user: User, *, version: str, purposes: list[str], language: str) -> Consent:
    if "processing" not in purposes or not set(purposes) <= {"processing", "reminders"}:
        raise AppError("validation_error", 422, "Processing consent is required to continue.")
    row = Consent(user_id=user.id, version=version, purposes=sorted(set(purposes)), language=language)
    s.add(row)
    user.onboarded_at = user.onboarded_at or now_utc()
    s.commit()
    return row


def create_case(c: AppContext, s: Session, user: User, body: CaseCreate) -> Case:
    e = body.eligibility
    if e.health_india == "no":
        raise AppError("out_of_scope", 422, "ClaimSathi helps only with health-insurance claims in India.")
    s.execute(select(User.id).where(User.id == user.id).with_for_update())  # serialise per-user creates
    open_count = (
        s.scalar(
            select(func.count(Case.id)).where(Case.user_id == user.id, Case.status == "open", Case.deleted_at.is_(None))
        )
        or 0
    )
    if open_count >= c.settings.max_open_cases:
        raise AppError("open_case_limit", 409, f"You have {open_count} open cases. Close one to start another.")
    nickname = (body.nickname or f"{e.complainant_name} – {now_utc():%b %Y}").strip()
    case = Case(
        id=uuid.uuid4(),
        user_id=user.id,
        nickname_enc=c.cipher.encrypt(nickname),
        complainant_name_enc=c.cipher.encrypt(e.complainant_name.strip()),
        complainant_relation=e.relation,
        policy_type=e.policy_type,
        mode="delay" if e.situation == "delayed" else "full",
        eligibility=e.model_dump(exclude={"complainant_name"}),
    )
    s.add(case)
    s.commit()
    return case


def _next_deadline(s: Session, case: Case) -> dict[str, Any] | None:
    from claimsathi.core.clock import today_ist
    from claimsathi.models import Deadline

    d = s.scalar(
        select(Deadline)
        .where(Deadline.case_id == case.id, Deadline.status == "active", Deadline.due_date >= today_ist())
        .order_by(Deadline.due_date)
        .limit(1)
    )
    return (
        {"kind": d.kind, "due_date": d.due_date.isoformat(), "days_left": (d.due_date - today_ist()).days}
        if d
        else None
    )


def case_summary(c: AppContext, s: Session, case: Case) -> dict[str, Any]:
    from claimsathi.extraction.service import extraction_state  # local import avoids an import cycle

    docs = s.scalars(select(Document).where(Document.case_id == case.id).order_by(Document.created_at)).all()
    return {
        "id": str(case.id),
        "nickname": c.cipher.decrypt(case.nickname_enc),
        "status": case.status,
        "stage": case.stage,
        "mode": case.mode,
        "insurer_name": case.insurer_name,
        "eligibility": case.eligibility,
        "flags": {
            "fields_confirmed": case.fields_confirmed_at is not None,
            "line_items_confirmed": case.line_items_confirmed_at is not None,
            "stale": case.stale_since is not None,
        },
        "extraction": extraction_state(s, case),
        "next_deadline": _next_deadline(s, case),
        "documents": [
            {
                "id": str(d.id),
                "type": d.type,
                "status": d.status,
                "status_reason": d.status_reason,
                "page_count": d.page_count,
            }
            for d in docs
        ],
        "version": case.lock_version,
    }


def progress(s: Session, case: Case) -> dict[str, Any]:
    steps = s.scalars(
        select(JobStep).where(JobStep.case_id == case.id).order_by(JobStep.job_ref, JobStep.ordinal)
    ).all()
    jobs: dict[str, dict[str, Any]] = {}
    for st in steps:
        j = jobs.setdefault(str(st.job_ref), {"kind": st.job_kind, "ref_id": str(st.job_ref), "steps": []})
        j["steps"].append({"key": st.step_key, "status": st.status, "attempt": st.attempt, "error_code": st.error_code})

    # Jobs in run order (job_ref is a random id): jobs that have not started yet come last.
    def started(j: dict[str, Any]) -> tuple[int, str]:
        times = [st.started_at for st in steps if str(st.job_ref) == j["ref_id"] and st.started_at is not None]
        return (0, min(times).isoformat()) if times else (1, "")

    return {"jobs": sorted(jobs.values(), key=started)}
