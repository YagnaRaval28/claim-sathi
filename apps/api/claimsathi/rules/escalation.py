"""Escalation rules and deadline maths (PRD FR-020, FR-021, FR-022). Pure functions: no database, no model.

Interpretation recorded in the rules table (RULE-DEADLINES) and pending legal confirmation (OQ-10):
"one month" is the same day number in the next calendar month, or that month's last day if the day does not
exist. "One year" is twelve such months. All dates are IST calendar dates.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from claimsathi.core.clock import IST

Result = Literal["pass", "block", "warn", "inform", "unavailable"]
ESC_RULES = ("RULE-ESC-01", "RULE-ESC-02", "RULE-ESC-03", "RULE-ESC-04", "RULE-ESC-05", "RULE-ESC-06")
LIMITATION_REMINDER_DAYS = (60, 30, 14, 3)
REMINDER_HOUR_IST = 9


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def add_years(d: date, years: int) -> date:
    return add_months(d, 12 * years)


@dataclass(frozen=True)
class Event:
    kind: str
    event_date: date
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Params:
    """From the rules table. Defaults mirror the seeded RULE-DEADLINES and RULE-ESC-05 values."""

    insurer_response_days: int = 14  # VERIFY-PRIMARY (OQ-05)
    eligibility_months: int = 1  # Rule 14(3)(a)
    limitation_years: int = 1  # Rule 14(3)(b)
    award_months: int = 3  # Rule 17(4), informational
    amount_cap_paise: int = 50_00_000 * 100  # Rule 17(3): ₹50 lakh


@dataclass(frozen=True)
class DeadlineOut:
    kind: str
    due_date: date
    rule_key: str
    computed_from: dict[str, str]


@dataclass(frozen=True)
class Check:
    rule_key: str
    result: Result
    message_key: str
    params: dict[str, str] = field(default_factory=dict)
    fix_action: str | None = None


def _latest(events: list[Event], kind: str, on_or_after: date | None = None) -> Event | None:
    found = [e for e in events if e.kind == kind and (on_or_after is None or e.event_date >= on_or_after)]
    return max(found, key=lambda e: e.event_date) if found else None


@dataclass(frozen=True)
class Timeline:
    s1: Event | None
    reply: Event | None
    s3: Event | None

    @property
    def satisfied(self) -> bool:
        return bool(self.reply and self.reply.meta.get("satisfied") is True)


def timeline(events: list[Event]) -> Timeline:
    s1 = _latest(events, "s1_sent")
    reply = _latest(events, "insurer_reply", s1.event_date) if s1 else None
    return Timeline(s1=s1, reply=reply, s3=_latest(events, "s3_filed"))


def eligible_from(t: Timeline, p: Params) -> date | None:
    """Rule 14(3)(a): the insurer rejected or replied unsatisfactorily, or one month passed without a reply."""
    if t.s1 is None or t.satisfied:
        return None
    month_end = add_months(t.s1.event_date, p.eligibility_months)
    if t.reply is not None and t.reply.event_date < month_end:
        return t.reply.event_date
    return month_end


def limitation(t: Timeline, p: Params) -> tuple[date, str] | None:
    """Rule 14(3)(b): one year from the insurer's reply, or from the expiry of the one month."""
    if t.s1 is None:
        return None
    if t.reply is not None:
        return add_years(t.reply.event_date, p.limitation_years), "insurer_reply"
    return add_years(add_months(t.s1.event_date, p.eligibility_months), p.limitation_years), "one_month_expiry"


def compute_deadlines(events: list[Event], p: Params) -> list[DeadlineOut]:
    t = timeline(events)
    out: list[DeadlineOut] = []
    if t.s1 is None:
        return out
    s1 = t.s1.event_date.isoformat()
    if t.reply is None:
        out.append(
            DeadlineOut(
                "insurer_response_expected",
                t.s1.event_date + timedelta(days=p.insurer_response_days),
                "RULE-DEADLINES",
                {"s1_sent": s1},
            )
        )
    ef = eligible_from(t, p)
    if ef is not None:
        basis = {"s1_sent": s1, **({"insurer_reply": t.reply.event_date.isoformat()} if t.reply else {})}
        out.append(DeadlineOut("ombudsman_eligible_from", ef, "RULE-ESC-02", basis))
    lim = limitation(t, p)
    if lim is not None and not t.satisfied:
        due, basis_kind = lim
        basis = {"s1_sent": s1, "basis": basis_kind}
        if t.reply:
            basis["insurer_reply"] = t.reply.event_date.isoformat()
        out.append(DeadlineOut("ombudsman_limitation", due, "RULE-ESC-03", basis))
    if t.s3 is not None:
        out.append(
            DeadlineOut(
                "ombudsman_award_expected",
                add_months(t.s3.event_date, p.award_months),
                "RULE-DEADLINES",
                {"s3_filed": t.s3.event_date.isoformat()},
            )
        )
    return out


