"""Application-level field encryption and keyed hashing (NFR-005, system-design §4.6)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VERSION = b"v1"
_KEY_ID = b"k1"


class FieldCipher:
    """AES-256-GCM. Format: b"v1" + key_id(2) + nonce(12) + ciphertext||tag."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("field key must be 32 bytes")
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(12)
        return _VERSION + _KEY_ID + nonce + self._aead.encrypt(nonce, plaintext.encode("utf-8"), _VERSION + _KEY_ID)

    def decrypt(self, blob: bytes) -> str:
        if blob[:2] != _VERSION or blob[2:4] != _KEY_ID:
            raise ValueError("unknown ciphertext version or key")
        nonce, ct = blob[4:16], blob[16:]
        return self._aead.decrypt(nonce, ct, _VERSION + _KEY_ID).decode("utf-8")


def keyed_hash(pepper: str, value: str) -> bytes:
    return hmac.new(pepper.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()


def constant_time_equal(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def normalize_email(email: str) -> str:
    return email.strip().lower()
