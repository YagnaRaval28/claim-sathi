"""Basic-mode Stage-1 letter (FR-024 subset, L1 + L4 of the letter pipeline): fully deterministic.

Every amount and date comes from confirmed facts. Quotes come from verified citations. The number
scanner (AI-005) re-checks the final text as a safety net. Identity values (complainant name, claim and
policy numbers) are filled server-side only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
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
    DecisionReason,
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


@dataclass
class _Material:
    """Confirmed facts and verified grounds shared by the Stage-1 letter and the Ombudsman complaint."""

    analysis: Analysis
    f: dict[str, str | None]
    chosen: list[LineItem]
    reasons: list[DecisionReason]
    cited: list[Any]
    total: int
    insurer: str
    claim_no: str
    policy_no: str
    name: str
    rejected: bool
    decision_date: date | None


def _gather(c: AppContext, s: Session, case: Case, include_ids: list[uuid.UUID] | None) -> _Material:
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
    reasons = [
        r
        for r in s.scalars(
            select(DecisionReason).where(DecisionReason.case_id == case.id).order_by(DecisionReason.ordinal)
        )
        if r.audit_status in ("NO_CLAUSE_CITED", "CLAUSE_NOT_FOUND")
    ]
    if not chosen and not reasons:
        raise AppError(
            "validation_error", 422, "There is nothing in this decision that the basic letter can challenge yet."
        )
    cited = list(
        s.execute(
            select(Citation, KnowledgeChunk, KnowledgeSource)
            .join(CounterPoint, CounterPoint.id == Citation.counter_point_id)
            .join(KnowledgeChunk, KnowledgeChunk.id == Citation.chunk_id)
            .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
            .where(
                CounterPoint.analysis_id == a.id,
                CounterPoint.shown.is_(True),
                CounterPoint.target_id.in_([i.id for i in chosen] + [r.id for r in reasons]),
                Citation.verified.is_(True),
            )
        ).all()
    )
    raw_date = f.get("decision_letter_date")
    return _Material(
        analysis=a,
        f=f,
        chosen=chosen,
        reasons=reasons,
        cited=cited,
        total=sum(i.deducted_paise for i in chosen),
        insurer=f.get("insurer") or "the insurer",
        claim_no=f.get("claim_number") or "[claim number]",
        policy_no=f.get("policy_number") or "[policy number]",
        name=c.cipher.decrypt(case.complainant_name_enc) if case.complainant_name_enc else "[your name]",
        rejected=f.get("decision_type") == "repudiation",
        decision_date=date.fromisoformat(raw_date) if raw_date else None,
    )


def _grounds(m: _Material, *, insurer_ref: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Numbered grounds (one per NO_CLAUSE_CITED group) plus the verified quote and its footnote."""
    blocks: list[dict[str, Any]] = []
    footnotes: list[dict[str, Any]] = []
    n = 0
    if m.chosen:
        n += 1
        item_list = "; ".join(f"{i.description} ({format_inr(i.deducted_paise)})" for i in m.chosen)
        blocks.append(
            {
                "type": "para",
                "text": (
                    f"{n}. For the following deductions, {insurer_ref} does not cite a specific term or condition of "
                    f"my policy: {item_list}. The total of these deductions is {format_inr(m.total)}."
                ),
            }
        )
    if m.reasons:
        n += 1
        quoted = "; ".join(f"“{r.text_verbatim}”" for r in m.reasons)
        blocks.append(
            {
                "type": "para",
                "text": (
                    f"{n}. {insurer_ref[0].upper()}{insurer_ref[1:]} gives the following reason for its decision but "
                    f"does not cite a specific term or condition of my policy: {quoted}."
                ),
            }
        )
    if m.cited:
        cit, ch, src = m.cited[0]
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
    return blocks, footnotes


def _facts_sentence(m: _Material, *, by: str) -> str:
    txt = f"My claim {m.claim_no} was {'rejected' if m.rejected else 'settled'}"
    if m.decision_date:
        txt += f" by {by} dated {format_date_dmy(m.decision_date)}"
    claimed, paid = m.f.get("claimed_paise"), m.f.get("paid_paise")
    if claimed and paid and not m.rejected:
        txt += f". The amount claimed was {format_inr(int(claimed))} and the amount paid was {format_inr(int(paid))}"
    elif claimed:
        txt += f". The amount claimed was {format_inr(int(claimed))}"
    return txt + "."


