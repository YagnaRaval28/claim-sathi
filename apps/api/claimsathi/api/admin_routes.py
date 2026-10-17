"""Admin console API (`/api/v1/admin`, system-design §5): sign-in with mandatory TOTP, review queue, case content
only under the user's grant. Admin sessions use the `cs_admin` cookie; consumer sessions are never accepted."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.admin import service as adm
from claimsathi.api.deps import csrf, ctx, db
from claimsathi.auth import google
from claimsathi.context import AppContext
from claimsathi.core.clock import now_utc
from claimsathi.core.errors import AppError, not_found
from claimsathi.models import AdminUser, Case, ReviewItem

router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(csrf)])


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


def current_admin(*roles: str) -> Callable[..., AdminUser]:
    def dep(request: Request, c: AppContext = Depends(ctx), s: Session = Depends(db)) -> AdminUser:
        admin, _row = adm.admin_for_session(c, s, request.cookies.get(c.settings.admin_cookie_name))
        if roles and admin.role not in roles:
            raise AppError("forbidden", 403, "Your role can't do this.")
        request.state.admin_session_id = _row.id
        return admin

    return dep


any_admin = current_admin("admin", "reviewer")
admin_only = current_admin("admin")


# --- Sign-in: Google allowlist, then TOTP ---------------------------------------------------------


@router.get("/auth/google/start")
def admin_google_start(c: AppContext = Depends(ctx)) -> Response:
    if not c.settings.admin_google_enabled:
        raise not_found()
    url, cookie = google.start(c, "en", google.admin_client(c))
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(
        google.COOKIE,
        cookie,
        max_age=google.STATE_TTL_S,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="lax",
        path="/api/v1/admin/auth/google",
    )
    return resp


@router.get("/auth/google/callback")
def admin_google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    c: AppContext = Depends(ctx),
    s: Session = Depends(db),
) -> Response:
    if not c.settings.admin_google_enabled:
        raise not_found()
    client = google.admin_client(c)
    try:
        data = google.read_state(c, request.cookies.get(google.COOKIE), state)
        if error or not code:
            raise google.GoogleSignInError("cancelled")
        tokens = google.exchange_code(c, code, data["v"], client)
        g_user = google.verify_id_token(c, str(tokens.get("id_token", "")), data["n"], client)
    except google.GoogleSignInError:
        return RedirectResponse("/en/admin/sign-in", status_code=302)
    admin = adm.allowlisted(c, s, subject=g_user.subject, email=g_user.email)
    if admin is None:
        adm.audit(s, None, "admin_sign_in_denied", "admin_user", None)
        s.commit()
        return RedirectResponse("/en/admin/sign-in?denied=1", status_code=302)
    s.commit()
    resp = RedirectResponse("/en/admin/mfa", status_code=302)
    resp.delete_cookie(google.COOKIE, path="/api/v1/admin/auth/google")
    resp.set_cookie(
        adm.MFA_COOKIE,
        adm.mfa_cookie(c, admin),
        max_age=adm.MFA_TTL_S,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="lax",
        path="/api/v1/admin/auth",
    )
    return resp


@router.get("/auth/mfa")
def admin_mfa_setup(request: Request, c: AppContext = Depends(ctx), s: Session = Depends(db)) -> dict[str, Any]:
    admin = adm.pending_admin(c, s, request.cookies.get(adm.MFA_COOKIE))
    return adm.mfa_setup(c, s, admin)


class TotpIn(_In):
    code: str = Field(pattern=r"^\d{6}$")


@router.post("/auth/totp", status_code=204)
def admin_totp(
    body: TotpIn, request: Request, response: Response, c: AppContext = Depends(ctx), s: Session = Depends(db)
) -> Response:
    admin = adm.pending_admin(c, s, request.cookies.get(adm.MFA_COOKIE))
    token = adm.verify_totp(c, s, admin, body.code)
    response.delete_cookie(adm.MFA_COOKIE, path="/api/v1/admin/auth")
    response.set_cookie(
        c.settings.admin_cookie_name,
        token,
        httponly=True,
        secure=c.settings.cookie_secure,
        samesite="strict",
        path="/",
        max_age=int(adm.ADMIN_SESSION.total_seconds()),
    )
    response.status_code = 204
    return response


@router.post("/auth/logout", status_code=204)
def admin_logout(
    request: Request,
    response: Response,
    admin: AdminUser = Depends(any_admin),
    s: Session = Depends(db),
    c: AppContext = Depends(ctx),
) -> Response:
    from claimsathi.models import Session as DbSession

    row = s.get(DbSession, request.state.admin_session_id)
    if row is not None:
        row.revoked_at = now_utc()
    adm.audit(s, admin, "admin_signed_out", "admin_user", str(admin.id))
    s.commit()
    response.delete_cookie(c.settings.admin_cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me")
def admin_me(admin: AdminUser = Depends(any_admin), c: AppContext = Depends(ctx)) -> dict[str, Any]:
    email = c.cipher.decrypt(admin.email_enc)
    local, _, domain = email.partition("@")
    return {"id": str(admin.id), "role": admin.role, "email_masked": f"{local[:1]}•••@{domain}"}


# --- Review queue (FR-040) and case content under grant (FR-042) ------------------------------------


def _item_view(s: Session, item: ReviewItem) -> dict[str, Any]:
    from claimsathi.datacontrols.service import active_grant

    grant = active_grant(s, item.case_id) if item.case_id else None
    return {
        "id": str(item.id),
        "source": item.source,
        "target_type": item.target_type,
        "reason": item.reason,
        "comment": item.comment,
        "language": item.language,
        "status": item.status,
        "decision_category": item.decision_category,
        "created_at": item.created_at.isoformat(),
        "payload": item.payload,  # the flagged output and its citations only (FR-035)
        "case_access_until": grant.expires_at.isoformat() if grant else None,
    }


@router.get("/review-items")
def list_review_items(
    status: Literal["open", "correct", "incorrect", "kb_fix", "skipped", "all"] = "open",
    admin: AdminUser = Depends(any_admin),
    s: Session = Depends(db),
) -> dict[str, Any]:
    q = select(ReviewItem).order_by(ReviewItem.created_at.desc()).limit(100)
    if status != "all":
        q = q.where(ReviewItem.status == status)
    return {"items": [_item_view(s, i) for i in s.scalars(q)]}


@router.get("/review-items/{item_id}")
def get_review_item(
    item_id: uuid.UUID, admin: AdminUser = Depends(any_admin), s: Session = Depends(db)
) -> dict[str, Any]:
    item = s.get(ReviewItem, item_id)
    if item is None:
        raise not_found()
    return _item_view(s, item)


class DecisionIn(_In):
    status: Literal["correct", "incorrect", "kb_fix", "skipped"]
    decision_category: str | None = Field(default=None, max_length=32)


@router.patch("/review-items/{item_id}")
def decide_review_item(
    item_id: uuid.UUID, body: DecisionIn, admin: AdminUser = Depends(any_admin), s: Session = Depends(db)
) -> dict[str, Any]:
    item = s.get(ReviewItem, item_id)
    if item is None:
        raise not_found()
    item.status, item.decision_category = body.status, body.decision_category
    item.decided_by, item.decided_at = admin.id, now_utc()
    adm.audit(s, admin, f"review_item_{body.status}", "review_item", str(item.id))
    s.commit()
    return _item_view(s, item)


@router.get("/review-items/{item_id}/case-content")
def review_case_content(
    item_id: uuid.UUID, admin: AdminUser = Depends(any_admin), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    """FR-042: case content only while the user's grant is active; otherwise 403, and the attempt is logged."""
    from claimsathi.datacontrols.service import active_grant
    from claimsathi.extraction.service import facts_view, line_items_view

    item = s.get(ReviewItem, item_id)
    if item is None or item.case_id is None:
        raise not_found()
    case = s.get(Case, item.case_id)
    if case is None or case.deleted_at is not None:
        raise not_found()
    if active_grant(s, case.id) is None:
        adm.audit(s, admin, "case_access_denied", "case", str(case.id))
        s.commit()
        raise AppError("forbidden", 403, "The user hasn't given access to this case.")
    adm.audit(s, admin, "case_content_viewed", "case", str(case.id))
    s.commit()
    return {"facts": facts_view(c, s, case)["fields"], "line_items": line_items_view(s, case)["items"]}


@router.get("/admins")
def list_admins(
    admin: AdminUser = Depends(admin_only), s: Session = Depends(db), c: AppContext = Depends(ctx)
) -> dict[str, Any]:
    out = []
    for a in s.scalars(select(AdminUser).order_by(AdminUser.created_at)):
        email = c.cipher.decrypt(a.email_enc)
        local, _, domain = email.partition("@")
        out.append(
            {
                "id": str(a.id),
                "role": a.role,
                "email_masked": f"{local[:1]}•••@{domain}",
                "mfa": a.totp_enabled_at is not None,
                "disabled": a.disabled_at is not None,
            }
        )
    return {"items": out}
