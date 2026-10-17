"""DOCX export (PRD FR-028): reviewed letters only, citations kept as a numbered Sources list, export logged."""

from __future__ import annotations

import io
import uuid
from typing import Any

import pytest
from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from sqlalchemy import select

from claimsathi.context import AppContext
from claimsathi.models import AuditLog
from tests.conftest import sign_in
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


def _letter(client: TestClient, ctx: AppContext) -> tuple[dict[str, str], dict[str, Any]]:
    h = sign_in(client, ctx)
    cid, _ = _to_findings(client, h)
    r = client.post(f"/api/v1/cases/{cid}/letters", json={}, headers={**h, "Idempotency-Key": str(uuid.uuid4())})
    return h, r.json()


def _docx_text(content: bytes) -> str:
    return "\n".join(p.text for p in DocxDocument(io.BytesIO(content)).paragraphs)


@pytest.mark.req("FR-028")
def test_docx_export_after_review_with_sources(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    url = f"/api/v1/letters/{letter['id']}/exports"
    r = client.post(url, json={"format": "docx"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "letter_not_reviewed"
    assert client.post(f"/api/v1/letters/{letter['id']}/review", json={"version": 1}, headers=h).status_code == 200
    r = client.post(url, json={"format": "docx"}, headers=h)
    assert r.status_code == 200 and r.json()["format"] == "docx"
    f = client.get(r.json()["download_path"])
    assert f.status_code == 200 and f.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert 'filename="claimsathi-letter.docx"' in f.headers["content-disposition"]
    text = _docx_text(f.content)
    assert "₹25,900" in text and "Ravi K. Mehta" in text and "Sources" in text
    assert "[1] Sample Regulation 001" in text and "SYNTHETIC test source" in text
    with ctx.session_factory() as s:
        actions = [a.action for a in s.scalars(select(AuditLog).where(AuditLog.entity_id == letter["id"]))]
    assert actions == ["letter_exported_docx"]  # AC3, ids only


@pytest.mark.req("FR-027")
def test_an_edited_quote_has_no_citation_in_the_docx(client: TestClient, ctx: AppContext) -> None:
    h, letter = _letter(client, ctx)
    blocks = [dict(b) for b in letter["doc"]["blocks"]]
    i = next(n for n, b in enumerate(blocks) if b["type"] == "quote")
    blocks[i]["text"] = blocks[i]["text"].replace("specific", "exact")
    edited = client.patch(
        f"/api/v1/letters/{letter['id']}", json={"base_version": 1, "blocks": blocks}, headers=h
    ).json()
    assert (
        client.post(
            f"/api/v1/letters/{letter['id']}/review", json={"version": edited["version"]}, headers=h
        ).status_code
        == 200
    )
    r = client.post(f"/api/v1/letters/{letter['id']}/exports", json={"format": "docx"}, headers=h)
    text = _docx_text(client.get(r.json()["download_path"]).content)
    assert "Sources" not in text and "[1]" not in text and "exact terms" in text
