"""Google sign-in (PRD FR-002, system-design §3.3): OpenID Connect authorization-code flow with PKCE.

`state`, the nonce and the PKCE verifier live in a signed, HttpOnly cookie for 10 minutes. The ID token comes
straight from Google's token endpoint over TLS, so (OIDC Core 3.1.3.7) its issuer, audience, expiry and nonce
are checked; `email_verified` must be true. The same verified email as an email-code account means the same user.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.auth.service import new_session, user_for_verified_email
from claimsathi.context import AppContext
from claimsathi.models import OAuthIdentity, User

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
EXCHANGE_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
STATE_TTL_S = 600
COOKIE = "cs_oauth"
LANGS = ("en", "gu", "hi")


class GoogleSignInError(Exception):
    """Any failure in the flow. The caller sends the user back to sign-in; details are never shown or logged."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(c: AppContext, body: str) -> str:
    key = c.settings.csrf_secret.get_secret_value().encode()
    return hmac.new(key, f"oauth:{body}".encode(), hashlib.sha256).hexdigest()


def redirect_uri(c: AppContext) -> str:
    return f"{c.settings.public_base_url}/api/v1/auth/google/callback"


def start(c: AppContext, lang: str) -> tuple[str, str]:
    """Returns (Google authorization URL, signed state cookie value)."""
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    body = _b64(
        json.dumps(
            {
                "s": state,
                "n": nonce,
                "v": verifier,
                "l": lang if lang in LANGS else "en",
                "e": int(time.time()) + STATE_TTL_S,
            }
        ).encode()
    )
    params = {
        "client_id": c.settings.google_oauth_client_id,
        "redirect_uri": redirect_uri(c),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "nonce": nonce,
        "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urlencode(params)}", f"{body}.{_sign(c, body)}"


def read_state(c: AppContext, cookie: str | None, state: str | None) -> dict[str, Any]:
    if not cookie or not state or "." not in cookie:
        raise GoogleSignInError("state")
    body, sig = cookie.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(c, body)):
        raise GoogleSignInError("state")
    data: dict[str, Any] = json.loads(_unb64(body))
    if data.get("e", 0) < time.time() or not hmac.compare_digest(str(data.get("s")), state):
        raise GoogleSignInError("state")
    return data


def exchange_code(c: AppContext, code: str, verifier: str) -> dict[str, Any]:
    """POST to Google's token endpoint (replaced in tests)."""
    r = httpx.post(
        EXCHANGE_URL,
        data={
            "code": code,
            "client_id": c.settings.google_oauth_client_id,
            "client_secret": c.settings.google_oauth_client_secret.get_secret_value(),
            "redirect_uri": redirect_uri(c),
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
        timeout=10,
    )
    if r.status_code != 200:
        raise GoogleSignInError("token")
    out: dict[str, Any] = r.json()
    return out


@dataclass(frozen=True)
class GoogleUser:
    subject: str
    email: str


def verify_id_token(c: AppContext, id_token: str, nonce: str) -> GoogleUser:
    try:
        claims: dict[str, Any] = json.loads(_unb64(id_token.split(".")[1]))
    except (IndexError, ValueError) as exc:
        raise GoogleSignInError("id_token") from exc
    if claims.get("iss") not in ISSUERS or claims.get("aud") != c.settings.google_oauth_client_id:
        raise GoogleSignInError("id_token")
    if int(claims.get("exp", 0)) < time.time() or not hmac.compare_digest(str(claims.get("nonce")), nonce):
        raise GoogleSignInError("id_token")
    if claims.get("email_verified") is not True or not claims.get("email") or not claims.get("sub"):
        raise GoogleSignInError("unverified_email")  # FR-002: the email must be verified by Google
    return GoogleUser(subject=str(claims["sub"]), email=str(claims["email"]))


def sign_in(c: AppContext, s: Session, g: GoogleUser) -> tuple[User, str, bool]:
    """Upserts the Google identity; links to the user with the same verified email (FR-002 AC3)."""
    ident = s.scalar(
        select(OAuthIdentity).where(OAuthIdentity.provider == "google", OAuthIdentity.subject == g.subject)
    )
    if ident is not None:
        user = s.get(User, ident.user_id)
        if user is None:
            raise GoogleSignInError("user")
        is_new = False
    else:
        user, is_new = user_for_verified_email(c, s, g.email)
        s.add(OAuthIdentity(user_id=user.id, provider="google", subject=g.subject))
    token = new_session(s, user, trusted=False)
    s.commit()
    return user, token, is_new
