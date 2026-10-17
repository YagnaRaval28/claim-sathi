"""RFC 9457 problem+json errors and the error-code catalogue (system-design §3.7)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from claimsathi.core.logging import get_logger

TITLES: dict[str, str] = {
    "validation_error": "Invalid request",
    "not_found": "Not found",
    "unauthenticated": "Sign-in required",
    "consent_required": "Consent required",
    "forbidden": "Not allowed",
    "csrf_failed": "Security check failed",
    "rate_limited": "Too many requests",
    "email_code_invalid": "Code not accepted",
    "email_code_expired": "Code expired",
    "fields_not_confirmed": "Details not confirmed",
    "line_items_not_confirmed": "Deductions not confirmed",
    "required_fields_missing": "Required details missing",
    "case_stale": "Details changed",
    "letter_not_reviewed": "Letter not reviewed",
    "version_conflict": "Changed elsewhere",
    "idempotency_key_reused": "Duplicate request key",
    "open_case_limit": "Too many open cases",
    "duplicate_file": "File already added",
    "case_upload_limit": "Upload limit reached",
    "payload_too_large": "File too large",
    "unsupported_media_type": "Unsupported file type",
    "storage_full": "Storage temporarily full",
    "out_of_scope": "Outside ClaimSathi's scope",
    "ai_paused_budget": "AI features paused",
    "export_unavailable": "PDF export unavailable",
    "case_closed": "Case closed",
    "escalation_blocked": "Ombudsman conditions not met",
    "confirmation_invalid": "Confirmation code mismatch",
    "retention_already_extended": "Already extended",
    "email_in_use": "Email already in use",
    "warnings_not_acknowledged": "Warnings not acknowledged",
    "internal_error": "Something went wrong",
}

log = get_logger("errors")


class AppError(Exception):
    def __init__(
        self,
        code: str,
        status: int,
        detail: str = "",
        *,
        errors: list[dict[str, str]] | None = None,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        if code not in TITLES:
            raise ValueError(f"unknown error code {code!r}: add it to the catalogue first")
        self.code, self.status, self.detail = code, status, detail
        self.errors, self.extra, self.headers = errors or [], extra or {}, headers or {}


def not_found() -> AppError:
    # Identical body for "missing" and "not owned": never reveal existence (system-design §3.4).
    return AppError("not_found", 404, "This item isn't available.")


def problem(request: Request, code: str, status: int, detail: str = "", **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://claimsathi.example/errors/{code}",
        "title": TITLES.get(code, code),
        "status": status,
        "code": code,
        "detail": detail,
        "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
    }
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        resp = problem(request, exc.code, exc.status, exc.detail, errors=exc.errors, **exc.extra)
        resp.headers.update(exc.headers)
        return resp

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in e.get("loc", [])[1:]),
                "code": str(e.get("type", "invalid")),
                "message": str(e.get("msg", "")),
            }
            for e in exc.errors()
        ]
        return problem(request, "validation_error", 422, "Some fields are invalid.", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return problem(request, "not_found", 404, "This item isn't available.")
        if exc.status_code == 405:
            return problem(request, "validation_error", 405, "Method not allowed.")
        return problem(request, "internal_error", exc.status_code, "")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", error_code="internal_error", route=request.url.path)
        return problem(request, "internal_error", 500, "Please try again. Quote the request ID if it continues.")
