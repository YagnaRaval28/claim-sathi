"""ORM models: the subset of system-design §4.2 needed through VS-1, plus cross-cutting tables.

Tables for later milestones are added by their own migrations, when that milestone is built.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from claimsathi.core.db import Base

UUIDPK = UUID(as_uuid=True)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDPK, primary_key=True, server_default=text("gen_random_uuid()"))


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _case_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)


# --- Identity & consent ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    email_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    email_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    display_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="en")
    large_text: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    analytics_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (CheckConstraint("display_language IN ('en','gu','hi')", name="lang"),)


class EmailChallenge(Base):
    __tablename__ = "email_challenges"
    id: Mapped[uuid.UUID] = _pk()
    email_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    code_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False, server_default="sign_in")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # change_email only: the signed-in user and the new address (encrypted), set when the code is sent
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id", ondelete="CASCADE"))
    new_email_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("attempts <= 5", name="attempts_max"),
        CheckConstraint("purpose IN ('sign_in','change_email')", name="purpose"),
        Index("ix_email_challenges_email_created", "email_hash", "created_at"),
    )


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = _pk()
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False, server_default="user")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDPK, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDPK, ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = _created()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("kind IN ('user','admin')", name="kind"),
        CheckConstraint(
            "(kind = 'user' AND user_id IS NOT NULL AND admin_user_id IS NULL) OR "
            "(kind = 'admin' AND admin_user_id IS NOT NULL AND user_id IS NULL)",
            name="owner",
        ),
    )


class AdminUser(Base):
    """Admin console accounts (PRD FR-037). Email kept as a keyed hash plus an encrypted copy, like users."""

    __tablename__ = "admin_users"
    id: Mapped[uuid.UUID] = _pk()
    email_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    email_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    totp_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_totp: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    first_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (CheckConstraint("role IN ('admin','reviewer')", name="role"),)


class ConsentVersion(Base):
    __tablename__ = "consent_versions"
    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    purposes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    notice_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    requires_reconsent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    published_at: Mapped[datetime] = _created()


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(ForeignKey("consent_versions.version"), nullable=False)
    purposes: Mapped[list[str]] = mapped_column(ARRAY(String(16)), nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    granted_at: Mapped[datetime] = _created()
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- Cases & documents -----------------------------------------------------------------------------


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nickname_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default="open")
    mode: Mapped[str] = mapped_column(String(8), nullable=False, server_default="full")
    stage: Mapped[str] = mapped_column(String(24), nullable=False, server_default="S0_PREPARE")
    policy_type: Mapped[str] = mapped_column(String(12), nullable=False, server_default="unknown")
    complainant_name_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    complainant_relation: Mapped[str | None] = mapped_column(String(12))
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    insurer_name: Mapped[str | None] = mapped_column(String(200))
    fields_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    line_items_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stale_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wording_mode: Mapped[str] = mapped_column(String(10), nullable=False, server_default="none")
    wording_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDPK, ForeignKey("knowledge_sources.id", use_alter=True, name="fk_cases_wording_source")
    )
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    s2_filed_at: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_extended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_activity_at: Mapped[datetime] = _created()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("status IN ('open','closed')", name="status"),
        CheckConstraint("mode IN ('full','limited','delay')", name="mode"),
        CheckConstraint("stage IN ('S0_PREPARE','S1_INSURER_GRIEVANCE','S3_OMBUDSMAN','CLOSED')", name="stage"),
        CheckConstraint("policy_type IN ('individual','floater','group','unknown')", name="policy_type"),
        CheckConstraint("wording_mode IN ('library','uploaded','none')", name="wording_mode"),
        Index("ix_cases_user_status", "user_id", "status"),
        Index(
            "ix_cases_retention_delete_after",
            "retention_delete_after",
            postgresql_where=text("retention_delete_after IS NOT NULL"),
        ),
    )


DOC_TYPES = (
    "decision_letter",
    "settlement_breakup",
    "policy_schedule",
    "policy_wording",
    "discharge_summary",
    "final_bill",
    "reports",
    "insurer_correspondence",
    "other",
)
DOC_STATUSES = ("uploading", "queued", "scanning", "reading", "ready", "needs_attention", "failed", "rejected")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="queued")
    status_reason: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("type IN (" + ",".join(f"'{t}'" for t in DOC_TYPES) + ")", name="type"),
        CheckConstraint("status IN (" + ",".join(f"'{s}'" for s in DOC_STATUSES) + ")", name="status"),
    )


class DocumentObject(Base):
    __tablename__ = "document_objects"
    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[uuid.UUID] = _case_fk()
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    mime: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    __table_args__ = (
        UniqueConstraint("case_id", "sha256", name="uq_document_objects_case_sha"),
        CheckConstraint("size_bytes <= 20971520", name="size"),
        CheckConstraint("mime IN ('application/pdf','image/jpeg','image/png')", name="mime"),
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[uuid.UUID] = _case_fk()
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_key: Mapped[str] = mapped_column(String(300), nullable=False)
    ocr_quality: Mapped[float] = mapped_column(nullable=False)
    __table_args__ = (UniqueConstraint("document_id", "page_no", name="uq_document_pages_doc_page"),)


# --- Facts -------------------------------------------------------------------------------------------


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    value_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    extracted_value: Mapped[str | None] = mapped_column(Text)
    extracted_value_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_flag: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ok")
    source_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    __table_args__ = (
        UniqueConstraint("case_id", "name", name="uq_extracted_fields_case_name"),
        CheckConstraint("value IS NULL OR value_enc IS NULL", name="one_value"),
        CheckConstraint("status IN ('found','not_found','user_entered','unknown_by_user')", name="status"),
        CheckConstraint("confidence_flag IN ('ok','please_check')", name="flag"),
    )


CATEGORIES = (  # PRD FR-013 taxonomy
    "ped_waiting",
    "non_disclosure",
    "specific_waiting",
    "initial_waiting",
    "exclusion",
    "not_medically_necessary",
    "documents_or_intimation",
    "policy_not_in_force",
    "non_payable_items",
    "room_rent_proportionate",
    "reasonable_customary",
    "sub_limit",
    "copay_deductible",
    "other_unknown",
)
_CATEGORY_CHECK = "category IS NULL OR category IN (" + ",".join(f"'{c}'" for c in CATEGORIES) + ")"


class DecisionReason(Base):
    __tablename__ = "decision_reasons"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text_verbatim: Mapped[str] = mapped_column(Text, nullable=False)
    clause_cited_verbatim: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    category: Mapped[str | None] = mapped_column(String(32))
    category_source: Mapped[str | None] = mapped_column(String(8))  # user | model
    audit_status: Mapped[str | None] = mapped_column(String(32))
    user_entered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))  # FR-019
    __table_args__ = (CheckConstraint(_CATEGORY_CHECK, name="category"),)


class LineItem(Base):
    __tablename__ = "line_items"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    billed_paise: Mapped[int | None] = mapped_column(BigInteger)
    deducted_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_verbatim: Mapped[str | None] = mapped_column(Text)
    clause_cited_verbatim: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(32))
    category_source: Mapped[str | None] = mapped_column(String(8))  # user | model
    audit_status: Mapped[str | None] = mapped_column(String(32))
    user_entered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    unitemised: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    source_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    __table_args__ = (
        CheckConstraint(_CATEGORY_CHECK, name="category"),
        CheckConstraint("deducted_paise >= 0", name="deducted_nonneg"),
        CheckConstraint("billed_paise IS NULL OR billed_paise >= 0", name="billed_nonneg"),
        CheckConstraint("billed_paise IS NULL OR deducted_paise <= billed_paise", name="deducted_le_billed"),
    )


# --- Knowledge & rules -----------------------------------------------------------------------------


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[uuid.UUID] = _pk()
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(8), nullable=False, server_default="library")
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    issuer: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(String(500))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")
    checked_by: Mapped[str | None] = mapped_column(String(200))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("type IN ('regulation','policy_wording')", name="type"),
        CheckConstraint("scope IN ('library','case')", name="scope"),
        CheckConstraint("(scope = 'case') = (case_id IS NOT NULL)", name="scope_case"),
        CheckConstraint("status IN ('draft','published','retired')", name="status"),
        CheckConstraint("status <> 'published' OR checked_by IS NOT NULL", name="published_attested"),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[uuid.UUID] = _pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_ref: Mapped[str | None] = mapped_column(String(80))
    clause_key: Mapped[str | None] = mapped_column(String(80), index=True)
    heading_path: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(clause_ref, '') || ' ' || text)", persisted=True),
    )
    flags: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False, server_default="{}")
    __table_args__ = (Index("ix_knowledge_chunks_tsv", "tsv", postgresql_using="gin"),)


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[uuid.UUID] = _pk()
    rule_key: Mapped[str] = mapped_column(String(48), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        UniqueConstraint("rule_key", "version", name="uq_rules_key_version"),
        CheckConstraint("status IN ('enabled','disabled_pending_verification','retired')", name="status"),
        CheckConstraint(
            "status <> 'enabled' OR (source_ref IS NOT NULL AND verified_by IS NOT NULL) "
            "OR kind IN ('pattern','limit','banned_phrases','model_price','quota','credit_budget')",
            name="enabled_needs_source",
        ),
        Index("uq_rules_one_enabled", "rule_key", unique=True, postgresql_where=text("status = 'enabled'")),
    )


# --- Analysis & letters ----------------------------------------------------------------------------


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="queued")
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    rule_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    source_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    totals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    error_code: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = _created()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','superseded','paused_budget')", name="status"
        ),
    )


class CounterPoint(Base):
    __tablename__ = "counter_points"
    id: Mapped[uuid.UUID] = _pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[uuid.UUID] = _case_fk()
    target_type: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, nullable=False)
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    statement_en: Mapped[str] = mapped_column(Text, nullable=False)
    basis_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_key: Mapped[str | None] = mapped_column(String(48))
    shown: Mapped[bool] = mapped_column(Boolean, nullable=False)
    drop_reason: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        CheckConstraint("shown OR drop_reason IS NOT NULL", name="dropped_has_reason"),
        CheckConstraint("basis_type IN ('regulation','policy_wording','case_fact','deterministic_rule')", name="basis"),
    )


class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[uuid.UUID] = _pk()
    counter_point_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("counter_points.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[uuid.UUID] = _case_fk()
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("knowledge_chunks.id"), index=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verifier_version: Mapped[str] = mapped_column(String(16), nullable=False)


class Letter(Base):
    __tablename__ = "letters"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("analyses.id", ondelete="SET NULL"))
    stage: Mapped[str] = mapped_column(String(4), nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ready")
    basic_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    included: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    doc: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    reviewed_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("stage IN ('S1','S3')", name="stage"),
        CheckConstraint("language IN ('en','gu','hi')", name="lang"),
    )


class LetterExport(Base):
    __tablename__ = "letter_exports"
    id: Mapped[uuid.UUID] = _pk()
    letter_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("letters.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[uuid.UUID] = _case_fk()
    letter_version: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(4), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = _created()
    __table_args__ = (UniqueConstraint("letter_id", "letter_version", "format", name="uq_letter_exports_ver_fmt"),)


# --- Operations ------------------------------------------------------------------------------------


class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[uuid.UUID] = _pk()
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String(48), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="open")
    decision_category: Mapped[str | None] = mapped_column(String(32))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("admin_users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("status IN ('open','correct','incorrect','kb_fix','skipped')", name="status"),
        Index("ix_review_items_status_created", "status", "created_at"),
    )


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(64), nullable=False)
    queue: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="pending")
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _created()
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('pending','dispatched','done','failed')", name="status"),
        Index("ix_outbox_pending", "status", "created_at", postgresql_where=text("status = 'pending'")),
    )


class JobStep(Base):
    __tablename__ = "job_steps"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    job_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    job_ref: Mapped[uuid.UUID] = mapped_column(UUIDPK, nullable=False)
    step_key: Mapped[str] = mapped_column(String(32), nullable=False)
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="waiting")
    attempt: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(48))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("job_ref", "step_key", name="uq_job_steps_ref_step"),
        CheckConstraint("status IN ('waiting','in_progress','done','retrying','failed')", name="status"),
    )


class AiCall(Base):
    __tablename__ = "ai_calls"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    step_key: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    thinking_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(48))
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _created()


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    scope_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created()


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    bucket_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(12), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created()


# --- Escalation: events, deadlines, reminders (PRD FR-020 to FR-023) ----------------------------------

EVENT_KINDS = ("s1_sent", "insurer_reply", "s2_filed", "s3_filed", "ombudsman_outcome", "payment_received", "closed")
DEADLINE_KINDS = (
    "ombudsman_eligible_from",
    "ombudsman_limitation",
    "insurer_response_expected",
    "ombudsman_award_expected",
)


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("documents.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("kind IN (" + ",".join(f"'{k}'" for k in EVENT_KINDS) + ")", name="kind"),
        Index("ix_case_events_case_date", "case_id", "event_date"),
    )


class Deadline(Base):
    __tablename__ = "deadlines"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    rule_key: Mapped[str] = mapped_column(String(48), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_from: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="active")
    __table_args__ = (
        CheckConstraint("kind IN (" + ",".join(f"'{k}'" for k in DEADLINE_KINDS) + ")", name="kind"),
        CheckConstraint("status IN ('active','passed','cancelled')", name="status"),
        UniqueConstraint("case_id", "kind", name="uq_deadlines_case_kind"),
        Index("ix_deadlines_due_active", "due_date", postgresql_where=text("status = 'active'")),
    )


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    deadline_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("deadlines.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="scheduled")
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("channel IN ('email','in_app')", name="channel"),
        CheckConstraint("status IN ('scheduled','sent','failed','cancelled')", name="status"),
        UniqueConstraint("case_id", "kind", "channel", "send_at", name="uq_reminders_case_kind_channel_send"),
        Index("ix_reminders_send_scheduled", "send_at", postgresql_where=text("status = 'scheduled'")),
    )


class RuleAcknowledgement(Base):
    __tablename__ = "rule_acknowledgements"
    case_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(48), primary_key=True)
    rule_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    acknowledged_at: Mapped[datetime] = _created()


# --- Data controls (PRD FR-030) ------------------------------------------------------------------------


class DataExport(Base):
    __tablename__ = "data_exports"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"))
    scope: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default="queued")
    storage_key: Mapped[str | None] = mapped_column(String(300))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("scope IN ('case','account')", name="scope"),
        CheckConstraint("status IN ('queued','ready','failed','expired')", name="status"),
        CheckConstraint("scope = 'account' OR case_id IS NOT NULL", name="case_scope_has_case"),
    )


class ChecklistItem(Base):
    """Evidence checklist (PRD FR-018): each item traces to a row of the RULE-EVIDENCE map."""

    __tablename__ = "checklist_items"
    case_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    item_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("documents.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = _created()
    __table_args__ = (CheckConstraint("status IN ('pending','obtained','uploaded')", name="status"),)


class OAuthIdentity(Base):
    """Google sign-in identities (PRD FR-002, system-design §4.2). One user may have both Google and email code."""

    __tablename__ = "oauth_identities"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        CheckConstraint("provider = 'google'", name="provider"),
        UniqueConstraint("provider", "subject", name="uq_oauth_identities_provider_subject"),
    )


class SupportGrant(Base):
    """A user's 7-day grant letting a reviewer see one case (PRD FR-042)."""

    __tablename__ = "support_grants"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    granted_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("expires_at <= granted_at + interval '7 days'", name="max_seven_days"),
        Index("ix_support_grants_active", "case_id", postgresql_where=text("revoked_at IS NULL")),
    )