def create_basic_letter(c: AppContext, s: Session, case: Case, include_ids: list[uuid.UUID] | None) -> Letter:
    m = _gather(c, s, case, include_ids)
    what = "the rejection of" if m.rejected else "deductions in"
    blocks: list[dict[str, Any]] = [
        {"type": "meta", "text": f"Date: {format_date_dmy(today_ist())}"},
        {"type": "meta", "text": f"To: The Grievance Redressal Officer, {m.insurer}"},
        {
            "type": "subject",
            "text": f"Subject: Request to review {what} claim {m.claim_no} under policy {m.policy_no}",
        },
        {"type": "para", "text": "Dear Sir or Madam,"},
        {"type": "para", "text": _facts_sentence(m, by="your letter")},
    ]
    grounds, footnotes = _grounds(m, insurer_ref="your letter")
    blocks += grounds
    first = (
        "(a) reconsider your decision and settle my claim;"
        if m.rejected
        else f"(a) reconsider these deductions and pay {format_inr(m.total)};"
    )
    each = "reason for rejection" if m.rejected and not m.chosen else "deduction"
    blocks += [
        {"type": "para", "text": "I therefore request that you:"},
        {
            "type": "list",
            "items": [
                first,
                f"(b) state, for each {each}, the specific term or condition of the policy relied on;",
                "(c) reply to me in writing.",
            ],
        },
        {"type": "para", "text": "Enclosure: copy of your settlement letter."},
        {"type": "para", "text": "Yours faithfully,"},
        {"type": "signature", "text": m.name},
    ]
    _check_numbers(
        blocks,
        m.f,
        m.cited,
        chosen=m.chosen,
        total=m.total,
        extra={m.claim_no, m.policy_no, format_date_dmy(today_ist()), *(r.text_verbatim for r in m.reasons)},
    )
    letter = Letter(
        case_id=case.id,
        analysis_id=m.analysis.id,
        stage="S1",
        language="en",
        basic_mode=True,
        included={"line_item_ids": [str(i.id) for i in m.chosen], "reason_ids": [str(r.id) for r in m.reasons]},
        doc={"blocks": blocks, "footnotes": footnotes, "disclaimer": DISCLAIMER},
        version=1,
    )
    s.add(letter)
    s.commit()
    return letter


METHOD_TEXT = {"email": "by email", "post": "by post", "portal": "on the insurer's website"}


