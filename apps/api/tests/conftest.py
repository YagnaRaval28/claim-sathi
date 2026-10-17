"""Integration fixtures: a real Postgres (TEST_DATABASE_URL), in-memory storage and mailer, fake AI provider.

Integration tests are skipped only when TEST_DATABASE_URL is unset (pure unit runs). CI always sets it,
so they always run there.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from claimsathi.admin.service import seed_bootstrap_admin
from claimsathi.ai.providers import FakeProvider
from claimsathi.auth import google
from claimsathi.context import AppContext
from claimsathi.core.config import Settings
from claimsathi.core.db import make_session_factory
from claimsathi.infra import MemoryMailer, MemoryObjectStore
from claimsathi.jobs import Dispatcher
from claimsathi.main_api import create_app
from claimsathi.security.crypto import FieldCipher
from claimsathi.security.totp import totp
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
    settings = Settings(
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
    code = code_in(last_mail_to(ctx, email)["text"])
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


# --- Admin console helpers (shared by the admin test modules) -----------------------------------------
ADMIN_CLIENT = "admin-client.apps.googleusercontent.com"
BOSS = "boss@example.com"


@pytest.fixture
def admin_ctx(ctx: AppContext) -> AppContext:
    ctx.settings.admin_oauth_client_id = ADMIN_CLIENT
    ctx.settings.admin_oauth_client_secret = SecretStr("admin-secret")
    ctx.settings.admin_bootstrap_email = BOSS
    with ctx.session_factory() as s:
        seed_bootstrap_admin(ctx, s)
    return ctx


def _b64(d: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def _google_admin(client: TestClient, monkeypatch: pytest.MonkeyPatch, email: str = BOSS) -> Any:
    r = client.get("/api/v1/admin/auth/google/start", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    claims = {
        "iss": "https://accounts.google.com",
        "aud": ADMIN_CLIENT,
        "sub": f"g-{email}",
        "email": email,
        "email_verified": True,
        "nonce": q["nonce"][0],
        "exp": int(time.time()) + 300,
    }
    token = f"{_b64({'alg': 'RS256'})}.{_b64(claims)}.sig"
    monkeypatch.setattr(google, "exchange_code", lambda *_a, **_k: {"id_token": token})
    return client.get(f"/api/v1/admin/auth/google/callback?code=x&state={q['state'][0]}", follow_redirects=False)


def admin_sign_in(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    r = _google_admin(client, monkeypatch)
    assert r.status_code == 302 and r.headers["location"] == "/en/admin/mfa"
    setup = client.get("/api/v1/admin/auth/mfa").json()
    secret = setup.get("secret")
    if secret is None:  # already enrolled earlier in the test
        raise AssertionError("expected enrolment")
    h = csrf_headers(client)
    assert client.post("/api/v1/admin/auth/totp", json={"code": totp(secret)}, headers=h).status_code == 204
    client.headers["x-test-totp"] = secret
    return h


# --- Typed helpers for the in-memory test doubles ----------------------------------------------------


def sent_mail(ctx: AppContext) -> list[dict[str, str]]:
    assert isinstance(ctx.mailer, MemoryMailer)
    return ctx.mailer.sent


def last_mail_to(ctx: AppContext, email: str) -> dict[str, str]:
    return [m for m in sent_mail(ctx) if m["to"] == email.strip().lower()][-1]


def code_in(text: str) -> str:
    m = re.search(r"\b(\d{6})\b", text)
    assert m is not None, "no 6-digit code in the email"
    return m.group(1)


def store_keys(ctx: AppContext, prefix: str) -> list[str]:
    assert isinstance(ctx.store, MemoryObjectStore)
    return [k for k in ctx.store.objects if k.startswith(prefix)]
