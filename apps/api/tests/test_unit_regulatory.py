"""RULE-MC-03 moratorium arithmetic (PRD FR-016 AC1: fires at 61 months, not at 59 or with a date unknown)."""

from __future__ import annotations

from datetime import date

import pytest

from claimsathi.rules.regulatory import full_months, moratorium_applies


@pytest.mark.parametrize(
    ("start", "end", "months"),
    [
        (date(2020, 4, 1), date(2026, 6, 10), 74),
        (date(2021, 1, 31), date(2021, 2, 28), 1),  # month end
        (date(2021, 1, 31), date(2021, 2, 27), 0),
        (date(2020, 2, 29), date(2025, 2, 28), 60),  # leap day: Feb 28 is the anniversary
        (date(2026, 1, 1), date(2026, 1, 1), 0),
    ],
)
def test_full_months(start: date, end: date, months: int) -> None:
    assert full_months(start, end) == months


@pytest.mark.req("FR-016")
def test_moratorium_fires_at_61_not_59_or_unknown() -> None:
    admission = date(2026, 6, 10)
    assert moratorium_applies("non_disclosure", date(2021, 5, 10), admission, 60)  # 61 months
    assert not moratorium_applies("non_disclosure", date(2021, 7, 10), admission, 60)  # 59 months
    assert moratorium_applies("ped_waiting", date(2021, 6, 10), admission, 60)  # exactly 60
    assert not moratorium_applies("non_disclosure", None, admission, 60)
    assert not moratorium_applies("non_disclosure", date(2015, 1, 1), None, 60)
    assert not moratorium_applies("exclusion", date(2015, 1, 1), admission, 60)
