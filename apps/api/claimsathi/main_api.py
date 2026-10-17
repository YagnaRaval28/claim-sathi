"""FastAPI application factory. Run: uvicorn --factory claimsathi.main_api:create_app"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from claimsathi.ai.gateway import Provider
from claimsathi.ai.providers import FakeProvider, GeminiDevProvider
from claimsathi.analysis.service import make_analysis_handler
from claimsathi.api.datacontrol_routes import router as datacontrol_router
from claimsathi.api.escalation_routes import router as escalation_router
from claimsathi.api.routes import router
from claimsathi.context import AppContext
from claimsathi.core.config import Settings, get_settings
from claimsathi.core.db import make_session_factory
from claimsathi.core.errors import install_error_handlers
from claimsathi.core.logging import configure_logging, get_logger
from claimsathi.datacontrols.service import make_export_handler, run_retention
from claimsathi.documents.service import make_read_handler
from claimsathi.escalation.service import send_due_reminders
from claimsathi.extraction.service import make_extract_handler
from claimsathi.infra import MemoryMailer, MemoryObjectStore, S3ObjectStore, SmtpMailer
from claimsathi.jobs import Dispatcher
from claimsathi.security.crypto import FieldCipher

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
    # JSON and file downloads only: nothing may load, run or frame (SEC-HDR-1).
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


def build_context(settings: Settings) -> AppContext:
    if settings.storage_backend == "memory":
        store: MemoryObjectStore | S3ObjectStore = MemoryObjectStore()
    else:
        s3 = S3ObjectStore(
            endpoint=settings.storage_s3_endpoint,
            region=settings.storage_s3_region,
            access_key=settings.supabase_storage_key.get_secret_value(),
            secret_key=settings.supabase_storage_secret.get_secret_value(),
            bucket=settings.storage_bucket_cases,
        )
        s3.ensure_bucket()
        store = s3
    mailer = (
        MemoryMailer()
        if settings.mailer == "memory"
        else SmtpMailer(settings.smtp_host, settings.smtp_port, settings.mail_from)
    )
    provider: Provider = (
        GeminiDevProvider(settings.gemini_dev_api_key.get_secret_value())
        if settings.llm_provider == "gemini_dev"
        else FakeProvider()
    )
    sf = make_session_factory(settings.database_url)
    return AppContext(
        settings=settings,
        session_factory=sf,
        store=store,
        mailer=mailer,
        cipher=FieldCipher(settings.field_key_bytes),
        provider=provider,
        dispatcher=Dispatcher(sf),
    )


def reminder_ticker(c: AppContext, stop: threading.Event, interval_s: float = 60.0) -> None:
    """Local stand-in for the Cloud Scheduler tick (system-design §3.6): sends due reminders once a minute."""
    log = get_logger("scheduler")
    while not stop.wait(interval_s):
        try:
            send_due_reminders(c)
            run_retention(c)
        except Exception as exc:  # keep ticking; the class name only
            log.error("reminder_tick_failed", error_code=type(exc).__name__)


def create_app(context: AppContext | None = None) -> FastAPI:
    settings = context.settings if context else get_settings()
    configure_logging(
        settings.log_level, json=settings.app_env in ("staging", "prod"), strict=settings.app_env == "test"
    )
    c = context or build_context(settings)
    make_read_handler(c)
    make_extract_handler(c)
    make_analysis_handler()
    make_export_handler(c)

    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # In-process queue: finish work that a stopped process left behind (tests drive tasks explicitly).
        if settings.task_queue == "inprocess" and settings.app_env != "test":

            def resume() -> None:
                c.dispatcher.requeue_interrupted()
                c.dispatcher.run_pending()

            threading.Thread(target=resume, name="resume-tasks", daemon=True).start()
            threading.Thread(target=reminder_ticker, args=(c, stop), name="reminders", daemon=True).start()
        yield
        stop.set()

    app = FastAPI(
        lifespan=lifespan,
        title="ClaimSathi API",
        version="0.1.0",
        docs_url=None if settings.app_env == "prod" else "/docs",
        openapi_url="/api/v1/openapi.json",
    )
    app.state.ctx = c
    install_error_handlers(app)
    log = get_logger("http")

    @app.middleware("http")
    async def _request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.request_id = str(uuid.uuid4())
        started = time.monotonic()
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        response.headers["X-Request-ID"] = request.state.request_id
        log.info(
            "request",
            route=request.url.path,
            method=request.method,
            status=response.status_code,
            latency_ms=int((time.monotonic() - started) * 1000),
            request_id=request.state.request_id,
        )
        return response

    app.include_router(router)
    app.include_router(escalation_router)
    app.include_router(datacontrol_router)
    return app
