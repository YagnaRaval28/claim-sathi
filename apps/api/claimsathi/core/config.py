"""Application configuration with fail-fast validation (backlog T-101).

Values come from the environment, or from the repository-root `.env` when running locally.
Secrets are never echoed in error messages.
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["local", "test", "staging", "prod"] = "local"
    log_level: str = "info"
    public_base_url: str = "http://localhost:3000"

    database_url: str = Field(alias="SUPABASE_DB_URL")

    storage_s3_endpoint: str = "http://localhost:9000"
    storage_s3_region: str = "ap-south-1"
    storage_bucket_cases: str = "cases"
    supabase_storage_key: SecretStr = SecretStr("")
    supabase_storage_secret: SecretStr = SecretStr("")
    storage_backend: Literal["s3", "memory"] = "s3"
    storage_limit_mb: int = 1024
    storage_guard_pct: int = 95

    field_data_key: SecretStr
    hash_pepper: SecretStr
    code_pepper: SecretStr
    csrf_secret: SecretStr
    session_cookie_name: str = "cs_session"
    csrf_cookie_name: str = "cs_csrf"

    mailer: Literal["smtp", "ses", "memory"] = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "ClaimSathi <no-reply@claimsathi.local>"

    llm_provider: Literal["fake", "gemini_dev", "vertex"] = "fake"
    llm_model_id: str = "gemini-2.5-flash"
    gemini_dev_api_key: SecretStr = SecretStr("")
    llm_timeout_s: float = 120.0

    task_queue: Literal["inprocess", "cloudtasks"] = "inprocess"

    max_open_cases: int = 3  # readiness default D-E (beta); PRD FR-007 originally 10
    max_files_per_case: int = 15
    max_case_bytes: int = 50 * 1024 * 1024
    max_file_bytes: int = 20 * 1024 * 1024
    max_pages_per_case: int = 60

    credit_budget_usd: float = 300.0
    credit_guard_pct: int = 90

    @field_validator("field_data_key")
    @classmethod
    def _key_is_32_bytes(cls, v: SecretStr) -> SecretStr:
        try:
            raw = base64.b64decode(v.get_secret_value(), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("FIELD_DATA_KEY must be base64") from exc
        if len(raw) != 32:
            raise ValueError("FIELD_DATA_KEY must decode to exactly 32 bytes")
        return v

    @field_validator("hash_pepper", "code_pepper", "csrf_secret")
    @classmethod
    def _long_enough(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("secret must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def _no_free_ai_tier_outside_dev(self) -> Settings:
        # D-008: real documents never go to a free AI tier.
        if self.llm_provider == "gemini_dev" and self.app_env in ("staging", "prod"):
            raise ValueError("LLM_PROVIDER=gemini_dev is only allowed for local synthetic data (D-008)")
        return self

    @model_validator(mode="after")
    def _no_memory_backends_outside_dev(self) -> Settings:
        # In-memory storage loses uploads on restart; the memory mailer never delivers sign-in codes.
        if self.app_env in ("staging", "prod") and "memory" in (self.storage_backend, self.mailer):
            raise ValueError("STORAGE_BACKEND=memory and MAILER=memory are only allowed locally and in tests")
        return self

    @property
    def cookie_secure(self) -> bool:
        return self.app_env in ("staging", "prod")

    @property
    def field_key_bytes(self) -> bytes:
        return base64.b64decode(self.field_data_key.get_secret_value())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
