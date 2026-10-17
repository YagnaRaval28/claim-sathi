"""HTTP endpoints for M1–M3 (VS-1). Contract: system-design §5 (paths, codes, idempotency)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, Request, Response, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.analysis.service import analysis_view, start_analysis
from claimsathi.api.deps import (
    consented_user,
    csrf,
    ctx,
    current_consent_version,
    current_user,
    db,
    has_processing_consent,
    owned_case,
)
from claimsathi.auth import service as auth
from claimsathi.cases.service import CaseCreate, case_summary, create_case, give_consent, progress
from claimsathi.context import AppContext
from claimsathi.core.errors import AppError, not_found
from claimsathi.documents.service import upload
from claimsathi.extraction import service as facts
from claimsathi.guards import idempotent_replay, idempotent_store
from claimsathi.letters.service import MIME, create_basic_letter, export_letter, letter_view, owned_letter
from claimsathi.models import Case, KnowledgeChunk, KnowledgeSource, LetterExport, User
from claimsathi.security.crypto import new_token

router = APIRouter(prefix="/api/v1", dependencies=[Depends(csrf)])
Lang = Literal["en", "gu", "hi"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _ip_hash(request: Request, c: AppContext) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256((c.settings.hash_pepper.get_secret_value() + ip).encode()).hexdigest()[:32]


def _after_commit(bg: BackgroundTasks, c: AppContext) -> None:
    if c.settings.task_queue == "inprocess":
        bg.add_task(c.dispatcher.run_pending)


# --- Health ------------------------------------------------------------------------------------------


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# --- Auth --------------------------------------------------------------------------------------------


@router.get("/auth/csrf")
def get_csrf(response: Response, request: Request, c: AppContext = Depends(ctx)) -> dict[str, str]:
    token = request.cookies.get(c.settings.csrf_cookie_name) or new_token(24)
    response.set_cookie(
        c.settings.csrf_cookie_name, token, httponly=False, secure=c.settings.cookie_secure, samesite="lax", path="/"
    )
    return {"csrf_token": token}


class EmailRequestIn(_In):
    email: EmailStr = Field(max_length=254)
    language: Lang = "en"


@router.post("/auth/email/request", status_code=204)
def email_request(
    body: EmailRequestIn, request: Request, c: AppContext = Depends(ctx), s: Session = Depends(db)
) -> Response:
    auth.request_code(c, s, email=str(body.email), ip_hash=_ip_hash(request, c), language=body.language)
    return Response(status_code=204)


class EmailVerifyIn(_In):
    email: EmailStr = Field(max_length=254)
    code: str = Field(pattern=r"^\d{6}$")
    trust_device: bool = False


@router.post("/auth/email/verify")
def email_verify(
    body: EmailVerifyIn, request: Request, response: Response, c: AppContext = Depends(ctx), s: Session = Depends(db)
) -> dict[str, Any]:
    res = auth.verify_code(
        c, s, email=str(body.email), code=body.code, trusted=body.trust_device, ip_hash=_ip_hash(request, c)
    )
    max_age = 90 * 24 * 3600 if body.trust_device else None
    response.set_cookie(
        c.settings.session_cookie_name,
        res.session_token,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    nxt = "consent" if not has_processing_consent(s, res.user.id) else "cases"
    if res.user.onboarded_at is None:
        nxt = "onboarding_language"
    return {"user": me_view(c, s, res.user), "next": nxt}


@router.get("/auth/providers")
def auth_providers(c: AppContext = Depends(ctx)) -> dict[str, bool]:
    return {"google": c.settings.google_enabled, "email": True}


@router.get("/auth/google/start")
def google_start(lang: Lang = "en", c: AppContext = Depends(ctx)) -> Response:
    from claimsathi.auth import google

    if not c.settings.google_enabled:
        raise not_found()
    url, cookie = google.start(c, lang)
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(
        google.COOKIE,
        cookie,
        max_age=google.STATE_TTL_S,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return resp


@router.get("/auth/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    c: AppContext = Depends(ctx),
    s: Session = Depends(db),
) -> Response:
    """FR-002: a cancelled or failed Google sign-in goes back to the sign-in page with no error state (AC2)."""
    from claimsathi.auth import google

    if not c.settings.google_enabled:
        raise not_found()
    cookie = request.cookies.get(google.COOKIE)
    lang = "en"
    try:
        data = google.read_state(c, cookie, state)
        lang = data["l"]
        if error or not code:
            raise google.GoogleSignInError("cancelled")
        tokens = google.exchange_code(c, code, data["v"])
        g_user = google.verify_id_token(c, str(tokens.get("id_token", "")), data["n"])
        user, token, _new = google.sign_in(c, s, g_user)
    except google.GoogleSignInError:
        resp = RedirectResponse(f"/{lang}/sign-in", status_code=302)
        resp.delete_cookie(google.COOKIE, path="/api/v1/auth/google")
        return resp
    if user.onboarded_at is None or not has_processing_consent(s, user.id):
        target = f"/{lang}/welcome/consent"
    else:
        target = f"/{lang}/cases"
    resp = RedirectResponse(target, status_code=302)
    resp.delete_cookie(google.COOKIE, path="/api/v1/auth/google")
    resp.set_cookie(
        c.settings.session_cookie_name,
        token,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return resp


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> Response:
    auth.revoke_session(s, request.state.session_id)
    response.delete_cookie(c.settings.session_cookie_name, path="/")
    response.status_code = 204
    return response


@router.post("/auth/logout-all", status_code=204)
def logout_all(
    response: Response, user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> Response:
    auth.revoke_all(s, user.id)
    response.delete_cookie(c.settings.session_cookie_name, path="/")
    response.status_code = 204
    return response


def me_view(c: AppContext, s: Session, user: User) -> dict[str, Any]:
    email = c.cipher.decrypt(user.email_enc)
    local, _, domain = email.partition("@")
    v = current_consent_version(s)
    return {
        "id": str(user.id),
        "display_language": user.display_language,
        "large_text": user.large_text,
        "email_masked": f"{local[:1]}•••@{domain}",
        "onboarded": user.onboarded_at is not None,
        "consent": {"version": v.version, "current": has_processing_consent(s, user.id)},
    }


@router.get("/me")
def me(user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)) -> dict[str, Any]:
    return me_view(c, s, user)


class MePatch(_In):
    display_language: Lang | None = None
    large_text: bool | None = None


@router.patch("/me")
def patch_me(
    body: MePatch, user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    if body.display_language:
        user.display_language = body.display_language
    if body.large_text is not None:
        user.large_text = body.large_text
    s.commit()
    return me_view(c, s, user)


# --- Consent -----------------------------------------------------------------------------------------


@router.get("/consent/notice")
def consent_notice(s: Session = Depends(db)) -> dict[str, Any]:
    v = current_consent_version(s)
    return {"version": v.version, "purposes": v.purposes, "draft": v.version.endswith("draft")}


class ConsentIn(_In):
    version: str = Field(max_length=32)
    purposes: list[Literal["processing", "reminders"]]


@router.post("/consents", status_code=201)
def consents(body: ConsentIn, user: User = Depends(current_user), s: Session = Depends(db)) -> dict[str, Any]:
    if body.version != current_consent_version(s).version:
        raise AppError("consent_required", 403, "The privacy notice has changed. Please review it again.")
    row = give_consent(s, user, version=body.version, purposes=list(body.purposes), language=user.display_language)
    # the reminders choice takes effect immediately (FR-036): replan email reminders on open cases
    from claimsathi.escalation.service import recompute

    open_cases = select(Case).where(Case.user_id == user.id, Case.status == "open", Case.deleted_at.is_(None))
    for case in s.scalars(open_cases):
        recompute(s, case)
    s.commit()
    return {"version": row.version, "purposes": row.purposes}


# --- Cases -------------------------------------------------------------------------------------------


@router.get("/cases")
def list_cases(
    user: User = Depends(current_user), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    rows = s.scalars(
        select(Case)
        .where(Case.user_id == user.id, Case.deleted_at.is_(None))
        .order_by(Case.last_activity_at.desc())
        .limit(50)
    ).all()
    return {"items": [case_summary(c, s, r) for r in rows]}


@router.post("/cases", status_code=201)
def post_case(
    body: CaseCreate,
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = body.model_dump()
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    case = create_case(c, s, user, body)
    out = case_summary(c, s, case)
    idempotent_store(s, user.id, idem or "", payload, 201, out)
    s.commit()
    return JSONResponse(out, status_code=201)


@router.get("/cases/{case_id}")
def get_case(
    case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    return case_summary(c, s, case)


@router.get("/cases/{case_id}/progress")
def get_progress(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    return progress(s, case)


# --- Documents ---------------------------------------------------------------------------------------


@router.post("/cases/{case_id}/documents", status_code=202)
async def post_document(
    bg: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form(alias="type")] = "decision_letter",
    case: Case = Depends(owned_case),
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> dict[str, Any]:
    data = await file.read(c.settings.max_file_bytes + 1)
    doc = upload(c, s, case, data=data, declared_mime=file.content_type or "", doc_type=doc_type)
    _after_commit(bg, c)
    return {"id": str(doc.id), "type": doc.type, "status": doc.status}


# --- Facts & line items ------------------------------------------------------------------------------


@router.get("/cases/{case_id}/facts")
def get_facts(
    case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    return facts.facts_view(c, s, case)


class FieldEdit(_In):
    name: str = Field(max_length=32)
    value: str | None = Field(default=None, max_length=300)
    unknown: bool = False


class FactsPatch(_In):
    base_version: int
    fields: list[FieldEdit] = Field(max_length=40)


@router.patch("/cases/{case_id}/facts")
def patch_facts(
    body: FactsPatch, case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    facts.patch_facts(c, s, case, body.base_version, [f.model_dump() for f in body.fields])
    return facts.facts_view(c, s, case)


class VersionIn(_In):
    base_version: int


@router.post("/cases/{case_id}/facts/confirm")
def confirm_facts(
    body: VersionIn, case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    facts.confirm_facts(s, case, body.base_version)
    return case_summary(c, s, case)


@router.get("/cases/{case_id}/line-items")
def get_line_items(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    return facts.line_items_view(s, case)


class LineItemIn(_In):
    description: str = Field(min_length=1, max_length=500)
    deducted_paise: int = Field(ge=0)
    billed_paise: int | None = Field(default=None, ge=0)
    reason_verbatim: str | None = Field(default=None, max_length=500)
    clause_cited_verbatim: str | None = Field(default=None, max_length=200)
    user_entered: bool = True


class LineItemsPut(_In):
    base_version: int
    items: list[LineItemIn] = Field(max_length=200)


@router.put("/cases/{case_id}/line-items")
def put_line_items(body: LineItemsPut, case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    facts.replace_line_items(s, case, body.base_version, [i.model_dump() for i in body.items])
    return facts.line_items_view(s, case)


@router.post("/cases/{case_id}/line-items/confirm")
def confirm_line_items(
    body: VersionIn, case: Case = Depends(owned_case), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    facts.confirm_line_items(s, case, body.base_version)
    return case_summary(c, s, case)


# --- Analysis ----------------------------------------------------------------------------------------


@router.post("/cases/{case_id}/analyses", status_code=202)
def post_analysis(
    bg: BackgroundTasks,
    case: Case = Depends(owned_case),
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    replay = idempotent_replay(s, user.id, idem, {"case": str(case.id), "op": "analysis"})
    if replay:
        return JSONResponse(replay[1], status_code=replay[0])
    a = start_analysis(s, case)
    out = {"id": str(a.id), "status": a.status}
    idempotent_store(s, user.id, idem or "", {"case": str(case.id), "op": "analysis"}, 202, out)
    s.commit()
    _after_commit(bg, c)
    return JSONResponse(out, status_code=202)


class CategoryIn(_In):
    category: Literal[
        "ped_waiting",
        "non_disclosure",
        "specific_waiting",
        "initial_waiting",
        "exclusion",
        "not_medically_necessary",
        "documents_or_intimation",
        "policy_not_in_force",
        "non_payable_items",
        "room_rent_proportionate",
        "reasonable_customary",
        "sub_limit",
        "copay_deductible",
        "other_unknown",
    ]


@router.patch("/cases/{case_id}/reasons/{reason_id}", status_code=202)
def patch_reason_category(
    reason_id: uuid.UUID,
    body: CategoryIn,
    bg: BackgroundTasks,
    case: Case = Depends(owned_case),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> dict[str, Any]:
    """FR-013: the user's choice of category overrides any model; the findings are checked again."""
    from claimsathi.models import DecisionReason

    reason = s.scalar(select(DecisionReason).where(DecisionReason.id == reason_id, DecisionReason.case_id == case.id))
    if reason is None:
        raise not_found()
    reason.category, reason.category_source = body.category, "user"
    a = start_analysis(s, case)
    _after_commit(bg, c)
    return {"analysis_id": str(a.id)}


