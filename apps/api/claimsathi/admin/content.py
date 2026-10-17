"""Admin knowledge base (PRD FR-038) and rules table (FR-039).

Sources start as drafts; publishing needs the admin's confirmation that the text was checked against the
official document. Retiring keeps the source and its chunks, so existing citations still resolve (FR-038 AC1).
Rule changes always create a new version; enabling one needs a source citation and a verifier (FR-039 AC1)
and disables the previously enabled version of that rule.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claimsathi.admin.service import audit
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError, not_found
from claimsathi.knowledge.ingest import chunk_text
from claimsathi.models import AdminUser, KnowledgeChunk, KnowledgeSource, Rule
from claimsathi.rules.audit import clause_key

SOURCE_FREE_KINDS = {"pattern", "limit", "banned_phrases", "model_price", "quota", "credit_budget"}


def source_view(src: KnowledgeSource, chunk_count: int, flagged: int) -> dict[str, Any]:
    return {
        "id": str(src.id),
        "type": src.type,
        "issuer": src.issuer,
        "title": src.title,
        "identifier": src.identifier,
        "version": src.version,
        "effective_from": src.effective_from.isoformat(),
        "effective_to": src.effective_to.isoformat() if src.effective_to else None,
        "url": src.url,
        "synthetic": src.synthetic,
        "status": src.status,
        "checked_by": src.checked_by,
        "checked_at": src.checked_at.isoformat() if src.checked_at else None,
        "chunks": chunk_count,
        "chunks_missing_clause_ref": flagged,
    }


def list_sources(s: Session) -> list[dict[str, Any]]:
    rows = s.execute(
        select(KnowledgeSource, func.count(KnowledgeChunk.id))
        .outerjoin(KnowledgeChunk, KnowledgeChunk.source_id == KnowledgeSource.id)
        .where(KnowledgeSource.scope == "library")
        .group_by(KnowledgeSource.id)
        .order_by(KnowledgeSource.created_at.desc())
    ).all()
    out = []
    for src, n in rows:
        flagged = s.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.source_id == src.id, KnowledgeChunk.clause_ref.is_(None)
            )
        )
        out.append(source_view(src, n, flagged or 0))
    return out


def create_draft(
    s: Session,
    admin: AdminUser,
    *,
    type: str,
    issuer: str,
    title: str,
    identifier: str,
    version: str,
    effective_from: date,
    effective_to: date | None,
    url: str | None,
    text: str,
) -> KnowledgeSource:
    if s.scalar(
        select(KnowledgeSource.id).where(
            KnowledgeSource.identifier == identifier,
            KnowledgeSource.version == version,
            KnowledgeSource.scope == "library",
        )
    ):
        raise AppError("validation_error", 422, "This identifier and version already exist.")
    chunks = chunk_text(text)
    if not chunks:
        raise AppError("validation_error", 422, "No readable text was found in the file.")
    src = KnowledgeSource(
        type=type,
        scope="library",
        issuer=issuer,
        title=title,
        identifier=identifier,
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        url=url,
        synthetic=False,
        status="draft",
    )
    s.add(src)
    s.flush()
    for i, ch in enumerate(chunks, start=1):
        s.add(
            KnowledgeChunk(
                source_id=src.id,
                ordinal=i,
                clause_ref=ch.clause_ref,
                clause_key=clause_key(ch.clause_ref) if ch.clause_ref else None,
                text=ch.text,
                flags=[] if ch.clause_ref else ["missing_clause_ref"],  # FR-038 AC2
            )
        )
    audit(s, admin, "source_drafted", "knowledge_source", str(src.id))
    s.commit()
    return src


def owned_source(s: Session, source_id: uuid.UUID) -> KnowledgeSource:
    src = s.get(KnowledgeSource, source_id)
    if src is None or src.scope != "library":
        raise not_found()
    return src


def chunks(s: Session, src: KnowledgeSource) -> list[dict[str, Any]]:
    return [
        {"id": str(c.id), "ordinal": c.ordinal, "clause_ref": c.clause_ref, "text": c.text, "flags": list(c.flags)}
        for c in s.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.source_id == src.id).order_by(KnowledgeChunk.ordinal)
        )
    ]


def publish(s: Session, admin: AdminUser, src: KnowledgeSource, attest_checked: bool) -> None:
    if src.status != "draft":
        raise AppError("validation_error", 422, "Only a draft can be published.")
    if not attest_checked:
        raise AppError("validation_error", 422, "Confirm that the text was checked against the official document.")
    src.status, src.checked_by, src.checked_at = "published", f"admin:{admin.id}", now_utc()
    audit(s, admin, "source_published", "knowledge_source", str(src.id))
    s.commit()


def retire(s: Session, admin: AdminUser, src: KnowledgeSource) -> None:
    if src.status != "published":
        raise AppError("validation_error", 422, "Only a published source can be retired.")
    src.status = "retired"  # chunks stay, so earlier citations keep resolving (FR-038 AC1)
    audit(s, admin, "source_retired", "knowledge_source", str(src.id))
    s.commit()


# --- Rules (FR-039) ----------------------------------------------------------------------------------


def rule_view(r: Rule) -> dict[str, Any]:
    return {
        "rule_key": r.rule_key,
        "version": r.version,
        "kind": r.kind,
        "status": r.status,
        "params": r.params,
        "source_ref": r.source_ref,
        "verified_by": r.verified_by,
        "created_at": r.created_at.isoformat(),
    }


def list_rules(s: Session) -> list[dict[str, Any]]:
    return [rule_view(r) for r in s.scalars(select(Rule).order_by(Rule.rule_key, Rule.version.desc()))]


def new_version(
    s: Session, admin: AdminUser, key: str, *, kind: str | None, params: dict[str, Any], source_ref: str | None
) -> Rule:
    latest = s.scalar(select(Rule).where(Rule.rule_key == key).order_by(Rule.version.desc()).limit(1))
    if latest is None and not kind:
        raise AppError("validation_error", 422, "A new rule needs a kind.")
    r = Rule(
        rule_key=key,
        version=(latest.version + 1) if latest else 1,
        kind=kind or (latest.kind if latest else "regulatory"),
        params=params,
        source_ref=source_ref,
        status="disabled_pending_verification",
    )
    s.add(r)
    audit(s, admin, "rule_version_created", "rule", f"{key}@{r.version}")
    s.commit()
    return r


def _version(s: Session, key: str, version: int) -> Rule:
    r = s.scalar(select(Rule).where(Rule.rule_key == key, Rule.version == version))
    if r is None:
        raise not_found()
    return r


def enable(s: Session, admin: AdminUser, key: str, version: int, verified_by: str) -> Rule:
    r = _version(s, key, version)
    if r.kind not in SOURCE_FREE_KINDS and not (r.source_ref and r.source_ref.strip()):
        raise AppError("validation_error", 422, "A rule can't be enabled without a source citation.")  # AC1
    if not verified_by.strip():
        raise AppError("validation_error", 422, "Name the person who verified this rule.")
    for other in s.scalars(select(Rule).where(Rule.rule_key == key, Rule.status == "enabled", Rule.id != r.id)):
        other.status = "retired"
    s.flush()
    r.status, r.verified_by = "enabled", verified_by.strip()
    audit(s, admin, "rule_enabled", "rule", f"{key}@{version}")
    s.commit()
    return r


def disable(s: Session, admin: AdminUser, key: str, version: int) -> Rule:
    r = _version(s, key, version)
    r.status = "disabled_pending_verification"
    audit(s, admin, "rule_disabled", "rule", f"{key}@{version}")
    s.commit()
    return r
