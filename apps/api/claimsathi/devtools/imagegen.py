"""SYNTHETIC "photo" and "scan" fixtures for OCR tests (FR-010): text drawn on a white page with Pillow."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont


def text_image(lines: list[str]) -> Image.Image:
    font = ImageFont.load_default(size=28)
    img = Image.new("RGB", (1700, 80 + len(lines) * 52), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((60, 40 + i * 52), line, fill="black", font=font)
    return img


def text_png(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    text_image(lines).save(buf, format="PNG")
    return buf.getvalue()


def sideways_jpeg(lines: list[str]) -> bytes:
    """A phone photo stored sideways with EXIF orientation 6 (viewers rotate it 90° clockwise to show it)."""
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = io.BytesIO()
    text_image(lines).rotate(90, expand=True).save(buf, format="JPEG", quality=92, exif=exif)
    return buf.getvalue()


def scanned_pdf(lines: list[str]) -> bytes:
    """A PDF whose only content is an image of the text: no text layer, like a scanner's output."""
    buf = io.BytesIO()
    text_image(lines).save(buf, format="PDF", resolution=150)
    return buf.getvalue()
