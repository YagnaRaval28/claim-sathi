"""Number and identifier scanner (PRD AI-005).

Every amount, date, percentage or clause identifier in generated text must be grounded: it must equal
a value from the allowed set (confirmed facts and cited chunk text). Sentences with ungrounded tokens
are removed by the caller.
"""

from __future__ import annotations

import re

_INDIC_DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯०१२३४५६७८९", "01234567890123456789")

# Order matters: dates before plain numbers.
_DATE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
_NUMBER = re.compile(r"(?<![\w/])(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w/])")
_CLAUSE = re.compile(
    r"\b(?:clause|section|para(?:graph)?|rule|annexure)\s+([0-9]+(?:\.[0-9]+)*(?:\([a-z0-9]+\))*)", re.IGNORECASE
)


def to_ascii_digits(text: str) -> str:
    return text.translate(_INDIC_DIGITS)


def tokens(text: str) -> set[str]:
    """Normalised grounding tokens: dates as YYYY-MM-DD, numbers without separators, clause ids lowercased."""
    t = to_ascii_digits(text)
    out: set[str] = set()
    for d, m, y in _DATE.findall(t):
        out.add(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    stripped = _DATE.sub(" ", t)
    for num in _NUMBER.findall(stripped):
        n = num.replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    for cid in _CLAUSE.findall(t):
        out.add("clause:" + cid.lower())
    return out


def ungrounded(text: str, allowed: set[str]) -> set[str]:
    return {tok for tok in tokens(text) if tok not in allowed}


def split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?।])\s+", text.strip()) if s]


def drop_ungrounded_sentences(text: str, allowed: set[str]) -> tuple[str, int]:
    kept, removed = [], 0
    for s in split_sentences(text):
        if ungrounded(s, allowed):
            removed += 1
        else:
            kept.append(s)
    return " ".join(kept), removed
