"""Postgres fixed-window rate limiter and Idempotency-Key replay (system-design §5.1, §5.5)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.models import IdempotencyKey, RateLimitBucket


def _window_start(now: datetime, window: timedelta) -> datetime:
    epoch = int(now.timestamp())
    size = int(window.total_seconds())
    return datetime.fromtimestamp(epoch - epoch % size, tz=now.tzinfo)


def hit(session: Session, key: str, *, limit: int, window: timedelta) -> None:
    """Count a hit; raise 429 once `limit` is exceeded within the window."""
    now = now_utc()
    start = _window_start(now, window)
    stmt = (
        insert(RateLimitBucket)
        .values(bucket_key=key, window_start=start, count=1)
        .on_conflict_do_update(index_elements=["bucket_key", "window_start"], set_={"count": RateLimitBucket.count + 1})
        .returning(RateLimitBucket.count)
    )
    count = session.execute(stmt).scalar_one()
    session.commit()
    if count > limit:
        retry = int((start + window - now).total_seconds()) + 1
        raise AppError(
            "rate_limited",
            429,
            "Too many attempts. Please wait and try again.",
            extra={"retry_after_s": retry},
            headers={"Retry-After": str(retry)},
        )


def request_hash(body: Any) -> bytes:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).digest()


def idempotent_replay(
    session: Session, scope_id: uuid.UUID, key: str | None, body: Any
) -> tuple[int, dict[str, Any]] | None:
    """Return the stored (status, response) for a repeated key, raise 409 on body mismatch, else None."""
    if not key:
        raise AppError(
            "validation_error",
            422,
            "Idempotency-Key header is required.",
            errors=[{"field": "Idempotency-Key", "code": "missing", "message": "required"}],
        )
    if len(key) > 64:
        raise AppError("validation_error", 422, "Idempotency-Key is too long.")
    row = session.get(IdempotencyKey, (scope_id, key))
    if row is None:
        return None
    if row.request_sha256 != request_hash(body):
        raise AppError("idempotency_key_reused", 409, "This request key was already used for a different request.")
    return row.status_code, row.response


def idempotent_store(
    session: Session, scope_id: uuid.UUID, key: str, body: Any, status: int, response: dict[str, Any]
) -> None:
    if (
        session.scalar(select(IdempotencyKey.key).where(IdempotencyKey.scope_id == scope_id, IdempotencyKey.key == key))
        is None
    ):
        session.add(
            IdempotencyKey(
                scope_id=scope_id, key=key, request_sha256=request_hash(body), status_code=status, response=response
            )
        )
