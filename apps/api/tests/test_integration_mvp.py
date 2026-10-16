"""MVP journeys beyond the SYN-001 happy path: manual entry when nothing is extracted, rejections (SYN-002),
failed background work, and a clear error when the PDF renderer is missing."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimsathi.context import AppContext
from claimsathi.devtools.pdfgen import text_pdf
from tests.conftest import ELIGIBILITY, sign_in
from tests.test_integration_vs1 import SYN001, _new_case, _upload_syn001

pytestmark = pytest.mark.integration
SYN002 = (
    (Path(__file__).resolve().parents[3] / "eval/fixtures/documents/SYN-002-repudiation-letter.txt")
    .read_text(encoding="utf-8")
    .splitlines()
)


def _upload(tc: TestClient, h: dict[str, str], cid: str, lines: list[str]) -> None:
    r = tc.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": ("letter.pdf", text_pdf(lines), "application/pdf")},
    )
    assert r.status_code == 202, r.text


def _fields(tc: TestClient, cid: str) -> dict[str, dict[str, Any]]:
    return {f["name"]: f for f in tc.get(f"/api/v1/cases/{cid}/facts").json()["fields"]}


@pytest.mark.req("FR-011")
def test_unrecognised_letter_shows_required_fields_and_manual_entry_reaches_a_letter(
    client: TestClient, ctx: AppContext
) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    _upload(client, h, cid, ["A letter the fake provider has no recording for", "Nothing to extract here"])
    facts = client.get(f"/api/v1/cases/{cid}/facts").json()
    assert facts["extraction"] == "done"
    f = {x["name"]: x for x in facts["fields"]}
    for name in ("insurer", "decision_letter_date", "decision_type", "claimed_paise", "paid_paise"):
        assert name in f and f[name]["value"] is None  # shown so the user can fill them in
    edits = [
        {"name": "insurer", "value": "Sample Health Insurance Co. Ltd."},
        {"name": "decision_letter_date", "value": "10/09/2026"},
        {"name": "decision_type", "value": "partial"},
        {"name": "claimed_paise", "value": "264820"},  # typed rupees, not paise
        {"name": "paid_paise", "value": "₹2,10,500"},
    ]
    r = client.patch(f"/api/v1/cases/{cid}/facts", headers=h, json={"base_version": facts["version"], "fields": edits})
    assert r.status_code == 200, r.text
    f = _fields(client, cid)
    assert f["claimed_paise"]["display"] == "₹2,64,820" and f["paid_paise"]["value"] == "21050000"
    assert f["paid_paise"]["required"] is True
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    assert client.post(f"/api/v1/cases/{cid}/facts/confirm", json={"base_version": v}, headers=h).status_code == 200
    li = client.get(f"/api/v1/cases/{cid}/line-items").json()
    r = client.put(
        f"/api/v1/cases/{cid}/line-items",
        headers=h,
        json={
            "base_version": li["version"],
            "items": [{"description": "Consumables", "deducted_paise": 625000}],
        },
    )
    assert r.status_code == 200, r.text
    li = client.get(f"/api/v1/cases/{cid}/line-items").json()
    assert li["items"][0]["user_entered"] is True
    assert (
        client.post(f"/api/v1/cases/{cid}/line-items/confirm", json={"base_version": li["version"]}, headers=h)
    ).status_code == 200
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202
    a = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()
    assert a["status"] == "succeeded" and [i["audit_status"] for i in a["line_items"]] == ["NO_CLAUSE_CITED"]
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text


@pytest.mark.req("FR-015")
def test_rejected_claim_reason_without_clause_gets_a_finding_and_a_letter(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "situation": "rejected"}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    cid = r.json()["id"]
    _upload(client, h, cid, SYN002)
    f = _fields(client, cid)
    assert f["decision_type"]["value"] == "repudiation" and f["claimed_paise"]["display"] == "₹1,85,000"
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    assert client.post(f"/api/v1/cases/{cid}/facts/confirm", json={"base_version": v}, headers=h).status_code == 200
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202, r.text
    a = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()
    assert a["line_items"] == [] and len(a["reasons"]) == 1
    reason = a["reasons"][0]
    assert reason["audit_status"] == "NO_CLAUSE_CITED" and len(reason["counter_point_ids"]) == 1
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    text = " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in r.json()["doc"]["blocks"])
    assert "was rejected" in text and "non-disclosure of pre-existing Diabetes Mellitus" in text
    assert "₹1,85,000" in text and "Request to review the rejection of claim" in text


def test_user_edits_survive_a_second_upload(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    _upload_syn001(client, h, cid)
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    r = client.patch(
        f"/api/v1/cases/{cid}/facts",
        headers=h,
        json={"base_version": v, "fields": [{"name": "hospital", "value": "City Hospital"}]},
    )
    assert r.status_code == 200
    _upload(client, h, cid, [*SYN001, "Page 2 of the same letter"])  # a different file re-runs extraction
    f = _fields(client, cid)
    assert f["hospital"]["value"] == "City Hospital" and f["hospital"]["provenance"] == "user"
    assert f["claimed_paise"]["value"] == "26482000"


def test_a_crashed_read_marks_the_document_failed(
    client: TestClient, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    import claimsathi.documents.service as docs

    def boom(_data: bytes) -> list[list[str]]:
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(docs, "read_pdf_lines", boom)
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    _upload_syn001(client, h, cid)
    case = client.get(f"/api/v1/cases/{cid}").json()
    assert case["documents"][0]["status"] == "failed" and case["documents"][0]["status_reason"] == "read_failed"


def test_missing_pdf_renderer_returns_a_clear_problem(
    client: TestClient, ctx: AppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    import claimsathi.letters.render as render

    def unavailable(_doc: dict[str, Any]) -> bytes:
        raise render.RendererUnavailable("OSError")

    monkeypatch.setattr(render, "render_pdf", unavailable)
    from tests.test_integration_vs1 import _to_findings

    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    letter = client.post(
        f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())}
    ).json()
    assert client.post(f"/api/v1/letters/{letter['id']}/review", json={"version": 1}, headers=h).status_code == 200
    r = client.post(f"/api/v1/letters/{letter['id']}/exports", json={"format": "pdf"}, headers=h)
    assert r.status_code == 503 and r.json()["code"] == "export_unavailable"
