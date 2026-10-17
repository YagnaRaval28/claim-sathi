"""Deterministic escalation rules and deadline maths (PRD FR-020 AC1/AC3, FR-021 AC1, FR-022)."""

from __future__ import annotations

from datetime import date

import pytest

from claimsathi.rules.escalation import (
    CaseFacts,
    Event,
    Params,
    add_months,
    add_years,
    blocked,
    compute_deadlines,
    derive_stage,
    ombudsman_checks,
    plan_reminders,
)

P = Params()
FACTS = CaseFacts(in_litigation="no", relation="self", complainant_name="Ravi K. Mehta", disputed_paise=5_432_000)


@pytest.mark.req("FR-021")
@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),  # day does not exist: last day of the month
        (date(2028, 1, 31), 1, date(2028, 2, 29)),  # leap year
        (date(2026, 3, 31), 1, date(2026, 4, 30)),
        (date(2026, 10, 15), 1, date(2026, 11, 15)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),  # year rollover
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
    ],
)
def test_add_months_same_day_or_month_end(start: date, months: int, expected: date) -> None:
    assert add_months(start, months) == expected


@pytest.mark.req("FR-021")
def test_add_years_on_29_february() -> None:
    assert add_years(date(2028, 2, 29), 1) == date(2029, 2, 28)
    assert add_years(date(2028, 2, 29), 4) == date(2032, 2, 29)


def _dl(events: list[Event]) -> dict[str, date]:
    return {d.kind: d.due_date for d in compute_deadlines(events, P)}


@pytest.mark.req("FR-021")
def test_deadlines_without_reply() -> None:
    d = _dl([Event("s1_sent", date(2026, 1, 31), {"method": "email"})])
    assert d == {
        "insurer_response_expected": date(2026, 2, 14),
        "ombudsman_eligible_from": date(2026, 2, 28),
        "ombudsman_limitation": date(2027, 2, 28),
    }


@pytest.mark.req("FR-021")
def test_unsatisfactory_reply_opens_eligibility_and_restarts_limitation() -> None:
    d = _dl([Event("s1_sent", date(2026, 10, 1)), Event("insurer_reply", date(2026, 10, 10), {"satisfied": False})])
    assert d["ombudsman_eligible_from"] == date(2026, 10, 10)
    assert d["ombudsman_limitation"] == date(2027, 10, 10)
    assert "insurer_response_expected" not in d


def test_no_deadlines_before_the_letter_is_sent_and_award_after_filing() -> None:
    assert compute_deadlines([], P) == []
    d = _dl([Event("s1_sent", date(2026, 1, 1)), Event("s3_filed", date(2026, 3, 1))])
    assert d["ombudsman_award_expected"] == date(2026, 6, 1)


def _check(events: list[Event], today: date, facts: CaseFacts = FACTS) -> dict[str, str]:
    return {c.rule_key: c.result for c in ombudsman_checks(events, facts, today, P)}


@pytest.mark.req("FR-020")
def test_esc01_and_esc02_block_until_written_and_a_month_passes() -> None:
    assert _check([], date(2026, 10, 15))["RULE-ESC-01"] == "block"
    sent = [Event("s1_sent", date(2026, 10, 15))]
    r = _check(sent, date(2026, 11, 14))
    assert r["RULE-ESC-01"] == "pass" and r["RULE-ESC-02"] == "block"
    assert _check(sent, date(2026, 11, 15))["RULE-ESC-02"] == "pass"


@pytest.mark.req("FR-020")
def test_esc02_reply_paths() -> None:
    unhappy = [Event("s1_sent", date(2026, 10, 1)), Event("insurer_reply", date(2026, 10, 5), {"satisfied": False})]
    assert _check(unhappy, date(2026, 10, 6))["RULE-ESC-02"] == "pass"
    happy = [Event("s1_sent", date(2026, 10, 1)), Event("insurer_reply", date(2026, 10, 5), {"satisfied": True})]
    assert _check(happy, date(2027, 1, 1))["RULE-ESC-02"] == "block"


