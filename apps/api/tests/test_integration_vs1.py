"""VS-1 end-to-end through the API (backlog §3): auth → consent → case → upload → extract → confirm → audit → letter."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from claimsathi.context import AppContext
from claimsathi.devtools.pdfgen import text_pdf
from claimsathi.models import AiCall, ExtractedField, ReviewItem, Rule
from tests.conftest import ELIGIBILITY, csrf_headers, sign_in

pytestmark = pytest.mark.integration
SYN001 = (
    (Path(__file__).resolve().parents[3] / "eval/fixtures/documents/SYN-001-settlement-letter.txt")
    .read_text(encoding="utf-8")
    .splitlines()
)


def _new_case(tc: TestClient, h: dict[str, str], key: str | None = None) -> dict[str, Any]:
    r = tc.post(
        "/api/v1/cases", json={"eligibility": ELIGIBILITY}, headers={**h, "Idempotency-Key": key or str(uuid.uuid4())}
    )
    assert r.status_code == 201, r.text
    return r.json()


def _upload_syn001(tc: TestClient, h: dict[str, str], case_id: str) -> None:
    r = tc.post(
        f"/api/v1/cases/{case_id}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": ("letter.pdf", text_pdf(SYN001), "application/pdf")},
    )
    assert r.status_code == 202, r.text


def _to_findings(tc: TestClient, h: dict[str, str]) -> tuple[str, dict[str, Any]]:
    case = _new_case(tc, h)
    cid = case["id"]
    _upload_syn001(tc, h, cid)
    facts = tc.get(f"/api/v1/cases/{cid}/facts").json()
    assert (
        tc.post(f"/api/v1/cases/{cid}/facts/confirm", json={"base_version": facts["version"]}, headers=h).status_code
        == 200
    )
    li = tc.get(f"/api/v1/cases/{cid}/line-items").json()
    assert (
        tc.post(f"/api/v1/cases/{cid}/line-items/confirm", json={"base_version": li["version"]}, headers=h).status_code
        == 200
    )
    r = tc.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202, r.text
    return cid, tc.get(f"/api/v1/cases/{cid}/analyses/latest").json()


@pytest.mark.req("FR-010")
def test_extraction_values_match_fixture_ground_truth(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    _upload_syn001(client, h, cid)
    case = client.get(f"/api/v1/cases/{cid}").json()
    assert case["documents"][0]["status"] == "ready"
    f = {x["name"]: x for x in client.get(f"/api/v1/cases/{cid}/facts").json()["fields"]}
    assert f["claimed_paise"]["value"] == "26482000" and f["claimed_paise"]["display"] == "₹2,64,820"
    assert f["paid_paise"]["value"] == "21050000"
    assert f["decision_letter_date"]["value"] == "2026-09-10" and f["decision_type"]["value"] == "partial"
    assert f["claim_number"]["value"] == "SHI/CL/2026/000123"
    li = client.get(f"/api/v1/cases/{cid}/line-items").json()
    assert [i["deducted_paise"] for i in li["items"]] == [1840000, 625000, 125000, 2842000]
    assert li["totals"]["deducted_paise"] == 5432000 and li["totals"]["matches_disallowed"] is True
    with ctx.session_factory() as s:  # identity fields encrypted at rest (NFR-005)
        row = s.scalar(select(ExtractedField).where(ExtractedField.name == "claim_number"))
        assert row is not None and row.value is None and b"SHI/CL" not in (row.value_enc or b"")
        assert s.scalar(select(AiCall.status)) == "ok"


@pytest.mark.req("FR-015")
def test_vs1_findings_letter_and_export(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, a = _to_findings(client, h)
    statuses = [i["audit_status"] for i in a["line_items"]]
    assert statuses == ["NO_CLAUSE_CITED", "NO_CLAUSE_CITED", "NO_CLAUSE_CITED", "CANNOT_ASSESS"]
    assert a["mode"] == "full" and a["wording"]["synthetic"] is True
    assert len(a["counter_points"]) == 3 and a["dropped_count"] == 0
    cit = a["counter_points"][0]["citations"][0]
    assert cit["verified"] and cit["clause_ref"] == "Para 17(b)" and cit["synthetic"]
    chunk = client.get(f"/api/v1/cases/{cid}/sources/chunks/{cit['chunk_id']}").json()
    assert cit["quote"] in chunk["text"]

    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    letter = r.json()
    text = " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in letter["doc"]["blocks"])
    assert "₹25,900" in text and "SHI/CL/2026/000123" in text and "Ravi K. Mehta" in text
    assert "Doctor visit" not in text  # CANNOT_ASSESS item not included by default

    lid = letter["id"]
    r = client.post(f"/api/v1/letters/{lid}/exports", json={"format": "pdf"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "letter_not_reviewed"
    assert client.post(f"/api/v1/letters/{lid}/review", json={"version": 1}, headers=h).status_code == 200
    exp = client.post(f"/api/v1/letters/{lid}/exports", json={"format": "pdf"}, headers=h)
    assert exp.status_code == 200, exp.text
    pdf = client.get(exp.json()["download_path"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


@pytest.mark.req("FR-011")
def test_editing_confirmed_facts_makes_letter_stale(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    r = client.patch(
        f"/api/v1/cases/{cid}/facts",
        headers=h,
        json={"base_version": v, "fields": [{"name": "paid_paise", "value": "Rs. 2,10,000"}]},
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 409 and r.json()["code"] == "case_stale"
    assert client.get(f"/api/v1/cases/{cid}/analyses/latest").json()["stale"] is True


def test_analysis_requires_confirmed_facts(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 409 and r.json()["code"] == "fields_not_confirmed"


@pytest.mark.req("AI-004")
def test_unverifiable_evidence_is_dropped_not_shown(client: TestClient, ctx: AppContext) -> None:
    with ctx.session_factory() as s:
        rule = s.scalar(select(Rule).where(Rule.rule_key == "RULE-MC-01"))
        assert rule is not None
        params = dict(rule.params)
        params["evidence"] = {
            **params["evidence"],
            "quote": "insurers may reduce any claim for any reason at all times",
        }
        s.execute(update(Rule).where(Rule.id == rule.id).values(params=params))
        s.commit()
    h = sign_in(client, ctx)
    _cid, a = _to_findings(client, h)
    assert a["counter_points"] == [] and a["dropped_count"] == 3
    with ctx.session_factory() as s:
        assert s.scalar(select(ReviewItem.reason)) == "quote_not_in_chunk"


@pytest.mark.req("FR-008")
def test_upload_rejects_spoofed_duplicate_and_wrong_types(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    url = f"/api/v1/cases/{cid}/documents"
    r = client.post(url, headers=h, files={"file": ("x.pdf", b"<html>not a pdf</html>", "application/pdf")})
    assert r.status_code == 415
    _upload_syn001(client, h, cid)
    r = client.post(url, headers=h, files={"file": ("again.pdf", text_pdf(SYN001), "application/pdf")})
    assert r.status_code == 409 and r.json()["code"] == "duplicate_file"


def test_storage_guard_refuses_uploads_when_nearly_full(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    ctx.settings.storage_limit_mb = 1  # 1 MB limit: same guard logic without allocating ~1 GB
    ctx.store.put("filler", b"x" * int(1024 * 1024 * 0.95), "x/y")
    r = client.post(
        f"/api/v1/cases/{cid}/documents", headers=h, files={"file": ("a.pdf", text_pdf(["hello"]), "application/pdf")}
    )
    assert r.status_code == 503 and r.json()["code"] == "storage_full"


@pytest.mark.req("NFR-019")
def test_no_fixture_identity_values_in_logs(
    client: TestClient, ctx: AppContext, capsys: pytest.CaptureFixture[str]
) -> None:
    h = sign_in(client, ctx)
    _to_findings(client, h)
    out = capsys.readouterr().out
    for secret in ("Ravi K. Mehta", "SHI/CL/2026/000123", "ravi@example.com", "Rs. 2,64,820"):
        assert secret not in out


def test_security_headers_on_api_responses(client: TestClient) -> None:
    h = client.get("/api/v1/healthz").headers
    assert (
        "default-src 'none'" in h["content-security-policy"]
        and "frame-ancestors 'none'" in h["content-security-policy"]
    )
    assert h["x-content-type-options"] == "nosniff" and h["cache-control"] == "no-store"
    assert h["strict-transport-security"].startswith("max-age=") and h["x-frame-options"] == "DENY"


def test_csrf_required_on_unsafe_methods(client: TestClient, ctx: AppContext) -> None:
    csrf_headers(client)
    r = client.post("/api/v1/auth/email/request", json={"email": "a@example.com"})
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    r = client.post(
        "/api/v1/auth/email/request",
        json={"email": "a@example.com"},
        headers={**csrf_headers(client), "Origin": "https://evil.example"},
    )
    assert r.status_code == 403
