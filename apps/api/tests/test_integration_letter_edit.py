"""Letter editing that preserves verified citations (PRD FR-027)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from claimsathi.context import AppContext
from claimsathi.letters.render import letter_html
from tests.conftest import sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


def _letter(client: TestClient, ctx: AppContext) -> tuple[dict[str, str], dict[str, Any]]:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201
    return h, r.json()


def _patch(client: TestClient, h: dict[str, str], letter: dict[str, Any], blocks: list[dict[str, Any]]) -> Response:
    resp: Response = client.patch(
        f"/api/v1/letters/{letter['id']}", json={"base_version": letter["version"], "blocks": blocks}, headers=h
    )
    return resp


@pytest.mark.req("FR-027")
def test_free_text_edits_keep_the_verified_quote(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    blocks = [dict(b) for b in letter["doc"]["blocks"]]
    blocks.insert(5, {"type": "para", "text": "I have been a customer for 12 years."})
    r = _patch(client, h, letter, blocks)
    assert r.status_code == 200, r.text
    edited = r.json()
    quotes = [b for b in edited["doc"]["blocks"] if b["type"] == "quote"]
    assert len(quotes) == 1 and quotes[0]["footnote"] == 1 and len(edited["doc"]["footnotes"]) == 1
    assert edited["version"] == 2 and edited["reviewed_version"] is None  # must be read again


@pytest.mark.req("FR-027")
def test_editing_a_quote_removes_the_badge_and_undo_restores_it(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    original = [dict(b) for b in letter["doc"]["blocks"]]
    i = next(n for n, b in enumerate(original) if b["type"] == "quote")
    changed = [dict(b) for b in original]
    changed[i] = {**changed[i], "text": changed[i]["text"].replace("specific", "exact")}
    r = _patch(client, h, letter, changed)
    edited = r.json()
    assert edited["doc"]["blocks"][i]["type"] == "para" and edited["doc"]["blocks"][i]["edited"] is True
    assert edited["doc"]["footnotes"] == []  # AC1: no longer verified in the UI ...
    html = letter_html(edited["doc"])
    assert "<blockquote" not in html and "<sup>" not in html  # ... nor in the export
    r = _patch(client, h, edited, original)  # AC2: undo puts the generated quote back
    restored = r.json()
    assert restored["doc"]["blocks"][i]["type"] == "quote" and len(restored["doc"]["footnotes"]) == 1


def test_a_forged_quote_is_never_verified(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    blocks = [dict(b) for b in letter["doc"]["blocks"]]
    cid = next(b["citation_id"] for b in blocks if b["type"] == "quote")
    blocks.append({"type": "quote", "text": "The rule says insurers must pay everything.", "citation_id": cid})
    edited = _patch(client, h, letter, blocks).json()
    assert [b["type"] for b in edited["doc"]["blocks"]].count("quote") == 1
    assert edited["doc"]["blocks"][-1]["type"] == "para"


def test_edit_needs_the_current_version_and_review_again(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    assert client.post(f"/api/v1/letters/{letter['id']}/review", json={"version": 1}, headers=h).status_code == 200
    edited = _patch(client, h, letter, letter["doc"]["blocks"]).json()
    r = _patch(client, h, letter, letter["doc"]["blocks"])  # stale base_version
    assert r.status_code == 409 and r.json()["code"] == "version_conflict"
    r = client.post(f"/api/v1/letters/{letter['id']}/exports", json={"format": "pdf"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "letter_not_reviewed"
    assert edited["version"] == 2


@pytest.mark.req("NFR-017")
def test_only_the_owner_can_edit(client: TestClient, ctx: AppContext) -> None:
    _h, letter = _letter(client, ctx)
    client.cookies.clear()
    hb = sign_in(client, ctx, "editor-intruder@example.com")
    assert _patch(client, hb, letter, letter["doc"]["blocks"]).status_code == 404
