"""Deterministic regulatory checks that need only confirmed facts and a confirmed category (PRD FR-016):
RULE-MC-02 (repudiation → ask for the claims review committee's approval), RULE-MC-03 (moratorium after
60 months of continuous cover), RULE-MC-05 (documents the insurer should collect itself). Pure functions.
"""

from __future__ import annotations

from datetime import date

from claimsathi.rules.escalation import add_months


def full_months(start: date, end: date) -> int:
    """Completed calendar months from `start` to `end` (same-day-or-month-end rule, as for deadlines)."""
    if end < start:
        return -full_months(end, start)
    months = (end.year - start.year) * 12 + (end.month - start.month)
    while months > 0 and add_months(start, months) > end:
        months -= 1
    return months


def moratorium_applies(category: str | None, inception: date | None, admission: date | None, min_months: int) -> bool:
    """RULE-MC-03 fires only with a qualifying category and both dates known (FR-016 AC1)."""
    if category not in ("non_disclosure", "ped_waiting") or inception is None or admission is None:
        return False
    return full_months(inception, admission) >= min_months
