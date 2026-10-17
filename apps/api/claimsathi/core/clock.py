"""Injectable clock. Rules code must never call datetime.now() directly (engineering standards §5)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def _system_now() -> datetime:
    return datetime.now(UTC)


_now: Callable[[], datetime] = _system_now


def now_utc() -> datetime:
    return _now()


def today_ist() -> date:
    return _now().astimezone(IST).date()


def set_clock(fn: Callable[[], datetime] | None) -> None:
    """Tests only: freeze or advance time."""
    global _now
    _now = fn or (lambda: datetime.now(UTC))
