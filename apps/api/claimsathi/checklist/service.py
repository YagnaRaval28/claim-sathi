"""Evidence checklist (PRD FR-018): items come only from the RULE-EVIDENCE map (base items plus items for each
confirmed category), never from a model. Uploaded documents of the matching type mark an item "uploaded"."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError, not_found
from claimsathi.models import Case, ChecklistItem, DecisionReason, Document, LineItem, Rule

DOC_TYPES_FOR_ITEM = {
    "decision_letter": {"decision_letter"},
    "policy_schedule": {"policy_schedule"},
    "policy_wording": {"policy_wording"},
    "discharge_summary": {"discharge_summary"},
    "final_bill": {"final_bill", "settlement_breakup"},
}


def _evidence_map(s: Session) -> dict[str, Any]:
    rule = s.scalar(select(Rule).where(Rule.rule_key == "RULE-EVIDENCE", Rule.status == "enabled"))
    return rule.params if rule else {"base": [], "by_category": {}}


def item_keys(s: Session, case: Case) -> list[tuple[str, str]]:
    """(item_key, source) in a stable order: base items first, then items for each category present."""
    m = _evidence_map(s)
    reason_cats = s.scalars(select(DecisionReason.category).where(DecisionReason.case_id == case.id))
    line_cats = s.scalars(select(LineItem.category).where(LineItem.case_id == case.id))
    cats = [c for c in (*reason_cats, *line_cats) if c]
    out: list[tuple[str, str]] = [(k, "base") for k in m.get("base", [])]
    seen = {k for k, _ in out}
    for cat in cats:
        for k in m.get("by_category", {}).get(cat, []):
            if k not in seen:
                out.append((k, cat))
                seen.add(k)
    return out


def checklist_view(s: Session, case: Case) -> list[dict[str, Any]]:
    rows = {r.item_key: r for r in s.scalars(select(ChecklistItem).where(ChecklistItem.case_id == case.id))}
    doc_types = {d.type for d in s.scalars(select(Document).where(Document.case_id == case.id))}
    out = []
    for key, source in item_keys(s, case):
        row = rows.get(key)
        status = row.status if row else "pending"
        if status == "pending" and DOC_TYPES_FOR_ITEM.get(key, set()) & doc_types:
            status = "uploaded"
        out.append(
            {
                "item_key": key,
                "source": source,
                "status": status,
                "document_id": str(row.document_id) if row and row.document_id else None,
            }
        )
    return out


def set_item(s: Session, case: Case, key: str, status: str, document_id: uuid.UUID | None) -> dict[str, Any]:
    if key not in {k for k, _ in item_keys(s, case)}:
        raise not_found()
    if (
        document_id is not None
        and s.scalar(select(Document.id).where(Document.id == document_id, Document.case_id == case.id)) is None
    ):
        raise AppError("validation_error", 422, "That document isn't part of this case.")
    row = s.get(ChecklistItem, (case.id, key)) or ChecklistItem(case_id=case.id, item_key=key)
    row.status, row.document_id, row.updated_at = status, document_id, now_utc()
    s.add(row)
    s.commit()
    return next(i for i in checklist_view(s, case) if i["item_key"] == key)


def obtained_items(s: Session, case: Case) -> list[str]:
    """Items the user has (ticked or uploaded), for the letters' enclosure lists (FR-018 AC2)."""
    return [i["item_key"] for i in checklist_view(s, case) if i["status"] in ("obtained", "uploaded")]
