"""Data controls through the API (PRD FR-030 to FR-036)."""

from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from claimsathi.context import AppContext
from claimsathi.core.clock import IST, now_utc
from claimsathi.datacontrols.service import run_retention
from claimsathi.models import AuditLog, Case, CaseEvent, Document, ExtractedField, Outbox, ReviewItem, User
from tests.conftest import code_in, csrf_headers, last_mail_to, sent_mail, sign_in, store_keys
from tests.test_integration_vs1 import _new_case, _to_findings, _upload_syn001

pytestmark = pytest.mark.integration


def _challenge(client: TestClient, h: dict[str, str], url: str) -> dict[str, str]:
    r = client.post(url, headers=h)
    assert r.status_code == 200, r.text
    body: dict[str, str] = r.json()
    return body


def _store_keys(ctx: AppContext, prefix: str) -> list[str]:
    return store_keys(ctx, prefix)


@pytest.mark.req("FR-031")
def test_delete_case_needs_the_typed_code_and_removes_everything(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert _store_keys(ctx, f"cases/{cid}/")
    ch = _challenge(client, h, f"/api/v1/cases/{cid}/delete-challenge")
    assert re.fullmatch(r"\d{4}", ch["code"])
    wrong = f"{(int(ch['code']) + 1) % 10_000:04d}"
    r = client.request(
        "DELETE",
        f"/api/v1/cases/{cid}",
        json={"confirm_code": wrong},
        headers={**h, "X-Confirm-Challenge": ch["challenge_id"]},
    )
    assert r.status_code == 422 and r.json()["code"] == "confirmation_invalid"
    r = client.request(
        "DELETE",
        f"/api/v1/cases/{cid}",
        json={"confirm_code": ch["code"]},
        headers={**h, "X-Confirm-Challenge": ch["challenge_id"]},
    )
    assert r.status_code == 202
    assert client.get(f"/api/v1/cases/{cid}").status_code == 404
    assert _store_keys(ctx, f"cases/{cid}/") == []
    with ctx.session_factory() as s:
        assert s.get(Case, uuid.UUID(cid)) is None
        assert s.scalar(select(func.count(ExtractedField.id)).where(ExtractedField.case_id == uuid.UUID(cid))) == 0
        assert s.scalar(select(func.count(Outbox.id)).where(Outbox.dedupe_key.like(f"%{cid}%"))) == 0
        audit = s.scalars(select(AuditLog).where(AuditLog.entity_id == cid)).all()
        assert [(a.action, a.entity_type) for a in audit] == [("case_deleted", "case")]


def test_a_challenge_is_bound_to_its_case(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    a, b = _new_case(client, h)["id"], _new_case(client, h)["id"]
    ch = _challenge(client, h, f"/api/v1/cases/{a}/delete-challenge")
    r = client.request(
        "DELETE",
        f"/api/v1/cases/{b}",
        json={"confirm_code": ch["code"]},
        headers={**h, "X-Confirm-Challenge": ch["challenge_id"]},
    )
    assert r.status_code == 422


@pytest.mark.req("FR-032")
def test_delete_account_then_sign_in_creates_a_fresh_empty_account(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, "gone@example.com")
    old_id = client.get("/api/v1/me").json()["id"]
    cid = _new_case(client, h)["id"]
    _upload_syn001(client, h, cid)
    ch = _challenge(client, h, "/api/v1/me/delete-challenge")
    r = client.request(
        "DELETE",
        "/api/v1/me",
        json={"confirm_code": ch["code"]},
        headers={**h, "X-Confirm-Challenge": ch["challenge_id"]},
    )
    assert r.status_code == 202
    assert sent_mail(ctx)[-1]["subject"] == "Your ClaimSathi account was deleted"
    assert client.get("/api/v1/me").status_code == 401
    assert _store_keys(ctx, f"cases/{cid}/") == []
    with ctx.session_factory() as s:
        assert s.get(User, uuid.UUID(old_id)) is None
    client.cookies.clear()
    sign_in(client, ctx, "gone@example.com")
    me = client.get("/api/v1/me").json()
    assert me["id"] != old_id and client.get("/api/v1/cases").json()["items"] == []


@pytest.mark.req("FR-030")
def test_export_my_data_zip(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    r = client.post("/api/v1/exports", json={"scope": "account"}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 202
    view = client.get(f"/api/v1/exports/{r.json()['id']}").json()
    assert view["status"] == "ready" and view["download_path"]
    expires = datetime.fromisoformat(view["expires_at"])
    assert timedelta(hours=23) < expires - now_utc() <= timedelta(hours=24)
    z = zipfile.ZipFile(io.BytesIO(client.get(view["download_path"]).content))
    names = set(z.namelist())
    for n in ("facts.json", "line_items.json", "analysis.json", "letters.json", "events.json", "case.json"):
        assert f"case-01/{n}" in names
    assert "consents.json" in names and any(n.startswith("case-01/documents/") for n in names)
    facts = {f["name"]: f for f in json.loads(z.read("case-01/facts.json"))}
    assert facts["claim_number"]["value"] == "SHI/CL/2026/000123"  # the user's own data, decrypted for them
    client.cookies.clear()
    sign_in(client, ctx, "someone-else@example.com")
    assert client.get(f"/api/v1/exports/{r.json()['id']}").status_code == 404
    assert client.get(view["download_path"]).status_code == 404
    assert cid


@pytest.mark.req("FR-033")
def test_retention_deletes_eligible_cases_and_leaves_the_others(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    closed_old, closed_new, idle, active = (_new_case(client, h)["id"] for _ in range(3)), None, None, None
    ids = list(closed_old)
    closed_old, closed_new, idle = ids
    for cid in ids:
        _upload_syn001(client, h, cid)
    now = now_utc()
    with ctx.session_factory() as s:
        for cid, closed_days_ago in ((closed_old, 91), (closed_new, 10)):
            case = s.get(Case, uuid.UUID(cid))
            assert case is not None
            case.status, case.stage = "closed", "CLOSED"
            case.closed_at = now - timedelta(days=closed_days_ago)
            case.retention_delete_after = case.closed_at + timedelta(days=90)
        idle_case = s.get(Case, uuid.UUID(idle))
        assert idle_case is not None
        idle_case.last_activity_at = now - timedelta(days=600)
        s.commit()
    out = run_retention(ctx, now)
    assert out["files_deleted"] == 1 and out["notices"] == 1 and out["cases_deleted"] == 0
    assert _store_keys(ctx, f"cases/{closed_old}/documents/") == []
    assert _store_keys(ctx, f"cases/{closed_new}/documents/")
    with ctx.session_factory() as s:
        assert s.scalar(select(func.count(Document.id)).where(Document.case_id == uuid.UUID(closed_old))) == 0
        assert s.get(Case, uuid.UUID(closed_old)) is not None  # the case and letters stay; only source files go
    later = run_retention(ctx, now + timedelta(days=31))
    assert later["cases_deleted"] == 1
    with ctx.session_factory() as s:
        assert s.get(Case, uuid.UUID(idle)) is None and s.get(Case, uuid.UUID(closed_new)) is not None
    assert active is None


@pytest.mark.req("FR-033")
def test_closing_sets_retention_and_it_can_be_extended_once(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    today = datetime.now(IST).date().isoformat()
    r = client.post(
        f"/api/v1/cases/{cid}/events",
        json={"kind": "closed", "event_date": today, "metadata": {}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    with ctx.session_factory() as s:
        case = s.get(Case, uuid.UUID(cid))
        assert case is not None and case.retention_delete_after is not None and case.closed_at is not None
        first = case.retention_delete_after
        assert first - case.closed_at == timedelta(days=90)
    assert client.post(f"/api/v1/cases/{cid}/retention/extend", headers=h).status_code == 200
    r = client.post(f"/api/v1/cases/{cid}/retention/extend", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "retention_already_extended"
    with ctx.session_factory() as s:
        case = s.get(Case, uuid.UUID(cid))
        assert case is not None and case.retention_delete_after == first + timedelta(days=90)
        ev = s.scalar(select(CaseEvent).where(CaseEvent.case_id == uuid.UUID(cid)))
        assert ev is not None
    assert client.delete(f"/api/v1/cases/{cid}/events/{ev.id}", headers=h).status_code == 204  # reopen
    with ctx.session_factory() as s:
        case = s.get(Case, uuid.UUID(cid))
        assert case is not None and case.status == "open" and case.retention_delete_after is None


@pytest.mark.req("FR-034")
def test_outcome_answers_are_all_optional(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    assert client.put(f"/api/v1/cases/{cid}/outcome", json={}, headers=h).status_code == 200
    body: dict[str, Any] = {"outcome": "partly_paid", "amount_received_paise": 1_000_000, "rating": 4}
    assert client.put(f"/api/v1/cases/{cid}/outcome", json=body, headers=h).status_code == 200
    with ctx.session_factory() as s:
        case = s.get(Case, uuid.UUID(cid))
        assert case is not None and case.outcome is not None and case.outcome["rating"] == 4
    assert client.put(f"/api/v1/cases/{cid}/outcome", json={"rating": 6}, headers=h).status_code == 422


@pytest.mark.req("FR-035")
def test_report_holds_only_the_flagged_output(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid, a = _to_findings(client, h)
    cp = a["counter_points"][0]
    r = client.post(
        "/api/v1/reports",
        json={
            "case_id": cid,
            "target_type": "counter_point",
            "target_id": cp["id"],
            "reason": "wrong_rule",
            "comment": "Not my case",
            "grant_access": False,
        },
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.text
    with ctx.session_factory() as s:
        item = s.scalar(select(ReviewItem).where(ReviewItem.source == "user_report"))
        assert item is not None and item.reason == "wrong_rule" and item.comment == "Not my case"
        text = json.dumps(item.payload)
        assert cp["statement"] in text and "Para 17(b)" in text
        for private in ("SHI/CL", "Ravi", "2,64,820"):
            assert private not in text
    letter = client.post(
        f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())}
    ).json()
    r = client.post(
        "/api/v1/reports",
        json={
            "case_id": cid,
            "target_type": "letter_block",
            "target_id": letter["id"],
            "block_index": 99,
            "reason": "other",
        },
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 404


@pytest.mark.req("FR-036")
def test_change_email_with_a_code_and_consent_history(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, "old@example.com")
    assert client.post("/api/v1/me/email", json={"new_email": "new@example.com"}, headers=h).status_code == 204
    code = code_in(last_mail_to(ctx, "new@example.com")["text"])
    bad = f"{(int(code) + 1) % 1_000_000:06d}"
    assert client.post("/api/v1/me/email/verify", json={"code": bad}, headers=h).status_code == 401
    assert client.post("/api/v1/me/email/verify", json={"code": code}, headers=h).status_code == 204
    assert client.get("/api/v1/me").json()["email_masked"] == "n•••@example.com"
    v = client.get("/api/v1/consent/notice").json()["version"]
    client.post("/api/v1/consents", json={"version": v, "purposes": ["processing", "reminders"]}, headers=h)
    items = client.get("/api/v1/me/consents").json()["items"]
    assert items[0]["purposes"] == ["processing", "reminders"] and len(items) == 2
    client.cookies.clear()
    sign_in(client, ctx, "taken@example.com")
    h2 = csrf_headers(client)
    r = client.post("/api/v1/me/email", json={"new_email": "new@example.com"}, headers=h2)
    assert r.status_code == 409 and r.json()["code"] == "email_in_use"


@pytest.mark.req("NFR-017")
def test_data_control_endpoints_are_owner_only(client: TestClient, ctx: AppContext) -> None:
    ha = sign_in(client, ctx, "owner-dc@example.com")
    cid, a = _to_findings(client, ha)
    exp = client.post(
        "/api/v1/exports", json={"scope": "case", "case_id": cid}, headers={**ha, "Idempotency-Key": str(uuid.uuid4())}
    ).json()
    client.cookies.clear()
    hb = sign_in(client, ctx, "intruder-dc@example.com")
    assert client.post(f"/api/v1/cases/{cid}/delete-challenge", headers=hb).status_code == 404
    r = client.request(
        "DELETE", f"/api/v1/cases/{cid}", json={"confirm_code": "0000"}, headers={**hb, "X-Confirm-Challenge": "x"}
    )
    assert r.status_code == 404
    assert client.post(f"/api/v1/cases/{cid}/retention/extend", headers=hb).status_code == 404
    assert client.put(f"/api/v1/cases/{cid}/outcome", json={}, headers=hb).status_code == 404
    r = client.post(
        "/api/v1/exports", json={"scope": "case", "case_id": cid}, headers={**hb, "Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 404
    assert client.get(f"/api/v1/exports/{exp['id']}").status_code == 404
    r = client.post(
        "/api/v1/reports",
        json={
            "case_id": cid,
            "target_type": "counter_point",
            "target_id": a["counter_points"][0]["id"],
            "reason": "other",
        },
        headers={**hb, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 404
