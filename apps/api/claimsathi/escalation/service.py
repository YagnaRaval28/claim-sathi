"""Case events, stage, deadlines, Ombudsman checks and reminders (PRD FR-020 to FR-023).

Every decision here comes from `claimsathi.rules.escalation` (pure, deterministic) and the rules table. Reminder
content holds the case nickname and the action only: no medical details, no amounts (FR-022).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc, today_ist
from claimsathi.core.errors import AppError
from claimsathi.core.logging import get_logger
from claimsathi.models import (
    Case,
    CaseEvent,
    Consent,
    ConsentVersion,
    Deadline,
    ExtractedField,
    Reminder,
    Rule,
    RuleAcknowledgement,
    User,
)
from claimsathi.rules import escalation as esc

log = get_logger("escalation")
EMAIL_RETRY_DELAY = timedelta(hours=2)  # 3 attempts over about 6 hours (FR-022)
MAX_EMAIL_ATTEMPTS = 3


# --- Inputs from the database ----------------------------------------------------------------------


def params(s: Session) -> esc.Params:
    rows = {
        r.rule_key: r
        for r in s.scalars(select(Rule).where(Rule.rule_key.in_(("RULE-DEADLINES", "RULE-ESC-05"))))
        if r.status == "enabled"
    }
    d = rows["RULE-DEADLINES"].params if "RULE-DEADLINES" in rows else {}
    cap = rows["RULE-ESC-05"].params.get("cap_paise") if "RULE-ESC-05" in rows else None
    base = esc.Params()
    return esc.Params(
        insurer_response_days=int(d.get("insurer_response_days", base.insurer_response_days)),
        eligibility_months=int(d.get("eligibility_months", base.eligibility_months)),
        limitation_years=int(d.get("limitation_years", base.limitation_years)),
        award_months=int(d.get("award_months", base.award_months)),
        amount_cap_paise=int(cap) if cap is not None else base.amount_cap_paise,
    )


def enabled_rules(s: Session) -> dict[str, Rule]:
    return {
        r.rule_key: r for r in s.scalars(select(Rule).where(Rule.rule_key.in_(esc.ESC_RULES), Rule.status == "enabled"))
    }


def event_rows(s: Session, case: Case) -> list[CaseEvent]:
    return list(
        s.scalars(
            select(CaseEvent).where(CaseEvent.case_id == case.id).order_by(CaseEvent.event_date, CaseEvent.created_at)
        )
    )


def _events(rows: list[CaseEvent]) -> list[esc.Event]:
    return [esc.Event(r.kind, r.event_date, dict(r.meta)) for r in rows]


def _facts(s: Session, case: Case) -> dict[str, str | None]:
    return {
        r.name: r.value
        for r in s.scalars(select(ExtractedField).where(ExtractedField.case_id == case.id))
        if r.value_enc is None
    }


def case_facts(c: AppContext | None, s: Session, case: Case) -> esc.CaseFacts:
    """Inputs for RULE-ESC-04 to 06. Without a context the complainant name is left out (Block checks only)."""
    f = _facts(s, case)
    claimed, paid = f.get("claimed_paise"), f.get("paid_paise")
    disputed: int | None = None
    if claimed and f.get("decision_type") == "repudiation":
        disputed = int(claimed)
    elif claimed and paid:
        disputed = int(claimed) - int(paid)
    name = c.cipher.decrypt(case.complainant_name_enc) if c and case.complainant_name_enc else ""
    return esc.CaseFacts(
        in_litigation=str(case.eligibility.get("in_litigation", "no")),
        relation=case.complainant_relation or "self",
        complainant_name=name,
        disputed_paise=disputed,
    )


def wants_email_reminders(s: Session, user_id: uuid.UUID) -> bool:
    version = s.scalar(select(ConsentVersion.version).order_by(ConsentVersion.published_at.desc()).limit(1))
    row = s.scalar(
        select(Consent)
        .where(Consent.user_id == user_id, Consent.version == version, Consent.withdrawn_at.is_(None))
        .order_by(Consent.granted_at.desc())
        .limit(1)
    )
    return row is not None and "reminders" in row.purposes


# --- Recompute: stage, deadlines, reminders (FR-021 AC2) -----------------------------------------


def recompute(s: Session, case: Case) -> None:
    rows = event_rows(s, case)
    events = _events(rows)
    stage, status, s2 = esc.derive_stage(events)
    case.stage, case.s2_filed_at = stage, s2
    if status == "closed" and case.status != "closed":
        case.closed_at = now_utc()
    elif status == "open":
        case.closed_at = None
    case.status = status
    from claimsathi.datacontrols.service import on_status_change

    on_status_change(case)
    p = params(s)
    rules = enabled_rules(s)
    deadline_rule = s.scalar(select(Rule).where(Rule.rule_key == "RULE-DEADLINES", Rule.status == "enabled"))
    planned = esc.compute_deadlines(events, p) if status == "open" else []
    existing = {d.kind: d for d in s.scalars(select(Deadline).where(Deadline.case_id == case.id))}
    today = today_ist()
    for d in planned:
        rule = rules.get(d.rule_key) or (deadline_rule if d.rule_key == "RULE-DEADLINES" else None)
        row = existing.pop(d.kind, None) or Deadline(case_id=case.id, kind=d.kind)
        row.due_date, row.rule_key, row.rule_version = d.due_date, d.rule_key, rule.version if rule else 0
        row.computed_from = d.computed_from
        row.status = "passed" if d.due_date < today else "active"
        s.add(row)
    for gone in existing.values():
        if status == "closed":
            gone.status = "cancelled"
        else:
            s.delete(gone)
    s.flush()
    _replan_reminders(s, case, planned, today)


def _replan_reminders(s: Session, case: Case, planned: list[esc.DeadlineOut], today: date) -> None:
    deadlines = {d.kind: d.id for d in s.scalars(select(Deadline).where(Deadline.case_id == case.id))}
    channels = ["in_app"] + (["email"] if wants_email_reminders(s, case.user_id) else [])
    want = {
        (r.kind, ch, r.send_at): deadlines.get(r.deadline_kind)
        for r in esc.plan_reminders(planned, today)
        for ch in channels
    }
    rows = s.scalars(select(Reminder).where(Reminder.case_id == case.id)).all()
    have = {(r.kind, r.channel, r.send_at): r for r in rows}
    for key, r in have.items():
        if r.status == "scheduled" and r.attempts == 0 and key not in want:
            r.status = "cancelled"
        elif r.status == "cancelled" and key in want:
            r.status, r.deadline_id = "scheduled", want[key]
    for (kind, channel, send_at), deadline_id in want.items():
        if (kind, channel, send_at) not in have:
            s.add(
                Reminder(
                    case_id=case.id, deadline_id=deadline_id, kind=kind, channel=channel, send_at=send_at, attempts=0
                )
            )


# --- Events (FR-023) -------------------------------------------------------------------------------


def _decision_date(s: Session, case: Case) -> date | None:
    v = s.scalar(
        select(ExtractedField.value).where(
            ExtractedField.case_id == case.id, ExtractedField.name == "decision_letter_date"
        )
    )
    return date.fromisoformat(v) if v else None


def add_event(
    s: Session, case: Case, *, kind: str, event_date: date, meta: dict[str, Any], document_id: uuid.UUID | None
) -> CaseEvent:
    if case.status == "closed" and kind != "closed":
        raise AppError("case_closed", 409, "This case is closed.")
    if event_date > today_ist():
        raise AppError(
            "validation_error",
            422,
            "The date can't be in the future.",
            errors=[{"field": "event_date", "code": "future", "message": "future date"}],
        )
    decided = _decision_date(s, case)
    if decided and event_date < decided:
        raise AppError(
            "validation_error",
            422,
            "The date can't be before the insurer's decision letter.",
            errors=[{"field": "event_date", "code": "before_decision", "message": "before decision date"}],
        )
    if kind == "s3_filed":
        events = _events(event_rows(s, case))
        checks = esc.ombudsman_checks(events, case_facts(None, s, case), today_ist(), params(s), set(enabled_rules(s)))
        if esc.blocked(checks):
            raise AppError(
                "escalation_blocked",
                409,
                "The Ombudsman conditions are not met yet.",
                extra={"rule_keys": [c.rule_key for c in checks if c.result in ("block", "unavailable")]},
            )
    ev = CaseEvent(case_id=case.id, kind=kind, event_date=event_date, meta=meta, document_id=document_id)
    s.add(ev)
    s.flush()
    recompute(s, case)
    case.last_activity_at = now_utc()
    return ev


def delete_event(s: Session, case: Case, event_id: uuid.UUID) -> None:
    ev = s.scalar(select(CaseEvent).where(CaseEvent.id == event_id, CaseEvent.case_id == case.id))
    if ev is None:
        from claimsathi.core.errors import not_found

        raise not_found()
    s.delete(ev)
    s.flush()
    recompute(s, case)
    case.last_activity_at = now_utc()


def event_view(e: CaseEvent) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "kind": e.kind,
        "event_date": e.event_date.isoformat(),
        "metadata": e.meta,
        "document_id": str(e.document_id) if e.document_id else None,
    }


# --- Views ---------------------------------------------------------------------------------------


def _next_action(case: Case, checks: list[esc.Check], deadlines: dict[str, Deadline], today: date) -> dict[str, Any]:
    if case.status == "closed":
        return {"key": "closed"}
    if case.stage == "S0_PREPARE":
        return {"key": "send_letter"}
    if case.stage == "S3_OMBUDSMAN":
        award = deadlines.get("ombudsman_award_expected")
        return {"key": "wait_for_ombudsman", "date": award.due_date.isoformat() if award else None}
    if not esc.blocked(checks):
        return {"key": "go_to_ombudsman"}
    reply = deadlines.get("insurer_response_expected")
    eligible = deadlines.get("ombudsman_eligible_from")
    if reply and reply.due_date <= today:
        return {"key": "log_reply", "date": eligible.due_date.isoformat() if eligible else None}
    return {"key": "wait_for_insurer", "date": eligible.due_date.isoformat() if eligible else None}


def escalation_view(c: AppContext, s: Session, case: Case) -> dict[str, Any]:
    today = today_ist()
    rules = enabled_rules(s)
    events = event_rows(s, case)
    checks = esc.ombudsman_checks(_events(events), case_facts(c, s, case), today, params(s), set(rules))
    acks = {
        (a.rule_key, a.rule_version)
        for a in s.scalars(select(RuleAcknowledgement).where(RuleAcknowledgement.case_id == case.id))
    }
    deadline_rows = {d.kind: d for d in s.scalars(select(Deadline).where(Deadline.case_id == case.id))}
    order = ("insurer_response_expected", "ombudsman_eligible_from", "ombudsman_limitation", "ombudsman_award_expected")
    deadlines = []
    for kind in order:
        d = deadline_rows.get(kind)
        if d is None:
            continue
        rule = rules.get(d.rule_key)
        deadlines.append(
            {
                "kind": d.kind,
                "due_date": d.due_date.isoformat(),
                "days_left": (d.due_date - today).days,
                "status": "cancelled" if d.status == "cancelled" else ("passed" if d.due_date < today else "active"),
                "rule": {
                    "key": d.rule_key,
                    "version": d.rule_version,
                    "source_ref": rule.source_ref if rule else None,
                },
                "computed_from": d.computed_from,
            }
        )
    return {
        "stage": case.stage,
        "status": case.status,
        "s2_filed_at": case.s2_filed_at.isoformat() if case.s2_filed_at else None,
        "deadlines": deadlines,
        "ombudsman_checks": [
            {
                "rule_key": ch.rule_key,
                "version": rules[ch.rule_key].version if ch.rule_key in rules else None,
                "result": ch.result,
                "message_key": ch.message_key,
                "params": ch.params,
                "fix_action": ch.fix_action,
                "source_ref": rules[ch.rule_key].source_ref if ch.rule_key in rules else None,
                "acknowledged": ch.rule_key in rules and (ch.rule_key, rules[ch.rule_key].version) in acks,
            }
            for ch in checks
        ],
        "blocked": esc.blocked(checks),
        "events": [event_view(e) for e in events],
        "next_action": _next_action(case, checks, deadline_rows, today),
    }


def acknowledge(s: Session, case: Case, rule_keys: list[str]) -> None:
    rules = enabled_rules(s)
    for key in rule_keys:
        if key not in ("RULE-ESC-03", "RULE-ESC-05") or key not in rules:
            raise AppError("validation_error", 422, "Only warnings can be acknowledged.")
        version = rules[key].version
        if s.get(RuleAcknowledgement, (case.id, key, version)) is None:
            s.add(RuleAcknowledgement(case_id=case.id, rule_key=key, rule_version=version))


# --- Ombudsman pack (FR-026) ----------------------------------------------------------------------

CIO_PORTAL = "https://cioins.co.in"  # Council for Insurance Ombudsmen (research source S50)


def pack_guard(c: AppContext, s: Session, case: Case) -> None:
    """Re-validated server-side on every pack request: no Block rule failing, every warning acknowledged."""
    view = escalation_view(c, s, case)
    if view["blocked"]:
        raise AppError(
            "escalation_blocked",
            409,
            "The Ombudsman conditions are not met yet.",
            extra={
                "rule_keys": [
                    x["rule_key"] for x in view["ombudsman_checks"] if x["result"] in ("block", "unavailable")
                ]
            },
        )
    pending = [x["rule_key"] for x in view["ombudsman_checks"] if x["result"] == "warn" and not x["acknowledged"]]
    if pending:
        raise AppError(
            "warnings_not_acknowledged", 409, "Please read and tick each warning.", extra={"rule_keys": pending}
        )


def pack_view(c: AppContext, s: Session, case: Case) -> dict[str, Any]:
    from claimsathi.letters.service import letter_view
    from claimsathi.models import Document, Letter

    letter = s.scalar(
        select(Letter)
        .where(Letter.case_id == case.id, Letter.stage == "S3")
        .order_by(Letter.created_at.desc())
        .limit(1)
    )
    events = event_rows(s, case)
    docs = s.scalars(select(Document).where(Document.case_id == case.id)).all()
    reply = next((e for e in reversed(events) if e.kind == "insurer_reply"), None)
    has_s1_letter = s.scalar(select(Letter.id).where(Letter.case_id == case.id, Letter.stage == "S1").limit(1))
    facts = case_facts(c, s, case)
    return {
        "letter": letter_view(s, letter, case) if letter else None,
        "signatory": {"name": facts.complainant_name, "is_helper": facts.relation != "self"},
        "enclosures": [
            {"key": "decision_letter", "present": any(d.type == "decision_letter" for d in docs)},
            {"key": "s1_letter", "present": has_s1_letter is not None},
            {
                "key": "insurer_reply" if reply else "no_reply_statement",
                "present": bool(reply and (reply.document_id or any(d.type == "insurer_correspondence" for d in docs)))
                or reply is None,
            },
        ],
        "filing": {"portal_url": CIO_PORTAL, "free": True},
    }


# --- Notifications (in-app reminders) --------------------------------------------------------------


def notifications(c: AppContext, s: Session, user: User) -> list[dict[str, Any]]:
    rows = s.execute(
        select(Reminder, Case)
        .join(Case, Case.id == Reminder.case_id)
        .where(
            Case.user_id == user.id,
            Case.deleted_at.is_(None),
            Reminder.channel == "in_app",
            Reminder.status == "sent",
        )
        .order_by(Reminder.sent_at.desc())
        .limit(50)
    ).all()
    failed_email = {
        (r.case_id, r.kind)
        for r in s.scalars(
            select(Reminder)
            .join(Case, Case.id == Reminder.case_id)
            .where(Case.user_id == user.id, Reminder.channel == "email", Reminder.status == "failed")
        )
    }
    return [
        {
            "id": str(r.id),
            "case_id": str(case.id),
            "case_nickname": c.cipher.decrypt(case.nickname_enc),
            "kind": r.kind,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "read": r.read_at is not None,
            "email_failed": (r.case_id, r.kind) in failed_email,
            "path": f"/cases/{case.id}/track",
        }
        for r, case in rows
    ]


def mark_read(s: Session, user: User, reminder_id: uuid.UUID) -> None:
    r = s.scalar(
        select(Reminder)
        .join(Case, Case.id == Reminder.case_id)
        .where(Reminder.id == reminder_id, Case.user_id == user.id, Reminder.channel == "in_app")
    )
    if r is None:
        from claimsathi.core.errors import not_found

        raise not_found()
    r.read_at = r.read_at or now_utc()


# --- Sending due reminders (scheduler tick, FR-022 AC1) --------------------------------------------

REMINDER_EMAIL = {
    "en": {
        "subject": "ClaimSathi: {action}",
        "body": "Case: {nickname}\n\n{action}\n\nOpen your case: {link}\n\n"
        "You get these emails because you asked for deadline reminders. You can turn them off in Settings.",
        "eligibility_open": "You can now go to the Insurance Ombudsman.",
        "insurer_reply_check": "Did your insurer reply? Log it in ClaimSathi.",
        "limitation": "{days} days left to go to the Insurance Ombudsman.",
        "retention_notice": "This case has had no activity for 18 months. Open it within 30 days to keep it.",
    },
    "gu": {
        "subject": "ClaimSathi: {action}",
        "body": "કેસ: {nickname}\n\n{action}\n\nતમારો કેસ ખોલો: {link}\n\n"
        "તમે ડેડલાઇન રિમાઇન્ડર માંગ્યા હોવાથી આ ઇમેઇલ મળે છે. તમે તે સેટિંગ્સમાં બંધ કરી શકો છો.",
        "eligibility_open": "હવે તમે ઇન્શ્યોરન્સ ઓમ્બુડ્સમેન પાસે જઈ શકો છો.",
        "insurer_reply_check": "શું તમારી વીમા કંપનીએ જવાબ આપ્યો? તેની ClaimSathiમાં નોંધ કરો.",
        "limitation": "ઇન્શ્યોરન્સ ઓમ્બુડ્સમેન પાસે જવા માટે {days} દિવસ બાકી છે.",
        "retention_notice": "આ કેસમાં 18 મહિનાથી કોઈ પ્રવૃત્તિ નથી. તેને રાખવા માટે 30 દિવસમાં ખોલો.",
    },
    "hi": {
        "subject": "ClaimSathi: {action}",
        "body": "केस: {nickname}\n\n{action}\n\nअपना केस खोलें: {link}\n\n"
        "आपको ये ईमेल इसलिए मिल रहे हैं क्योंकि आपने डेडलाइन रिमाइंडर माँगे थे। आप इन्हें सेटिंग्स में बंद कर सकते हैं।",
        "eligibility_open": "अब आप इंश्योरेंस ओम्बड्समैन के पास जा सकते हैं।",
        "insurer_reply_check": "क्या आपकी बीमा कंपनी ने जवाब दिया? इसे ClaimSathi में दर्ज करें।",
        "limitation": "इंश्योरेंस ओम्बड्समैन के पास जाने के लिए {days} दिन बाकी हैं।",
        "retention_notice": "इस केस में 18 महीनों से कोई गतिविधि नहीं हुई है। इसे रखने के लिए 30 दिनों के अंदर खोलें।",
    },
}


def reminder_email(lang: str, kind: str, nickname: str, link: str) -> tuple[str, str]:
    t = REMINDER_EMAIL.get(lang, REMINDER_EMAIL["en"])
    action = t["limitation"].format(days=kind.split("_", 1)[1]) if kind.startswith("limitation_") else t[kind]
    return t["subject"].format(action=action), t["body"].format(nickname=nickname, action=action, link=link)


def send_due_reminders(c: AppContext, now: datetime | None = None, batch: int = 50) -> int:
    """Send each due reminder once. Rows are locked (SKIP LOCKED), so concurrent ticks never double-send."""
    now = now or now_utc()
    sent = 0
    with c.session_factory() as s:
        rows = s.execute(
            select(Reminder, Case, User)
            .join(Case, Case.id == Reminder.case_id)
            .join(User, User.id == Case.user_id)
            .where(Reminder.status == "scheduled", Reminder.send_at <= now)
            .order_by(Reminder.send_at)
            .limit(batch)
            .with_for_update(of=Reminder, skip_locked=True)
        ).all()
        for r, case, user in rows:
            if case.status != "open" or case.deleted_at is not None:
                r.status = "cancelled"
                continue
            if r.channel == "in_app":
                r.status, r.sent_at = "sent", now
                sent += 1
                continue
            if not wants_email_reminders(s, user.id):
                r.status = "cancelled"
                continue
            nickname = c.cipher.decrypt(case.nickname_enc)
            link = f"{c.settings.public_base_url}/{user.display_language}/cases/{case.id}/track"
            subject, body = reminder_email(user.display_language, r.kind, nickname, link)
            r.attempts += 1
            try:
                c.mailer.send(to=c.cipher.decrypt(user.email_enc), subject=subject, text=body)
            except Exception as exc:  # the class name only (allowlisted logs)
                log.warning("reminder_email_failed", error_code=type(exc).__name__)
                if r.attempts >= MAX_EMAIL_ATTEMPTS:
                    r.status = "failed"
                else:
                    r.send_at = now + EMAIL_RETRY_DELAY
                continue
            r.status, r.sent_at = "sent", now
            sent += 1
        s.commit()
    return sent
