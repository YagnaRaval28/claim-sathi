"""Process-wide dependencies, built once in create_app() and replaced in tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from claimsathi.ai.gateway import CallRecord, ModelGateway, Provider
from claimsathi.core.config import Settings
from claimsathi.infra import Mailer, ObjectStore
from claimsathi.jobs import Dispatcher
from claimsathi.models import AiCall
from claimsathi.security.crypto import FieldCipher


@dataclass
class AppContext:
    settings: Settings
    session_factory: sessionmaker[Session]
    store: ObjectStore
    mailer: Mailer
    cipher: FieldCipher
    provider: Provider
    dispatcher: Dispatcher

    def gateway(self, case_id: uuid.UUID | None) -> ModelGateway:
        sf = self.session_factory

        def record(rec: CallRecord) -> None:
            # Separate short transaction: usage is recorded even if the caller's transaction rolls back.
            with sf() as s:
                s.add(
                    AiCall(
                        case_id=case_id,
                        step_key=rec.step_key,
                        provider=rec.provider,
                        model=rec.model,
                        prompt_version=rec.prompt_version,
                        input_tokens=rec.input_tokens,
                        output_tokens=rec.output_tokens,
                        thinking_tokens=rec.thinking_tokens,
                        latency_ms=rec.latency_ms,
                        status=rec.status,
                        error_code=rec.error_code,
                        cost_micro_usd=rec.cost_micro_usd,
                    )
                )
                s.commit()

        def spent() -> int:
            with sf() as s:
                return int(s.scalar(select(func.coalesce(func.sum(AiCall.cost_micro_usd), 0))) or 0)

        budget = int(self.settings.credit_budget_usd * 1_000_000 * self.settings.credit_guard_pct / 100)
        return ModelGateway(
            self.provider,
            model=self.settings.llm_model_id,
            timeout_s=self.settings.llm_timeout_s,
            record=record,
            spent_micro_usd=spent,
            budget_micro_usd=budget,
            bill=self.provider.name == "vertex",
        )
