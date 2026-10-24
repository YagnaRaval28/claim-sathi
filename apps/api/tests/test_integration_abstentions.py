"""Abstention and limited-analysis states, each with its recovery actions (PRD FR-019)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimsathi.analysis.service import RECOVERY, abstentions
from claimsathi.context import AppContext
from claimsathi.models import Analysis, DecisionReason, LineItem
from tests.conftest import ELIGIBILITY, sign_in
from tests.test_integration_mvp import _upload
from tests.test_integration_rules_checklist import _rejected_case

pytestmark = pytest.mark.integration
NOTHING = ["A letter the fake provider has no recording for", "Nothing to extract here"]


def _case(client: TestClient, h: dict[str, str], situation: str, edits: list[dict[str, str]]) -> str:
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "situation": situation}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    cid: str = r.json()["id"]
    _upload(client, h, cid, NOTHING)
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    r = client.patch(f"/api/v1/cases/{cid}/facts", headers=h, json={"base_version": v, "fields": edits})
    assert r.status_code == 200, r.text
    v = client.get(f"/api/v1/cases/{cid}/facts").json()["version"]
    assert client.post(f"/api/v1/cases/{cid}/facts/confirm", json={"base_version": v}, headers=h).status_code == 200
    return cid


def _analyse(client: TestClient, h: dict[str, str], cid: str) -> dict[str, Any]:
    r = client.post(f"/api/v1/cases/{cid}/analyses", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202, r.text
    body: dict[str, Any] = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()
    return body


def _codes(a: dict[str, Any]) -> list[str]:
    return [g["reason_code"] for g in a["abstentions"]]


REJECTED = [
    {"name": "insurer", "value": "Sample Health Insurance Co. Ltd."},
    {"name": "decision_letter_date", "value": "02/07/2026"},
    {"name": "decision_type", "value": "repudiation"},
    {"name": "claimed_paise", "value": "185000"},
]


@pytest.mark.req("FR-019")
def test_no_reason_found_offers_typing_it_and_the_typed_reason_is_kept(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _case(client, h, "rejected", REJECTED)
    a = _analyse(client, h, cid)
    assert a["status"] == "succeeded" and a["reasons"] == []
    gap = next(g for g in a["abstentions"] if g["reason_code"] == "no_reasons_found")
    assert gap["recovery"] == ["type_reason", "upload_page"]  # AC2: never an empty screen without a way on

    typed = "  Claim not payable as per policy terms and conditions.  "
    r = client.post(f"/api/v1/cases/{cid}/reasons", json={"text": typed}, headers=h)
    assert r.status_code == 202, r.text
    a = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()
    assert a["id"] == r.json()["analysis_id"] and "no_reasons_found" not in _codes(a)
    reason = a["reasons"][0]
    assert reason["text"] == typed.strip() and reason["user_entered"] is True  # stored verbatim, as confirmed
    assert reason["audit_status"] == "NO_CLAUSE_CITED" and reason["counter_point_ids"]

    _upload(client, h, cid, [*NOTHING, "Page 2"])  # reading another page must not drop what the user typed
    assert [x["text"] for x in _analyse(client, h, cid)["reasons"]] == [typed.strip()]

    r = client.delete(f"/api/v1/cases/{cid}/reasons/{reason['id']}", headers=h)
    assert r.status_code == 202, r.text
    assert "no_reasons_found" in _codes(client.get(f"/api/v1/cases/{cid}/analyses/latest").json())


@pytest.mark.req("FR-019")
def test_a_typed_reason_needs_text_and_confirmed_details(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _case(client, h, "rejected", REJECTED)
    r = client.post(f"/api/v1/cases/{cid}/reasons", json={"text": "   "}, headers=h)
    assert r.status_code == 422
    r = client.post(
        "/api/v1/cases",
        json={"eligibility": {**ELIGIBILITY, "situation": "rejected"}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    unconfirmed = r.json()["id"]
    r = client.post(f"/api/v1/cases/{unconfirmed}/reasons", json={"text": "Not payable."}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "fields_not_confirmed"
    assert client.get(f"/api/v1/cases/{unconfirmed}/analyses/latest").status_code == 404  # nothing half-saved


@pytest.mark.req("FR-019")
def test_a_reason_read_from_the_letter_cannot_be_removed(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "letter-reason@example.com")
    reason = client.get(f"/api/v1/cases/{cid}/analyses/latest").json()["reasons"][0]
    assert reason["user_entered"] is False
    r = client.delete(f"/api/v1/cases/{cid}/reasons/{reason['id']}", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "reason_from_letter"


@pytest.mark.req("FR-019")
def test_unknown_wording_gives_limited_states_for_the_case_and_each_cited_clause(
    client: TestClient, ctx: AppContext
) -> None:
    h = sign_in(client, ctx)
    partial = [
        {"name": "insurer", "value": "Unlisted Insurer Ltd."},
        {"name": "decision_letter_date", "value": "10/09/2026"},
        {"name": "decision_type", "value": "partial"},
        {"name": "claimed_paise", "value": "264820"},
        {"name": "paid_paise", "value": "210500"},
    ]
    cid = _case(client, h, "partly_paid", partial)
    li = client.get(f"/api/v1/cases/{cid}/line-items").json()
    items = [
        {"description": "Consumables", "deducted_paise": 625000},
        {"description": "Room rent", "deducted_paise": 900000, "clause_cited_verbatim": "Clause 4.2"},
    ]
    r = client.put(f"/api/v1/cases/{cid}/line-items", headers=h, json={"base_version": li["version"], "items": items})
    assert r.status_code == 200, r.text
    v = client.get(f"/api/v1/cases/{cid}/line-items").json()["version"]
    r = client.post(f"/api/v1/cases/{cid}/line-items/confirm", json={"base_version": v}, headers=h)
    assert r.status_code == 200
    a = _analyse(client, h, cid)
    assert a["mode"] == "limited"
    by_code = {g["reason_code"]: g for g in a["abstentions"]}
    assert by_code["no_wording"]["recovery"] == ["upload_wording", "check_insurer", "contact_support"]
    room = next(i for i in a["line_items"] if i["description"] == "Room rent")
    assert room["audit_status"] == "CANNOT_ASSESS" and room["abstention"] == "clause_not_checkable"
    assert by_code["clause_not_checkable"]["target_id"] == room["id"]
    consumables = next(i for i in a["line_items"] if i["description"] == "Consumables")
    assert consumables["audit_status"] == "NO_CLAUSE_CITED" and consumables["abstention"] is None


@pytest.mark.req("FR-019")
def test_each_trigger_maps_to_one_distinct_state_with_recovery() -> None:
    """AC1, for the triggers the deterministic pipeline can raise (the model's own arrive with the AI step)."""
    failed = Analysis(status="failed", mode="full")
    assert [g["reason_code"] for g in abstentions(failed, [], [], 0)] == ["analysis_failed"]
    assert abstentions(Analysis(status="running", mode="full"), [], [], 0) == []
    ok = Analysis(status="succeeded", mode="full")
    item = LineItem(id=uuid.uuid4(), description="x", deducted_paise=100, audit_status="NO_CLAUSE_CITED")
    assert [g["reason_code"] for g in abstentions(ok, [item], [], 1)] == ["document_unreadable"]
    reason = DecisionReason(id=uuid.uuid4(), text_verbatim="x", audit_status="CANNOT_ASSESS")
    assert abstentions(ok, [], [reason], 0) == []  # clause found in the wording: a full analysis, not a gap
    assert len(set(RECOVERY)) == len(RECOVERY) and all(RECOVERY.values())
