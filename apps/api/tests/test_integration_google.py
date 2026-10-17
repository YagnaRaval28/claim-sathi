"""Google sign-in (PRD FR-002) against a fake Google token endpoint: PKCE, state, nonce, verified email, linking."""

from __future__ import annotations

import base64
import json
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select

from claimsathi.auth import google
from claimsathi.context import AppContext
from claimsathi.models import OAuthIdentity, User
from tests.conftest import sign_in

pytestmark = pytest.mark.integration
CLIENT = "test-client.apps.googleusercontent.com"


@pytest.fixture
def enabled(ctx: AppContext) -> AppContext:
    ctx.settings.google_oauth_client_id = CLIENT
    ctx.settings.google_oauth_client_secret = SecretStr("test-secret")
    return ctx


def _b64(d: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def _id_token(nonce: str, *, email: str = "meena@example.com", verified: bool = True, aud: str = CLIENT) -> str:
    claims = {
        "iss": "https://accounts.google.com",
        "aud": aud,
        "sub": f"g-{email}",
        "email": email,
        "email_verified": verified,
        "nonce": nonce,
        "exp": int(time.time()) + 300,
    }
    return f"{_b64({'alg': 'RS256'})}.{_b64(claims)}.signature"


def _start(client: TestClient, lang: str = "en") -> tuple[str, str]:
    r = client.get(f"/api/v1/auth/google/start?lang={lang}", follow_redirects=False)
    assert r.status_code == 302, r.text
    q = parse_qs(urlparse(r.headers["location"]).query)
    return q["state"][0], q["nonce"][0]


def _callback(client: TestClient, monkeypatch: pytest.MonkeyPatch, state: str, token: str) -> Any:
    monkeypatch.setattr(google, "exchange_code", lambda _c, _code, _verifier: {"id_token": token})
    return client.get(f"/api/v1/auth/google/callback?code=abc&state={state}", follow_redirects=False)


def test_google_hidden_until_configured(client: TestClient, ctx: AppContext) -> None:
    assert client.get("/api/v1/auth/providers").json() == {"google": False, "email": True}
    assert client.get("/api/v1/auth/google/start", follow_redirects=False).status_code == 404


@pytest.mark.req("FR-002")
def test_start_uses_pkce_state_and_nonce(client: TestClient, enabled: AppContext) -> None:
    r = client.get("/api/v1/auth/google/start?lang=gu", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert r.headers["location"].startswith(google.AUTH_URL)
    assert q["client_id"] == [CLIENT] and q["code_challenge_method"] == ["S256"] and q["scope"] == ["openid email"]
    assert q["redirect_uri"] == ["http://testserver/api/v1/auth/google/callback"]
    cookie = r.headers["set-cookie"].lower()
    assert "cs_oauth=" in cookie and "httponly" in cookie and "max-age=600" in cookie
    assert client.get("/api/v1/auth/providers").json()["google"] is True


@pytest.mark.req("FR-002")
def test_verified_google_email_signs_in_and_goes_to_consent(
    client: TestClient, enabled: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, nonce = _start(client, "hi")
    r = _callback(client, monkeypatch, state, _id_token(nonce))
    assert r.status_code == 302 and r.headers["location"] == "/hi/welcome/consent"
    assert "cs_session=" in r.headers["set-cookie"]
    me = client.get("/api/v1/me")
    assert me.status_code == 200 and me.json()["email_masked"] == "m•••@example.com"


@pytest.mark.req("FR-002")
def test_cancel_returns_to_sign_in_without_an_error(client: TestClient, enabled: AppContext) -> None:
    state, _ = _start(client)
    r = client.get(f"/api/v1/auth/google/callback?error=access_denied&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/en/sign-in"
    assert client.get("/api/v1/me").status_code == 401


@pytest.mark.req("FR-002")
def test_google_and_email_code_reach_the_same_account(
    client: TestClient, enabled: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_in(client, enabled, "Meena@Example.com")
    first = client.get("/api/v1/me").json()["id"]
    client.cookies.clear()
    state, nonce = _start(client)
    r = _callback(client, monkeypatch, state, _id_token(nonce, email="meena@example.com"))
    assert r.headers["location"] == "/en/cases"  # already consented
    assert client.get("/api/v1/me").json()["id"] == first
    with enabled.session_factory() as s:
        assert s.scalar(select(func.count(User.id))) == 1
        assert s.scalar(select(func.count(OAuthIdentity.id))) == 1


@pytest.mark.parametrize(
    "case",
    ["unverified", "wrong_state", "wrong_audience", "wrong_nonce"],
)
def test_bad_google_responses_are_refused(
    client: TestClient, enabled: AppContext, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    state, nonce = _start(client)
    token = {
        "unverified": _id_token(nonce, verified=False),
        "wrong_state": _id_token(nonce),
        "wrong_audience": _id_token(nonce, aud="someone-else"),
        "wrong_nonce": _id_token("not-the-nonce"),
    }[case]
    r = _callback(client, monkeypatch, "forged-state" if case == "wrong_state" else state, token)
    assert r.status_code == 302 and r.headers["location"] == "/en/sign-in"
    assert client.get("/api/v1/me").status_code == 401
    with enabled.session_factory() as s:
        assert s.scalar(select(func.count(User.id))) == 0
