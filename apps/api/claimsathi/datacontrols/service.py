"""Data controls (PRD FR-030 to FR-036): typed delete confirmations, hard deletion, data export, retention,
outcome capture, problem reports and email change.

Deletion is a hard delete: storage objects, database rows (by cascade), queued tasks and cached idempotent
responses. The audit log keeps only the action, the entity id and the time (no content).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import secrets
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError, not_found
from claimsathi.core.logging import get_logger
from claimsathi.models import (
    Analysis,
    AuditLog,
    Case,
    CaseEvent,
    Citation,
    Consent,
    CounterPoint,
    DataExport,
    DecisionReason,
    Document,
    DocumentObject,
    EmailChallenge,
    IdempotencyKey,
    KnowledgeChunk,
    KnowledgeSource,
    Letter,
    Outbox,
    Reminder,
    ReviewItem,
    SupportGrant,
    User,
)

log = get_logger("datacontrols")
CHALLENGE_TTL = timedelta(minutes=10)
EXPORT_TTL = timedelta(hours=24)
CLOSED_RETENTION = timedelta(days=90)  # PROVISIONAL (FR-033), pending legal review
INACTIVE_AFTER = timedelta(days=548)  # about 18 months
INACTIVE_GRACE = timedelta(days=30)


def _audit(s: Session, *, actor: str, actor_id: str | None, action: str, entity: str, entity_id: str) -> None:
    s.add(AuditLog(actor_type=actor, actor_id=actor_id, action=action, entity_type=entity, entity_id=entity_id))


# --- Typed confirmations (design DD-10) ------------------------------------------------------------


def _sign(c: AppContext, msg: str) -> str:
    key = c.settings.csrf_secret.get_secret_value().encode()
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()[:32]


def new_challenge(c: AppContext, purpose: str, subject_id: uuid.UUID) -> dict[str, str]:
    """A 4-digit code shown on screen, bound to the purpose and subject and valid for 10 minutes."""
    code = f"{secrets.randbelow(10_000):04d}"
    expires = int((now_utc() + CHALLENGE_TTL).timestamp())
    body = f"{purpose}:{subject_id}:{expires}"
    token = base64.urlsafe_b64encode(f"{body}:{_sign(c, f'{body}:{code}')}".encode()).decode()
    return {"challenge_id": token, "code": code}


def check_challenge(c: AppContext, token: str | None, code: str, purpose: str, subject_id: uuid.UUID) -> None:
    bad = AppError("confirmation_invalid", 422, "The confirmation code doesn't match. Please type it again.")
    try:
        p, subject, expires, sig = base64.urlsafe_b64decode((token or "").encode()).decode().split(":")
    except (ValueError, UnicodeDecodeError) as exc:
        raise bad from exc
    if p != purpose or subject != str(subject_id) or int(expires) < int(now_utc().timestamp()):
        raise bad
    if not hmac.compare_digest(sig, _sign(c, f"{p}:{subject}:{expires}:{code}")):
        raise bad


# --- Hard deletion (FR-031, FR-032) ----------------------------------------------------------------


def purge_case(c: AppContext, s: Session, case: Case, *, actor: str = "user") -> None:
    doc_ids = [str(d) for d in s.scalars(select(Document.id).where(Document.case_id == case.id))]
    analysis_ids = [str(a) for a in s.scalars(select(Analysis.id).where(Analysis.case_id == case.id))]
    keys = (
        [f"case.extract:{case.id}:%"] + [f"doc.read:{d}" for d in doc_ids] + [f"analysis.run:{a}" for a in analysis_ids]
    )
    # queued jobs are cancelled, and finished job rows that point at the case are removed too
    s.execute(
        delete(Outbox).where(
            or_(*(Outbox.dedupe_key.like(k) for k in keys), Outbox.payload["case_id"].astext == str(case.id))
        )
    )
    for exp in s.scalars(select(DataExport).where(DataExport.case_id == case.id, DataExport.storage_key.is_not(None))):
        c.store.delete_prefix(exp.storage_key or "")
    # cached idempotent replies can hold letter text: drop this user's cache (short-lived anyway)
    s.execute(delete(IdempotencyKey).where(IdempotencyKey.scope_id == case.user_id))
    c.store.delete_prefix(f"cases/{case.id}/")
    s.execute(delete(Case).where(Case.id == case.id))  # every case table cascades
    _audit(s, actor=actor, actor_id=None, action="case_deleted", entity="case", entity_id=str(case.id))


DELETED_EMAIL = {
    "en": ("Your ClaimSathi account was deleted", "Your ClaimSathi account and all its cases have been deleted."),
    "gu": ("તમારું ClaimSathi એકાઉન્ટ કાઢી નાખવામાં આવ્યું", "તમારું ClaimSathi એકાઉન્ટ અને તેના બધા કેસ કાઢી નાખવામાં આવ્યા છે."),
    "hi": ("आपका ClaimSathi खाता हटा दिया गया", "आपका ClaimSathi खाता और उसके सभी केस हटा दिए गए हैं।"),
}


def delete_account(c: AppContext, s: Session, user: User) -> None:
    email = c.cipher.decrypt(user.email_enc)
    lang = user.display_language
    for case in s.scalars(select(Case).where(Case.user_id == user.id)).all():
        purge_case(c, s, case)
    c.store.delete_prefix(f"users/{user.id}/")
    s.execute(delete(EmailChallenge).where(EmailChallenge.email_hash == user.email_hash))
    s.execute(delete(IdempotencyKey).where(IdempotencyKey.scope_id == user.id))
    s.execute(delete(User).where(User.id == user.id))  # sessions, consents and exports cascade
    _audit(s, actor="user", actor_id=None, action="account_deleted", entity="user", entity_id=str(user.id))
    s.commit()
    subject, body = DELETED_EMAIL.get(lang, DELETED_EMAIL["en"])
    try:
        c.mailer.send(to=email, subject=subject, text=body)
    except Exception as exc:  # deletion already happened; the confirmation is also shown on screen (AC2)
        log.warning("account_deleted_email_failed", error_code=type(exc).__name__)


# --- Data export (FR-030) --------------------------------------------------------------------------


def request_export(s: Session, user: User, scope: str, case: Case | None) -> DataExport:
    exp = DataExport(id=uuid.uuid4(), user_id=user.id, case_id=case.id if case else None, scope=scope)
    s.add(exp)
    s.flush()
    from claimsathi.jobs import enqueue

    enqueue(s, "export.data_zip", {"export_id": str(exp.id)}, dedupe_key=f"export.data_zip:{exp.id}", queue="io")
    return exp


def _case_bundle(c: AppContext, s: Session, case: Case, z: zipfile.ZipFile, folder: str) -> None:
    from claimsathi.analysis.service import analysis_view
    from claimsathi.escalation.service import event_rows, event_view
    from claimsathi.extraction.service import facts_view, line_items_view

    def put(name: str, data: Any) -> None:
        z.writestr(f"{folder}/{name}", json.dumps(data, ensure_ascii=False, indent=2, default=str))

    put(
        "case.json",
        {
            "nickname": c.cipher.decrypt(case.nickname_enc),
            "complainant_name": c.cipher.decrypt(case.complainant_name_enc) if case.complainant_name_enc else None,
            "status": case.status,
            "stage": case.stage,
            "eligibility": case.eligibility,
            "insurer_name": case.insurer_name,
            "outcome": case.outcome,
            "created_at": case.created_at.isoformat(),
        },
    )
    put("facts.json", facts_view(c, s, case)["fields"])
    put("line_items.json", line_items_view(s, case)["items"])
    put(
        "reasons.json",
        [
            {"text": r.text_verbatim, "clause_cited": r.clause_cited_verbatim, "audit_status": r.audit_status}
            for r in s.scalars(select(DecisionReason).where(DecisionReason.case_id == case.id))
        ],
    )
    put("analysis.json", analysis_view(s, case))
    put(
        "letters.json",
        [
            {"id": str(lt.id), "stage": lt.stage, "language": lt.language, "version": lt.version, "doc": lt.doc}
            for lt in s.scalars(select(Letter).where(Letter.case_id == case.id).order_by(Letter.created_at))
        ],
    )
    put("events.json", [event_view(e) for e in event_rows(s, case)])
    for n, (doc, obj) in enumerate(
        s.execute(
            select(Document, DocumentObject)
            .join(DocumentObject, DocumentObject.document_id == Document.id)
            .where(Document.case_id == case.id)
            .order_by(Document.created_at)
        ).all(),
        start=1,
    ):
        try:
            z.writestr(f"{folder}/documents/{n:02d}-{doc.type}.pdf", c.store.get(obj.storage_key))
        except KeyError:
            continue  # already removed by retention


def build_export(c: AppContext, s: Session, exp: DataExport) -> None:
    user = s.get(User, exp.user_id)
    if user is None:
        return
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        cases = (
            [s.get(Case, exp.case_id)]
            if exp.scope == "case"
            else list(s.scalars(select(Case).where(Case.user_id == user.id, Case.deleted_at.is_(None))))
        )
        for n, case in enumerate([x for x in cases if x is not None], start=1):
            _case_bundle(c, s, case, z, f"case-{n:02d}")
        consents = s.scalars(select(Consent).where(Consent.user_id == user.id).order_by(Consent.granted_at)).all()
        z.writestr(
            "consents.json",
            json.dumps(
                [
                    {
                        "version": x.version,
                        "purposes": list(x.purposes),
                        "granted_at": x.granted_at.isoformat(),
                        "withdrawn_at": x.withdrawn_at.isoformat() if x.withdrawn_at else None,
                    }
                    for x in consents
                ],
                indent=2,
            ),
        )
        z.writestr(
            "README.txt", "Your ClaimSathi data export. JSON files hold your details; documents/ holds your files.\n"
        )
    key = f"users/{user.id}/exports/{exp.id}.zip"
    c.store.put(key, buf.getvalue(), "application/zip")
    exp.storage_key, exp.status, exp.expires_at = key, "ready", now_utc() + EXPORT_TTL


def make_export_handler(c: AppContext) -> Any:
    from claimsathi.jobs import task

    def _failed(s: Session, payload: dict[str, Any]) -> None:
        exp = s.get(DataExport, uuid.UUID(payload["export_id"]))
        if exp is not None and exp.status == "queued":
            exp.status = "failed"

    @task("export.data_zip", on_failure=_failed)
    def _export(s: Session, payload: dict[str, Any]) -> None:
        exp = s.get(DataExport, uuid.UUID(payload["export_id"]))
        if exp is None or exp.status != "queued":
            return
        build_export(c, s, exp)

    return _export


def export_view(exp: DataExport) -> dict[str, Any]:
    expired = exp.status == "expired" or (exp.expires_at is not None and exp.expires_at <= now_utc())
    status = "expired" if expired else exp.status
    return {
        "id": str(exp.id),
        "scope": exp.scope,
        "status": status,
        "expires_at": exp.expires_at.isoformat() if exp.expires_at else None,
        "download_path": f"/api/v1/exports/{exp.id}/file" if status == "ready" else None,
    }


def owned_export(s: Session, user: User, export_id: uuid.UUID) -> DataExport:
    exp = s.scalar(select(DataExport).where(DataExport.id == export_id, DataExport.user_id == user.id))
    if exp is None:
        raise not_found()
    return exp


# --- Retention (FR-033) ----------------------------------------------------------------------------


def on_status_change(case: Case) -> None:
    """Closed cases keep source files for 90 days after closure (once extendable); reopening clears it."""
    if case.status == "closed" and case.closed_at is not None:
        extra = CLOSED_RETENTION if case.retention_extended else timedelta(0)
        case.retention_delete_after = case.closed_at + CLOSED_RETENTION + extra
    elif case.status == "open" and case.retention_delete_after is not None and case.closed_at is None:
        case.retention_delete_after = None


def extend_retention(case: Case) -> None:
    if case.status != "closed" or case.retention_delete_after is None:
        raise AppError("validation_error", 422, "Only a closed case's files can be kept longer.")
    if case.retention_extended:
        raise AppError("retention_already_extended", 409, "You've already kept these files for longer once.")
    case.retention_extended = True
    case.retention_delete_after = case.retention_delete_after + CLOSED_RETENTION


def _delete_source_files(c: AppContext, s: Session, case: Case) -> None:
    for doc in s.scalars(select(Document).where(Document.case_id == case.id)).all():
        c.store.delete_prefix(f"cases/{case.id}/documents/{doc.id}/")
        s.execute(update(CaseEvent).where(CaseEvent.document_id == doc.id).values(document_id=None))
        s.delete(doc)
    case.retention_delete_after = None
    _audit(s, actor="system", actor_id=None, action="case_files_deleted", entity="case", entity_id=str(case.id))


def run_retention(c: AppContext, now: datetime | None = None) -> dict[str, int]:
    """The retention job: closed-case files after 90 days; inactive open cases after notice + 30 days;
    expired data exports. Returns counts (no content)."""
    now = now or now_utc()
    out = {"files_deleted": 0, "cases_deleted": 0, "notices": 0, "exports_expired": 0}
    with c.session_factory() as s:
        due = s.scalars(select(Case).where(Case.retention_delete_after <= now, Case.deleted_at.is_(None))).all()
        for case in due:
            deadline = case.retention_delete_after
            if deadline is None:
                continue
            if case.status == "closed":
                _delete_source_files(c, s, case)
                out["files_deleted"] += 1
            elif case.last_activity_at <= deadline - INACTIVE_GRACE:
                purge_case(c, s, case, actor="system")
                out["cases_deleted"] += 1
            else:
                case.retention_delete_after = None  # the user acted after the notice
        idle = s.scalars(
            select(Case).where(
                Case.status == "open",
                Case.deleted_at.is_(None),
                Case.retention_delete_after.is_(None),
                Case.last_activity_at <= now - INACTIVE_AFTER,
            )
        ).all()
        from claimsathi.escalation.service import wants_email_reminders

        for case in idle:
            case.retention_delete_after = now + INACTIVE_GRACE
            channels = ["in_app"] + (["email"] if wants_email_reminders(s, case.user_id) else [])
            for ch in channels:
                s.add(Reminder(case_id=case.id, kind="retention_notice", channel=ch, send_at=now, attempts=0))
            out["notices"] += 1
        for exp in s.scalars(
            select(DataExport).where(DataExport.status == "ready", DataExport.expires_at <= now)
        ).all():
            c.store.delete_prefix(exp.storage_key or "")
            exp.status, exp.storage_key = "expired", None
            out["exports_expired"] += 1
        s.commit()
    return out


# --- Outcome (FR-034) and problem reports (FR-035) -------------------------------------------------


def set_outcome(s: Session, case: Case, data: dict[str, Any]) -> None:
    case.outcome = {k: v for k, v in data.items() if v is not None} | {"recorded_at": now_utc().isoformat()}


def _citation_payload(s: Session, cit: Citation) -> dict[str, Any]:
    row = s.execute(
        select(KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(KnowledgeChunk.id == cit.chunk_id)
    ).first()
    ch, src = row if row else (None, None)
    return {
        "quote": cit.quote,
        "source_title": src.title if src else None,
        "clause_ref": ch.clause_ref if ch else None,
        "verified": cit.verified,
    }


def create_report(
    s: Session,
    case: Case,
    *,
    target_type: str,
    target_id: uuid.UUID,
    block_index: int | None,
    reason: str,
    comment: str | None,
    grant_access: bool,
    language: str,
) -> ReviewItem:
    """The review item holds only the flagged output and its citations (FR-035)."""
    payload: dict[str, Any]
    if target_type == "counter_point":
        cp = s.scalar(select(CounterPoint).where(CounterPoint.id == target_id, CounterPoint.case_id == case.id))
        if cp is None:
            raise not_found()
        cits = s.scalars(select(Citation).where(Citation.counter_point_id == cp.id)).all()
        payload = {
            "statement": cp.statement_en,
            "rule_key": cp.rule_key,
            "citations": [_citation_payload(s, x) for x in cits],
        }
    elif target_type == "citation":
        cit = s.scalar(select(Citation).where(Citation.id == target_id, Citation.case_id == case.id))
        if cit is None:
            raise not_found()
        payload = {"citation": _citation_payload(s, cit)}
    else:
        letter = s.scalar(select(Letter).where(Letter.id == target_id, Letter.case_id == case.id))
        blocks = letter.doc.get("blocks", []) if letter else []
        if letter is None or block_index is None or not 0 <= block_index < len(blocks):
            raise not_found()
        b = blocks[block_index]
        payload = {"letter_version": letter.version, "block_index": block_index, "block": b}
    payload["grant_access"] = grant_access
    if grant_access:
        grant_support_access(s, case)
    item = ReviewItem(
        source="user_report",
        case_id=case.id,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        reason=reason,
        comment=comment,
        language=language,
    )
    s.add(item)
    return item


# --- Support access by user grant (FR-042) ---------------------------------------------------------

SUPPORT_GRANT = timedelta(days=7)


def active_grant(s: Session, case_id: uuid.UUID) -> SupportGrant | None:
    return s.scalar(
        select(SupportGrant)
        .where(SupportGrant.case_id == case_id, SupportGrant.revoked_at.is_(None), SupportGrant.expires_at > now_utc())
        .order_by(SupportGrant.expires_at.desc())
        .limit(1)
    )


def grant_support_access(s: Session, case: Case) -> SupportGrant:
    existing = active_grant(s, case.id)
    if existing is not None:
        return existing
    now = now_utc()
    g = SupportGrant(case_id=case.id, granted_at=now, expires_at=now + SUPPORT_GRANT)
    s.add(g)
    _audit(s, actor="user", actor_id=None, action="support_access_granted", entity="case", entity_id=str(case.id))
    return g


def revoke_support_access(s: Session, case: Case) -> None:
    for g in s.scalars(select(SupportGrant).where(SupportGrant.case_id == case.id, SupportGrant.revoked_at.is_(None))):
        g.revoked_at = now_utc()
    _audit(s, actor="user", actor_id=None, action="support_access_revoked", entity="case", entity_id=str(case.id))


# --- Email change (FR-036) -------------------------------------------------------------------------


def request_email_change(c: AppContext, s: Session, user: User, new_email: str) -> None:
    from claimsathi.auth.service import CODE_EMAIL, CODE_TTL, _code_hash, email_hash
    from claimsathi.guards import hit
    from claimsathi.security.crypto import normalize_email, six_digit_code

    eh = email_hash(c, new_email)
    hit(s, f"email_change:user:{user.id}", limit=5, window=timedelta(hours=1))
    if s.scalar(select(User.id).where(User.email_hash == eh, User.id != user.id)) is not None:
        raise AppError("email_in_use", 409, "That email address is already used by another account.")
    ch = EmailChallenge(
        id=uuid.uuid4(),
        email_hash=eh,
        code_hash=b"",
        purpose="change_email",
        expires_at=now_utc() + CODE_TTL,
        user_id=user.id,
        new_email_enc=c.cipher.encrypt(normalize_email(new_email)),
    )
    code = six_digit_code()
    ch.code_hash = _code_hash(c, ch.id, code)
    s.add(ch)
    s.commit()
    subject, body = CODE_EMAIL.get(user.display_language, CODE_EMAIL["en"])
    c.mailer.send(to=normalize_email(new_email), subject=subject, text=body.format(code=code))


def verify_email_change(c: AppContext, s: Session, user: User, code: str) -> None:
    from claimsathi.auth.service import MAX_ATTEMPTS, _code_hash
    from claimsathi.security.crypto import constant_time_equal

    ch = s.scalar(
        select(EmailChallenge)
        .where(
            EmailChallenge.user_id == user.id,
            EmailChallenge.purpose == "change_email",
            EmailChallenge.consumed_at.is_(None),
        )
        .order_by(EmailChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    now = now_utc()
    if ch is None or ch.attempts >= MAX_ATTEMPTS or ch.new_email_enc is None:
        raise AppError(
            "email_code_invalid", 401, "That code isn't right. Request a new code.", extra={"attempts_left": 0}
        )
    if ch.expires_at <= now:
        raise AppError("email_code_expired", 410, "This code has expired. Send a new one.")
    ch.attempts += 1
    if not constant_time_equal(ch.code_hash, _code_hash(c, ch.id, code)):
        s.commit()
        raise AppError(
            "email_code_invalid", 401, "That code isn't right.", extra={"attempts_left": MAX_ATTEMPTS - ch.attempts}
        )
    if s.scalar(select(User.id).where(User.email_hash == ch.email_hash, User.id != user.id)) is not None:
        raise AppError("email_in_use", 409, "That email address is already used by another account.")
    ch.consumed_at = now
    user.email_hash, user.email_enc, user.email_verified_at = ch.email_hash, ch.new_email_enc, now
    ch.new_email_enc = None
    _audit(s, actor="user", actor_id=None, action="email_changed", entity="user", entity_id=str(user.id))
    s.commit()


def consent_history(s: Session, user: User) -> list[dict[str, Any]]:
    return [
        {
            "version": x.version,
            "purposes": list(x.purposes),
            "granted_at": x.granted_at.isoformat(),
            "withdrawn_at": x.withdrawn_at.isoformat() if x.withdrawn_at else None,
        }
        for x in s.scalars(select(Consent).where(Consent.user_id == user.id).order_by(Consent.granted_at.desc()))
    ]
