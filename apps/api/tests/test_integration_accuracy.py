"""Monthly citation audit (PRD FR-040 AC1) and the published accuracy figure (FR-043, PUB-04)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from claimsathi.admin.accuracy import draw_sample
from claimsathi.context import AppContext
from claimsathi.core.clock import today_ist
from claimsathi.models import AdminUser, ReviewItem, User
from tests.conftest import admin_sign_in, sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration
PERIOD = today_ist().strftime("%Y-%m")


def _cases_in(client: TestClient, ctx: AppContext, languages: list[str]) -> None:
    for n, lang in enumerate(languages):
        client.cookies.clear()
        h = sign_in(client, ctx, f"audit-{n}-{lang}@example.com")
        _to_findings(client, h)
        with ctx.session_factory() as s:
            user = s.scalars(select(User).order_by(User.created_at.desc())).first()
            assert user is not None
            user.display_language = lang
            s.commit()
    client.cookies.clear()


@pytest.mark.req("FR-040")
def test_sample_is_random_and_spread_across_languages(client: TestClient, admin_ctx: AppContext) -> None:
    _cases_in(client, admin_ctx, ["en", "en", "gu", "hi"])
    with admin_ctx.session_factory() as s:
        admin = s.scalars(select(AdminUser)).one()
        assert draw_sample(s, admin, PERIOD, size=3) == 3
        items = s.scalars(select(ReviewItem).where(ReviewItem.source == "audit_sample")).all()
        assert sorted(i.language or "" for i in items) == ["en", "gu", "hi"]  # stratified, not proportional
        assert all(i.target_type == "citation" and i.payload["period"] == PERIOD for i in items)
        assert all(i.payload["quote"] and i.payload["clause_ref"] for i in items)
        assert draw_sample(s, admin, PERIOD) == 3  # drawing again keeps the month's sample


@pytest.mark.req("FR-043")
def test_accuracy_is_published_only_after_every_sampled_citation_is_decided(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    _cases_in(client, admin_ctx, ["en", "gu"])
    assert client.get("/api/v1/public/accuracy").json() == {"audit": None}  # empty state, no number
    h = admin_sign_in(client, monkeypatch)
    r = client.post(f"/api/v1/admin/accuracy-audits/{PERIOD}/publish", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "audit_not_ready"
    view = client.post(f"/api/v1/admin/accuracy-audits/{PERIOD}/sample", headers=h).json()
    assert view["sampled"] > 1 and view["open"] == view["sampled"] and view["by_language"]["gu"] >= 1
    assert client.post(f"/api/v1/admin/accuracy-audits/{PERIOD}/publish", headers=h).status_code == 409

    items = client.get("/api/v1/admin/review-items?status=open", headers=h).json()["items"]
    samples = [i for i in items if i["source"] == "audit_sample"]
    for n, item in enumerate(samples):
        decision = "incorrect" if n == 0 else "correct"
        r = client.patch(f"/api/v1/admin/review-items/{item['id']}", json={"status": decision}, headers=h)
        assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/admin/accuracy-audits/{PERIOD}/publish", headers=h)
    assert r.status_code == 200, r.text
    audit = client.get("/api/v1/public/accuracy").json()["audit"]
    assert audit["period"] == PERIOD and audit["sample_size"] == len(samples)
    assert audit["correct"] == len(samples) - 1  # computed from stored decisions, never hard-coded
    listing = client.get("/api/v1/admin/accuracy-audits", headers=h).json()
    assert listing["sample_size"] == 100 and listing["items"][0]["published"] == audit
    assert listing["current_period"] == PERIOD


def test_audit_periods_are_real_months(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = admin_sign_in(client, monkeypatch)
    for bad in ("2026-13", "26-10", "2999-01"):
        assert client.post(f"/api/v1/admin/accuracy-audits/{bad}/sample", headers=h).status_code == 422
    client.cookies.delete("cs_admin")
    assert client.post(f"/api/v1/admin/accuracy-audits/{PERIOD}/sample", headers=h).status_code == 401
