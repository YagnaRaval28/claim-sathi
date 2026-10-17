"""Crypto, config validation, logging allowlist, PDF reading, chunking, model gateway, letter HTML escaping."""

from __future__ import annotations

import base64
import json
import os

import pytest
from cryptography.exceptions import InvalidTag
from pydantic import ValidationError

from claimsathi.ai.gateway import (
    BudgetExceeded,
    CallRecord,
    ModelGateway,
    ModelOutputInvalid,
    Provider,
    ProviderResult,
    TransientProviderError,
)
from claimsathi.ai.providers import FakeProvider
from claimsathi.ai.schemas import ExtractionResult
from claimsathi.core import logging as cslog
from claimsathi.core.config import Settings
from claimsathi.devtools.pdfgen import text_pdf
from claimsathi.documents.service import read_pdf_lines, sniff_mime
from claimsathi.knowledge.ingest import chunk_text
from claimsathi.letters.render import letter_html
from claimsathi.security.crypto import FieldCipher, keyed_hash

KEY = os.urandom(32)


def test_field_cipher_roundtrip_and_tamper_detection() -> None:
    c = FieldCipher(KEY)
    blob = c.encrypt("Ravi K. Mehta")
    assert b"Ravi" not in blob and c.decrypt(blob) == "Ravi K. Mehta"
    with pytest.raises(InvalidTag):  # AES-GCM authentication failure
        c.decrypt(blob[:-1] + bytes([blob[-1] ^ 1]))


def test_keyed_hash_depends_on_pepper() -> None:
    assert keyed_hash("p" * 32, "a@b.c") != keyed_hash("q" * 32, "a@b.c")


def _env(**over: str) -> dict[str, str]:
    base = {
        "SUPABASE_DB_URL": "postgresql+psycopg://x@y/z",
        "FIELD_DATA_KEY": base64.b64encode(KEY).decode(),
        "HASH_PEPPER": "h" * 64,
        "CODE_PEPPER": "c" * 64,
        "CSRF_SECRET": "s" * 64,
    }
    base.update(over)
    return base


@pytest.mark.req("AI-014")
def test_config_refuses_free_ai_tier_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(APP_ENV="prod", LLM_PROVIDER="gemini_dev").items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError, match="D-008"):
        Settings(_env_file=None)


@pytest.mark.parametrize("over", [{"STORAGE_BACKEND": "memory"}, {"MAILER": "memory"}])
def test_config_refuses_memory_backends_in_staging(monkeypatch: pytest.MonkeyPatch, over: dict[str, str]) -> None:
    for k, v in _env(APP_ENV="staging", **over).items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError, match="only allowed locally"):
        Settings(_env_file=None)


def test_config_rejects_short_key_without_echoing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(FIELD_DATA_KEY=base64.b64encode(b"short-secret-value").decode()).items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError) as ei:
        Settings(_env_file=None)
    assert "short-secret-value" not in str(ei.value)


@pytest.mark.req("NFR-019")
def test_logging_allowlist_drops_or_rejects_unknown_keys() -> None:
    previous = cslog._strict  # create_app() in test env turns strict mode on; set both modes explicitly here
    try:
        cslog._strict = False
        ev = cslog.allowlist_filter(None, "info", {"event": "x", "route": "/a", "email": "a@b.c"})
        assert "email" not in ev and ev["dropped_keys"] == 1
        cslog._strict = True
        with pytest.raises(ValueError):
            cslog.allowlist_filter(None, "info", {"event": "x", "ocr_text": "secret"})
    finally:
        cslog._strict = previous


def test_pdf_fixture_text_layer_roundtrip() -> None:
    lines = ["Claim No. SHI/CL/2026/000123", "Amount claimed: Rs. 2,64,820", "1) Consumables (gloves): Rs. 6,250"]
    data = text_pdf(lines)
    assert sniff_mime(data) == "application/pdf"
    assert read_pdf_lines(data) == [lines]


def test_sniff_rejects_spoofed_type() -> None:
    assert sniff_mime(b"<html><script>") is None
    assert sniff_mime(b"\x89PNG\r\n\x1a\n....") == "image/png"


def test_chunking_by_clause_headings() -> None:
    chunks = chunk_text("Intro line\nPara 17(a) First.\nPara 17(b) Second\ncontinued.\nAnnexure I List.")
    assert [(c.clause_ref, c.text) for c in chunks] == [
        (None, "Intro line"),
        ("Para 17(a)", "Para 17(a) First."),
        ("Para 17(b)", "Para 17(b) Second continued."),
        ("Annexure I", "Annexure I List."),
    ]


class _Seq:
    name = "seq"

    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs

    def generate(self, **_: object) -> ProviderResult:
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return ProviderResult(text=str(out), input_tokens=100, output_tokens=10)


def _gw(provider: Provider, records: list[CallRecord], spent: int = 0) -> ModelGateway:
    def record(r: CallRecord) -> None:
        records.append(r)

    return ModelGateway(
        provider,
        model="gemini-2.5-flash",
        timeout_s=1,
        record=record,
        spent_micro_usd=lambda: spent,
        budget_micro_usd=1000,
        sleep=lambda _: None,
    )


VALID = json.dumps({"fields": [], "line_items": [], "reasons": []})


@pytest.mark.req("AI-003")
def test_gateway_repairs_invalid_json_once() -> None:
    recs: list[CallRecord] = []
    out = _gw(_Seq(["not json", VALID]), recs).structured(
        step_key="x", prompt_version="v", system="s", user="u", schema=ExtractionResult
    )
    assert out.fields == [] and [r.status for r in recs] == ["ok", "ok"]


def test_gateway_fails_cleanly_after_second_invalid_output() -> None:
    recs: list[CallRecord] = []
    with pytest.raises(ModelOutputInvalid):
        _gw(_Seq(["{}", "{}"]), recs).structured(
            step_key="x", prompt_version="v", system="s", user="u", schema=ExtractionResult
        )


@pytest.mark.req("AI-008")
def test_gateway_retries_transient_errors_then_succeeds() -> None:
    recs: list[CallRecord] = []
    p = _Seq([TransientProviderError("503"), TransientProviderError("429"), VALID])
    _gw(p, recs).structured(step_key="x", prompt_version="v", system="s", user="u", schema=ExtractionResult)
    assert [r.status for r in recs] == ["transient_error", "transient_error", "ok"]


@pytest.mark.req("NFR-023")
def test_gateway_credit_guard_blocks_calls() -> None:
    with pytest.raises(BudgetExceeded):
        _gw(_Seq([VALID]), [], spent=1000).structured(
            step_key="x", prompt_version="v", system="s", user="u", schema=ExtractionResult
        )


def test_call_records_hold_no_content() -> None:
    assert set(CallRecord.__dataclass_fields__) == {
        "step_key",
        "provider",
        "model",
        "prompt_version",
        "input_tokens",
        "output_tokens",
        "thinking_tokens",
        "latency_ms",
        "status",
        "error_code",
        "cost_micro_usd",
    }


def test_fake_provider_returns_empty_result_when_no_recording_matches() -> None:
    res = FakeProvider().generate(model="m", system="s", user="unrelated", json_schema={}, timeout_s=1)
    assert json.loads(res.text) == {"fields": [], "line_items": [], "reasons": []}


def test_letter_html_escapes_everything() -> None:
    html = letter_html(
        {"blocks": [{"type": "para", "text": "<script>alert(1)</script>"}], "footnotes": [], "disclaimer": "d"}
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
