"""OCR for photos and scanned PDFs with Tesseract (PRD FR-010, AI-006)."""

from __future__ import annotations

import io
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from claimsathi.context import AppContext
from claimsathi.devtools.imagegen import scanned_pdf, sideways_jpeg, text_png
from claimsathi.documents.ocr import parse_tsv
from tests.conftest import sign_in
from tests.test_integration_vs1 import SYN001, _new_case

pytestmark = pytest.mark.integration


@pytest.fixture
def ocr_ctx(ctx: AppContext) -> AppContext:
    ctx.settings.ocr_engine = "tesseract"
    ctx.settings.tesseract_cmd = os.environ.get("TESSERACT_CMD", "tesseract")
    ctx.settings.tessdata_dir = os.environ.get("TESSDATA_DIR") or None
    return ctx


def _upload(client: TestClient, h: dict[str, str], cid: str, name: str, data: bytes, mime: str) -> dict[str, Any]:
    r = client.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": (name, data, mime)},
    )
    assert r.status_code == 202, r.text
    doc: dict[str, Any] = client.get(f"/api/v1/cases/{cid}").json()["documents"][-1]
    return doc


def _claimed(client: TestClient, cid: str) -> str | None:
    f = {x["name"]: x for x in client.get(f"/api/v1/cases/{cid}/facts").json()["fields"]}
    value: str | None = f["claimed_paise"]["display"]
    return value


@pytest.mark.req("FR-010")
@pytest.mark.parametrize(
    ("name", "mime", "make"),
    [
        ("letter.png", "image/png", text_png),
        ("letter.jpg", "image/jpeg", sideways_jpeg),
        ("scan.pdf", "application/pdf", scanned_pdf),
    ],
)
def test_photos_and_scans_are_read_and_their_details_extracted(
    client: TestClient, ocr_ctx: AppContext, name: str, mime: str, make: Any
) -> None:
    h = sign_in(client, ocr_ctx)
    cid = _new_case(client, h)["id"]
    doc = _upload(client, h, cid, name, make(SYN001), mime)
    assert doc["status"] == "ready", doc
    assert _claimed(client, cid) == "₹2,64,820"  # AC3: every value is found word for word in the OCR text


@pytest.mark.req("FR-010")
def test_an_unreadable_photo_asks_for_a_retake(client: TestClient, ocr_ctx: AppContext) -> None:
    h = sign_in(client, ocr_ctx)
    cid = _new_case(client, h)["id"]
    noise = Image.effect_noise((900, 600), 120).convert("RGB")
    buf = io.BytesIO()
    noise.save(buf, format="PNG")
    doc = _upload(client, h, cid, "blurry.png", buf.getvalue(), "image/png")
    assert doc["status"] == "needs_attention" and doc["status_reason"] == "photo_unclear"


def test_photos_are_refused_while_ocr_is_off(client: TestClient, ctx: AppContext) -> None:
    h = sign_in(client, ctx)
    cid = _new_case(client, h)["id"]
    r = client.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": ("letter.png", text_png(SYN001), "image/png")},
    )
    assert r.status_code == 415 and r.json()["code"] == "unsupported_media_type"


def test_a_missing_ocr_engine_fails_the_read_not_the_user(client: TestClient, ocr_ctx: AppContext) -> None:
    ocr_ctx.settings.tesseract_cmd = "no-such-tesseract-binary"
    h = sign_in(client, ocr_ctx)
    cid = _new_case(client, h)["id"]
    doc = _upload(client, h, cid, "letter.png", text_png(SYN001), "image/png")
    assert doc["status"] == "failed" and doc["status_reason"] == "read_failed"


def test_tsv_lines_keep_reading_order_and_quality_is_mean_confidence() -> None:
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [
        "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t90\tClaim",
        "5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t80\tNo.",
        "4\t1\t1\t1\t2\t0\t0\t0\t1\t1\t-1\t",
        "5\t1\t1\t1\t2\t1\t0\t0\t1\t1\t70\tRs.",
        "5\t1\t1\t1\t2\t2\t0\t0\t1\t1\t-1\t ",
    ]
    page = parse_tsv("\n".join([header, *rows]))
    assert page.lines == ["Claim No.", "Rs."] and page.quality == pytest.approx(0.8)
