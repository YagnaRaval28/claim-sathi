"""The policy wording a user uploads (PRD FR-014): used first, case-scoped, and switchable with the library."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from claimsathi.context import AppContext
from claimsathi.devtools.pdfgen import text_pdf
from claimsathi.models import KnowledgeChunk
from tests.conftest import sign_in
from tests.test_integration_abstentions import _analyse, _case
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration
WORDING = [  # SYNTHETIC policy wording, not a real product
    "Sample Unlisted Health Policy - Policy Wording (SYNTHETIC)",
    "Clause 4.2 Room rent is payable up to the room category stated in the schedule.",
    "Clause 5.1 Consumables listed in Annexure II are not payable.",
]
PARTIAL = [
    {"name": "insurer", "value": "Unlisted Insurer Ltd."},
    {"name": "decision_letter_date", "value": "10/09/2026"},
    {"name": "decision_type", "value": "partial"},
    {"name": "claimed_paise", "value": "264820"},
    {"name": "paid_paise", "value": "210500"},
]


def _upload_wording(client: TestClient, h: dict[str, str], cid: str) -> None:
    r = client.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "policy_wording"},
        files={"file": ("wording.pdf", text_pdf(WORDING), "application/pdf")},
    )
    assert r.status_code == 202, r.text


def _items(client: TestClient, h: dict[str, str], cid: str) -> None:
    li = client.get(f"/api/v1/cases/{cid}/line-items").json()
    items = [
        {"description": "Room rent", "deducted_paise": 900000, "clause_cited_verbatim": "Clause 4.2"},
        {"description": "Nursing", "deducted_paise": 300000, "clause_cited_verbatim": "Clause 9.9"},
    ]
    r = client.put(f"/api/v1/cases/{cid}/line-items", headers=h, json={"base_version": li["version"], "items": items})
    assert r.status_code == 200, r.text
    v = client.get(f"/api/v1/cases/{cid}/line-items").json()["version"]
    r = client.post(f"/api/v1/cases/{cid}/line-items/confirm", json={"base_version": v}, headers=h)
    assert r.status_code == 200, r.text


def _status(a: dict[str, Any], description: str) -> str:
    return str(next(i["audit_status"] for i in a["line_items"] if i["description"] == description))


@pytest.mark.req("FR-014")
def test_uploaded_wording_turns_limited_mode_into_clause_checks(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _case(client, h, "partly_paid", PARTIAL)
    _items(client, h, cid)
    a = _analyse(client, h, cid)
    assert a["mode"] == "limited" and _status(a, "Nursing") == "CANNOT_ASSESS"

    facts_before = client.get(f"/api/v1/cases/{cid}/facts").json()["fields"]
    _upload_wording(client, h, cid)
    case = client.get(f"/api/v1/cases/{cid}").json()
    assert case["documents"][-1]["status"] == "ready"
    assert client.get(f"/api/v1/cases/{cid}/analyses/latest").json()["stale"] is True  # must be checked again
    assert client.get(f"/api/v1/cases/{cid}/facts").json()["fields"] == facts_before  # wording isn't a letter

    a = _analyse(client, h, cid)
    assert a["mode"] == "full" and a["wording"]["mode"] == "uploaded"  # AC1: the source is shown
    assert a["wording"]["title"] == "Your uploaded policy wording"
    assert _status(a, "Room rent") == "CANNOT_ASSESS"  # clause found in the wording
    assert _status(a, "Nursing") == "CLAUSE_NOT_FOUND"  # cited clause isn't in the wording
    assert "no_wording" not in [g["reason_code"] for g in a["abstentions"]]
    assert a["wording_choice"] == {"uploaded": True, "library": False, "preference": "auto"}


@pytest.mark.req("FR-014")
def test_uploaded_wording_is_only_visible_within_its_case(client: TestClient, ctx: AppContext) -> None:
    ha = sign_in(client, ctx, "wording-owner@example.com")
    cid = _case(client, ha, "partly_paid", PARTIAL)
    _upload_wording(client, ha, cid)
    with ctx.session_factory() as s:
        chunk = s.scalars(
            select(KnowledgeChunk).where(
                KnowledgeChunk.case_id == uuid.UUID(cid), KnowledgeChunk.clause_ref == "Clause 4.2"
            )
        ).first()
        assert chunk is not None
    assert client.get(f"/api/v1/cases/{cid}/sources/chunks/{chunk.id}").status_code == 200
    client.cookies.clear()
    hb = sign_in(client, ctx, "wording-other@example.com")
    other = _case(client, hb, "partly_paid", PARTIAL)
    r = client.get(f"/api/v1/cases/{other}/sources/chunks/{chunk.id}")
    assert r.status_code == 404 and r.json()["code"] == "not_found"  # AC3, through B's own case


@pytest.mark.req("FR-014")
def test_user_can_switch_between_uploaded_and_library_wording(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, "wording-switch@example.com")
    cid, a = _to_findings(client, h)
    assert a["wording"]["mode"] == "library"
    r = client.put(f"/api/v1/cases/{cid}/wording", json={"mode": "uploaded"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "wording_unavailable"

    _upload_wording(client, h, cid)
    a = _analyse(client, h, cid)
    assert a["wording"]["mode"] == "uploaded" and a["wording_choice"]["library"] is True
    assert client.put(f"/api/v1/cases/{cid}/wording", json={"mode": "library"}, headers=h).status_code == 200
    assert client.get(f"/api/v1/cases/{cid}/analyses/latest").json()["stale"] is True
    a = _analyse(client, h, cid)
    assert a["wording"]["mode"] == "library" and a["wording_choice"]["preference"] == "library"