@pytest.mark.req("FR-020")
def test_esc03_warns_but_does_not_block_when_late() -> None:
    sent = [Event("s1_sent", date(2025, 1, 10))]
    checks = ombudsman_checks(sent, FACTS, date(2026, 2, 11), P)
    r = {c.rule_key: c.result for c in checks}
    assert r["RULE-ESC-03"] == "warn" and not blocked(checks)
    assert _check(sent, date(2026, 2, 10))["RULE-ESC-03"] == "pass"  # last day is still in time


@pytest.mark.req("FR-020")
def test_esc04_blocks_only_when_in_court() -> None:
    sent = [Event("s1_sent", date(2026, 1, 1))]
    for answer, expected in (("yes", "block"), ("no", "pass"), ("not_sure", "pass")):
        facts = CaseFacts(answer, "self", "R", 100)
        assert _check(sent, date(2026, 3, 1), facts)["RULE-ESC-04"] == expected


@pytest.mark.req("FR-020")
def test_esc05_warns_above_fifty_lakh_and_esc06_informs_helpers() -> None:
    sent = [Event("s1_sent", date(2026, 1, 1))]
    big = CaseFacts("no", "self", "R", 50_00_000 * 100 + 1)
    assert _check(sent, date(2026, 3, 1), big)["RULE-ESC-05"] == "warn"
    assert _check(sent, date(2026, 3, 1))["RULE-ESC-05"] == "pass"
    helper = CaseFacts("no", "parent", "Ravi K. Mehta", 100)
    esc06 = next(c for c in ombudsman_checks(sent, helper, date(2026, 3, 1), P) if c.rule_key == "RULE-ESC-06")
    assert esc06.result == "inform" and esc06.params["name"] == "Ravi K. Mehta"


@pytest.mark.req("FR-020")
def test_bima_bharosa_is_optional_for_ombudsman_eligibility() -> None:
    base = [Event("s1_sent", date(2026, 1, 1))]
    with_s2 = [*base, Event("s2_filed", date(2026, 1, 5))]
    assert _check(base, date(2026, 3, 1)) == _check(with_s2, date(2026, 3, 1))
    assert not blocked(ombudsman_checks(base, FACTS, date(2026, 3, 1), P))


def test_disabled_rule_is_unavailable_and_blocks() -> None:
    sent = [Event("s1_sent", date(2026, 1, 1))]
    checks = ombudsman_checks(sent, FACTS, date(2026, 3, 1), P, enabled={"RULE-ESC-01"})
    assert blocked(checks) and {c.result for c in checks if c.rule_key != "RULE-ESC-01"} == {"unavailable"}


def test_block_rows_sort_first() -> None:
    results = [c.result for c in ombudsman_checks([], CaseFacts("yes", "parent", "R", 1), date(2026, 1, 1), P)]
    assert results[:3] == ["block", "block", "block"]


def test_stage_derivation() -> None:
    assert derive_stage([]) == ("S0_PREPARE", "open", None)
    s1 = Event("s1_sent", date(2026, 1, 1))
    assert derive_stage([s1])[0] == "S1_INSURER_GRIEVANCE"
    s2 = Event("s2_filed", date(2026, 1, 3))
    assert derive_stage([s1, s2]) == ("S1_INSURER_GRIEVANCE", "open", date(2026, 1, 3))  # parallel flag
    assert derive_stage([s1, Event("s3_filed", date(2026, 3, 1))])[0] == "S3_OMBUDSMAN"
    assert derive_stage([s1, Event("closed", date(2026, 3, 1))])[:2] == ("CLOSED", "closed")


@pytest.mark.req("FR-022")
def test_reminder_plan_skips_past_dates() -> None:
    deadlines = compute_deadlines([Event("s1_sent", date(2026, 10, 15))], P)
    kinds = {r.kind: r.send_at.date() for r in plan_reminders(deadlines, date(2026, 10, 16))}
    assert kinds["insurer_reply_check"] == date(2026, 10, 29)
    assert kinds["eligibility_open"] == date(2026, 11, 15)
    assert kinds["limitation_60"] == date(2027, 9, 16) and kinds["limitation_3"] == date(2027, 11, 12)
    later = {r.kind for r in plan_reminders(deadlines, date(2026, 11, 20))}
    assert "eligibility_open" not in later and "insurer_reply_check" not in later
