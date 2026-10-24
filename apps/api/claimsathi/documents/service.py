"""Uploads (PRD FR-008/009) and text-layer reading (FR-010 subset).

Upload path: browser → API (decision CI-04 default: no storage keys in the browser). Validation order:
magic bytes, size, per-case caps, duplicate, global storage guard. Parsing happens only in the task.
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import timedelta
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claimsathi.context import AppContext
from claimsathi.core.errors import AppError, not_found
from claimsathi.guards import hit
from claimsathi.jobs import Handler, enqueue, step, task
from claimsathi.models import DOC_TYPES, Case, Document, DocumentObject, DocumentPage
from claimsathi.security.crypto import sha256

MAGIC = {b"%PDF-": "application/pdf", b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg"}
VS1_ACCEPTED = {"application/pdf"}  # photos/OCR arrive in milestone M4


def sniff_mime(data: bytes) -> str | None:
    for magic, mime in MAGIC.items():
        if data.startswith(magic):
            return mime
    return None


def upload(c: AppContext, s: Session, case: Case, *, data: bytes, declared_mime: str, doc_type: str) -> Document:
    st = c.settings
    if doc_type not in DOC_TYPES:
        raise AppError("validation_error", 422, "Unknown document type.")
    if len(data) == 0:
        raise AppError("validation_error", 422, "The file is empty.")
    if len(data) > st.max_file_bytes:
        raise AppError("payload_too_large", 413, "Files can be up to 20 MB each.")
    mime = sniff_mime(data)
    if mime is None or mime != declared_mime or mime not in VS1_ACCEPTED:
        raise AppError("unsupported_media_type", 415, "Only PDF files are supported in this version.")
    files, size = s.execute(
        select(func.count(DocumentObject.id), func.coalesce(func.sum(DocumentObject.size_bytes), 0)).where(
            DocumentObject.case_id == case.id
        )
    ).one()
    if files >= st.max_files_per_case or size + len(data) > st.max_case_bytes:
        raise AppError("case_upload_limit", 409, "This case has reached its upload limit (15 files, 50 MB).")
    digest = sha256(data)
    if s.scalar(select(DocumentObject.id).where(DocumentObject.case_id == case.id, DocumentObject.sha256 == digest)):
        raise AppError("duplicate_file", 409, "You've already added this file.")
    if c.store.total_bytes() + len(data) > st.storage_limit_mb * 1024 * 1024 * st.storage_guard_pct / 100:
        raise AppError("storage_full", 503, "Uploads are paused for a while. Please try again later.")
    doc = Document(id=uuid.uuid4(), case_id=case.id, type=doc_type, status="queued")
    key = f"cases/{case.id}/documents/{doc.id}/objects/0.pdf"
    c.store.put(key, data, mime)
    s.add(doc)
    s.flush()
    s.add(
        DocumentObject(
            document_id=doc.id, case_id=case.id, seq=0, storage_key=key, mime=mime, size_bytes=len(data), sha256=digest
        )
    )
    enqueue(s, "doc.read", {"document_id": str(doc.id)}, dedupe_key=f"doc.read:{doc.id}")
    s.commit()
    return doc


def is_password_error(exc: pdfium.PdfiumError) -> bool:
    return "password" in str(exc).lower()


def read_pdf_lines(data: bytes) -> list[list[str]]:
    """Text layer per page → list of non-empty lines. Scanned PDFs return empty pages."""
    pdf = pdfium.PdfDocument(data)
    try:
        pages: list[list[str]] = []
        for page in pdf:
            text = page.get_textpage().get_text_range()
            pages.append([ln.strip() for ln in text.splitlines() if ln.strip()])
        return pages
    finally:
        pdf.close()


def _read_failed(s: Session, payload: dict[str, Any]) -> None:
    doc = s.get(Document, uuid.UUID(payload["document_id"]))
    if doc is None or doc.status not in ("queued", "reading"):
        return
    doc.status, doc.status_reason = "failed", "read_failed"
    step(
        s,
        case_id=doc.case_id,
        job_kind="document",
        job_ref=doc.id,
        step_key="reading",
        ordinal=1,
        status="failed",
        error_code="read_failed",
    )


def make_read_handler(c: AppContext) -> Handler:
    @task("doc.read", on_failure=_read_failed)
    def _read(s: Session, payload: dict[str, Any]) -> None:
        doc = s.get(Document, uuid.UUID(payload["document_id"]))
        if doc is None or doc.status not in ("queued", "reading"):
            return  # idempotent: deleted or already processed
        step(
            s,
            case_id=doc.case_id,
            job_kind="document",
            job_ref=doc.id,
            step_key="reading",
            ordinal=1,
            status="in_progress",
        )
        doc.status = "reading"
        obj = s.scalar(select(DocumentObject).where(DocumentObject.document_id == doc.id))
        assert obj is not None
        try:
            pages = read_pdf_lines(c.store.get(obj.storage_key))
        except pdfium.PdfiumError as exc:
            # FR-008 AC3: a password-protected PDF waits for the user's password (see unlock_pdf).
            locked = is_password_error(exc)
            doc.status = "needs_attention" if locked else "failed"
            doc.status_reason = "password_required" if locked else "unreadable_pdf"
            step(
                s,
                case_id=doc.case_id,
                job_kind="document",
                job_ref=doc.id,
                step_key="reading",
                ordinal=1,
                status="failed",
                error_code=doc.status_reason,
            )
            return
        if len(pages) > c.settings.max_pages_per_case:
            doc.status, doc.status_reason = "rejected", "too_many_pages"
            step(
                s,
                case_id=doc.case_id,
                job_kind="document",
                job_ref=doc.id,
                step_key="reading",
                ordinal=1,
                status="failed",
                error_code="too_many_pages",
            )
            return
        for i, lines in enumerate(pages, start=1):
            key = f"cases/{doc.case_id}/documents/{doc.id}/ocr/{i}.json"
            payload_lines = [{"id": f"p{i}-l{j}", "text": t} for j, t in enumerate(lines, 1)]
            c.store.put(key, json.dumps(payload_lines, ensure_ascii=False).encode(), "application/json")
            s.add(
                DocumentPage(
                    document_id=doc.id, case_id=doc.case_id, page_no=i, ocr_key=key, ocr_quality=1.0 if lines else 0.0
                )
            )
        doc.page_count = len(pages)
        has_text = any(pages)
        doc.status = "ready" if has_text else "needs_attention"
        doc.status_reason = None if has_text else "no_text_layer"
        step(s, case_id=doc.case_id, job_kind="document", job_ref=doc.id, step_key="reading", ordinal=1, status="done")
        if has_text:
            enqueue(
                s,
                "case.extract",
                {"case_id": str(doc.case_id), "after": str(doc.id)},
                dedupe_key=f"case.extract:{doc.case_id}:{doc.id}",
                queue="ai",
            )

    return _read


def unlock_pdf(c: AppContext, s: Session, case: Case, document_id: uuid.UUID, password: str) -> Document:
    """FR-008 AC3: open a password-protected PDF with the user's password and keep an unlocked copy in its place,
    then read it as usual. The password is used in memory only: it is never stored, logged or queued."""
    doc = s.scalar(select(Document).where(Document.id == document_id, Document.case_id == case.id))
    if doc is None:
        raise not_found()
    if doc.status_reason != "password_required":
        raise AppError("not_password_protected", 409, "This file doesn't need a password.")
    hit(s, f"pdf_password:{doc.id}", limit=10, window=timedelta(hours=1))
    obj = s.scalar(select(DocumentObject).where(DocumentObject.document_id == doc.id))
    assert obj is not None
    try:
        pdf = pdfium.PdfDocument(c.store.get(obj.storage_key), password=password)
    except pdfium.PdfiumError as exc:
        if is_password_error(exc):
            raise AppError("pdf_password_incorrect", 422, "That password didn't open the file.") from None
        raise AppError("unsupported_media_type", 415, "This PDF can't be read.") from None
    try:
        buf = io.BytesIO()
        pdf.save(buf, flags=pdfium_c.FPDF_REMOVE_SECURITY)
    finally:
        pdf.close()
    unlocked = buf.getvalue()
    c.store.put(obj.storage_key, unlocked, obj.mime)
    obj.size_bytes = len(unlocked)  # sha256 stays the uploaded file's, so the same upload is still a duplicate
    doc.status, doc.status_reason = "queued", None
    enqueue(s, "doc.read", {"document_id": str(doc.id)}, dedupe_key=f"doc.read:{doc.id}:unlocked")
    s.commit()
    return doc


def case_lines(c: AppContext, s: Session, case_id: uuid.UUID) -> list[tuple[str, str]]:
    """All ready text lines of a case with stable IDs `D{doc_index}-p{page}-l{line}`."""
    out: list[tuple[str, str]] = []
    docs = s.scalars(
        select(Document)
        .where(Document.case_id == case_id, Document.status == "ready")
        .order_by(Document.created_at, Document.id)
    ).all()
    for n, doc in enumerate(docs, start=1):
        pages = s.scalars(
            select(DocumentPage).where(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_no)
        ).all()
        for p in pages:
            out.extend((f"D{n}-{ln['id']}", ln["text"]) for ln in json.loads(c.store.get(p.ocr_key)))
    return out
