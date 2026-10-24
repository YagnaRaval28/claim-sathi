"""OCR with Tesseract (PRD FR-010, AI-006): photos and scanned PDF pages → text lines and a page quality.

Runs the free Tesseract engine inside our own server: the image never goes to
a third party, and the text is never logged. Quality is the mean word confidence (0–1); pages below
`ocr_min_quality` are flagged "photo unclear" rather than guessed at.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps

RENDER_SCALE = 300 / 72  # PDF points → 300 dpi, Tesseract's preferred resolution
TIMEOUT_S = 120


class OcrUnavailable(RuntimeError):
    """The Tesseract binary is missing or failed (a server problem, never the user's)."""


@dataclass(frozen=True)
class OcrPage:
    lines: list[str]
    quality: float


def parse_tsv(tsv: str) -> OcrPage:
    """Tesseract TSV → lines in reading order, and the mean confidence of the recognised words."""
    lines: dict[tuple[str, str, str, str], list[str]] = {}
    confs: list[float] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        text, conf = (row.get("text") or "").strip(), float(row.get("conf") or -1)
        if row.get("level") != "5" or not text or conf < 0:
            continue
        lines.setdefault((row["page_num"], row["block_num"], row["par_num"], row["line_num"]), []).append(text)
        confs.append(conf)
    return OcrPage([" ".join(w) for w in lines.values()], sum(confs) / len(confs) / 100 if confs else 0.0)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_png(data: bytes) -> bytes:
    """A phone photo as an upright PNG (EXIF orientation applied)."""
    with Image.open(io.BytesIO(data)) as img:
        return _png(ImageOps.exif_transpose(img).convert("RGB"))


def pdf_page_png(page: Any) -> bytes:
    """A scanned PDF page (pypdfium2 page) rendered at 300 dpi."""
    return _png(page.render(scale=RENDER_SCALE).to_pil().convert("RGB"))


def ocr_png(png: bytes, *, cmd: str, languages: str, tessdata_dir: str | None) -> OcrPage:
    """Tesseract via pytesseract (it runs the binary on a temporary file of its own and deletes it)."""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = cmd
    if tessdata_dir:  # Tesseract's own variable: safe for paths with spaces on every OS
        os.environ["TESSDATA_PREFIX"] = tessdata_dir
    config = "--psm 3"
    with Image.open(io.BytesIO(png)) as img:
        try:
            tsv = pytesseract.image_to_data(img, lang=languages, config=config, timeout=TIMEOUT_S)
        except (OSError, RuntimeError, pytesseract.TesseractError) as exc:  # missing binary, timeout, engine error
            raise OcrUnavailable(type(exc).__name__) from exc
    return parse_tsv(str(tsv))