class ChecklistIn(_In):
    status: Literal["pending", "obtained", "uploaded"]
    document_id: uuid.UUID | None = None


@router.patch("/cases/{case_id}/checklist/{item_key}")
def patch_checklist(
    item_key: str, body: ChecklistIn, case: Case = Depends(owned_case), s: Session = Depends(db)
) -> dict[str, Any]:
    from claimsathi.checklist.service import set_item

    return set_item(s, case, item_key[:64], body.status, body.document_id)


@router.get("/cases/{case_id}/analyses/latest")
def latest_analysis(case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    view = analysis_view(s, case)
    if view is None:
        raise not_found()
    return view


@router.get("/cases/{case_id}/sources/chunks/{chunk_id}")
def get_chunk(chunk_id: uuid.UUID, case: Case = Depends(owned_case), s: Session = Depends(db)) -> dict[str, Any]:
    row = s.execute(
        select(KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeSource)
        .where(
            KnowledgeChunk.id == chunk_id,
            KnowledgeSource.status != "draft",
            (KnowledgeSource.case_id.is_(None)) | (KnowledgeSource.case_id == case.id),
        )
    ).first()
    if row is None:
        raise not_found()
    ch, src = row
    return {
        "chunk_id": str(ch.id),
        "clause_ref": ch.clause_ref,
        "text": ch.text,
        "source": {
            "title": src.title,
            "issuer": src.issuer,
            "version": src.version,
            "effective_from": src.effective_from.isoformat(),
            "url": src.url,
            "synthetic": src.synthetic,
        },
    }


# --- Letters -----------------------------------------------------------------------------------------


class LetterIn(_In):
    stage: Literal["S1"] = "S1"
    language: Literal["en"] = "en"
    basic_mode: Literal[True] = True
    line_item_ids: list[uuid.UUID] | None = None


@router.post("/cases/{case_id}/letters", status_code=201)
def post_letter(
    body: LetterIn,
    case: Case = Depends(owned_case),
    user: User = Depends(consented_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
    idem: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    payload = {"case": str(case.id), **body.model_dump(mode="json")}
    replay = idempotent_replay(s, user.id, idem, payload)
    if replay:  # same letter, but its *current* state (review status, staleness)
        existing, _ = owned_letter(s, uuid.UUID(replay[1]["id"]), user.id)
        return JSONResponse(letter_view(s, existing, case), status_code=replay[0])
    letter = create_basic_letter(c, s, case, body.line_item_ids)
    out = letter_view(s, letter, case)
    idempotent_store(s, user.id, idem or "", payload, 201, out)
    s.commit()
    return JSONResponse(out, status_code=201)


@router.get("/letters/{letter_id}")
def get_letter(letter_id: uuid.UUID, user: User = Depends(current_user), s: Session = Depends(db)) -> dict[str, Any]:
    letter, case = owned_letter(s, letter_id, user.id)
    return letter_view(s, letter, case)


class LetterBlockIn(_In):
    type: Literal["meta", "subject", "para", "heading", "list", "quote", "signature"]
    text: str | None = Field(default=None, max_length=4000)
    items: list[str] | None = Field(default=None, max_length=20)
    citation_id: str | None = Field(default=None, max_length=64)
    footnote: int | None = None
    quote: str | None = Field(default=None, max_length=2000)
    edited: bool | None = None


class LetterEditIn(_In):
    base_version: int
    blocks: list[LetterBlockIn] = Field(min_length=1, max_length=80)


@router.patch("/letters/{letter_id}")
def patch_letter(
    letter_id: uuid.UUID, body: LetterEditIn, user: User = Depends(current_user), s: Session = Depends(db)
) -> dict[str, Any]:
    from claimsathi.letters.service import edit_letter

    letter, case = owned_letter(s, letter_id, user.id)
    edit_letter(s, letter, case, body.base_version, [b.model_dump(exclude_none=True) for b in body.blocks])
    return letter_view(s, letter, case)


class ReviewIn(_In):
    version: int


@router.post("/letters/{letter_id}/review")
def review_letter(
    letter_id: uuid.UUID, body: ReviewIn, user: User = Depends(current_user), s: Session = Depends(db)
) -> dict[str, Any]:
    letter, case = owned_letter(s, letter_id, user.id)
    if body.version != letter.version:
        raise AppError(
            "version_conflict",
            409,
            "The letter changed. Read the latest version.",
            extra={"current_version": letter.version},
        )
    letter.reviewed_version = letter.version
    s.commit()
    return letter_view(s, letter, case)


class ExportIn(_In):
    format: Literal["pdf", "docx"] = "pdf"


@router.post("/letters/{letter_id}/exports")
def post_export(
    letter_id: uuid.UUID,
    body: ExportIn,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> dict[str, Any]:
    letter, case = owned_letter(s, letter_id, user.id)
    exp = export_letter(c, s, letter, case, body.format)
    return {
        "id": str(exp.id),
        "format": exp.format,
        "download_path": f"/api/v1/letters/{letter.id}/exports/{exp.id}/file",
    }


@router.get("/letters/{letter_id}/exports/{export_id}/file")
def download_export(
    letter_id: uuid.UUID,
    export_id: uuid.UUID,
    user: User = Depends(current_user),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> Response:
    letter, _case = owned_letter(s, letter_id, user.id)
    exp = s.scalar(select(LetterExport).where(LetterExport.id == export_id, LetterExport.letter_id == letter.id))
    if exp is None:
        raise not_found()
    return Response(
        c.store.get(exp.storage_key),
        media_type=MIME.get(exp.format, "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="claimsathi-letter.{exp.format}"',
            "Cache-Control": "no-store",
        },
    )
