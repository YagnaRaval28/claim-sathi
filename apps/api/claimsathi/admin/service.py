"""Admin console authentication and access (PRD FR-037, FR-042; system-design §3.3 "Admin").

Google proves the identity; the email must be on the admin allowlist; TOTP is mandatory on every sign-in.
Five wrong TOTP codes within 15 minutes lock the account for 15 minutes. Admin sessions use the `cs_admin`
cookie and last 8 hours at most. Consumer sessions never work on admin routes, and the reverse.
Every admin action is written to the audit log (ids only, no content).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.auth.service import email_hash
from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.models import AdminUser, AuditLog
from claimsathi.models import Session as DbSession
from claimsathi.security import totp
from claimsathi.security.crypto import new_token, normalize_email, sha256

ADMIN_SESSION = timedelta(hours=8)
MFA_TTL_S = 600
MFA_COOKIE = "cs_admin_mfa"
LOCK_AFTER = 5
LOCK_WINDOW = timedelta(minutes=15)
LOCK_FOR = timedelta(minutes=15)


def audit(s: Session, admin: AdminUser | None, action: str, entity: str, entity_id: str | None) -> None:
    s.add(
        AuditLog(
            actor_type="admin",
            actor_id=str(admin.id) if admin else None,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
        )
    )


def seed_bootstrap_admin(c: AppContext, s: Session) -> None:
    """ADMIN_BOOTSTRAP_EMAIL becomes the first admin (allowlist). No-op if unset or already present."""
    email = c.settings.admin_bootstrap_email
    if not email:
        return
    eh = email_hash(c, email)
    if s.scalar(select(AdminUser.id).where(AdminUser.email_hash == eh)) is None:
        s.add(AdminUser(email_hash=eh, email_enc=c.cipher.encrypt(normalize_email(email)), role="admin"))
        s.commit()


def allowlisted(c: AppContext, s: Session, *, subject: str, email: str) -> AdminUser | None:
    admin = s.scalar(select(AdminUser).where(AdminUser.google_sub == subject))
    if admin is None:
        admin = s.scalar(select(AdminUser).where(AdminUser.email_hash == email_hash(c, email)))
        if admin is not None and admin.google_sub is None:
            admin.google_sub = subject
    if admin is None or admin.disabled_at is not None:
        return None
    return admin


# --- the short-lived "Google done, TOTP pending" step ------------------------------------------------


def _sign(c: AppContext, body: str) -> str:
    key = c.settings.csrf_secret.get_secret_value().encode()
    return hmac.new(key, f"admin-mfa:{body}".encode(), hashlib.sha256).hexdigest()


def mfa_cookie(c: AppContext, admin: AdminUser) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"a": str(admin.id), "e": int(time.time()) + MFA_TTL_S}).encode())
    text = body.decode().rstrip("=")
    return f"{text}.{_sign(c, text)}"


def pending_admin(c: AppContext, s: Session, cookie: str | None) -> AdminUser:
    bad = AppError("unauthenticated", 401, "Please sign in again.")
    if not cookie or "." not in cookie:
        raise bad
    body, sig = cookie.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(c, body)):
        raise bad
    data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    if data.get("e", 0) < time.time():
        raise bad
    admin = s.get(AdminUser, uuid.UUID(str(data["a"])))
    if admin is None or admin.disabled_at is not None:
        raise bad
    return admin


def mfa_setup(c: AppContext, s: Session, admin: AdminUser) -> dict[str, Any]:
    """First sign-in: create (or reuse) an unconfirmed secret and return what the authenticator app needs."""
    if admin.totp_enabled_at is not None:
        return {"enrolled": True}
    if admin.totp_secret_enc is None:
        admin.totp_secret_enc = c.cipher.encrypt(totp.new_secret())
        s.commit()
    secret = c.cipher.decrypt(admin.totp_secret_enc)
    account = c.cipher.decrypt(admin.email_enc)
    return {"enrolled": False, "secret": secret, "otpauth_uri": totp.provisioning_uri(secret, account)}


def verify_totp(c: AppContext, s: Session, admin: AdminUser, code: str) -> str:
    """Checks the TOTP code with lockout; returns a new admin session token (FR-037 AC2: no MFA, no sign-in)."""
    now = now_utc()
    if admin.locked_until and admin.locked_until > now:
        raise AppError("rate_limited", 429, "Too many wrong codes. Try again in 15 minutes.")
    if admin.totp_secret_enc is None:
        raise AppError("unauthenticated", 401, "Set up your authenticator first.")
    if not totp.verify(c.cipher.decrypt(admin.totp_secret_enc), code):
        if admin.first_failed_at is None or now - admin.first_failed_at > LOCK_WINDOW:
            admin.first_failed_at, admin.failed_totp = now, 0
        admin.failed_totp += 1
        if admin.failed_totp >= LOCK_AFTER:
            admin.locked_until, admin.failed_totp, admin.first_failed_at = now + LOCK_FOR, 0, None
            audit(s, admin, "admin_totp_locked", "admin_user", str(admin.id))
        s.commit()
        raise AppError("totp_invalid", 401, "That code isn't right.")
    admin.failed_totp, admin.first_failed_at, admin.locked_until = 0, None, None
    if admin.totp_enabled_at is None:
        admin.totp_enabled_at = now
        audit(s, admin, "admin_totp_enrolled", "admin_user", str(admin.id))
    token = new_token()
    s.add(
        DbSession(
            token_hash=sha256(token.encode()),
            kind="admin",
            admin_user_id=admin.id,
            idle_expires_at=now + ADMIN_SESSION,
            absolute_expires_at=now + ADMIN_SESSION,
        )
    )
    audit(s, admin, "admin_signed_in", "admin_user", str(admin.id))
    s.commit()
    return token


def admin_for_session(c: AppContext, s: Session, token: str | None) -> tuple[AdminUser, DbSession]:
    if not token:
        raise AppError("unauthenticated", 401, "Please sign in.")
    row = s.scalar(select(DbSession).where(DbSession.token_hash == sha256(token.encode()), DbSession.kind == "admin"))
    now = now_utc()
    if row is None or row.revoked_at is not None or row.absolute_expires_at <= now or row.admin_user_id is None:
        raise AppError("unauthenticated", 401, "Your session has ended. Please sign in again.")
    admin = s.get(AdminUser, row.admin_user_id)
    if admin is None or admin.disabled_at is not None:
        raise AppError("unauthenticated", 401, "Please sign in.")
    return admin, row
