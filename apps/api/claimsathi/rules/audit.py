"""Deterministic deduction audit (PRD FR-015). The model is never consulted here.

- NO_CLAUSE_CITED: the insurer's clause text is empty, "none", or contains no clause identifier.
- CLAUSE_NOT_FOUND: an identifier was cited but is not present in the resolved wording.
- CANNOT_ASSESS: limited mode (no wording), or the clause exists but no grounded counter-point
  analysis has run (VS-1 has no AI counter-points yet, so it never claims APPEARS_VALID).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

DEFAULT_IDENTIFIER_PATTERNS: tuple[str, ...] = (
    r"\b(?:clause|section|para(?:graph)?|rule|annexure|list|exclusion|condition)\s*(?:no\.?\s*)?"
    r"[0-9ivx]+(?:\.[0-9]+)*(?:\([a-z0-9]+\))*",
    r"\b[0-9]+(?:\.[0-9]+)+(?:\([a-z0-9]+\))*\b",
)

_KEY_STRIP = re.compile(r"\b(?:clause|section|para(?:graph)?|rule|annexure|list)\b|\bno\.|\bno\b|\s", re.IGNORECASE)


@dataclass(frozen=True)
class AuditResult:
    status: str
    clause_key: str | None = None


def identifiers(text: str | None, patterns: Sequence[str] = DEFAULT_IDENTIFIER_PATTERNS) -> list[str]:
    if not text or text.strip().lower() in {"none", "nil", "na", "n/a", "-"}:
        return []
    found: list[str] = []
    for p in patterns:
        found.extend(m.group(0) for m in re.finditer(p, text, re.IGNORECASE))
    return found


def clause_key(identifier: str) -> str:
    """Canonical lookup key: 'Clause 4.7' -> '4.7', 'Para 17(b)' -> '17(b)'."""
    core = _KEY_STRIP.sub("", identifier).lower().strip(" .:-")
    head = identifier.strip().split(" ", 1)[0].lower()
    return f"{head}-{core}" if head in ("annexure", "list") else core  # 'Annexure I' != 'List I'


def audit_item(
    *,
    clause_cited: str | None,
    wording_clause_keys: Iterable[str] | None,
    patterns: Sequence[str] = DEFAULT_IDENTIFIER_PATTERNS,
) -> AuditResult:
    ids = identifiers(clause_cited, patterns)
    if not ids:
        return AuditResult("NO_CLAUSE_CITED")
    if wording_clause_keys is None:  # limited mode: no wording to check against
        return AuditResult("CANNOT_ASSESS")
    keys = set(wording_clause_keys)
    for ident in ids:
        k = clause_key(ident)
        if k in keys:
            return AuditResult("CANNOT_ASSESS", clause_key=k)  # found; detailed check needs counter-points
    return AuditResult("CLAUSE_NOT_FOUND", clause_key=clause_key(ids[0]))
