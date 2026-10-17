"""Admin knowledge base (PRD FR-038) and rules table (FR-039)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select

from claimsathi.context import AppContext
from claimsathi.models import AdminUser, KnowledgeSource
from tests.conftest import admin_sign_in, sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration
DRAFT_TEXT = (
    "SYNTHETIC TEST CIRCULAR - not a real regulation.\n"
    "Para 1 This synthetic paragraph exists only for software tests.\n"
    "Para 2 Another synthetic paragraph for the knowledge base tests.\n"
)


def _upload(client: TestClient, h: dict[str, str], **over: Any) -> Response:
    data = {
        "type": "regulation",
        "issuer": "SYNTHETIC test issuer",
        "title": "Synthetic circular",
        "identifier": "SYN-CIRC-1",
        "version": "1",
        "effective_from": "2026-01-01",
        **over,
    }
    resp: Response = client.post(
        "/api/v1/admin/sources",
        headers=h,
        data=data,
        files={"file": ("circular.txt", DRAFT_TEXT.encode(), "text/plain")},
    )
    return resp


@pytest.mark.req("FR-038")
def test_source_draft_publish_needs_attestation_and_flags_missing_refs(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = admin_sign_in(client, monkeypatch)
    r = _upload(client, h)
    assert r.status_code == 201 and r.json()["status"] == "draft"
    sid = r.json()["id"]
    chunks = client.get(f"/api/v1/admin/sources/{sid}/chunks").json()["items"]
    assert [c["clause_ref"] for c in chunks] == [None, "Para 1", "Para 2"]
    assert chunks[0]["flags"] == ["missing_clause_ref"]  # AC2: flagged, never silently dropped
    assert _upload(client, h).status_code == 422  # same identifier + version
    r = client.post(f"/api/v1/admin/sources/{sid}/publish", json={"attest_checked": False}, headers=h)
    assert r.status_code == 422
    assert (
        client.post(f"/api/v1/admin/sources/{sid}/publish", json={"attest_checked": True}, headers=h).status_code == 204
    )
    listed = {x["id"]: x for x in client.get("/api/v1/admin/sources").json()["items"]}
    assert listed[sid]["status"] == "published" and listed[sid]["checked_by"].startswith("admin:")
    assert listed[sid]["chunks_missing_clause_ref"] == 1


@pytest.mark.req("FR-038")
def test_retiring_a_source_keeps_existing_citations(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    hu = sign_in(client, admin_ctx, "cited@example.com")
    cid, a = _to_findings(client, hu)
    chunk_id = a["counter_points"][0]["citations"][0]["chunk_id"]
    user_cookies = dict(client.cookies)
    client.cookies.clear()
    h = admin_sign_in(client, monkeypatch)
    with admin_ctx.session_factory() as s:
        src = s.scalar(select(KnowledgeSource).where(KnowledgeSource.identifier == "SAMPLE-REG-001"))
        assert src is not None
        sid = str(src.id)
    assert client.post(f"/api/v1/admin/sources/{sid}/retire", headers=h).status_code == 204
    client.cookies.clear()
    for k, v in user_cookies.items():
        client.cookies.set(k, v)
    r = client.get(f"/api/v1/cases/{cid}/sources/chunks/{chunk_id}")
    assert r.status_code == 200 and "Para 17(b)" in r.json()["text"]  # AC1: the old citation still resolves


@pytest.mark.req("FR-039")
def test_rules_need_a_source_to_be_enabled_and_new_versions_replace_old(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = admin_sign_in(client, monkeypatch)
    r = client.post(
        "/api/v1/admin/rules/RULE-DEADLINES/versions",
        json={"params": {"insurer_response_days": 15}, "source_ref": None},
        headers=h,
    )
    assert r.status_code == 201 and r.json()["version"] == 2 and r.json()["status"] == "disabled_pending_verification"
    r = client.post(
        "/api/v1/admin/rules/RULE-MC-02/versions", json={"params": {"evidence": {}}, "source_ref": "  "}, headers=h
    )
    v = r.json()["version"]
    r = client.post(
        f"/api/v1/admin/rules/RULE-MC-02/versions/{v}/enable", json={"verified_by": "Reviewer A"}, headers=h
    )
    assert r.status_code == 422  # AC1: no source, no enabling
    r = client.post(
        "/api/v1/admin/rules/RULE-DEADLINES/versions/2/enable", json={"verified_by": "Reviewer A"}, headers=h
    )
    assert r.status_code == 200 and r.json()["status"] == "enabled"
    rules = [x for x in client.get("/api/v1/admin/rules").json()["items"] if x["rule_key"] == "RULE-DEADLINES"]
    assert {(x["version"], x["status"]) for x in rules} == {(2, "enabled"), (1, "retired")}


@pytest.mark.req("FR-039")
def test_analysis_records_the_rule_versions_applied(client: TestClient, admin_ctx: AppContext) -> None:
    h = sign_in(client, admin_ctx, "versions@example.com")
    _cid, a = _to_findings(client, h)
    assert a["rule_versions"]["RULE-MC-01"] == 1 and "RULE-PATTERNS" in a["rule_versions"]


def test_reviewers_cannot_manage_content(
    client: TestClient, admin_ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    with admin_ctx.session_factory() as s:
        admin = s.scalar(select(AdminUser))
        assert admin is not None
        admin.role = "reviewer"
        s.commit()
    h = admin_sign_in(client, monkeypatch)
    assert client.get("/api/v1/admin/sources").status_code == 403
    assert client.get("/api/v1/admin/rules").status_code == 403
    assert _upload(client, h).status_code == 403
