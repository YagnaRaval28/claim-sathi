"""Findings for VS-1. This is a deterministic subset of the N1–N13 pipeline (system-design §9):
N1 load, N2 resolve wording, N4 deterministic audit, N8 verify citations, N9 statuses and totals.

AI counter-points (N7), explanation (N10) and translation (N12) arrive in milestone M5. Until then, no
item is ever labelled "appears valid": that would need an analysis we have not run.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError
from claimsathi.core.values import format_inr
from claimsathi.jobs import Handler, enqueue, step, task
from claimsathi.models import (
    Analysis,
    Case,
    Citation,
    CounterPoint,
    DecisionReason,
    ExtractedField,
    KnowledgeChunk,
    KnowledgeSource,
    LineItem,
    ReviewItem,
    Rule,
)
from claimsathi.rules.audit import DEFAULT_IDENTIFIER_PATTERNS, audit_item
from claimsathi.verify.citations import VERIFIER_VERSION, verify_quote

STEPS = ("checking_wording", "checking_deductions", "checking_sources")


def _rule(s: Session, key: str) -> Rule | None:
    return s.scalar(select(Rule).where(Rule.rule_key == key, Rule.status == "enabled"))


def start_analysis(s: Session, case: Case) -> Analysis:
    if case.fields_confirmed_at is None:
        raise AppError("fields_not_confirmed", 409, "Confirm your case details before checking.")
    decision = s.scalar(
        select(ExtractedField.value).where(ExtractedField.case_id == case.id, ExtractedField.name == "decision_type")
    )
    if decision == "partial" and case.line_items_confirmed_at is None:
        raise AppError("line_items_not_confirmed", 409, "Confirm the list of deductions first.")
    for old in s.scalars(
        select(Analysis).where(Analysis.case_id == case.id, Analysis.status.in_(("queued", "running", "succeeded")))
    ):
        old.status = "superseded"
    a = Analysis(id=uuid.uuid4(), case_id=case.id, status="queued", mode="full")
    s.add(a)
    s.flush()
    for i, k in enumerate(STEPS, start=1):
        step(s, case_id=case.id, job_kind="analysis", job_ref=a.id, step_key=k, ordinal=i, status="waiting")
    enqueue(s, "analysis.run", {"analysis_id": str(a.id)}, dedupe_key=f"analysis.run:{a.id}", queue="ai")
    s.commit()
    return a


def _resolve_wording(s: Session, case: Case) -> KnowledgeSource | None:
    if not case.insurer_name:
        return None
    return s.scalar(
        select(KnowledgeSource)
        .where(
            KnowledgeSource.type == "policy_wording",
            KnowledgeSource.status == "published",
            KnowledgeSource.scope == "library",
            func.lower(KnowledgeSource.issuer) == case.insurer_name.lower(),
        )
        .order_by(KnowledgeSource.effective_from.desc())
        .limit(1)
    )


def _evidence_point(
    s: Session, analysis: Analysis, case: Case, target_type: str, target_id: uuid.UUID, ordinal: int
) -> None:
    rule = _rule(s, "RULE-MC-01")
    if rule is None:
        return
    ev = rule.params["evidence"]
    chunk = s.scalar(
        select(KnowledgeChunk)
        .join(KnowledgeSource)
        .where(
            KnowledgeSource.identifier == ev["source_identifier"],
            KnowledgeSource.status == "published",
            KnowledgeChunk.clause_key == ev["clause_key"],
        )
        .order_by(KnowledgeSource.effective_from.desc())
        .limit(1)
    )
    cp = CounterPoint(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        case_id=case.id,
        target_type=target_type,
        target_id=target_id,
        ordinal=ordinal,
        statement_en=rule.params["statement_en"],
        basis_type="deterministic_rule",
        rule_key=rule.rule_key,
        shown=False,
    )
    reason: str | None = None
    if chunk is None:
        reason = "evidence_missing"
    else:
        check = verify_quote(chunk_id=str(chunk.id), quote=ev["quote"], provided_chunks={str(chunk.id): chunk.text})
        if not check.ok:
            reason = check.reason or "verify_failed"
    if chunk is None or reason is not None:
        cp.drop_reason = reason or "verify_failed"
        s.add(cp)
        s.add(
            ReviewItem(
                source="verifier",
                case_id=case.id,
                target_type="counter_point",
                payload={"rule_key": rule.rule_key, "reason": cp.drop_reason},
                reason=cp.drop_reason,
            )
        )
        return
    cp.shown = True
    s.add(cp)
    s.flush()
    s.add(
        Citation(
            counter_point_id=cp.id,
            case_id=case.id,
            chunk_id=chunk.id,
            quote=ev["quote"],
            verified=True,
            verifier_version=VERIFIER_VERSION,
        )
    )


def make_analysis_handler() -> Handler:
    @task("analysis.run")
    def _run(s: Session, payload: dict[str, Any]) -> None:
        a = s.get(Analysis, uuid.UUID(payload["analysis_id"]))
        if a is None or a.status != "queued":
            return
        case = s.get(Case, a.case_id)
        if case is None or case.deleted_at is not None:
            return
        a.status = "running"
        step(
            s,
            case_id=case.id,
            job_kind="analysis",
            job_ref=a.id,
            step_key="checking_wording",
            ordinal=1,
            status="in_progress",
        )
        wording = _resolve_wording(s, case)
        keys: set[str] | None = None
        if wording is not None:
            keys = {
                k
                for k in s.scalars(
                    select(KnowledgeChunk.clause_key).where(
                        KnowledgeChunk.source_id == wording.id, KnowledgeChunk.clause_key.is_not(None)
                    )
                )
                if k
            }
            case.wording_mode, case.wording_source_id = "library", wording.id
        else:
            case.wording_mode, case.wording_source_id = "none", None
        a.mode = "full" if wording is not None else "limited"
        step(
            s, case_id=case.id, job_kind="analysis", job_ref=a.id, step_key="checking_wording", ordinal=1, status="done"
        )
        step(
            s,
            case_id=case.id,
            job_kind="analysis",
            job_ref=a.id,
            step_key="checking_deductions",
            ordinal=2,
            status="in_progress",
        )
        pattern_rule = _rule(s, "RULE-PATTERNS")
        patterns = tuple(pattern_rule.params["identifier_patterns"]) if pattern_rule else DEFAULT_IDENTIFIER_PATTERNS
        ordinal = 0
        items = s.scalars(select(LineItem).where(LineItem.case_id == case.id).order_by(LineItem.ordinal)).all()
        for li in items:
            li.audit_status = audit_item(
                clause_cited=li.clause_cited_verbatim, wording_clause_keys=keys, patterns=patterns
            ).status
            if li.audit_status == "NO_CLAUSE_CITED":
                ordinal += 1
                _evidence_point(s, a, case, "line_item", li.id, ordinal)
        for r in s.scalars(select(DecisionReason).where(DecisionReason.case_id == case.id)):
            r.audit_status = audit_item(
                clause_cited=r.clause_cited_verbatim, wording_clause_keys=keys, patterns=patterns
            ).status
            if r.audit_status == "NO_CLAUSE_CITED":
                ordinal += 1
                _evidence_point(s, a, case, "reason", r.id, ordinal)
        step(
            s,
            case_id=case.id,
            job_kind="analysis",
            job_ref=a.id,
            step_key="checking_deductions",
            ordinal=2,
            status="done",
        )
        step(
            s, case_id=case.id, job_kind="analysis", job_ref=a.id, step_key="checking_sources", ordinal=3, status="done"
        )
        by_status: dict[str, dict[str, int]] = {}
        for li in items:
            agg = by_status.setdefault(li.audit_status or "CANNOT_ASSESS", {"count": 0, "deducted_paise": 0})
            agg["count"] += 1
            agg["deducted_paise"] += li.deducted_paise
        a.totals = {"by_status": [{"status": k, **v} for k, v in sorted(by_status.items())]}
        a.rule_versions = {r.rule_key: r.version for r in s.scalars(select(Rule).where(Rule.status == "enabled"))}
        a.source_versions = {str(wording.id): wording.version} if wording else {}
        a.status, a.completed_at = "succeeded", now_utc()
        case.last_activity_at = now_utc()

    return _run


def analysis_view(s: Session, case: Case) -> dict[str, Any] | None:
    a = s.scalar(
        select(Analysis)
        .where(Analysis.case_id == case.id, Analysis.status != "superseded")
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    if a is None:
        return None
    facts = {r.name: r.value for r in s.scalars(select(ExtractedField).where(ExtractedField.case_id == case.id))}
    points = s.scalars(
        select(CounterPoint).where(CounterPoint.analysis_id == a.id).order_by(CounterPoint.ordinal)
    ).all()
    shown = [p for p in points if p.shown]
    cits: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for c_, ch, src in s.execute(
        select(Citation, KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeChunk, KnowledgeChunk.id == Citation.chunk_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(Citation.counter_point_id.in_([p.id for p in shown] or [uuid.uuid4()]))
    ):
        cits.setdefault(c_.counter_point_id, []).append(
            {
                "id": str(c_.id),
                "chunk_id": str(ch.id),
                "quote": c_.quote,
                "verified": c_.verified,
                "source_title": src.title,
                "clause_ref": ch.clause_ref,
                "version": src.version,
                "synthetic": src.synthetic,
            }
        )
    items = s.scalars(select(LineItem).where(LineItem.case_id == case.id).order_by(LineItem.ordinal)).all()
    points_by_target: dict[uuid.UUID, list[str]] = {}
    for p in shown:
        points_by_target.setdefault(p.target_id, []).append(str(p.id))
    wording = s.get(KnowledgeSource, case.wording_source_id) if case.wording_source_id else None
    stale = bool(case.stale_since and case.stale_since > a.created_at)
    claimed, paid = facts.get("claimed_paise"), facts.get("paid_paise")
    return {
        "id": str(a.id),
        "status": a.status,
        "mode": a.mode,
        "stale": stale,
        "summary": {
            "claimed_paise": int(claimed) if claimed else None,
            "paid_paise": int(paid) if paid else None,
            "decision_type": facts.get("decision_type"),
            "provenance": "rule",
        },
        "wording": (
            {
                "title": wording.title,
                "version": wording.version,
                "effective_from": wording.effective_from.isoformat(),
                "synthetic": wording.synthetic,
            }
            if wording
            else None
        ),
        "totals": a.totals,
        "line_items": [
            {
                "id": str(li.id),
                "description": li.description,
                "deducted_paise": li.deducted_paise,
                "deducted_display": format_inr(li.deducted_paise),
                "audit_status": li.audit_status,
                "clause_cited_verbatim": li.clause_cited_verbatim,
                "counter_point_ids": points_by_target.get(li.id, []),
                "include_by_default": li.audit_status in ("NO_CLAUSE_CITED", "CLAUSE_NOT_FOUND"),
            }
            for li in items
        ],
        "counter_points": [
            {
                "id": str(p.id),
                "statement": p.statement_en,
                "statement_language": "en",
                "provenance": "rule",
                "basis_type": p.basis_type,
                "target_id": str(p.target_id),
                "citations": cits.get(p.id, []),
            }
            for p in shown
        ],
        "dropped_count": len(points) - len(shown),
    }
