"""Transactional outbox + task runner (system-design §3.6).

Services call `enqueue()` inside their transaction. After commit, `Dispatcher.run_pending()` executes the
tasks. In-process mode runs them in the same process, which is the local and test default. Cloud Tasks
dispatch is added at M9. Task handlers are idempotent: progress lives in `job_steps`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from claimsathi.core.clock import now_utc
from claimsathi.core.logging import get_logger
from claimsathi.models import JobStep, Outbox

log = get_logger("jobs")

Handler = Callable[[Session, dict[str, Any]], None]
_HANDLERS: dict[str, Handler] = {}
_ON_FAILURE: dict[str, Handler] = {}


def task(name: str, on_failure: Handler | None = None) -> Callable[[Handler], Handler]:
    """Register a task handler. `on_failure` runs in a fresh transaction if the handler raises, so the user
    sees a real "failed" state instead of work that stays queued forever."""

    def deco(fn: Handler) -> Handler:
        _HANDLERS[name] = fn
        if on_failure is not None:
            _ON_FAILURE[name] = on_failure
        return fn

    return deco


def enqueue(session: Session, task_name: str, payload: dict[str, Any], *, dedupe_key: str, queue: str = "docs") -> None:
    exists = session.scalar(select(Outbox.id).where(Outbox.dedupe_key == dedupe_key))
    if exists is None:
        session.add(Outbox(task_name=task_name, queue=queue, payload=payload, dedupe_key=dedupe_key))
        session.flush()


def step(
    session: Session,
    *,
    case_id: uuid.UUID,
    job_kind: str,
    job_ref: uuid.UUID,
    step_key: str,
    ordinal: int,
    status: str,
    error_code: str | None = None,
) -> None:
    row = session.scalar(select(JobStep).where(JobStep.job_ref == job_ref, JobStep.step_key == step_key))
    if row is None:
        row = JobStep(
            case_id=case_id,
            job_kind=job_kind,
            job_ref=job_ref,
            step_key=step_key,
            ordinal=ordinal,
            status="waiting",
            attempt=0,
        )
        session.add(row)
        session.flush()
    if status == "in_progress":
        row.started_at = now_utc()
        row.attempt = (row.attempt or 0) + 1
    if status in ("done", "failed"):
        row.finished_at = now_utc()
    row.status, row.error_code = status, error_code


class Dispatcher:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def requeue_interrupted(self) -> int:
        """In-process mode only: tasks left "dispatched" by a stopped process are queued again on start-up."""
        with self._sf() as s:
            rows = s.scalars(select(Outbox).where(Outbox.status == "dispatched")).all()
            for r in rows:
                r.status = "pending"
            s.commit()
            return len(rows)

    def run_pending(self, max_tasks: int = 50) -> int:
        ran = 0
        for _ in range(max_tasks):
            with self._sf() as s:
                row = s.scalar(
                    select(Outbox)
                    .where(Outbox.status == "pending")
                    .order_by(Outbox.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                if row is None:
                    return ran
                row.status, row.dispatched_at = "dispatched", now_utc()
                row.attempts += 1
                name, payload, oid = row.task_name, dict(row.payload), row.id
                s.commit()
            handler = _HANDLERS[name]
            try:
                with self._sf() as s:
                    handler(s, payload)
                    s.commit()
                status = "done"
            except Exception as exc:  # the class name only: messages can carry document content
                log.error("task_failed", task=name, error_code=type(exc).__name__)
                status = "failed"
                hook = _ON_FAILURE.get(name)
                if hook is not None:
                    try:
                        with self._sf() as s:
                            hook(s, payload)
                            s.commit()
                    except Exception as hook_exc:
                        log.error("task_failure_hook_failed", task=name, error_code=type(hook_exc).__name__)
            with self._sf() as s:
                ob = s.get(Outbox, oid)
                if ob is not None:
                    ob.status = status
                    s.commit()
            ran += 1
        return ran
