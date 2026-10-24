"""Monthly citation audit (PRD FR-040 AC1, M-04) and the public accuracy figure (FR-043, PUB-04).

An admin draws a random sample of the citations shown to users in a month, stratified across en, gu and hi.
Each sampled citation becomes a review item that reviewers mark correct or incorrect in the review queue. Once
every item is decided, an admin publishes the period; the accuracy page shows only published figures.
"""

from __future__ import annotations

import random
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.admin.service import audit
from claimsathi.core.clock import IST, now_utc, today_ist
from claimsathi.core.errors import AppError
from claimsathi.models import (
    AccuracyAudit,
    AdminUser,
    Analysis,
    Case,
    Citation,
    CounterPoint,
    KnowledgeChunk,
    KnowledgeSource,
    ReviewItem,
    User,
)

SAMPLE_SIZE = 100  # FR-040 AC1 (PROVISIONAL)
SOURCE = "audit_sample"
PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
INCORRECT = ("incorrect", "kb_fix")  # a knowledge-base fix means the citation shown was wrong


def _bounds(period: str) -> tuple[datetime, datetime]:
    if not PERIOD.match(period):
        raise AppError("validation_error", 422, "Use a month like 2026-10.")
    year, month = int(period[:4]), int(period[5:])
    start = datetime(year, month, 1, tzinfo=IST)
    if start.date() > today_ist():
        raise AppError("validation_error", 422, "That month hasn't started yet.")
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=IST)
    return start, end


def _items(s: Session, period: str) -> list[ReviewItem]:
    return list(
        s.scalars(select(ReviewItem).where(ReviewItem.source == SOURCE, ReviewItem.payload["period"].astext == period))
    )


def draw_sample(s: Session, admin: AdminUser, period: str, size: int = SAMPLE_SIZE) -> int:
    """Pick up to `size` shown, verified citations from the month, taking languages in turn so en, gu and hi are
    all represented. Drawing again for the same month returns the existing sample."""
    start, end = _bounds(period)
    existing = _items(s, period)
    if existing:
        return len(existing)
    rows = s.execute(
        select(Citation, CounterPoint, KnowledgeChunk, KnowledgeSource, Case.id, User.display_language)
        .join(CounterPoint, CounterPoint.id == Citation.counter_point_id)
        .join(Analysis, Analysis.id == CounterPoint.analysis_id)
        .join(Case, Case.id == Analysis.case_id)
        .join(User, User.id == Case.user_id)
        .join(KnowledgeChunk, KnowledgeChunk.id == Citation.chunk_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(
            CounterPoint.shown.is_(True),
            Citation.verified.is_(True),
            Analysis.status == "succeeded",
            Analysis.created_at >= start,
            Analysis.created_at < end,
            Case.deleted_at.is_(None),
        )
    ).all()
    pick = random.SystemRandom()
    by_lang: dict[str, list[Any]] = {}
    for row in rows:
        by_lang.setdefault(row[5], []).append(row)
    for group in by_lang.values():
        pick.shuffle(group)
    chosen: list[Any] = []
    while len(chosen) < size and any(by_lang.values()):
        for lang in sorted(by_lang):
            if by_lang[lang] and len(chosen) < size:
                chosen.append(by_lang[lang].pop())
    for cit, cp, ch, src, case_id, lang in chosen:
        s.add(
            ReviewItem(
                source=SOURCE,
                case_id=case_id,
                target_type="citation",
                target_id=cit.id,
                reason=SOURCE,
                language=lang,
                # The shown statement and quote are rule and regulation text, not the user's case content.
                payload={
                    "period": period,
                    "statement": cp.statement_en,
                    "quote": cit.quote,
                    "source_title": src.title,
                    "clause_ref": ch.clause_ref,
                    "version": src.version,
                },
            )
        )
    audit(s, admin, "accuracy_sampled", "accuracy_audit", period)
    s.commit()
    return len(chosen)


def period_view(s: Session, period: str) -> dict[str, Any]:
    items = _items(s, period)
    published = s.scalar(select(AccuracyAudit).where(AccuracyAudit.period == period))
    count = {k: sum(i.status == k for i in items) for k in ("open", "correct", "incorrect", "kb_fix", "skipped")}
    return {
        "period": period,
        "sampled": len(items),
        "by_language": {lang: sum(i.language == lang for i in items) for lang in ("en", "gu", "hi")},
        **count,
        "published": public_view(published) if published else None,
    }


def list_periods(s: Session) -> list[dict[str, Any]]:
    sampled = s.scalars(select(ReviewItem.payload["period"].astext).where(ReviewItem.source == SOURCE).distinct()).all()
    published = s.scalars(select(AccuracyAudit.period)).all()
    return [period_view(s, p) for p in sorted({*sampled, *published}, reverse=True)]


def publish(s: Session, admin: AdminUser, period: str) -> dict[str, Any]:
    """FR-043: publish the month's result. Every sampled item must be decided; skipped items don't count."""
    _bounds(period)
    view = period_view(s, period)
    if view["sampled"] == 0:
        raise AppError("audit_not_ready", 409, "Draw a sample for this month first.")
    if view["open"]:
        raise AppError("audit_not_ready", 409, f"{view['open']} sampled citations still need a decision.")
    decided = view["correct"] + view["incorrect"] + view["kb_fix"]
    if decided == 0:
        raise AppError("audit_not_ready", 409, "No sampled citation was assessed.")
    row = s.scalar(select(AccuracyAudit).where(AccuracyAudit.period == period))
    if row is None:
        row = AccuracyAudit(period=period, sample_size=decided, correct=view["correct"], published_at=now_utc())
        s.add(row)
    row.sample_size, row.correct, row.published_at, row.published_by = decided, view["correct"], now_utc(), admin.id
    audit(s, admin, "accuracy_published", "accuracy_audit", period)
    s.commit()
    return public_view(row)


def public_view(row: AccuracyAudit) -> dict[str, Any]:
    return {
        "period": row.period,
        "sample_size": row.sample_size,
        "correct": row.correct,
        "published_at": row.published_at.isoformat(),
    }


def latest_published(s: Session) -> dict[str, Any] | None:
    row = s.scalar(select(AccuracyAudit).order_by(AccuracyAudit.period.desc()).limit(1))
    return public_view(row) if row else None