@dataclass(frozen=True)
class CaseFacts:
    in_litigation: str  # FR-006 Q5: yes / no / not_sure
    relation: str  # FR-006 Q4: self / spouse / parent / child / other
    complainant_name: str
    disputed_paise: int | None


def ombudsman_checks(
    events: list[Event], facts: CaseFacts, today: date, p: Params, enabled: set[str] | None = None
) -> list[Check]:
    """RULE-ESC-01 to 06 (PRD FR-020). A rule that is not enabled is "unavailable", which blocks like a failure."""
    t = timeline(events)
    checks: list[Check] = []

    def add(c: Check) -> None:
        if enabled is not None and c.rule_key not in enabled:
            checks.append(Check(c.rule_key, "unavailable", "rule_unavailable"))
        else:
            checks.append(c)

    if t.s1 is None:
        add(Check("RULE-ESC-01", "block", "write_first", fix_action="log_s1_sent"))
    else:
        add(Check("RULE-ESC-01", "pass", "wrote_on", {"date": t.s1.event_date.isoformat()}))

    ef = eligible_from(t, p)
    if t.s1 is None:
        add(Check("RULE-ESC-02", "block", "write_first", fix_action="log_s1_sent"))
    elif t.satisfied:
        add(Check("RULE-ESC-02", "block", "satisfied_with_reply", fix_action="log_insurer_reply"))
    elif ef is not None and today >= ef:
        add(Check("RULE-ESC-02", "pass", "eligible_since", {"date": ef.isoformat()}))
    else:
        params = {"date": ef.isoformat()} if ef else {}
        add(Check("RULE-ESC-02", "block", "wait_for_insurer", params, fix_action="log_insurer_reply"))

    lim = limitation(t, p)
    if lim is None or t.satisfied:
        add(Check("RULE-ESC-03", "pass", "limitation_not_started"))
    elif today <= lim[0]:
        add(Check("RULE-ESC-03", "pass", "file_by", {"date": lim[0].isoformat()}))
    else:
        add(Check("RULE-ESC-03", "warn", "late", {"date": lim[0].isoformat()}))

    if facts.in_litigation == "yes":
        add(Check("RULE-ESC-04", "block", "in_court"))
    else:
        add(Check("RULE-ESC-04", "pass", "not_in_court"))

    if facts.disputed_paise is not None and facts.disputed_paise > p.amount_cap_paise:
        add(Check("RULE-ESC-05", "warn", "above_cap"))
    else:
        add(Check("RULE-ESC-05", "pass", "within_cap"))

    if facts.relation != "self":
        add(Check("RULE-ESC-06", "inform", "complainant_must_sign", {"name": facts.complainant_name}))
    else:
        add(Check("RULE-ESC-06", "pass", "you_sign"))

    order = {"block": 0, "unavailable": 0, "warn": 1, "inform": 2, "pass": 3}
    return sorted(checks, key=lambda c: order[c.result])


def blocked(checks: list[Check]) -> bool:
    return any(c.result in ("block", "unavailable") for c in checks)


def derive_stage(events: list[Event]) -> tuple[str, str, date | None]:
    """(stage, status, s2_filed_at) from the logged events (system-design §3.5)."""
    kinds = {e.kind for e in events}
    s2 = _latest(events, "s2_filed")
    if "closed" in kinds:
        return "CLOSED", "closed", s2.event_date if s2 else None
    stage = "S3_OMBUDSMAN" if "s3_filed" in kinds else "S1_INSURER_GRIEVANCE" if "s1_sent" in kinds else "S0_PREPARE"
    return stage, "open", s2.event_date if s2 else None


@dataclass(frozen=True)
class PlannedReminder:
    kind: str
    deadline_kind: str
    send_at: datetime


def plan_reminders(deadlines: list[DeadlineOut], today: date) -> list[PlannedReminder]:
    """FR-022: eligibility opening; 60/30/14/3 days before the limitation date; the expected insurer reply.
    Reminders whose date has already passed are not scheduled."""

    def at(d: date) -> datetime:
        return datetime.combine(d, time(REMINDER_HOUR_IST), tzinfo=IST)

    out: list[PlannedReminder] = []
    for d in deadlines:
        if d.kind == "ombudsman_eligible_from" and d.due_date >= today:
            out.append(PlannedReminder("eligibility_open", d.kind, at(d.due_date)))
        elif d.kind == "insurer_response_expected" and d.due_date >= today:
            out.append(PlannedReminder("insurer_reply_check", d.kind, at(d.due_date)))
        elif d.kind == "ombudsman_limitation":
            for n in LIMITATION_REMINDER_DAYS:
                when = d.due_date - timedelta(days=n)
                if when >= today:
                    out.append(PlannedReminder(f"limitation_{n}", d.kind, at(when)))
    return out
