"""Model providers.

- fake: deterministic recorded responses (CI and offline development). It matches a recording when every
  `match_all` substring occurs in the user content.
- gemini_dev: Gemini Developer API **free tier, synthetic data only** (D-008). Startup config refuses it
  in staging and prod.
- vertex: added at milestone M9 (asia-south1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claimsathi.ai.gateway import ProviderResult, TransientProviderError

RECORDINGS_DIR = Path(__file__).parent / "recordings"


class FakeProvider:
    name = "fake"

    def __init__(self, recordings_dir: Path = RECORDINGS_DIR) -> None:
        self._recs: list[dict[str, Any]] = [
            json.loads(p.read_text(encoding="utf-8")) for p in sorted(recordings_dir.glob("*.json"))
        ]

    def generate(
        self, *, model: str, system: str, user: str, json_schema: dict[str, object], timeout_s: float
    ) -> ProviderResult:
        for rec in self._recs:
            if all(s in user for s in rec["match_all"]):
                text = json.dumps(rec["response"], ensure_ascii=False)
                return ProviderResult(text=text, input_tokens=len(user) // 4, output_tokens=len(text) // 4)
        # No recording: behave like a model that found nothing. Never invent values.
        return ProviderResult(text=json.dumps({"fields": [], "line_items": [], "reasons": []}))


class GeminiDevProvider:
    name = "gemini_dev"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_DEV_API_KEY is required for LLM_PROVIDER=gemini_dev")
        from google import genai

        self._client = genai.Client(api_key=api_key)

    def generate(
        self, *, model: str, system: str, user: str, json_schema: dict[str, object], timeout_s: float
    ) -> ProviderResult:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=json_schema,
            temperature=0,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        try:
            resp = self._client.models.generate_content(model=model, contents=user, config=config)
        except errors.ServerError as exc:
            raise TransientProviderError(str(exc.code)) from exc
        except errors.ClientError as exc:
            if exc.code == 429:
                raise TransientProviderError("429") from exc
            raise
        usage = resp.usage_metadata
        return ProviderResult(
            text=resp.text or "",
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,
            thinking_tokens=(usage.thoughts_token_count if usage else None),
        )
