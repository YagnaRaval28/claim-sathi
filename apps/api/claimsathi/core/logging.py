"""Structured logging with a field allowlist (NFR-019, system-design §3.8).

Only allowlisted keys reach the log sink. Document content, field values, emails, prompts
and codes can therefore never be logged by accident. In strict mode (tests) an unknown key raises.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

ALLOWED_KEYS = frozenset(
    {
        "event",
        "level",
        "timestamp",
        "logger",
        "request_id",
        "route",
        "method",
        "status",
        "latency_ms",
        "user_pseudo_id",
        "case_id",
        "job",
        "step",
        "attempt",
        "error_code",
        "cold_start",
        "count",
        "provider",
        "model",
        "task",
    }
)

_strict = False


def allowlist_filter(_logger: Any, _method: str, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    unknown = set(event_dict) - ALLOWED_KEYS
    if unknown:
        if _strict:
            raise ValueError(f"log keys not in allowlist: {sorted(unknown)}")
        for key in unknown:
            event_dict.pop(key, None)
        event_dict["dropped_keys"] = len(unknown)
    return event_dict


def configure_logging(level: str = "info", *, json: bool = False, strict: bool = False) -> None:
    global _strict
    _strict = strict
    logging.basicConfig(stream=sys.stdout, level=level.upper(), format="%(message)s")
    renderer: Any = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            allowlist_filter,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = "claimsathi") -> Any:
    return structlog.get_logger(name)
