"""Admin console (PRD FR-037, FR-040, FR-042): allowlisted Google sign-in, mandatory TOTP, review queue,
case content only under the user's 7-day grant."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc, set_clock
from claimsathi.models import AdminUser, AuditLog
from claimsathi.security.totp import totp
from tests.conftest import _google_admin, admin_sign_in, csrf_headers, sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


@pytest.mark.req("FR-037")
def test_admin_signs_in_with_google_then_mandatory_totp(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _google_admin(client, monkeypatch)
    assert r.status_code == 302 and r.headers["location"] == "/en/admin/mfa"
    assert client.get("/api/v1/admin/me").status_code == 401  # AC2: no admin session without MFA
    setup = client.get("/api/v1/admin/auth/mfa").json()
    assert setup["enrolled"] is False and setup["otpauth_uri"].startswith("otpauth://totp/")
    h = csrf_headers(client)
    r = client.post("/api/v1/admin/auth/totp", json={"code": totp(setup["secret"])}, headers=h)
    assert r.status_code == 204 and "cs_admin=" in r.headers["set-cookie"]
    me = client.get("/api/v1/admin/me").json()
    assert me["role"] == "admin" and me["email_masked"] == "b•••@example.com"
    with admin_ctx.session_factory() as s:
        actions = {a.action for a in s.scalars(select(AuditLog).where(AuditLog.actor_type == "admin"))}
    assert {"admin_totp_enrolled", "admin_signed_in"} <= actions


def test_non_allowlisted_google_account_is_denied(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _google_admin(client, monkeypatch, email="stranger@example.com")
    assert r.status_code == 302 and r.headers["location"] == "/en/admin/sign-in?denied=1"
    assert client.get("/api/v1/admin/auth/mfa").status_code == 401


@pytest.mark.req("FR-037")
def test_five_wrong_totp_codes_lock_the_account(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    _google_admin(client, monkeypatch)
    client.get("/api/v1/admin/auth/mfa")
    h = csrf_headers(client)
    for _ in range(5):
        r = client.post("/api/v1/admin/auth/totp", json={"code": "000000"}, headers=h)
        assert r.status_code == 401 and r.json()["code"] == "totp_invalid"
    with admin_ctx.session_factory() as s:
        admin = s.scalar(select(AdminUser))
        assert admin is not None and admin.locked_until is not None
        secret = admin_ctx.cipher.decrypt(admin.totp_secret_enc or b"")
    r = client.post("/api/v1/admin/auth/totp", json={"code": totp(secret)}, headers=h)
    assert r.status_code == 429  # even the right code waits out the lock


@pytest.mark.req("FR-037")
def test_consumer_and_admin_sessions_never_cross(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_in(client, admin_ctx, "user@example.com")
    assert client.get("/api/v1/admin/me").status_code == 401  # AC1: consumer session rejected
    assert client.get("/api/v1/admin/review-items").status_code == 401
    client.cookies.clear()
    admin_sign_in(client, monkeypatch)
    assert client.get("/api/v1/me").status_code == 401  # and an admin session is not a user session


@pytest.mark.req("FR-042")
def test_review_queue_and_case_content_only_under_the_users_grant(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = sign_in(client, admin_ctx, "reporter@example.com")
    cid, a = _to_findings(client, h)
    r = client.post(
        "/api/v1/reports",
        json={
            "case_id": cid,
            "target_type": "counter_point",
            "target_id": a["counter_points"][0]["id"],
            "reason": "wrong_rule",
            "grant_access": False,
        },
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    user_cookies = dict(client.cookies)
    client.cookies.clear()
    ha = admin_sign_in(client, monkeypatch)
    items = client.get("/api/v1/admin/review-items").json()["items"]
    item = next(i for i in items if i["source"] == "user_report")
    assert item["payload"]["statement"] and item["case_access_until"] is None
    r = client.get(f"/api/v1/admin/review-items/{item['id']}/case-content")
    assert r.status_code == 403  # AC1: no grant, no content
    with admin_ctx.session_factory() as s:
        assert s.scalar(select(AuditLog.action).where(AuditLog.action == "case_access_denied")) is not None

    admin_cookies = dict(client.cookies)
    client.cookies.clear()
    for k, v in user_cookies.items():
        client.cookies.set(k, v)
    hu = csrf_headers(client)
    g = client.post(f"/api/v1/cases/{cid}/support-grant", headers=hu).json()
    assert g["active"] is True
    expires = g["expires_at"]
    client.cookies.clear()
    for k, v in admin_cookies.items():
        client.cookies.set(k, v)
    r = client.get(f"/api/v1/admin/review-items/{item['id']}/case-content")
    assert r.status_code == 200 and any(f["name"] == "claimed_paise" for f in r.json()["facts"])

    r = client.patch(
        f"/api/v1/admin/review-items/{item['id']}",
        json={"status": "incorrect", "decision_category": "rule_misapplied"},
        headers=ha,
    )
    assert r.status_code == 200 and r.json()["status"] == "incorrect"

    later = now_utc() + timedelta(days=8)  # AC2: the grant expires by itself
    set_clock(lambda: later)
    try:
        with admin_ctx.session_factory() as s:
            from claimsathi.datacontrols.service import active_grant

            assert active_grant(s, uuid.UUID(cid)) is None
    finally:
        set_clock(None)
    assert expires


def test_reviewer_cannot_use_admin_only_endpoints(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    with admin_ctx.session_factory() as s:
        admin = s.scalar(select(AdminUser))
        assert admin is not None
        admin.role = "reviewer"
        s.commit()
    admin_sign_in(client, monkeypatch)
    assert client.get("/api/v1/admin/review-items").status_code == 200
    assert client.get("/api/v1/admin/admins").status_code == 403
