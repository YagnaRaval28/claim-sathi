"""Bima Bharosa copy-ready complaint content (PRD FR-025, P1)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimsathi.context import AppContext
from tests.conftest import sign_in
from tests.test_integration_escalation import _event
from tests.test_integration_rules_checklist import _rejected_case
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


def _fields(client: TestClient, cid: str) -> dict[str, Any]:
    r = client.get(f"/api/v1/cases/{cid}/packs/bima-bharosa")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    assert body["portal_url"] == "https://bimabharosa.irdai.gov.in" and body["toll_free"] == "155255"
    return {f["key"]: f for f in body["fields"]}


@pytest.mark.req("FR-025")
def test_partly_paid_content_reuses_confirmed_amounts_and_verified_grounds(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    f = _fields(client, cid)
    assert f["claim_number"]["value"] == "SHI/CL/2026/000123" and f["amount_claimed"]["value"] == "₹2,64,820"
    assert f["amount_paid"]["value"] == "₹2,10,500" and f["amount_disputed"]["value"] == "₹25,900"
    assert "partly paid my health insurance claim SHI/CL/2026/000123" in f["summary"]["value"]
    # AC1: the grounds are the verified ones, each with the source it was verified against.
    assert "does not cite a specific term or condition of my policy" in f["grounds"]["value"]
    assert "(Source: Sample Regulation 001 (SYNTHETIC, not a real regulation), Para 17(b))" in f["grounds"]["value"]
    assert all(x["length"] == len(x["value"]) for x in f.values())  # counts shown; nothing is cut (OQ-04)
    assert "grievance_date" not in f


@pytest.mark.req("FR-025")
def test_rejected_content_includes_the_logged_grievance_date(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "bima@example.com")
    r = _event(client, h, cid, "s1_sent", "2026-07-10", {"method": "email"})
    assert r.status_code == 201, r.text
    f = _fields(client, cid)
    assert "rejected my health insurance claim SHI/CL/2026/000456" in f["summary"]["value"]
    assert f["grievance_date"]["value"] == "10/07/2026" and "on 10/07/2026" in f["summary"]["value"]
    assert "amount_paid" not in f and "claims review committee" in f["grounds"]["value"]


def test_content_needs_findings_first(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    from tests.test_integration_vs1 import _new_case

    cid = _new_case(client, h)["id"]
    assert client.get(f"/api/v1/cases/{cid}/packs/bima-bharosa").status_code == 409
