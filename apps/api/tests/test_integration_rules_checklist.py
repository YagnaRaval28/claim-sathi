"""User-picked categories drive the deterministic RULE-MC-02/03/05 checks and the evidence checklist
(PRD FR-013 user override, FR-016 deterministic rules, FR-018)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimsathi.context import AppContext
from claimsathi.devtools.pdfgen import text_pdf
from tests.conftest import ELIGIBILITY, sign_in

pytestmark = pytest.mark.integration
SYN002 = (
    (Path(__file__).resolve().parents[3] / "eval/fixtures/documents/SYN-002-repudiation-letter.txt")
    .read_text(encoding="utf-8")
    .splitlines()
)


def _rejected_case(client: TestClient, ctx: AppContext, email: str) -> tuple[dict[str, str], str]:
    h = sign_in(client, ctx, email)
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "situation": "rejected"}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    cid = r.json()["id"]
    r = client.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": ("letter.pdf", text_pdf(SYN002), "application/pdf")},
    )
    assert r.status_code == 202
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    assert client.post(f"/api/v1/cases/{cid}/facts/confirm", json={"base_version": v}, headers=h).status_code == 200
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202
    return h, cid


def _analysis(client: TestClient, cid: str) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()
    return body


def _set_fact(client: TestClient, h: dict[str, str], cid: str, name: str, value: str) -> None:
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    r = client.patch(
        f"/api/v1/cases/{cid}/facts", headers=h, json={"base_version": v, "fields": [{"name": name, "value": value}]}
    )
    assert r.status_code == 200, r.text


def _set_category(client: TestClient, h: dict[str, str], cid: str, category: str) -> None:
    reason = _analysis(client, cid)["reasons"][0]
    r = client.patch(f"/api/v1/cases/{cid}/reasons/{reason['id']}", json={"category": category}, headers=h)
    assert r.status_code == 202, r.text


def _letter_text(client: TestClient, h: dict[str, str], cid: str) -> tuple[str, dict[str, Any]]:
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    doc = r.json()["doc"]
    return " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in doc["blocks"]), doc


@pytest.mark.req("FR-016")
def test_full_rejection_asks_for_claims_review_committee_approval(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "mc02@example.com")
    a = _analysis(client, cid)
    mc02 = next(p for p in a["counter_points"] if p["rule_key"] == "RULE-MC-02")
    assert mc02["citations"][0]["clause_ref"] == "Para 17(a)" and mc02["citations"][0]["verified"]
    text, doc = _letter_text(client, h, cid)
    assert "(c) confirm that your claims review committee approved the rejection;" in text
    assert [n["clause_ref"] for n in doc["footnotes"]] == ["Para 17(b)", "Para 17(a)"]


@pytest.mark.req("FR-016")
def test_moratorium_fires_only_with_the_category_and_more_than_60_months(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "mc03@example.com")
    _set_fact(client, h, cid, "first_inception_date", "01/04/2020")  # 74 months before admission 10/06/2026
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202
    assert "RULE-MC-03" not in {p["rule_key"] for p in _analysis(client, cid)["counter_points"]}  # no category yet
    _set_category(client, h, cid, "non_disclosure")
    a = _analysis(client, cid)
    assert a["reasons"][0]["category"] == "non_disclosure" and a["reasons"][0]["category_source"] == "user"
    mc03 = next(p for p in a["counter_points"] if p["rule_key"] == "RULE-MC-03")
    assert mc03["citations"][0]["clause_ref"] == "Para 13"
    text, _ = _letter_text(client, h, cid)
    assert "more than 60 months of continuous cover" in text and "established fraud" in text
    keys = {i["item_key"] for i in a["checklist"]}
    assert {"doctor_certificate_first_diagnosis", "previous_policy_schedules", "decision_letter"} <= keys

    _set_fact(client, h, cid, "first_inception_date", "01/08/2021")  # 58 months: no moratorium
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202
    assert "RULE-MC-03" not in {p["rule_key"] for p in _analysis(client, cid)["counter_points"]}


@pytest.mark.req("FR-016")
def test_documents_reason_cites_para_17c(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "mc05@example.com")
    _set_category(client, h, cid, "documents_or_intimation")
    a = _analysis(client, cid)
    mc05 = next(p for p in a["counter_points"] if p["rule_key"] == "RULE-MC-05")
    assert mc05["citations"][0]["clause_ref"] == "Para 17(c)"
    assert {"proof_documents_submitted", "intimation_proof"} <= {i["item_key"] for i in a["checklist"]}


@pytest.mark.req("FR-018")
def test_checklist_items_trace_to_the_map_and_obtained_items_become_enclosures(
    client: TestClient, ctx: AppContext
) -> None:
    h, cid = _rejected_case(client, ctx, "checklist@example.com")
    _set_category(client, h, cid, "non_disclosure")
    items = {i["item_key"]: i for i in _analysis(client, cid)["checklist"]}
    assert items["decision_letter"]["status"] == "uploaded"  # the decision letter is on file
    assert items["previous_policy_schedules"]["status"] == "pending"
    r = client.patch(f"/api/v1/cases/{cid}/checklist/previous_policy_schedules", json={"status": "obtained"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "obtained"
    assert (
        client.patch(f"/api/v1/cases/{cid}/checklist/made_up_item", json={"status": "obtained"}, headers=h).status_code
        == 404
    )
    text, _ = _letter_text(client, h, cid)
    assert "Enclosures: a copy of your decision letter; my earlier policy schedules showing continuous cover." in text


@pytest.mark.req("NFR-017")
def test_category_and_checklist_endpoints_are_owner_only(client: TestClient, ctx: AppContext) -> None:
    _h, cid = _rejected_case(client, ctx, "cat-owner@example.com")
    reason_id = _analysis(client, cid)["reasons"][0]["id"]
    client.cookies.clear()
    hb = sign_in(client, ctx, "cat-intruder@example.com")
    r = client.patch(f"/api/v1/cases/{cid}/reasons/{reason_id}", json={"category": "exclusion"}, headers=hb)
    assert r.status_code == 404
    r = client.patch(f"/api/v1/cases/{cid}/checklist/decision_letter", json={"status": "obtained"}, headers=hb)
    assert r.status_code == 404
