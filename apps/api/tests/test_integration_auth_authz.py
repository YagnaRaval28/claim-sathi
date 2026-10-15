"""Auth (FR-001/003), consent (FR-005), cases (FR-006/007), idempotency, and the VS-1 authorization matrix."""

from __future__ import annotations

import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc, set_clock
from tests.conftest import ELIGIBILITY, csrf_headers, sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


def _code(ctx: AppContext, email: str) -> str:
    mail = [m for m in ctx.mailer.sent if m["to"] == email.strip().lower()][-1]  # type: ignore[attr-defined]
    return re.search(r"\b(\d{6})\b", mail["text"]).group(1)  # type: ignore[union-attr]


@pytest.mark.req("FR-001")
def test_email_code_rules(client: TestClient, ctx: AppContext) -> None:
    h = csrf_headers(client)
    email = "meena@example.com"
    for _ in range(5):
        assert client.post("/api/v1/auth/email/request", json={"email": email}, headers=h).status_code == 204
    r = client.post("/api/v1/auth/email/request", json={"email": email}, headers=h)
    assert r.status_code == 429 and "Retry-After" in r.headers
    code = _code(ctx, email)
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    for left in (4, 3, 2, 1, 0):
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": wrong}, headers=h)
        assert r.status_code == 401 and r.json()["attempts_left"] == left
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code}, headers=h)
    assert r.status_code == 401  # locked after 5 attempts: the correct code no longer works


def test_expired_code_rejected(client: TestClient, ctx: AppContext) -> None:
    h = csrf_headers(client)
    client.post("/api/v1/auth/email/request", json={"email": "x@example.com"}, headers=h)
    code = _code(ctx, "x@example.com")
    later = now_utc() + timedelta(minutes=11)
    set_clock(lambda: later)
    try:
        r = client.post("/api/v1/auth/email/verify", json={"email": "x@example.com", "code": code}, headers=h)
    finally:
        set_clock(None)
    assert r.status_code == 410 and r.json()["code"] == "email_code_expired"


def test_sign_in_normalises_email_to_one_account(client: TestClient, ctx: AppContext) -> None:
    sign_in(client, ctx, "same@example.com")
    first = client.get("/api/v1/me").json()["id"]
    client.cookies.clear()
    sign_in(client, ctx, "Same@Example.com ", consent=False)
    assert client.get("/api/v1/me").json()["id"] == first


@pytest.mark.req("FR-003")
def test_session_cookie_flags(client: TestClient, ctx: AppContext) -> None:
    h = csrf_headers(client)
    client.post("/api/v1/auth/email/request", json={"email": "c@example.com"}, headers=h)
    r = client.post(
        "/api/v1/auth/email/verify", json={"email": "c@example.com", "code": _code(ctx, "c@example.com")}, headers=h
    )
    cookie = r.headers["set-cookie"].lower()
    assert "cs_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie


@pytest.mark.req("FR-003")
def test_logout_all_revokes_every_session(ctx: AppContext, client: TestClient) -> None:
    h = sign_in(client, ctx, "multi@example.com")
    from claimsathi.main_api import create_app

    with TestClient(create_app(ctx), base_url="http://testserver") as other:
        sign_in(other, ctx, "multi@example.com", consent=False)
        assert other.get("/api/v1/me").status_code == 200
        assert client.post("/api/v1/auth/logout-all", headers=h).status_code == 204
        assert other.get("/api/v1/me").status_code == 401


@pytest.mark.req("FR-005")
def test_case_creation_requires_consent(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, consent=False)
    r = client.post("/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": "k1"})
    assert r.status_code == 403 and r.json()["code"] == "consent_required"


@pytest.mark.req("FR-006")
def test_out_of_scope_and_open_case_cap_and_idempotency(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "health_india": "no"}},
        headers={**h, "Idempotency-Key": "oos"},
    )
    assert r.status_code == 422 and r.json()["code"] == "out_of_scope"
    first = client.post("/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": "a"})
    again = client.post("/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": "a"})
    assert first.status_code == again.status_code == 201 and first.json()["id"] == again.json()["id"]
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "relation": "parent"}},
        headers={**h, "Idempotency-Key": "a"},
    )
    assert r.status_code == 409 and r.json()["code"] == "idempotency_key_reused"
    for k in ("b", "c"):
        assert (
            client.post(
                "/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": k}
            ).status_code
            == 201
        )
    r = client.post("/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": "d"})
    assert r.status_code == 409 and r.json()["code"] == "open_case_limit"


@pytest.mark.req("NFR-017")
def test_authorization_matrix_vs1(client: TestClient, ctx: AppContext) -> None:
    """User B, and an anonymous caller, must get an identical 404 or a 401 on every VS-1 resource of user A."""
    ha = sign_in(client, ctx, "a@example.com")
    cid, analysis = _to_findings(client, ha)
    letter = client.post(
        f"/api/v1/cases/{cid}/letters", json={}, headers={**ha, "Idempotency-Key": str(uuid.uuid4())}
    ).json()
    chunk_id = analysis["counter_points"][0]["citations"][0]["chunk_id"]
    lid = letter["id"]
    get_paths = [
        f"/api/v1/cases/{cid}",
        f"/api/v1/cases/{cid}/facts",
        f"/api/v1/cases/{cid}/line-items",
        f"/api/v1/cases/{cid}/progress",
        f"/api/v1/cases/{cid}/analyses/latest",
        f"/api/v1/cases/{cid}/sources/chunks/{chunk_id}",
        f"/api/v1/letters/{lid}",
    ]
    post_paths = [
        (f"/api/v1/cases/{cid}/facts/confirm", {"base_version": 0}),
        (f"/api/v1/cases/{cid}/analyses", {}),
        (f"/api/v1/cases/{cid}/letters", {}),
        (f"/api/v1/letters/{lid}/review", {"version": 1}),
        (f"/api/v1/letters/{lid}/exports", {"format": "pdf"}),
    ]
    client.cookies.clear()
    anon = csrf_headers(client)
    for p in get_paths:
        assert client.get(p).status_code == 401, p
    hb = sign_in(client, ctx, "b@example.com")
    bodies = set()
    for p in get_paths:
        r = client.get(p)
        assert r.status_code == 404, p
        bodies.add((r.json()["code"], r.json()["detail"]))
    for p, body in post_paths:
        r = client.post(p, json=body, headers={**hb, "Idempotency-Key": str(uuid.uuid4())})
        assert r.status_code == 404, p
    r = client.post(
        f"/api/v1/cases/{cid}/documents", headers=hb, files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")}
    )
    assert r.status_code == 404
    assert bodies == {("not_found", "This item isn't available.")}  # identical body: existence not revealed
    assert anon
