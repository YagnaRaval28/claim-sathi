"""Escalation through the API: events, stage, deadlines, Ombudsman checks, reminders (PRD FR-020 to FR-023)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from claimsathi.context import AppContext
from claimsathi.core.clock import IST, set_clock
from claimsathi.escalation.service import send_due_reminders
from claimsathi.models import Reminder
from tests.conftest import csrf_headers, sign_in
from tests.test_integration_vs1 import _new_case, _upload_syn001

pytestmark = pytest.mark.integration


def _at(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(hour=12, tzinfo=IST)


@pytest.fixture
def clock() -> Any:
    def go(day: str) -> None:
        moment = _at(day)
        set_clock(lambda: moment)

    yield go
    set_clock(None)


def _case(client: TestClient, ctx: AppContext, *, reminders: bool = True) -> tuple[dict[str, str], str]:
    email = f"esc-{uuid.uuid4().hex[:8]}@example.com"
    client.headers["x-test-email"] = email  # remembered so a test can sign in again after moving the clock
    h = sign_in(client, ctx, email)
    if reminders:
        v = client.get("/api/v1/consent/notice").json()["version"]
        r = client.post("/api/v1/consents", json={"version": v, "purposes": ["processing", "reminders"]}, headers=h)
        assert r.status_code == 201
    cid = _new_case(client, h)["id"]
    _upload_syn001(client, h, cid)  # decision letter dated 10/09/2026
    return h, cid


def _event(client: TestClient, h: dict[str, str], cid: str, kind: str, day: str, meta: dict[str, Any] | None = None):
    return client.post(
        f"/api/v1/cases/{cid}/events",
        json={"kind": kind, "event_date": day, "metadata": meta or {}},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )


def _esc(client: TestClient, cid: str) -> dict[str, Any]:
    r = client.get(f"/api/v1/cases/{cid}/escalation")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.req("FR-023")
def test_event_dates_cannot_be_future_or_before_the_decision(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    r = _event(client, h, cid, "s1_sent", "2026-10-18", {"method": "email"})
    assert r.status_code == 422 and r.json()["errors"][0]["code"] == "future"
    r = _event(client, h, cid, "s1_sent", "2026-09-09", {"method": "email"})
    assert r.status_code == 422 and r.json()["errors"][0]["code"] == "before_decision"
    r = _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "fax"})
    assert r.status_code == 422  # metadata validated per event kind
    assert _esc(client, cid)["events"] == []


@pytest.mark.req("FR-023")
def test_s1_sent_starts_the_clock_and_s3_is_blocked_until_eligible(
    client: TestClient, ctx: AppContext, clock: Any
) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    e = _esc(client, cid)
    assert e["stage"] == "S0_PREPARE" and e["next_action"]["key"] == "send_letter" and e["blocked"] is True
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201
    e = _esc(client, cid)
    assert e["stage"] == "S1_INSURER_GRIEVANCE"
    d = {x["kind"]: x for x in e["deadlines"]}
    assert d["ombudsman_eligible_from"]["due_date"] == "2026-11-15"
    assert d["ombudsman_limitation"]["due_date"] == "2027-11-15"
    assert (
        d["insurer_response_expected"]["due_date"] == "2026-10-29" and d["insurer_response_expected"]["days_left"] == 12
    )
    assert d["ombudsman_eligible_from"]["rule"]["source_ref"].startswith("Insurance Ombudsman Rules, 2017")
    checks = {c["rule_key"]: c for c in e["ombudsman_checks"]}
    assert checks["RULE-ESC-01"]["result"] == "pass" and checks["RULE-ESC-02"]["result"] == "block"
    assert checks["RULE-ESC-02"]["params"]["date"] == "2026-11-15"
    r = _event(client, h, cid, "s3_filed", "2026-10-17")
    assert r.status_code == 409 and r.json()["code"] == "escalation_blocked"
    assert "RULE-ESC-02" in r.json()["rule_keys"]

    clock("2026-11-16")
    h = sign_in(client, ctx, client.headers["x-test-email"], consent=False)  # the old session idled out
    e = _esc(client, cid)
    assert e["blocked"] is False and e["next_action"]["key"] == "go_to_ombudsman"
    assert _event(client, h, cid, "s3_filed", "2026-11-16", {"reference": "OMB-1"}).status_code == 201
    e = _esc(client, cid)
    assert e["stage"] == "S3_OMBUDSMAN"
    assert {x["kind"] for x in e["deadlines"]} >= {"ombudsman_award_expected"}


@pytest.mark.req("FR-021")
def test_changing_a_source_date_recomputes_deadlines_and_reschedules_reminders(
    client: TestClient, ctx: AppContext, clock: Any
) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    first = _event(client, h, cid, "s1_sent", "2026-10-01", {"method": "post"}).json()
    with ctx.session_factory() as s:
        before = {(r.kind, r.channel) for r in s.scalars(select(Reminder).where(Reminder.status == "scheduled"))}
    assert ("eligibility_open", "email") in before and ("eligibility_open", "in_app") in before
    assert client.delete(f"/api/v1/cases/{cid}/events/{first['id']}", headers=h).status_code == 204
    e = _esc(client, cid)
    assert e["stage"] == "S0_PREPARE" and e["deadlines"] == []
    assert _event(client, h, cid, "s1_sent", "2026-10-16", {"method": "post"}).status_code == 201
    d = {x["kind"]: x["due_date"] for x in _esc(client, cid)["deadlines"]}
    assert d["ombudsman_eligible_from"] == "2026-11-16"
    with ctx.session_factory() as s:
        sched = {
            r.kind: r.send_at.astimezone(IST).date().isoformat()
            for r in s.scalars(select(Reminder).where(Reminder.status == "scheduled", Reminder.channel == "email"))
        }
    assert sched["eligibility_open"] == "2026-11-16"


@pytest.mark.req("FR-022")
def test_due_reminders_are_sent_exactly_once_without_medical_details(
    client: TestClient, ctx: AppContext, clock: Any
) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201
    before = len(ctx.mailer.sent)  # type: ignore[attr-defined]
    due = datetime(2026, 10, 29, 10, tzinfo=IST)
    assert send_due_reminders(ctx, due) == 2  # in-app + email for the expected insurer reply
    assert send_due_reminders(ctx, due) == 0  # duplicate run sends nothing
    mails = ctx.mailer.sent[before:]  # type: ignore[attr-defined]
    assert len(mails) == 1
    body = mails[0]["subject"] + mails[0]["text"]
    # FR-022 AC2: the nickname and the action only; no amounts, claim numbers or medical details
    for banned in ("₹", "Rs.", "2,64,820", "SHI/CL", "Consumables", "Hospital"):
        assert banned not in body
    assert f"/cases/{cid}/track" in body
    notes = client.get("/api/v1/notifications").json()["items"]
    assert [n["kind"] for n in notes] == ["insurer_reply_check"] and notes[0]["read"] is False
    assert client.post(f"/api/v1/notifications/{notes[0]['id']}/read", headers=h).status_code == 204
    assert client.get("/api/v1/notifications").json()["items"][0]["read"] is True


def test_email_reminders_need_the_reminders_consent(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx, reminders=False)
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201
    with ctx.session_factory() as s:
        channels = {r.channel for r in s.scalars(select(Reminder))}
    assert channels == {"in_app"}


@pytest.mark.req("FR-022")
def test_closing_the_case_cancels_reminders_and_stops_new_events(
    client: TestClient, ctx: AppContext, clock: Any
) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201
    assert _event(client, h, cid, "closed", "2026-10-17").status_code == 201
    e = _esc(client, cid)
    assert e["stage"] == "CLOSED" and e["status"] == "closed"
    with ctx.session_factory() as s:
        assert {r.status for r in s.scalars(select(Reminder))} == {"cancelled"}
    assert send_due_reminders(ctx, datetime(2026, 11, 20, tzinfo=IST)) == 0
    r = _event(client, h, cid, "insurer_reply", "2026-10-17", {"satisfied": False})
    assert r.status_code == 409 and r.json()["code"] == "case_closed"
    assert client.get(f"/api/v1/cases/{cid}").json()["status"] == "closed"


def test_only_warnings_can_be_acknowledged(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    url = f"/api/v1/cases/{cid}/escalation/acknowledgements"
    assert client.post(url, json={"rule_keys": ["RULE-ESC-01"]}, headers=h).status_code == 422
    assert client.post(url, json={"rule_keys": ["RULE-ESC-03"]}, headers=h).status_code == 204
    ack = {c["rule_key"]: c["acknowledged"] for c in _esc(client, cid)["ombudsman_checks"]}
    assert ack["RULE-ESC-03"] is True and ack["RULE-ESC-05"] is False


def test_calendar_file_holds_nickname_and_action_only(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201
    r = client.get(f"/api/v1/cases/{cid}/deadlines.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    assert "DTSTART;VALUE=DATE:20261115" in r.text and "Insurance Ombudsman" in r.text
    for banned in ("₹", "SHI/CL", "Consumables"):
        assert banned not in r.text


@pytest.mark.req("NFR-017")
def test_escalation_endpoints_are_owner_only(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    ha, cid = _case(client, ctx)
    ev = _event(client, ha, cid, "s1_sent", "2026-10-15", {"method": "email"}).json()
    send_due_reminders(ctx, datetime(2026, 10, 29, 10, tzinfo=IST))
    note = client.get("/api/v1/notifications").json()["items"][0]["id"]
    client.cookies.clear()
    hb = sign_in(client, ctx, "other-esc@example.com")
    for path in (
        f"/api/v1/cases/{cid}/escalation",
        f"/api/v1/cases/{cid}/events",
        f"/api/v1/cases/{cid}/deadlines.ics",
    ):
        r = client.get(path)
        assert r.status_code == 404 and r.json()["detail"] == "This item isn't available.", path
    assert _event(client, hb, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 404
    assert client.delete(f"/api/v1/cases/{cid}/events/{ev['id']}", headers=hb).status_code == 404
    url = f"/api/v1/cases/{cid}/escalation/acknowledgements"
    assert client.post(url, json={"rule_keys": ["RULE-ESC-03"]}, headers=hb).status_code == 404
    assert client.post(f"/api/v1/notifications/{note}/read", headers=hb).status_code == 404
    assert client.get("/api/v1/notifications").json()["items"] == []
    client.cookies.clear()
    csrf_headers(client)
    assert client.get(f"/api/v1/cases/{cid}/escalation").status_code == 401


def test_reminder_retry_then_failed_after_three_attempts(client: TestClient, ctx: AppContext, clock: Any) -> None:
    clock("2026-10-17")
    h, cid = _case(client, ctx)
    assert _event(client, h, cid, "s1_sent", "2026-10-15", {"method": "email"}).status_code == 201

    class Down:
        def send(self, *, to: str, subject: str, text: str) -> None:
            raise ConnectionError("smtp down")

    real = ctx.mailer
    ctx.mailer = Down()  # type: ignore[misc]
    try:
        t = datetime(2026, 10, 29, 10, tzinfo=IST)
        for _ in range(3):
            send_due_reminders(ctx, t)
            t += timedelta(hours=3)
    finally:
        ctx.mailer = real  # type: ignore[misc]
    with ctx.session_factory() as s:
        r = s.scalar(select(Reminder).where(Reminder.channel == "email", Reminder.kind == "insurer_reply_check"))
        assert r is not None and r.status == "failed" and r.attempts == 3
    assert client.get("/api/v1/notifications").json()["items"][0]["email_failed"] is True
