"""Stage-1 letters in Gujarati and Hindi, always with the English copy (PRD FR-024, OQ-03 default)."""

from __future__ import annotations

import io
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimsathi.context import AppContext
from claimsathi.letters.render import letter_html
from tests.conftest import sign_in
from tests.test_integration_rules_checklist import _rejected_case
from tests.test_integration_vs1 import _to_findings

pytestmark = pytest.mark.integration


def _letter(client: TestClient, h: dict[str, str], cid: str, language: str) -> dict[str, Any]:
    r = client.post(
        f"/api/v1/cases/{cid}/letters",
        json={"language": language},
        headers={**h, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def _quotes(blocks: list[dict[str, Any]]) -> list[str]:
    return [b["quote"] for b in blocks if b["type"] == "quote"]


@pytest.mark.req("FR-024")
def test_gujarati_letter_carries_the_english_copy_with_the_same_grounds(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "gujarati-letter@example.com")
    en = _letter(client, h, cid, "en")
    gu = _letter(client, h, cid, "gu")
    assert gu["language"] == "gu" and "english" not in en["doc"]
    blocks = gu["doc"]["blocks"]
    assert blocks[2]["text"].startswith("વિષય:") and "SHI/CL/2026/000456" in blocks[2]["text"]
    assert "₹1,85,000" in blocks[4]["text"] and "02/07/2026" in blocks[4]["text"]
    # Quotes stay verbatim English (what the verifier checked), with the same footnotes as the English copy.
    assert _quotes(blocks) == _quotes(en["doc"]["blocks"]) and len(_quotes(blocks)) == 2
    assert gu["doc"]["footnotes"] == en["doc"]["footnotes"]
    assert gu["doc"]["english"]["blocks"] == en["doc"]["blocks"]
    assert gu["doc"]["disclaimer"] != en["doc"]["disclaimer"]
    html = letter_html(gu["doc"], "gu", "અંગ્રેજી નકલ (English copy)")
    assert "<html lang='gu'>" in html and "class='english-copy'" in html and "Dear Sir or Madam," in html


@pytest.mark.req("FR-024")
def test_hindi_letter_for_deductions_and_its_word_export(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx, "hindi-letter@example.com")
    cid, _ = _to_findings(client, h)
    hi = _letter(client, h, cid, "hi")
    text = " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in hi["doc"]["blocks"])
    assert "विषय:" in text and "₹2,64,820" in text and "(क)" in text
    assert hi["doc"]["english"]["blocks"][2]["text"].startswith("Subject: Request to review deductions")
    lid = hi["id"]
    assert client.post(f"/api/v1/letters/{lid}/review", json={"version": 1}, headers=h).status_code == 200
    exp = client.post(f"/api/v1/letters/{lid}/exports", json={"format": "docx"}, headers=h).json()
    from docx import Document

    paras = [p.text for p in Document(io.BytesIO(client.get(exp["download_path"]).content)).paragraphs]
    assert "अंग्रेज़ी प्रति (English copy)" in paras and "Yours faithfully," in paras and "भवदीय," in paras


@pytest.mark.req("FR-024")
def test_editing_the_translated_letter_keeps_verification_and_the_english_copy(
    client: TestClient, ctx: AppContext
) -> None:
    h, cid = _rejected_case(client, ctx, "gujarati-edit@example.com")
    gu = _letter(client, h, cid, "gu")
    original = [dict(b) for b in gu["doc"]["blocks"]]
    i = next(n for n, b in enumerate(original) if b["type"] == "quote")
    changed = [dict(b) for b in original]
    changed[i] = {**changed[i], "text": changed[i]["text"] + " ઉમેરો"}
    r = client.patch(f"/api/v1/letters/{gu['id']}", json={"base_version": 1, "blocks": changed}, headers=h)
    edited = r.json()
    assert edited["doc"]["blocks"][i]["type"] == "para" and len(edited["doc"]["footnotes"]) == 1
    assert edited["doc"]["english"] == gu["doc"]["english"]  # the English copy is as generated
    r = client.patch(f"/api/v1/letters/{gu['id']}", json={"base_version": 2, "blocks": original}, headers=h)
    assert len(_quotes(r.json()["doc"]["blocks"])) == 2  # undo re-verifies the Gujarati quote block


def test_only_supported_languages(client: TestClient, ctx: AppContext) -> None:
    h, cid = _rejected_case(client, ctx, "letter-lang@example.com")
    r = client.post(
        f"/api/v1/cases/{cid}/letters", json={"language": "ta"}, headers={**h, "Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 422
