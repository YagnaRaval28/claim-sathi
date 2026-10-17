"""TOTP (RFC 6238; HOTP RFC 4226) for mandatory admin MFA (PRD FR-037). SHA-1, 30-second steps, 6 digits,
which is what standard authenticator apps use. A pure module: no dependency, constant-time comparison."""

from __future__ import annotations

import base64
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_S = 30
DIGITS = 6


def new_secret() -> str:
    """160-bit base32 secret (no padding), as authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret_b32: str) -> bytes:
    return base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8), casefold=True)


def hotp(key: bytes, counter: int, digits: int = DIGITS, digest: str = "sha1") -> str:
    mac = hmac.new(key, struct.pack(">Q", counter), digest).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 10**digits).zfill(digits)


def totp(secret_b32: str, at: float | None = None) -> str:
    return hotp(_key(secret_b32), int((time.time() if at is None else at) // STEP_S))


def verify(secret_b32: str, code: str, at: float | None = None, window: int = 1) -> bool:
    """Accepts the current step and ±`window` steps for clock drift."""
    if not (code.isdigit() and len(code) == DIGITS):
        return False
    now = time.time() if at is None else at
    key = _key(secret_b32)
    counter = int(now // STEP_S)
    return any(hmac.compare_digest(hotp(key, counter + d), code) for d in range(-window, window + 1))


def provisioning_uri(secret_b32: str, account: str, issuer: str = "ClaimSathi Admin") -> str:
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret_b32}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_S}"
    )
