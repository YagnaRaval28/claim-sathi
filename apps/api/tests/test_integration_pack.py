"""Ombudsman complaint pack (PRD FR-026): guarded by the RULE-ESC checks, history from logged events."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from claimsathi.context import AppContext
from claimsathi.core.clock import IST, set_clock
from tests.conftest import sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


@pytest.fixture
def clock() -> Any:
    def go(day: str) -> None:
        moment = datetime.fromisoformat(day).replace(hour=12, tzinfo=IST)
        set_clock(lambda: moment)

    yield go
    set_clock(None)


def _event(
    client: TestClient, h: dict[str, str], cid: str, kind: str, day: str, meta: dict[str, Any] | None = None
) -> Response:
    r: Response = client.post(
        f"/api/v1/cases/{cid}/events",
        json={"kind": kind, "event_date": day, "metadata": meta or {}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.text
    return r


def _pack(client: TestClient, h: dict[str, str], cid: str) -> Response:
    resp: Response = client.post(
        f"/api/v1/cases/{cid}/packs/ombudsman", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())}
    )
    return resp


def _text(letter: dict[str, Any]) -> str:
    return " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in letter["doc"]["blocks"])


@pytest.mark.req("FR-026")
def test_pack_is_refused_while_blocked_and_history_matches_events(
    client: TestClient, ctx: AppContext, clock: Any
) -> None:
    clock("2026-10-17")
    email = "pack@example.com"
    h = sign_in(client, ctx, email)
    cid, _ = _to_findings(client, h)
    r = _pack(client, h, cid)
    assert r.status_code == 409 and r.json()["code"] == "escalation_blocked"  # nothing logged yet
    _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"})
    r = _pack(client, h, cid)
    assert r.status_code == 409 and "RULE-ESC-02" in r.json()["rule_keys"]  # within the one month

    clock("2026-11-16")
    h = sign_in(client, ctx, email, consent=False)
    _event(client, h, cid, "s2_filed", "2026-10-20", {"token": "BB-77"})
    r = _pack(client, h, cid)
    assert r.status_code == 202, r.text
    pack = client.get(f"/api/v1/cases/{cid}/packs/ombudsman").json()
    letter = pack["letter"]
    assert letter["stage"] == "S3" and letter["id"] == r.json()["letter_id"]
    text = _text(letter)
    assert "On 15/10/2026 I wrote to the insurer's grievance redressal officer by email" in text
    assert "The insurer has not replied within one month of my letter." in text
    assert "On 20/10/2026 I also filed a complaint on Bima Bharosa." in text
    assert "₹25,900" in text and "Ravi K. Mehta" in text and "not pending before" in text
    assert "a statement that the insurer did not reply" in text
    keys = {e["key"]: e["present"] for e in pack["enclosures"]}
    assert keys == {"decision_letter": True, "s1_letter": False, "no_reply_statement": True}
    assert pack["filing"]["portal_url"] == "https://cioins.co.in" and pack["signatory"]["is_helper"] is False


@pytest.mark.req("FR-026")
def test_pack_needs_each_warning_acknowledged(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    email = "late@example.com"
    h = sign_in(client, ctx, email)
    cid, _ = _to_findings(client, h)
    _event(client, h, cid, "s1_sent", "2026-09-12", {"method": "post"})
    _event(client, h, cid, "insurer_reply", "2026-09-20", {"satisfied": False})
    clock("2027-09-21")  # one year after the reply: late (RULE-ESC-03 warns, does not block)
    h = sign_in(client, ctx, email, consent=False)
    r = _pack(client, h, cid)
    assert r.status_code == 409 and r.json()["code"] == "warnings_not_acknowledged"
    assert r.json()["rule_keys"] == ["RULE-ESC-03"]
    url = f"/api/v1/cases/{cid}/escalation/acknowledgements"
    assert client.post(url, json={"rule_keys": ["RULE-ESC-03"]}, headers=h).status_code == 204
    r = _pack(client, h, cid)
    assert r.status_code == 202, r.text
    text = _text(client.get(f"/api/v1/cases/{cid}/packs/ombudsman").json()["letter"])
    assert "On 20/09/2026 the insurer replied. I am not satisfied with the reply." in text
    assert "(iii) the insurer's reply" in text


@pytest.mark.req("NFR-017")
def test_pack_endpoints_are_owner_only(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, "pack-owner@example.com")
    cid, _ = _to_findings(client, h)
    client.cookies.clear()
    hb = sign_in(client, ctx, "pack-intruder@example.com")
    assert client.get(f"/api/v1/cases/{cid}/packs/ombudsman").status_code == 404
    assert _pack(client, hb, cid).status_code == 404
