"""Knowledge ingestion (FR-038 subset): text → clause chunks, with attestation required to publish.

Production sources are official PDFs that an admin has checked against the original. Local and test use
clearly labelled SYNTHETIC fixtures (`synthetic=True`), never regulation text typed from memory.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.core.clock import now_utc
from claimsathi.models import KnowledgeChunk, KnowledgeSource
from claimsathi.rules.audit import clause_key

HEADING = re.compile(
    r"^(?P<ref>(?:Para(?:graph)?|Clause|Section|Rule|Annexure)\s+[0-9IVX]+(?:\.[0-9]+)*(?:\([a-z0-9]+\))*)"
    r"\s*[:.\-–]?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Chunk:
    clause_ref: str | None
    text: str


def chunk_text(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    ref: str | None = None
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = HEADING.match(line)
        if m:
            if buf:
                chunks.append(Chunk(ref, " ".join(buf)))
            ref, buf = m.group("ref"), [line]
        else:
            buf.append(line)
    if buf:
        chunks.append(Chunk(ref, " ".join(buf)))
    return chunks


def ingest_text(
    s: Session,
    *,
    type: str,
    issuer: str,
    title: str,
    identifier: str,
    version: str,
    effective_from: date,
    text: str,
    attested_by: str,
    synthetic: bool,
    url: str | None = None,
) -> KnowledgeSource:
    existing = s.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.identifier == identifier,
            KnowledgeSource.version == version,
            KnowledgeSource.scope == "library",
        )
    )
    if existing is not None:
        return existing
    src = KnowledgeSource(
        type=type,
        scope="library",
        issuer=issuer,
        title=title,
        identifier=identifier,
        version=version,
        effective_from=effective_from,
        url=url,
        synthetic=synthetic,
        status="published",
        checked_by=attested_by,
        checked_at=now_utc(),
    )
    s.add(src)
    s.flush()
    for i, ch in enumerate(chunk_text(text), start=1):
        s.add(
            KnowledgeChunk(
                source_id=src.id,
                ordinal=i,
                clause_ref=ch.clause_ref,
                clause_key=clause_key(ch.clause_ref) if ch.clause_ref else None,
                text=ch.text,
                flags=[] if ch.clause_ref else ["missing_clause_ref"],
            )
        )
    return src


USER_UPLOAD = "user_upload"  # `checked_by` of a case wording: the user's own copy, not admin-attested


def ingest_case_wording(
    s: Session, *, case_id: uuid.UUID, document_id: uuid.UUID, insurer: str | None, text: str
) -> KnowledgeSource | None:
    """FR-014: the policy wording a user uploads becomes a source visible only within their case (AC3). It is
    the user's own document, so it is usable at once; it never enters the shared library."""
    chunks = chunk_text(text)
    if not chunks:
        return None
    src = KnowledgeSource(
        type="policy_wording",
        scope="case",
        case_id=case_id,
        issuer=insurer or "Your insurer",
        title="Your uploaded policy wording",
        identifier=f"upload:{document_id}",
        version="uploaded",
        effective_from=now_utc().date(),
        synthetic=False,
        status="published",
        checked_by=USER_UPLOAD,
        checked_at=now_utc(),
    )
    s.add(src)
    s.flush()
    for i, ch in enumerate(chunks, start=1):
        s.add(
            KnowledgeChunk(
                source_id=src.id,
                case_id=case_id,
                ordinal=i,
                clause_ref=ch.clause_ref,
                clause_key=clause_key(ch.clause_ref) if ch.clause_ref else None,
                text=ch.text,
                flags=[] if ch.clause_ref else ["missing_clause_ref"],
            )
        )
    return src
