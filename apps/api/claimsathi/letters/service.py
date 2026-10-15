"""Basic-mode Stage-1 letter (FR-024 subset, L1 + L4 of the letter pipeline): fully deterministic.

Every amount and date comes from confirmed facts. Quotes come from verified citations. The number
scanner (AI-005) re-checks the final text as a safety net. Identity values (complainant name, claim and
policy numbers) are filled server-side only.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.clock import today_ist
from claimsathi.core.errors import AppError
from claimsathi.core.values import format_date_dmy, format_inr
from claimsathi.models import (
    Analysis,
    Case,
    Citation,
    CounterPoint,
    ExtractedField,
    KnowledgeChunk,
    KnowledgeSource,
    Letter,
    LetterExport,
    LineItem,
)
from claimsathi.verify.numbers import tokens, ungrounded

DISCLAIMER = (
    "Prepared with ClaimSathi, a self-help drafting tool. This is not legal advice. You send this letter yourself."
)


def _facts(c: AppContext, s: Session, case: Case) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for r in s.scalars(select(ExtractedField).where(ExtractedField.case_id == case.id)):
        out[r.name] = c.cipher.decrypt(r.value_enc) if r.value_enc else r.value
    return out


def create_basic_letter(c: AppContext, s: Session, case: Case, include_ids: list[uuid.UUID] | None) -> Letter:
    a = s.scalar(
        select(Analysis)
        .where(Analysis.case_id == case.id, Analysis.status == "succeeded")
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    if a is None:
        raise AppError("fields_not_confirmed", 409, "Check your case before writing a letter.")
    if case.stale_since and case.stale_since > a.created_at:
        raise AppError("case_stale", 409, "Your details changed. Update the findings first.")
    f = _facts(c, s, case)
    items = s.scalars(select(LineItem).where(LineItem.case_id == case.id).order_by(LineItem.ordinal)).all()
    default = [i for i in items if i.audit_status in ("NO_CLAUSE_CITED", "CLAUSE_NOT_FOUND")]
    chosen = [i for i in items if i.id in set(include_ids)] if include_ids is not None else default
    if not chosen:
        raise AppError("validation_error", 422, "Choose at least one deduction to include.")
    cited = s.execute(
        select(Citation, KnowledgeChunk, KnowledgeSource)
        .join(CounterPoint, CounterPoint.id == Citation.counter_point_id)
        .join(KnowledgeChunk, KnowledgeChunk.id == Citation.chunk_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(
            CounterPoint.analysis_id == a.id,
            CounterPoint.shown.is_(True),
            CounterPoint.target_id.in_([i.id for i in chosen]),
            Citation.verified.is_(True),
        )
    ).all()
    total = sum(i.deducted_paise for i in chosen)
    raw_date = f.get("decision_letter_date")
    decision_date = date.fromisoformat(raw_date) if raw_date else None
    insurer = f.get("insurer") or "the insurer"
    claim_no = f.get("claim_number") or "[claim number]"
    policy_no = f.get("policy_number") or "[policy number]"
    name = c.cipher.decrypt(case.complainant_name_enc) if case.complainant_name_enc else "[your name]"
    item_list = "; ".join(f"{i.description} ({format_inr(i.deducted_paise)})" for i in chosen)

    blocks: list[dict[str, Any]] = [
        {"type": "meta", "text": f"Date: {format_date_dmy(today_ist())}"},
        {"type": "meta", "text": f"To: The Grievance Redressal Officer, {insurer}"},
        {
            "type": "subject",
            "text": f"Subject: Request to review deductions in claim {claim_no} under policy {policy_no}",
        },
        {"type": "para", "text": "Dear Sir or Madam,"},
    ]
    facts_txt = f"My claim {claim_no} was settled"
    if decision_date:
        facts_txt += f" by your letter dated {format_date_dmy(decision_date)}"
    claimed, paid = f.get("claimed_paise"), f.get("paid_paise")
    if claimed and paid:
        facts_txt += (
            f". The amount claimed was {format_inr(int(claimed))} and the amount paid was {format_inr(int(paid))}"
        )
    blocks.append({"type": "para", "text": facts_txt + "."})
    footnotes: list[dict[str, Any]] = []
    ground = (
        f"1. For the following deductions, your letter does not cite a specific term or condition of my "
        f"policy: {item_list}. The total of these deductions is {format_inr(total)}."
    )
    blocks.append({"type": "para", "text": ground})
    if cited:
        cit, ch, src = cited[0]
        footnotes.append(
            {
                "n": 1,
                "citation_id": str(cit.id),
                "chunk_id": str(ch.id),
                "source_title": src.title,
                "clause_ref": ch.clause_ref,
                "version": src.version,
                "synthetic": src.synthetic,
            }
        )
        blocks.append(
            {
                "type": "quote",
                "text": f"The applicable rule states: “{cit.quote}”",
                "footnote": 1,
                "quote": cit.quote,
                "citation_id": str(cit.id),
            }
        )
    blocks += [
        {"type": "para", "text": "I therefore request that you:"},
        {
            "type": "list",
            "items": [
                f"(a) reconsider these deductions and pay {format_inr(total)};",
                "(b) state, for each deduction, the specific term or condition of the policy relied on;",
                "(c) reply to me in writing.",
            ],
        },
        {"type": "para", "text": "Enclosure: copy of your settlement letter."},
        {"type": "para", "text": "Yours faithfully,"},
        {"type": "signature", "text": name},
    ]
    _check_numbers(
        blocks, f, cited, chosen=chosen, total=total, extra={claim_no, policy_no, format_date_dmy(today_ist())}
    )
    letter = Letter(
        case_id=case.id,
        analysis_id=a.id,
        stage="S1",
        language="en",
        basic_mode=True,
        included={"line_item_ids": [str(i.id) for i in chosen]},
        doc={"blocks": blocks, "footnotes": footnotes, "disclaimer": DISCLAIMER},
        version=1,
    )
    s.add(letter)
    s.commit()
    return letter


def _text_of(blocks: list[dict[str, Any]]) -> str:
    out = []
    for b in blocks:
        out.append(b.get("text", ""))
        out.extend(b.get("items", []))
    return "\n".join(out)


def _check_numbers(
    blocks: list[dict[str, Any]],
    f: dict[str, str | None],
    cited: Any,
    *,
    chosen: list[LineItem],
    total: int,
    extra: set[str],
) -> None:
    """AI-005 safety net: every number in the letter must come from confirmed facts, chosen deductions,
    the cited chunk or the system-provided extras. No shortcut path exists."""
    allowed: set[str] = {"1"}  # the ground's own paragraph number
    for name, v in f.items():
        if not v:
            continue
        if name.endswith("_paise"):
            allowed |= tokens(format_inr(int(v)))
        elif len(v) == 10 and v[4] == "-" and v[7] == "-":
            allowed |= tokens(format_date_dmy(date.fromisoformat(v)))
        else:
            allowed |= tokens(v)
    for li in chosen:
        allowed |= tokens(format_inr(li.deducted_paise)) | tokens(li.description)
    allowed |= tokens(format_inr(total))
    for i in extra:
        allowed |= tokens(i)
    for _cit, ch, _src in cited:
        allowed |= tokens(ch.text)
    if ungrounded(_text_of(blocks), allowed):
        raise AppError("internal_error", 500, "Letter failed the number check.")


def letter_view(s: Session, letter: Letter, case: Case) -> dict[str, Any]:
    stale = bool(case.stale_since and case.stale_since > letter.created_at)
    return {
        "id": str(letter.id),
        "stage": letter.stage,
        "language": letter.language,
        "status": letter.status,
        "basic_mode": letter.basic_mode,
        "doc": letter.doc,
        "version": letter.version,
        "reviewed_version": letter.reviewed_version,
        "stale": stale,
    }


def owned_letter(s: Session, letter_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Letter, Case]:
    row = s.execute(
        select(Letter, Case)
        .join(Case, Case.id == Letter.case_id)
        .where(Letter.id == letter_id, Case.user_id == user_id, Case.deleted_at.is_(None))
    ).first()
    if row is None:
        from claimsathi.core.errors import not_found

        raise not_found()
    return row[0], row[1]


def export_pdf(c: AppContext, s: Session, letter: Letter, case: Case) -> LetterExport:
    if letter.reviewed_version != letter.version:
        raise AppError("letter_not_reviewed", 409, "Please read the letter and confirm before downloading.")
    if case.stale_since and case.stale_since > letter.created_at:
        raise AppError("case_stale", 409, "Your details changed. Create a new letter.")
    existing = s.scalar(
        select(LetterExport).where(
            LetterExport.letter_id == letter.id,
            LetterExport.letter_version == letter.version,
            LetterExport.format == "pdf",
        )
    )
    if existing is not None:
        return existing
    from claimsathi.letters.render import render_pdf

    data = render_pdf(letter.doc)
    key = f"cases/{case.id}/letters/{letter.id}/v{letter.version}.pdf"
    c.store.put(key, data, "application/pdf")
    exp = LetterExport(
        letter_id=letter.id, case_id=case.id, letter_version=letter.version, format="pdf", storage_key=key
    )
    s.add(exp)
    s.commit()
    return exp