def create_ombudsman_letter(c: AppContext, s: Session, case: Case) -> Letter:
    """FR-026 item 1: the complaint letter to the Insurance Ombudsman. The caller has re-validated the
    RULE-ESC checks. The grievance history uses the logged event dates exactly (AC2)."""
    from claimsathi.escalation.service import event_rows

    m = _gather(c, s, case, None)
    events = event_rows(s, case)
    s1 = max((e for e in events if e.kind == "s1_sent"), key=lambda e: e.event_date)
    replies = [e for e in events if e.kind == "insurer_reply" and e.event_date >= s1.event_date]
    reply = max(replies, key=lambda e: e.event_date) if replies else None
    s2 = max((e for e in events if e.kind == "s2_filed"), key=lambda e: e.event_date, default=None)

    history = [
        f"On {format_date_dmy(s1.event_date)} I wrote to the insurer's grievance redressal officer "
        f"{METHOD_TEXT.get(str(s1.meta.get('method')), '')}".rstrip()
        + ", asking them to review this decision."
    ]
    if reply is not None:
        history.append(
            f"On {format_date_dmy(reply.event_date)} the insurer replied. I am not satisfied with the reply."
        )
    else:
        history.append("The insurer has not replied within one month of my letter.")
    if s2 is not None:
        history.append(f"On {format_date_dmy(s2.event_date)} I also filed a complaint on Bima Bharosa.")

    what = "the rejection of" if m.rejected else "deductions in"
    blocks: list[dict[str, Any]] = [
        {"type": "meta", "text": f"Date: {format_date_dmy(today_ist())}"},
        {"type": "meta", "text": "To: The Insurance Ombudsman, [office for your area]"},
        {
            "type": "subject",
            "text": (
                f"Subject: Complaint against {m.insurer} about {what} claim {m.claim_no} under policy {m.policy_no}"
            ),
        },
        {"type": "para", "text": "Respected Sir or Madam,"},
        {"type": "para", "text": f"I, {m.name}, make this complaint against {m.insurer.rstrip('.')}."},
        {"type": "para", "text": _facts_sentence(m, by="the insurer's letter")},
        {"type": "heading", "text": "Grievance with the insurer"},
        *({"type": "para", "text": h} for h in history),
        {"type": "heading", "text": "Grounds of complaint"},
    ]
    grounds, footnotes = _grounds(m, insurer_ref="the insurer's letter")
    blocks += grounds
    relief = (
        "(a) direct the insurer to settle my claim;"
        if m.rejected
        else f"(a) direct the insurer to pay the deducted amount of {format_inr(m.total)};"
    )
    blocks += [
        {"type": "para", "text": "I request the Ombudsman to:"},
        {
            "type": "list",
            "items": [
                relief,
                "(b) direct the insurer to state the specific policy terms it relied on;",
                "(c) grant any other relief that is fair.",
            ],
        },
        {
            "type": "para",
            "text": "I declare that this matter is not pending before, or decided by, any court, consumer commission "
            "or arbitrator.",
        },
        {"type": "heading", "text": "Enclosures"},
        {
            "type": "list",
            "items": [
                "(i) the insurer's decision letter;",
                "(ii) my letter to the insurer's grievance redressal officer;",
                "(iii) the insurer's reply"
                if reply is not None
                else "(iii) a statement that the insurer did not reply",
            ],
        },
        {"type": "para", "text": "Yours faithfully,"},
        {"type": "signature", "text": m.name},
    ]
    event_dates = {format_date_dmy(e.event_date) for e in (s1, reply, s2) if e is not None}
    _check_numbers(
        blocks,
        m.f,
        m.cited,
        chosen=m.chosen,
        total=m.total,
        extra={
            m.claim_no,
            m.policy_no,
            format_date_dmy(today_ist()),
            *event_dates,
            *(r.text_verbatim for r in m.reasons),
        },
    )
    letter = Letter(
        case_id=case.id,
        analysis_id=m.analysis.id,
        stage="S3",
        language="en",
        basic_mode=True,
        included={
            "line_item_ids": [str(i.id) for i in m.chosen],
            "reason_ids": [str(r.id) for r in m.reasons],
            "event_ids": [str(e.id) for e in (s1, reply, s2) if e is not None],
        },
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
    allowed: set[str] = {"1", "2"}  # the grounds' own paragraph numbers
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


EDITABLE_TYPES = {"meta", "subject", "para", "heading", "list", "quote", "signature"}
MAX_BLOCKS = 80
MAX_TEXT = 4000


def _original_quotes(letter: Letter) -> dict[str, dict[str, Any]]:
    """Verified quote blocks as generated (kept in `included` so later edits can always be checked against them)."""
    saved = letter.included.get("verified_quotes")
    if isinstance(saved, dict):
        return saved
    return {
        b["citation_id"]: {"text": b["text"], "quote": b.get("quote"), "footnote": b.get("footnote")}
        for b in letter.doc.get("blocks", [])
        if b.get("type") == "quote" and b.get("citation_id")
    }


def edit_letter(s: Session, letter: Letter, case: Case, base_version: int, blocks: list[dict[str, Any]]) -> Letter:
    """FR-027: user edits. A quote stays verified only if it is exactly the generated verified quote; otherwise it
    becomes plain text and loses its citation (AC1). Restoring the text restores the badge (AC2)."""
    if case.stale_since and case.stale_since > letter.created_at:
        raise AppError("case_stale", 409, "Your details changed. Create a new letter.")
    if base_version != letter.version:
        raise AppError(
            "version_conflict", 409, "The letter changed in another tab.", extra={"current_version": letter.version}
        )
    if not blocks or len(blocks) > MAX_BLOCKS:
        raise AppError("validation_error", 422, "The letter needs at least one paragraph.")
    originals = _original_quotes(letter)
    notes_by_citation = {n["citation_id"]: n for n in letter.doc.get("footnotes", []) if n.get("citation_id")}
    if not notes_by_citation:
        notes_by_citation = {n["citation_id"]: n for n in letter.included.get("footnotes", []) if n.get("citation_id")}
    out: list[dict[str, Any]] = []
    footnotes: list[dict[str, Any]] = []
    for b in blocks:
        kind = b.get("type")
        if kind not in EDITABLE_TYPES:
            raise AppError("validation_error", 422, "Unknown paragraph type.")
        if kind == "list":
            items = [str(x)[:MAX_TEXT] for x in (b.get("items") or [])]
            out.append({"type": "list", "items": items})
            continue
        text = str(b.get("text") or "")[:MAX_TEXT]
        cid = b.get("citation_id")
        orig = originals.get(cid) if isinstance(cid, str) else None
        if kind == "quote" and orig is not None and text == orig["text"] and cid in notes_by_citation:
            n = len(footnotes) + 1
            footnotes.append({**notes_by_citation[cid], "n": n})
            out.append({"type": "quote", "text": text, "footnote": n, "quote": orig["quote"], "citation_id": cid})
        else:
            out.append({"type": "para" if kind == "quote" else kind, "text": text, "edited": kind == "quote"})
    letter.included = {
        **letter.included,
        "verified_quotes": originals,
        "footnotes": list(notes_by_citation.values()),
    }
    letter.doc = {**letter.doc, "blocks": out, "footnotes": footnotes}
    letter.version += 1
    letter.reviewed_version = None  # an edited letter must be read again before export
    s.commit()
    return letter


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
    from claimsathi.letters.render import RendererUnavailable, render_pdf

    try:
        data = render_pdf(letter.doc)
    except RendererUnavailable as exc:
        raise AppError("export_unavailable", 503, "PDF download isn't available on this server right now.") from exc
    key = f"cases/{case.id}/letters/{letter.id}/v{letter.version}.pdf"
    c.store.put(key, data, "application/pdf")
    exp = LetterExport(
        letter_id=letter.id, case_id=case.id, letter_version=letter.version, format="pdf", storage_key=key
    )
    s.add(exp)
    s.commit()
    return exp
