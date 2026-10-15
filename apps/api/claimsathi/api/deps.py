"""Request dependencies: DB session, current user, CSRF, consent and case ownership (system-design §3.4)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError, not_found
from claimsathi.models import Case, Consent, ConsentVersion, User
from claimsathi.models import Session as DbSession
from claimsathi.security.crypto import constant_time_equal, sha256

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
IDLE = timedelta(hours=24)
IDLE_TRUSTED = timedelta(days=30)


def ctx(request: Request) -> AppContext:
    c: AppContext = request.app.state.ctx
    return c


def db(c: AppContext = Depends(ctx)) -> Iterator[Session]:
    s = c.session_factory()
    try:
        yield s
    finally:
        s.close()


def csrf(request: Request, c: AppContext = Depends(ctx)) -> None:
    """Double-submit token + Origin check on unsafe methods."""
    if request.method not in UNSAFE:
        return
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != c.settings.public_base_url.rstrip("/"):
        raise AppError("csrf_failed", 403, "Request origin not allowed.")
    cookie = request.cookies.get(c.settings.csrf_cookie_name, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not constant_time_equal(cookie.encode(), header.encode()):
        raise AppError("csrf_failed", 403, "Security check failed. Reload the page and try again.")


def current_user(request: Request, c: AppContext = Depends(ctx), s: Session = Depends(db)) -> User:
    token = request.cookies.get(c.settings.session_cookie_name)
    if not token:
        raise AppError("unauthenticated", 401, "Please sign in.")
    row = s.scalar(select(DbSession).where(DbSession.token_hash == sha256(token.encode()), DbSession.kind == "user"))
    now = now_utc()
    if row is None or row.revoked_at is not None or row.idle_expires_at <= now or row.absolute_expires_at <= now:
        raise AppError("unauthenticated", 401, "Your session has ended. Please sign in again.")
    row.last_seen_at = now
    row.idle_expires_at = min(now + (IDLE_TRUSTED if row.trusted else IDLE), row.absolute_expires_at)
    user = s.get(User, row.user_id)
    if user is None:
        raise AppError("unauthenticated", 401, "Please sign in.")
    request.state.session_id = row.id
    s.commit()
    return user


def current_consent_version(s: Session) -> ConsentVersion:
    v = s.scalar(select(ConsentVersion).order_by(ConsentVersion.published_at.desc()).limit(1))
    if v is None:
        raise AppError("internal_error", 500, "Consent notice not configured.")
    return v


def has_processing_consent(s: Session, user_id: uuid.UUID) -> bool:
    version = current_consent_version(s).version
    row = s.scalar(
        select(Consent)
        .where(Consent.user_id == user_id, Consent.version == version, Consent.withdrawn_at.is_(None))
        .order_by(Consent.granted_at.desc())
    )
    return row is not None and "processing" in row.purposes


def consented_user(user: User = Depends(current_user), s: Session = Depends(db)) -> User:
    if not has_processing_consent(s, user.id):
        raise AppError("consent_required", 403, "Please review and accept the privacy notice first.")
    return user


def owned_case(case_id: uuid.UUID, user: User = Depends(current_user), s: Session = Depends(db)) -> Case:
    case = s.scalar(select(Case).where(Case.id == case_id, Case.user_id == user.id, Case.deleted_at.is_(None)))
    if case is None:
        raise not_found()
    return case
