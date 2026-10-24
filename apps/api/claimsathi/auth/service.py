"""Email-code sign-in and sessions (PRD FR-001, FR-003; system-design §3.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.guards import hit
from claimsathi.models import EmailChallenge, User
from claimsathi.models import Session as DbSession
from claimsathi.security.crypto import (
    constant_time_equal,
    keyed_hash,
    new_token,
    normalize_email,
    sha256,
    six_digit_code,
)

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
ABSOLUTE = timedelta(days=90)

CODE_EMAIL = {
    "en": (
        "Your ClaimSathi sign-in code",
        "Your ClaimSathi sign-in code is {code}.\nIt expires in 10 minutes.\n\n"
        "If you did not ask for this code, you can ignore this email.",
    ),
    "gu": (
        "તમારો ClaimSathi સાઇન-ઇન કોડ",
        "તમારો ClaimSathi સાઇન-ઇન કોડ {code} છે.\nતે 10 મિનિટમાં સમાપ્ત થશે.\n\nજો તમે આ કોડ માંગ્યો ન હોય, તો આ ઇમેઇલને અવગણો.",
    ),
    "hi": (
        "आपका ClaimSathi साइन-इन कोड",
        "आपका ClaimSathi साइन-इन कोड {code} है।\nयह 10 मिनट में समाप्त हो जाएगा।\n\n"
        "अगर आपने यह कोड नहीं माँगा था, तो इस ईमेल को अनदेखा करें।",
    ),
}


def _code_hash(c: AppContext, challenge_id: uuid.UUID, code: str) -> bytes:
    return keyed_hash(c.settings.code_pepper.get_secret_value(), f"{challenge_id}:{code}")


def email_hash(c: AppContext, email: str) -> bytes:
    return keyed_hash(c.settings.hash_pepper.get_secret_value(), normalize_email(email))


def request_code(c: AppContext, s: Session, *, email: str, ip_hash: str, language: str) -> None:
    eh = email_hash(c, email)
    hit(s, f"code_req:email:{eh.hex()}", limit=5, window=timedelta(hours=1))
    hit(s, f"code_req:ip:{ip_hash}", limit=c.settings.code_requests_per_ip_per_hour, window=timedelta(hours=1))
    hit(s, "code_req:global", limit=500, window=timedelta(days=1))
    challenge = EmailChallenge(id=uuid.uuid4(), email_hash=eh, code_hash=b"", expires_at=now_utc() + CODE_TTL)
    code = six_digit_code()
    challenge.code_hash = _code_hash(c, challenge.id, code)
    s.add(challenge)
    s.commit()
    subject, body = CODE_EMAIL.get(language, CODE_EMAIL["en"])
    c.mailer.send(to=normalize_email(email), subject=subject, text=body.format(code=code))


@dataclass(frozen=True)
class SignInResult:
    user: User
    session_token: str
    is_new: bool


def verify_code(c: AppContext, s: Session, *, email: str, code: str, trusted: bool, ip_hash: str) -> SignInResult:
    hit(s, f"code_verify:ip:{ip_hash}", limit=c.settings.code_verifies_per_ip_per_hour, window=timedelta(hours=1))
    eh = email_hash(c, email)
    ch = s.scalar(
        select(EmailChallenge)
        .where(
            EmailChallenge.email_hash == eh, EmailChallenge.purpose == "sign_in", EmailChallenge.consumed_at.is_(None)
        )
        .order_by(EmailChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    now = now_utc()
    if ch is None or ch.attempts >= MAX_ATTEMPTS:
        raise AppError(
            "email_code_invalid", 401, "That code isn't right. Request a new code.", extra={"attempts_left": 0}
        )
    if ch.expires_at <= now:
        raise AppError("email_code_expired", 410, "This code has expired. Send a new one.")
    ch.attempts += 1
    if not constant_time_equal(ch.code_hash, _code_hash(c, ch.id, code)):
        left = MAX_ATTEMPTS - ch.attempts
        s.commit()
        raise AppError("email_code_invalid", 401, "That code isn't right.", extra={"attempts_left": left})
    ch.consumed_at = now
    user, is_new = user_for_verified_email(c, s, email)
    token = new_session(s, user, trusted=trusted)
    s.commit()
    return SignInResult(user=user, session_token=token, is_new=is_new)


def user_for_verified_email(c: AppContext, s: Session, email: str) -> tuple[User, bool]:
    """Account linking (system-design §3.3 step 7): one user per verified email, whichever way they sign in."""
    eh = email_hash(c, email)
    user = s.scalar(select(User).where(User.email_hash == eh))
    if user is not None:
        return user, False
    user = User(email_hash=eh, email_enc=c.cipher.encrypt(normalize_email(email)), email_verified_at=now_utc())
    s.add(user)
    s.flush()
    return user, True


def new_session(s: Session, user: User, *, trusted: bool) -> str:
    now = now_utc()
    token = new_token()
    s.add(
        DbSession(
            token_hash=sha256(token.encode()),
            user_id=user.id,
            trusted=trusted,
            idle_expires_at=now + (timedelta(days=30) if trusted else timedelta(hours=24)),
            absolute_expires_at=now + ABSOLUTE,
        )
    )
    return token


def revoke_session(s: Session, session_id: uuid.UUID) -> None:
    s.execute(update(DbSession).where(DbSession.id == session_id).values(revoked_at=now_utc()))
    s.commit()


def revoke_all(s: Session, user_id: uuid.UUID) -> None:
    s.execute(
        update(DbSession)
        .where(DbSession.user_id == user_id, DbSession.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    s.commit()
