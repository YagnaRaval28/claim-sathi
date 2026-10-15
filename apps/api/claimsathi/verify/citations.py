"""Deterministic citation verifier (PRD AI-004, system-design §8.5).

A quote is accepted only if:
1. its chunk was among the chunks provided for this call;
2. after normalisation, the quote appears verbatim (as a substring) in the chunk text;
3. it is at least MIN_WORDS words long, or MIN_CHARS characters long.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

VERIFIER_VERSION = "v1"
MIN_WORDS = 8
MIN_CHARS = 40

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
_WS = re.compile(r"\s+")
_LATIN = re.compile(r"[A-Za-z]")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_QUOTES)
    text = _WS.sub(" ", text).strip()
    # Case-fold Latin letters only; Indic scripts have no case.
    return "".join(ch.lower() if _LATIN.match(ch) else ch for ch in text)


@dataclass(frozen=True)
class CitationCheck:
    ok: bool
    reason: str | None = None


def verify_quote(*, chunk_id: str, quote: str, provided_chunks: dict[str, str]) -> CitationCheck:
    if chunk_id not in provided_chunks:
        return CitationCheck(False, "chunk_not_provided")
    q = normalise(quote)
    if len(q.split(" ")) < MIN_WORDS and len(q) < MIN_CHARS:
        return CitationCheck(False, "quote_too_short")
    if q not in normalise(provided_chunks[chunk_id]):
        return CitationCheck(False, "quote_not_in_chunk")
    return CitationCheck(True)
