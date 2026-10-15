"""Integration fixtures: a real Postgres (TEST_DATABASE_URL), in-memory storage and mailer, fake AI provider.

Integration tests are skipped only when TEST_DATABASE_URL is unset (pure unit runs). CI always sets it,
so they always run there.
"""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from claimsathi.ai.providers import FakeProvider
from claimsathi.context import AppContext
from claimsathi.core.config import Settings
from claimsathi.core.db import make_session_factory
from claimsathi.infra import MemoryMailer, MemoryObjectStore
from claimsathi.jobs import Dispatcher
from claimsathi.main_api import create_app
from claimsathi.security.crypto import FieldCipher
from claimsathi.seeds import seed

TEST_DB = os.environ.get("TEST_DATABASE_URL")
API_ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set (integration tests need Postgres)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def migrated_db() -> str:
    assert TEST_DB
    from alembic import command
    from alembic.config import Config

    engine = create_engine(TEST_DB)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    os.environ["MIGRATION_DATABASE_URL"] = TEST_DB
    command.upgrade(cfg, "head")
    return TEST_DB


@pytest.fixture
def ctx(migrated_db: str) -> Iterator[AppContext]:
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        tables = (
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
            )
            .scalars()
            .all()
        )
        conn.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"))
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        SUPABASE_DB_URL=migrated_db,
        public_base_url="http://testserver",
        field_data_key=base64.b64encode(b"k" * 32).decode(),
        hash_pepper="h" * 40,
        code_pepper="c" * 40,
        csrf_secret="s" * 40,
        storage_backend="memory",
        mailer="memory",
        llm_provider="fake",
    )
    sf = make_session_factory(migrated_db)
    c = AppContext(
        settings=settings,
        session_factory=sf,
        store=MemoryObjectStore(),
        mailer=MemoryMailer(),
        cipher=FieldCipher(b"k" * 32),
        provider=FakeProvider(),
        dispatcher=Dispatcher(sf),
    )
    with sf() as s:
        seed(s, "test")
    yield c


@pytest.fixture
def client(ctx: AppContext) -> Iterator[TestClient]:
    with TestClient(create_app(ctx), base_url="http://testserver") as tc:
        yield tc


def csrf_headers(tc: TestClient) -> dict[str, str]:
    token = tc.get("/api/v1/auth/csrf").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def sign_in(tc: TestClient, ctx: AppContext, email: str = "ravi@example.com", consent: bool = True) -> dict[str, str]:
    h = csrf_headers(tc)
    assert tc.post("/api/v1/auth/email/request", json={"email": email}, headers=h).status_code == 204
    mail = [m for m in ctx.mailer.sent if m["to"] == email.strip().lower()][-1]  # type: ignore[attr-defined]
    code = re.search(r"\b(\d{6})\b", mail["text"]).group(1)  # type: ignore[union-attr]
    r = tc.post("/api/v1/auth/email/verify", json={"email": email, "code": code}, headers=h)
    assert r.status_code == 200, r.text
    if consent:
        v = tc.get("/api/v1/consent/notice").json()["version"]
        assert (
            tc.post("/api/v1/consents", json={"version": v, "purposes": ["processing"]}, headers=h).status_code == 201
        )
    return h


ELIGIBILITY = {
    "health_india": "yes",
    "situation": "partly_paid",
    "policy_type": "floater",
    "complainant_name": "Ravi K. Mehta",
    "relation": "self",
    "in_litigation": "no",
}
