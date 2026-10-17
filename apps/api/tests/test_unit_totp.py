"""TOTP against the RFC 6238 Appendix B test vectors (SHA-1 seed "12345678901234567890")."""

from __future__ import annotations

import base64

import pytest

from claimsathi.security.totp import hotp, new_secret, provisioning_uri, totp, verify

SEED = base64.b32encode(b"12345678901234567890").decode().rstrip("=")


@pytest.mark.parametrize(
    ("at", "eight_digit"),
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
    ],
)
def test_rfc6238_vectors(at: int, eight_digit: str) -> None:
    key = base64.b32decode(SEED + "=" * (-len(SEED) % 8))
    assert hotp(key, at // 30, digits=8) == eight_digit
    assert totp(SEED, at) == eight_digit[-6:]


@pytest.mark.req("FR-037")
def test_verify_accepts_one_step_of_drift_only() -> None:
    code = totp(SEED, 1111111111)
    assert verify(SEED, code, at=1111111111)
    assert verify(SEED, code, at=1111111111 + 30)
    assert not verify(SEED, code, at=1111111111 + 90)
    assert not verify(SEED, "12345", at=1111111111) and not verify(SEED, "abcdef", at=1111111111)


def test_new_secret_and_uri() -> None:
    s = new_secret()
    assert len(s) == 32 and verify(s, totp(s))
    assert provisioning_uri(s, "admin@example.com").startswith(
        "otpauth://totp/ClaimSathi%20Admin:admin%40example.com?secret="
    )
