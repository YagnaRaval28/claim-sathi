"""Structured-output schemas for model calls (PRD AI-003). Versioned with their prompts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FieldName = Literal[
    "insurer",
    "tpa",
    "policy_number",
    "product_name",
    "policy_type",
    "first_inception_date",
    "patient_name",
    "hospital",
    "admission_date",
    "discharge_date",
    "claim_number",
    "claim_type",
    "claimed_amount",
    "paid_amount",
    "disallowed_amount",
    "decision_letter_date",
    "decision_type",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldOut(_Strict):
    name: FieldName
    value: str | None = Field(description="Copied exactly as written in the document, or null if absent")
    line_ids: list[str] = Field(default_factory=list, max_length=10)


class LineItemOut(_Strict):
    description: str = Field(max_length=500)
    deducted_amount: str = Field(max_length=40, description="Exactly as written, e.g. 'Rs. 18,400'")
    billed_amount: str | None = Field(default=None, max_length=40)
    reason_verbatim: str | None = Field(default=None, max_length=500)
    clause_cited_verbatim: str | None = Field(default=None, max_length=200)
    line_ids: list[str] = Field(default_factory=list, max_length=10)


class ReasonOut(_Strict):
    text_verbatim: str = Field(max_length=1000)
    clause_cited_verbatim: str | None = Field(default=None, max_length=200)
    line_ids: list[str] = Field(default_factory=list, max_length=10)


class ExtractionResult(_Strict):
    fields: list[FieldOut] = Field(max_length=40)
    line_items: list[LineItemOut] = Field(default_factory=list, max_length=200)
    reasons: list[ReasonOut] = Field(default_factory=list, max_length=20)
