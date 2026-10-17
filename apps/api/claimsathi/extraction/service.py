"""Fact extraction (FR-010/012) and confirmation (FR-011/012).

The model proposes values. The server accepts a value only if it appears verbatim in the cited source lines.
Amounts and dates are parsed by code, never by the model. Identity fields are encrypted at rest.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from claimsathi.ai.gateway import BudgetExceeded, ModelOutputInvalid, TransientProviderError
from claimsathi.ai.prompts import EXTRACT_SYSTEM_V1, EXTRACT_V1, extract_user_v1
from claimsathi.ai.schemas import ExtractionResult
from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.core.values import format_date_dmy, format_inr, parse_amount_paise, parse_date
from claimsathi.documents.service import case_lines
from claimsathi.jobs import Handler, step, task
from claimsathi.models import Case, DecisionReason, ExtractedField, JobStep, LineItem, Outbox
from claimsathi.verify.citations import normalise

IDENTITY_FIELDS = {"patient_name", "policy_number", "claim_number"}
AMOUNT_FIELDS = {
    "claimed_amount": "claimed_paise",
    "paid_amount": "paid_paise",
    "disallowed_amount": "disallowed_paise",
}
DATE_FIELDS = {"decision_letter_date", "admission_date", "discharge_date", "first_inception_date"}
ENUM_FIELDS = {"decision_type": {"partial", "repudiation"}}
REQUIRED = ("insurer", "decision_letter_date", "decision_type", "claimed_paise")
FIELD_ORDER = (
    "insurer",
    "tpa",
    "policy_number",
    "claim_number",
    "patient_name",
    "hospital",
    "policy_type",
    "first_inception_date",
    "admission_date",
    "discharge_date",
    "claim_type",
    "claimed_paise",
    "paid_paise",
    "disallowed_paise",
    "decision_letter_date",
    "decision_type",
)


def _verbatim(value: str, line_ids: list[str], lines: dict[str, str]) -> bool:
    src = normalise(" ".join(lines.get(i, "") for i in line_ids)) if line_ids else ""
    return bool(src) and normalise(value) in src


def _store_name(field: str) -> str:
    return AMOUNT_FIELDS.get(field, field)


def apply_extraction(
    c: AppContext, s: Session, case: Case, result: ExtractionResult, lines: list[tuple[str, str]]
) -> None:
    by_id = dict(lines)
    user_set = set(
        s.scalars(
            select(ExtractedField.name).where(
                ExtractedField.case_id == case.id, ExtractedField.status.in_(("user_entered", "unknown_by_user"))
            )
        )
    )
    s.execute(
        delete(ExtractedField).where(ExtractedField.case_id == case.id, ExtractedField.name.not_in(user_set or {""}))
    )
    s.execute(delete(LineItem).where(LineItem.case_id == case.id, LineItem.user_entered.is_(False)))
    s.execute(delete(DecisionReason).where(DecisionReason.case_id == case.id))
    seen: set[str] = set(user_set)  # a value the user typed always wins over a newly extracted one
    for f in result.fields:
        name = _store_name(f.name)
        if name in seen or f.value is None:
            continue
        raw = f.value.strip()
        value: str | None
        if f.name in ENUM_FIELDS:
            low = raw.lower()
            value = "partial" if "part" in low else "repudiation" if ("repud" in low or "reject" in low) else None
        elif not _verbatim(raw, f.line_ids, by_id):
            value = None  # not grounded in the cited lines: never store an invented value
        elif f.name in AMOUNT_FIELDS:
            p = parse_amount_paise(raw)
            value = str(p) if p is not None else None
        elif f.name in DATE_FIELDS:
            d = parse_date(raw)
            value = d.isoformat() if d else None
        else:
            value = raw
        if value is None:
            continue
        seen.add(name)
        ref = {"line_ids": f.line_ids}
        row = ExtractedField(case_id=case.id, name=name, status="found", source_ref=ref)
        if name in IDENTITY_FIELDS:
            row.value_enc = row.extracted_value_enc = c.cipher.encrypt(value)
        else:
            row.value = row.extracted_value = value
        s.add(row)
    for name in REQUIRED:
        if name not in seen:
            s.add(ExtractedField(case_id=case.id, name=name, status="not_found", confidence_flag="please_check"))
    for i, li in enumerate(result.line_items, start=1):
        amount = parse_amount_paise(li.deducted_amount) if _verbatim(li.deducted_amount, li.line_ids, by_id) else None
        if amount is None:
            continue
        clause = (
            li.clause_cited_verbatim
            if (li.clause_cited_verbatim and _verbatim(li.clause_cited_verbatim, li.line_ids, by_id))
            else None
        )
        billed = parse_amount_paise(li.billed_amount) if li.billed_amount else None
        s.add(
            LineItem(
                case_id=case.id,
                ordinal=i,
                description=li.description.strip(),
                deducted_paise=amount,
                billed_paise=billed if billed is not None and billed >= amount else None,
                reason_verbatim=li.reason_verbatim,
                clause_cited_verbatim=clause,
                source_ref={"line_ids": li.line_ids},
            )
        )
    for i, r in enumerate(result.reasons, start=1):
        if _verbatim(r.text_verbatim, r.line_ids, by_id):
            s.add(
                DecisionReason(
                    case_id=case.id,
                    ordinal=i,
                    text_verbatim=r.text_verbatim,
                    clause_cited_verbatim=r.clause_cited_verbatim,
                    source_ref={"line_ids": r.line_ids},
                )
            )
    insurer = s.scalar(
        select(ExtractedField.value).where(ExtractedField.case_id == case.id, ExtractedField.name == "insurer")
    )
    case.insurer_name = insurer


def _extract_failed(s: Session, payload: dict[str, Any]) -> None:
    case = s.get(Case, uuid.UUID(payload["case_id"]))
    if case is None:
        return
    step(
        s,
        case_id=case.id,
        job_kind="extraction",
        job_ref=uuid.UUID(payload["after"]),
        step_key="finding_details",
        ordinal=2,
        status="failed",
        error_code="extraction_failed",
    )


def make_extract_handler(c: AppContext) -> Handler:
    @task("case.extract", on_failure=_extract_failed)
    def _extract(s: Session, payload: dict[str, Any]) -> None:
        case = s.get(Case, uuid.UUID(payload["case_id"]))
        if case is None or case.deleted_at is not None or case.fields_confirmed_at is not None:
            return
        job_ref = uuid.UUID(payload["after"])
        step(
            s,
            case_id=case.id,
            job_kind="extraction",
            job_ref=job_ref,
            step_key="finding_details",
            ordinal=2,
            status="in_progress",
        )
        s.commit()
        lines = case_lines(c, s, case.id)
        try:
            result = c.gateway(case.id).structured(
                step_key="extract",
                prompt_version=EXTRACT_V1,
                system=EXTRACT_SYSTEM_V1,
                user=extract_user_v1(lines),
                schema=ExtractionResult,
            )
        except (ModelOutputInvalid, TransientProviderError, BudgetExceeded) as exc:
            code = "ai_paused_budget" if isinstance(exc, BudgetExceeded) else "extraction_failed"
            step(
                s,
                case_id=case.id,
                job_kind="extraction",
                job_ref=job_ref,
                step_key="finding_details",
                ordinal=2,
                status="failed",
                error_code=code,
            )
            return
        apply_extraction(c, s, case, result, lines)
        step(
            s,
            case_id=case.id,
            job_kind="extraction",
            job_ref=job_ref,
            step_key="finding_details",
            ordinal=2,
            status="done",
        )

    return _extract


# --- Facts API service ----------------------------------------------------------------------------


def extraction_state(s: Session, case: Case) -> str:
    """ "running" while a case.extract task is queued or in progress; else "failed", "done" or "none"."""
    pending = s.scalar(
        select(Outbox.id)
        .where(
            Outbox.task_name == "case.extract",
            Outbox.dedupe_key.like(f"case.extract:{case.id}:%"),
            Outbox.status.in_(("pending", "dispatched")),
        )
        .limit(1)
    )
    steps = s.scalars(select(JobStep).where(JobStep.case_id == case.id, JobStep.job_kind == "extraction")).all()
    if pending is not None or any(st.status in ("waiting", "in_progress", "retrying") for st in steps):
        return "running"
    finished = [st for st in steps if st.finished_at is not None]
    if not finished:
        failed_outbox = s.scalar(
            select(Outbox.id)
            .where(
                Outbox.task_name == "case.extract",
                Outbox.dedupe_key.like(f"case.extract:{case.id}:%"),
                Outbox.status == "failed",
            )
            .limit(1)
        )
        return "failed" if failed_outbox is not None else "none"
    latest = max(finished, key=lambda st: st.finished_at or now_utc())
    return "failed" if latest.status == "failed" else "done"


def _display(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    if name.endswith("_paise"):
        return format_inr(int(value))
    d = parse_date(value) if name in DATE_FIELDS else None
    return format_date_dmy(d) if d else value


def facts_view(c: AppContext, s: Session, case: Case) -> dict[str, Any]:
    rows = {r.name: r for r in s.scalars(select(ExtractedField).where(ExtractedField.case_id == case.id))}
    partial = rows.get("decision_type") is not None and rows["decision_type"].value == "partial"
    required = set(REQUIRED) | ({"paid_paise"} if partial else set())
    fields: list[dict[str, Any]] = []
    for name in FIELD_ORDER:
        r = rows.get(name)
        if r is None:
            # every field is listed, so the user can add what the letter didn't say (FR-011)
            fields.append(
                {
                    "name": name,
                    "value": None,
                    "display": None,
                    "status": "not_found",
                    "confidence_flag": "please_check" if name in required else "ok",
                    "source_ref": None,
                    "provenance": "document",
                    "required": name in required,
                    "confirmed": False,
                }
            )
            continue
        val = c.cipher.decrypt(r.value_enc) if r.value_enc else r.value
        fields.append(
            {
                "name": name,
                "value": val,
                "display": _display(name, val),
                "status": r.status,
                "confidence_flag": r.confidence_flag,
                "source_ref": r.source_ref,
                "provenance": "user" if r.status == "user_entered" else "document",
                "required": name in required,
                "confirmed": r.confirmed_by_user,
            }
        )
    return {
        "fields": fields,
        "confirmed": case.fields_confirmed_at is not None,
        "version": case.lock_version,
        "extraction": extraction_state(s, case),
    }


def _validate_value(name: str, value: str) -> str:
    if name.endswith("_paise"):
        p = parse_amount_paise(value)
        if p is None or p < 0:
            raise AppError(
                "validation_error",
                422,
                "Enter an amount in rupees.",
                errors=[{"field": name, "code": "amount", "message": "invalid amount"}],
            )
        return str(p)
    if name in DATE_FIELDS:
        d = parse_date(value)
        if d is None:
            raise AppError(
                "validation_error",
                422,
                "Enter a date as DD/MM/YYYY.",
                errors=[{"field": name, "code": "date", "message": "invalid date"}],
            )
        return d.isoformat()
    if name in ENUM_FIELDS and value not in ENUM_FIELDS[name]:
        raise AppError("validation_error", 422, "Choose a valid option.")
    if len(value) > 300:
        raise AppError("validation_error", 422, "Value is too long.")
    return value.strip()


def mark_stale(case: Case) -> None:
    if case.fields_confirmed_at is not None:
        case.stale_since = now_utc()


def patch_facts(c: AppContext, s: Session, case: Case, base_version: int, edits: list[dict[str, Any]]) -> None:
    if base_version != case.lock_version:
        raise AppError(
            "version_conflict",
            409,
            "These details changed in another tab. Reload to continue.",
            extra={"current_version": case.lock_version},
        )
    for e in edits:
        name = e["name"]
        if name not in FIELD_ORDER:
            raise AppError("validation_error", 422, f"Unknown field {name}.")
        row = s.scalar(select(ExtractedField).where(ExtractedField.case_id == case.id, ExtractedField.name == name))
        if row is None:
            row = ExtractedField(case_id=case.id, name=name, status="user_entered")
            s.add(row)
        raw = e.get("value")
        val = _validate_value(name, str(raw)) if raw not in (None, "") else None
        row.value, row.value_enc = None, None
        if val is not None and name in IDENTITY_FIELDS:
            row.value_enc = c.cipher.encrypt(val)
        else:
            row.value = val
        row.status = "user_entered" if val is not None else ("unknown_by_user" if e.get("unknown") else "not_found")
        row.confidence_flag = "ok"
        if name == "insurer":
            case.insurer_name = val
    case.lock_version += 1
    mark_stale(case)
    s.commit()


def confirm_facts(s: Session, case: Case, base_version: int) -> None:
    if base_version != case.lock_version:
        raise AppError(
            "version_conflict",
            409,
            "These details changed. Reload to continue.",
            extra={"current_version": case.lock_version},
        )
    rows = {r.name: r for r in s.scalars(select(ExtractedField).where(ExtractedField.case_id == case.id))}
    missing = [n for n in REQUIRED if n not in rows or (rows[n].value is None and rows[n].value_enc is None)]
    if (
        rows.get("decision_type")
        and rows["decision_type"].value == "partial"
        and ("paid_paise" not in rows or rows["paid_paise"].value is None)
    ):
        missing.append("paid_paise")
    if missing:
        raise AppError(
            "required_fields_missing",
            422,
            "Some required details are missing.",
            errors=[{"field": m, "code": "required", "message": "required"} for m in missing],
        )
    for r in rows.values():
        r.confirmed_by_user = True
    case.fields_confirmed_at = now_utc()
    case.lock_version += 1
    s.commit()


def line_items_view(s: Session, case: Case) -> dict[str, Any]:
    items = s.scalars(select(LineItem).where(LineItem.case_id == case.id).order_by(LineItem.ordinal)).all()
    total = sum(i.deducted_paise for i in items)
    disallowed = s.scalar(
        select(ExtractedField.value).where(ExtractedField.case_id == case.id, ExtractedField.name == "disallowed_paise")
    )
    claimed = s.scalar(
        select(ExtractedField.value).where(ExtractedField.case_id == case.id, ExtractedField.name == "claimed_paise")
    )
    paid = s.scalar(
        select(ExtractedField.value).where(ExtractedField.case_id == case.id, ExtractedField.name == "paid_paise")
    )
    expected = int(disallowed) if disallowed else (int(claimed) - int(paid) if claimed and paid else None)
    mismatch = None if expected is None else total - expected
    threshold = max(100, abs(expected or 0) // 100)
    return {
        "items": [
            {
                "id": str(i.id),
                "ordinal": i.ordinal,
                "description": i.description,
                "billed_paise": i.billed_paise,
                "deducted_paise": i.deducted_paise,
                "deducted_display": format_inr(i.deducted_paise),
                "reason_verbatim": i.reason_verbatim,
                "clause_cited_verbatim": i.clause_cited_verbatim,
                "user_entered": i.user_entered,
                "audit_status": i.audit_status,
            }
            for i in items
        ],
        "totals": {
            "deducted_paise": total,
            "deducted_display": format_inr(total),
            "matches_disallowed": mismatch is None or abs(mismatch) <= threshold,
            "mismatch_paise": mismatch,
        },
        "confirmed": case.line_items_confirmed_at is not None,
        "version": case.lock_version,
    }


def replace_line_items(s: Session, case: Case, base_version: int, items: list[dict[str, Any]]) -> None:
    if base_version != case.lock_version:
        raise AppError(
            "version_conflict",
            409,
            "These details changed. Reload to continue.",
            extra={"current_version": case.lock_version},
        )
    if len(items) > 200:
        raise AppError("validation_error", 422, "Too many lines.")
    s.execute(delete(LineItem).where(LineItem.case_id == case.id))
    for i, it in enumerate(items, start=1):
        deducted = int(it["deducted_paise"])
        billed = it.get("billed_paise")
        if deducted < 0 or (billed is not None and int(billed) < deducted):
            raise AppError("validation_error", 422, "A deducted amount can't be negative or more than billed.")
        desc = str(it.get("description", "")).strip()
        if not desc:
            raise AppError("validation_error", 422, "Each line needs a description.")
        s.add(
            LineItem(
                case_id=case.id,
                ordinal=i,
                description=desc[:500],
                deducted_paise=deducted,
                billed_paise=int(billed) if billed is not None else None,
                reason_verbatim=(it.get("reason_verbatim") or None),
                clause_cited_verbatim=(it.get("clause_cited_verbatim") or None),
                user_entered=bool(it.get("user_entered", True)),
            )
        )
    case.lock_version += 1
    if case.line_items_confirmed_at is not None:
        case.stale_since = now_utc()
    s.commit()


def confirm_line_items(s: Session, case: Case, base_version: int) -> None:
    if base_version != case.lock_version:
        raise AppError(
            "version_conflict",
            409,
            "These details changed. Reload to continue.",
            extra={"current_version": case.lock_version},
        )
    case.line_items_confirmed_at = now_utc()
    case.lock_version += 1
    s.commit()
