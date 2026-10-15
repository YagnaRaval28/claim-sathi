"""ModelGateway: the only path to a language model (engineering standards §7).

Responsibilities: provider selection, schema validation with one repair attempt, retries with backoff,
timeouts, content-free usage accounting (`ai_calls`) and the credit guard. The model has no tools.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# US$ per 1M tokens (VERIFIED 15 Oct 2026, Vertex pricing). Developer free tier is billed at 0.
PRICES_PER_M: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.5-flash": (1.65, 9.90),
}


@dataclass(frozen=True)
class ProviderResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int | None = None


class Provider(Protocol):
    name: str

    def generate(
        self, *, model: str, system: str, user: str, json_schema: dict[str, object], timeout_s: float
    ) -> ProviderResult: ...


class TransientProviderError(Exception):
    """Retryable: network errors, 429, 5xx."""


class ModelOutputInvalid(Exception):
    """Schema-invalid output after the single repair attempt."""


class BudgetExceeded(Exception):
    """Credit guard tripped (NFR-023)."""


@dataclass(frozen=True)
class CallRecord:
    step_key: str
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int | None
    latency_ms: int
    status: str
    error_code: str | None
    cost_micro_usd: int


class ModelGateway:
    def __init__(
        self,
        provider: Provider,
        *,
        model: str,
        timeout_s: float,
        record: Callable[[CallRecord], None],
        spent_micro_usd: Callable[[], int],
        budget_micro_usd: int,
        bill: bool = True,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._p, self._model, self._timeout = provider, model, timeout_s
        self._record, self._spent, self._budget = record, spent_micro_usd, budget_micro_usd
        self._bill, self._retries, self._sleep = bill, retries, sleep

    def structured(self, *, step_key: str, prompt_version: str, system: str, user: str, schema: type[T]) -> T:
        if self._spent() >= self._budget:
            raise BudgetExceeded()
        json_schema = schema.model_json_schema()
        prompt = user
        for repair in (False, True):
            result = self._call_with_retries(step_key, prompt_version, system, prompt, json_schema)
            try:
                return schema.model_validate_json(result.text)
            except ValidationError as exc:
                if repair:
                    self._log(step_key, prompt_version, result, 0, "invalid_output", "schema_invalid")
                    raise ModelOutputInvalid(step_key) from exc
                errs = json.dumps([{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()][:10], default=str)
                prompt = (
                    f"{user}\n\nYour previous output did not match the JSON schema. "
                    f"Validation errors: {errs}. Return only valid JSON for the schema."
                )
        raise AssertionError("unreachable")

    def _call_with_retries(
        self, step_key: str, pv: str, system: str, user: str, json_schema: dict[str, object]
    ) -> ProviderResult:
        delays = [2.0, 8.0, 30.0][: self._retries]
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                res = self._p.generate(
                    model=self._model, system=system, user=user, json_schema=json_schema, timeout_s=self._timeout
                )
            except TransientProviderError:
                ms = int((time.monotonic() - started) * 1000)
                self._log(step_key, pv, ProviderResult(""), ms, "transient_error", "provider_transient")
                if attempt >= len(delays):
                    raise
                self._sleep(delays[attempt])
                attempt += 1
                continue
            ms = int((time.monotonic() - started) * 1000)
            self._log(step_key, pv, res, ms, "ok", None)
            return res

    def _cost(self, res: ProviderResult) -> int:
        if not self._bill:
            return 0
        pin, pout = PRICES_PER_M.get(self._model, (0.0, 0.0))
        out = res.output_tokens + (res.thinking_tokens or 0)
        return round(res.input_tokens * pin + out * pout)  # micro-USD: tokens * $/1M

    def _log(self, step_key: str, pv: str, res: ProviderResult, ms: int, status: str, err: str | None) -> None:
        self._record(
            CallRecord(
                step_key,
                self._p.name,
                self._model,
                pv,
                res.input_tokens,
                res.output_tokens,
                res.thinking_tokens,
                ms,
                status,
                err,
                self._cost(res),
            )
        )
