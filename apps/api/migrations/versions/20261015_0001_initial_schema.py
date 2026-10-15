"""initial schema (M1/VS-1 tables)

Generated from claimsathi.models via SQLAlchemy's PostgreSQL DDL compiler, then reviewed. Later migrations
are written with `alembic revision --autogenerate` against a live database and reviewed.

Revision ID: 0001
Revises:
Create Date: 2026-10-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE users (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\temail_hash BYTEA NOT NULL, \n\temail_enc BYTEA NOT NULL, \n\temail_verified_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdisplay_language VARCHAR(2) DEFAULT 'en' NOT NULL, \n\tlarge_text BOOLEAN DEFAULT false NOT NULL, \n\tanalytics_opt_out BOOLEAN DEFAULT false NOT NULL, \n\tonboarded_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_users PRIMARY KEY (id), \n\tCONSTRAINT ck_users_lang CHECK (display_language IN ('en','gu','hi')), \n\tCONSTRAINT uq_users_email_hash UNIQUE (email_hash)\n)"
    )
    op.execute(
        "CREATE TABLE email_challenges (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\temail_hash BYTEA NOT NULL, \n\tcode_hash BYTEA NOT NULL, \n\tpurpose VARCHAR(16) DEFAULT 'sign_in' NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tattempts SMALLINT DEFAULT '0' NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_email_challenges PRIMARY KEY (id), \n\tCONSTRAINT ck_email_challenges_attempts_max CHECK (attempts <= 5), \n\tCONSTRAINT ck_email_challenges_purpose CHECK (purpose IN ('sign_in','change_email'))\n)"
    )
    op.execute("CREATE INDEX ix_email_challenges_email_created ON email_challenges (email_hash, created_at)")
    op.execute(
        "CREATE TABLE consent_versions (\n\tversion VARCHAR(32) NOT NULL, \n\tpurposes JSONB NOT NULL, \n\tnotice_sha256 BYTEA NOT NULL, \n\trequires_reconsent BOOLEAN DEFAULT false NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_consent_versions PRIMARY KEY (version)\n)"
    )
    op.execute(
        "CREATE TABLE rules (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\trule_key VARCHAR(48) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\tparams JSONB NOT NULL, \n\tsource_ref TEXT, \n\tstatus VARCHAR(32) NOT NULL, \n\tverified_by VARCHAR(200), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_rules PRIMARY KEY (id), \n\tCONSTRAINT uq_rules_key_version UNIQUE (rule_key, version), \n\tCONSTRAINT ck_rules_status CHECK (status IN ('enabled','disabled_pending_verification','retired')), \n\tCONSTRAINT ck_rules_enabled_needs_source CHECK (status <> 'enabled' OR (source_ref IS NOT NULL AND verified_by IS NOT NULL) OR kind IN ('pattern','limit','banned_phrases','model_price','quota','credit_budget'))\n)"
    )
    op.execute("CREATE UNIQUE INDEX uq_rules_one_enabled ON rules (rule_key) WHERE status = 'enabled'")
    op.execute(
        "CREATE TABLE outbox (\n\tid BIGSERIAL NOT NULL, \n\ttask_name VARCHAR(64) NOT NULL, \n\tqueue VARCHAR(16) NOT NULL, \n\tpayload JSONB NOT NULL, \n\tdedupe_key VARCHAR(200) NOT NULL, \n\tstatus VARCHAR(12) DEFAULT 'pending' NOT NULL, \n\tattempts SMALLINT DEFAULT '0' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tdispatched_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_outbox PRIMARY KEY (id), \n\tCONSTRAINT ck_outbox_status CHECK (status IN ('pending','dispatched','done','failed')), \n\tCONSTRAINT uq_outbox_dedupe_key UNIQUE (dedupe_key)\n)"
    )
    op.execute("CREATE INDEX ix_outbox_pending ON outbox (status, created_at) WHERE status = 'pending'")
    op.execute(
        "CREATE TABLE idempotency_keys (\n\tscope_id UUID NOT NULL, \n\tkey VARCHAR(64) NOT NULL, \n\trequest_sha256 BYTEA NOT NULL, \n\tstatus_code INTEGER NOT NULL, \n\tresponse JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_idempotency_keys PRIMARY KEY (scope_id, key)\n)"
    )
    op.execute(
        "CREATE TABLE rate_limit_buckets (\n\tbucket_key VARCHAR(160) NOT NULL, \n\twindow_start TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcount INTEGER DEFAULT '0' NOT NULL, \n\tCONSTRAINT pk_rate_limit_buckets PRIMARY KEY (bucket_key, window_start)\n)"
    )
    op.execute(
        "CREATE TABLE audit_log (\n\tid BIGSERIAL NOT NULL, \n\tactor_type VARCHAR(12) NOT NULL, \n\tactor_id VARCHAR(64), \n\taction VARCHAR(48) NOT NULL, \n\tentity_type VARCHAR(32) NOT NULL, \n\tentity_id VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_audit_log PRIMARY KEY (id)\n)"
    )
    op.execute(
        "CREATE TABLE sessions (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\ttoken_hash BYTEA NOT NULL, \n\tkind VARCHAR(8) DEFAULT 'user' NOT NULL, \n\tuser_id UUID NOT NULL, \n\ttrusted BOOLEAN DEFAULT false NOT NULL, \n\tidle_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tabsolute_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlast_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_sessions PRIMARY KEY (id), \n\tCONSTRAINT ck_sessions_kind CHECK (kind IN ('user','admin')), \n\tCONSTRAINT uq_sessions_token_hash UNIQUE (token_hash), \n\tCONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_sessions_user_id ON sessions (user_id)")
    op.execute(
        "CREATE TABLE consents (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tuser_id UUID NOT NULL, \n\tversion VARCHAR(32) NOT NULL, \n\tpurposes VARCHAR(16)[] NOT NULL, \n\tlanguage VARCHAR(2) NOT NULL, \n\tgranted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\twithdrawn_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_consents PRIMARY KEY (id), \n\tCONSTRAINT fk_consents_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_consents_version_consent_versions FOREIGN KEY(version) REFERENCES consent_versions (version)\n)"
    )
    op.execute("CREATE INDEX ix_consents_user_id ON consents (user_id)")
    op.execute(
        "CREATE TABLE cases (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tuser_id UUID NOT NULL, \n\tnickname_enc BYTEA NOT NULL, \n\tstatus VARCHAR(8) DEFAULT 'open' NOT NULL, \n\tmode VARCHAR(8) DEFAULT 'full' NOT NULL, \n\tstage VARCHAR(24) DEFAULT 'S0_PREPARE' NOT NULL, \n\tpolicy_type VARCHAR(12) DEFAULT 'unknown' NOT NULL, \n\tcomplainant_name_enc BYTEA, \n\tcomplainant_relation VARCHAR(12), \n\teligibility JSONB NOT NULL, \n\tinsurer_name VARCHAR(200), \n\tfields_confirmed_at TIMESTAMP WITH TIME ZONE, \n\tline_items_confirmed_at TIMESTAMP WITH TIME ZONE, \n\tstale_since TIMESTAMP WITH TIME ZONE, \n\twording_mode VARCHAR(10) DEFAULT 'none' NOT NULL, \n\twording_source_id UUID, \n\tlock_version INTEGER DEFAULT '0' NOT NULL, \n\tlast_activity_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_cases PRIMARY KEY (id), \n\tCONSTRAINT ck_cases_status CHECK (status IN ('open','closed')), \n\tCONSTRAINT ck_cases_mode CHECK (mode IN ('full','limited','delay')), \n\tCONSTRAINT ck_cases_stage CHECK (stage IN ('S0_PREPARE','S1_INSURER_GRIEVANCE','S3_OMBUDSMAN','CLOSED')), \n\tCONSTRAINT ck_cases_policy_type CHECK (policy_type IN ('individual','floater','group','unknown')), \n\tCONSTRAINT ck_cases_wording_mode CHECK (wording_mode IN ('library','uploaded','none')), \n\tCONSTRAINT fk_cases_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_cases_user_status ON cases (user_id, status)")
    op.execute(
        "CREATE TABLE documents (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\ttype VARCHAR(24) NOT NULL, \n\tstatus VARCHAR(16) DEFAULT 'queued' NOT NULL, \n\tstatus_reason VARCHAR(64), \n\tpage_count INTEGER DEFAULT '0' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_documents PRIMARY KEY (id), \n\tCONSTRAINT ck_documents_type CHECK (type IN ('decision_letter','settlement_breakup','policy_schedule','policy_wording','discharge_summary','final_bill','reports','insurer_correspondence','other')), \n\tCONSTRAINT ck_documents_status CHECK (status IN ('uploading','queued','scanning','reading','ready','needs_attention','failed','rejected')), \n\tCONSTRAINT fk_documents_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_documents_case_id ON documents (case_id)")
    op.execute(
        "CREATE TABLE extracted_fields (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tname VARCHAR(32) NOT NULL, \n\tvalue TEXT, \n\tvalue_enc BYTEA, \n\textracted_value TEXT, \n\textracted_value_enc BYTEA, \n\tstatus VARCHAR(16) NOT NULL, \n\tconfidence_flag VARCHAR(12) DEFAULT 'ok' NOT NULL, \n\tsource_ref JSONB, \n\tconfirmed_by_user BOOLEAN DEFAULT false NOT NULL, \n\tCONSTRAINT pk_extracted_fields PRIMARY KEY (id), \n\tCONSTRAINT uq_extracted_fields_case_name UNIQUE (case_id, name), \n\tCONSTRAINT ck_extracted_fields_one_value CHECK (value IS NULL OR value_enc IS NULL), \n\tCONSTRAINT ck_extracted_fields_status CHECK (status IN ('found','not_found','user_entered','unknown_by_user')), \n\tCONSTRAINT ck_extracted_fields_flag CHECK (confidence_flag IN ('ok','please_check')), \n\tCONSTRAINT fk_extracted_fields_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_extracted_fields_case_id ON extracted_fields (case_id)")
    op.execute(
        "CREATE TABLE decision_reasons (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tordinal SMALLINT NOT NULL, \n\ttext_verbatim TEXT NOT NULL, \n\tclause_cited_verbatim TEXT, \n\tsource_ref JSONB, \n\tcategory VARCHAR(32), \n\taudit_status VARCHAR(32), \n\tCONSTRAINT pk_decision_reasons PRIMARY KEY (id), \n\tCONSTRAINT fk_decision_reasons_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_decision_reasons_case_id ON decision_reasons (case_id)")
    op.execute(
        "CREATE TABLE line_items (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tordinal SMALLINT NOT NULL, \n\tdescription TEXT NOT NULL, \n\tbilled_paise BIGINT, \n\tdeducted_paise BIGINT NOT NULL, \n\treason_verbatim TEXT, \n\tclause_cited_verbatim TEXT, \n\tcategory VARCHAR(32), \n\taudit_status VARCHAR(32), \n\tuser_entered BOOLEAN DEFAULT false NOT NULL, \n\tunitemised BOOLEAN DEFAULT false NOT NULL, \n\tsource_ref JSONB, \n\tCONSTRAINT pk_line_items PRIMARY KEY (id), \n\tCONSTRAINT ck_line_items_deducted_nonneg CHECK (deducted_paise >= 0), \n\tCONSTRAINT ck_line_items_billed_nonneg CHECK (billed_paise IS NULL OR billed_paise >= 0), \n\tCONSTRAINT ck_line_items_deducted_le_billed CHECK (billed_paise IS NULL OR deducted_paise <= billed_paise), \n\tCONSTRAINT fk_line_items_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_line_items_case_id ON line_items (case_id)")
    op.execute(
        "CREATE TABLE knowledge_sources (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\ttype VARCHAR(16) NOT NULL, \n\tscope VARCHAR(8) DEFAULT 'library' NOT NULL, \n\tcase_id UUID, \n\tissuer VARCHAR(200) NOT NULL, \n\ttitle VARCHAR(300) NOT NULL, \n\tidentifier VARCHAR(120) NOT NULL, \n\tversion VARCHAR(40) NOT NULL, \n\teffective_from DATE NOT NULL, \n\teffective_to DATE, \n\turl VARCHAR(500), \n\tsynthetic BOOLEAN DEFAULT false NOT NULL, \n\tstatus VARCHAR(10) DEFAULT 'draft' NOT NULL, \n\tchecked_by VARCHAR(200), \n\tchecked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_knowledge_sources PRIMARY KEY (id), \n\tCONSTRAINT ck_knowledge_sources_type CHECK (type IN ('regulation','policy_wording')), \n\tCONSTRAINT ck_knowledge_sources_scope CHECK (scope IN ('library','case')), \n\tCONSTRAINT ck_knowledge_sources_scope_case CHECK ((scope = 'case') = (case_id IS NOT NULL)), \n\tCONSTRAINT ck_knowledge_sources_status CHECK (status IN ('draft','published','retired')), \n\tCONSTRAINT ck_knowledge_sources_published_attested CHECK (status <> 'published' OR checked_by IS NOT NULL), \n\tCONSTRAINT fk_knowledge_sources_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_knowledge_sources_case_id ON knowledge_sources (case_id)")
    op.execute(
        "CREATE TABLE analyses (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tstatus VARCHAR(16) DEFAULT 'queued' NOT NULL, \n\tmode VARCHAR(8) NOT NULL, \n\trule_versions JSONB DEFAULT '{}' NOT NULL, \n\tsource_versions JSONB DEFAULT '{}' NOT NULL, \n\tsummary JSONB DEFAULT '{}' NOT NULL, \n\ttotals JSONB DEFAULT '{}' NOT NULL, \n\terror_code VARCHAR(48), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_analyses PRIMARY KEY (id), \n\tCONSTRAINT ck_analyses_status CHECK (status IN ('queued','running','succeeded','failed','superseded','paused_budget')), \n\tCONSTRAINT fk_analyses_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_analyses_case_id ON analyses (case_id)")
    op.execute(
        "CREATE TABLE review_items (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tsource VARCHAR(16) NOT NULL, \n\tcase_id UUID, \n\ttarget_type VARCHAR(24) NOT NULL, \n\tpayload JSONB NOT NULL, \n\treason VARCHAR(48) NOT NULL, \n\tstatus VARCHAR(12) DEFAULT 'open' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_review_items PRIMARY KEY (id), \n\tCONSTRAINT fk_review_items_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_review_items_case_id ON review_items (case_id)")
    op.execute(
        "CREATE TABLE job_steps (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tjob_kind VARCHAR(24) NOT NULL, \n\tjob_ref UUID NOT NULL, \n\tstep_key VARCHAR(32) NOT NULL, \n\tordinal SMALLINT NOT NULL, \n\tstatus VARCHAR(12) DEFAULT 'waiting' NOT NULL, \n\tattempt SMALLINT DEFAULT '0' NOT NULL, \n\terror_code VARCHAR(48), \n\tstarted_at TIMESTAMP WITH TIME ZONE, \n\tfinished_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_job_steps PRIMARY KEY (id), \n\tCONSTRAINT uq_job_steps_ref_step UNIQUE (job_ref, step_key), \n\tCONSTRAINT ck_job_steps_status CHECK (status IN ('waiting','in_progress','done','retrying','failed')), \n\tCONSTRAINT fk_job_steps_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_job_steps_case_id ON job_steps (case_id)")
    op.execute(
        "CREATE TABLE ai_calls (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID, \n\tstep_key VARCHAR(32) NOT NULL, \n\tprovider VARCHAR(16) NOT NULL, \n\tmodel VARCHAR(64) NOT NULL, \n\tprompt_version VARCHAR(32) NOT NULL, \n\tinput_tokens INTEGER DEFAULT '0' NOT NULL, \n\toutput_tokens INTEGER DEFAULT '0' NOT NULL, \n\tthinking_tokens INTEGER, \n\tlatency_ms INTEGER NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\terror_code VARCHAR(48), \n\tcost_micro_usd BIGINT DEFAULT '0' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_ai_calls PRIMARY KEY (id), \n\tCONSTRAINT fk_ai_calls_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE SET NULL\n)"
    )
    op.execute("CREATE INDEX ix_ai_calls_case_id ON ai_calls (case_id)")
    op.execute(
        "CREATE TABLE document_objects (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tdocument_id UUID NOT NULL, \n\tcase_id UUID NOT NULL, \n\tseq SMALLINT DEFAULT '0' NOT NULL, \n\tstorage_key VARCHAR(300) NOT NULL, \n\tmime VARCHAR(32) NOT NULL, \n\tsize_bytes INTEGER NOT NULL, \n\tsha256 BYTEA NOT NULL, \n\tCONSTRAINT pk_document_objects PRIMARY KEY (id), \n\tCONSTRAINT uq_document_objects_case_sha UNIQUE (case_id, sha256), \n\tCONSTRAINT ck_document_objects_size CHECK (size_bytes <= 20971520), \n\tCONSTRAINT ck_document_objects_mime CHECK (mime IN ('application/pdf','image/jpeg','image/png')), \n\tCONSTRAINT fk_document_objects_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_document_objects_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_document_objects_document_id ON document_objects (document_id)")
    op.execute("CREATE INDEX ix_document_objects_case_id ON document_objects (case_id)")
    op.execute(
        "CREATE TABLE document_pages (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tdocument_id UUID NOT NULL, \n\tcase_id UUID NOT NULL, \n\tpage_no INTEGER NOT NULL, \n\tocr_key VARCHAR(300) NOT NULL, \n\tocr_quality DOUBLE PRECISION NOT NULL, \n\tCONSTRAINT pk_document_pages PRIMARY KEY (id), \n\tCONSTRAINT uq_document_pages_doc_page UNIQUE (document_id, page_no), \n\tCONSTRAINT fk_document_pages_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_document_pages_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_document_pages_document_id ON document_pages (document_id)")
    op.execute("CREATE INDEX ix_document_pages_case_id ON document_pages (case_id)")
    op.execute(
        "CREATE TABLE knowledge_chunks (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tsource_id UUID NOT NULL, \n\tcase_id UUID, \n\tordinal INTEGER NOT NULL, \n\tclause_ref VARCHAR(80), \n\tclause_key VARCHAR(80), \n\theading_path TEXT[] DEFAULT '{}' NOT NULL, \n\ttext TEXT NOT NULL, \n\ttsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(clause_ref, '') || ' ' || text)) STORED NOT NULL, \n\tflags VARCHAR(32)[] DEFAULT '{}' NOT NULL, \n\tCONSTRAINT pk_knowledge_chunks PRIMARY KEY (id), \n\tCONSTRAINT fk_knowledge_chunks_source_id_knowledge_sources FOREIGN KEY(source_id) REFERENCES knowledge_sources (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_knowledge_chunks_case_id ON knowledge_chunks (case_id)")
    op.execute("CREATE INDEX ix_knowledge_chunks_source_id ON knowledge_chunks (source_id)")
    op.execute("CREATE INDEX ix_knowledge_chunks_clause_key ON knowledge_chunks (clause_key)")
    op.execute("CREATE INDEX ix_knowledge_chunks_tsv ON knowledge_chunks USING gin (tsv)")
    op.execute(
        "CREATE TABLE counter_points (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tanalysis_id UUID NOT NULL, \n\tcase_id UUID NOT NULL, \n\ttarget_type VARCHAR(12) NOT NULL, \n\ttarget_id UUID NOT NULL, \n\tordinal SMALLINT NOT NULL, \n\tstatement_en TEXT NOT NULL, \n\tbasis_type VARCHAR(20) NOT NULL, \n\trule_key VARCHAR(48), \n\tshown BOOLEAN NOT NULL, \n\tdrop_reason VARCHAR(64), \n\tCONSTRAINT pk_counter_points PRIMARY KEY (id), \n\tCONSTRAINT ck_counter_points_dropped_has_reason CHECK (shown OR drop_reason IS NOT NULL), \n\tCONSTRAINT ck_counter_points_basis CHECK (basis_type IN ('regulation','policy_wording','case_fact','deterministic_rule')), \n\tCONSTRAINT fk_counter_points_analysis_id_analyses FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_counter_points_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_counter_points_analysis_id ON counter_points (analysis_id)")
    op.execute("CREATE INDEX ix_counter_points_case_id ON counter_points (case_id)")
    op.execute(
        "CREATE TABLE letters (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcase_id UUID NOT NULL, \n\tanalysis_id UUID, \n\tstage VARCHAR(4) NOT NULL, \n\tlanguage VARCHAR(2) NOT NULL, \n\tstatus VARCHAR(12) DEFAULT 'ready' NOT NULL, \n\tbasic_mode BOOLEAN NOT NULL, \n\tincluded JSONB DEFAULT '{}' NOT NULL, \n\tdoc JSONB NOT NULL, \n\tversion INTEGER DEFAULT '1' NOT NULL, \n\treviewed_version INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_letters PRIMARY KEY (id), \n\tCONSTRAINT ck_letters_stage CHECK (stage IN ('S1','S3')), \n\tCONSTRAINT ck_letters_lang CHECK (language IN ('en','gu','hi')), \n\tCONSTRAINT fk_letters_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_letters_analysis_id_analyses FOREIGN KEY(analysis_id) REFERENCES analyses (id) ON DELETE SET NULL\n)"
    )
    op.execute("CREATE INDEX ix_letters_case_id ON letters (case_id)")
    op.execute(
        "CREATE TABLE citations (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tcounter_point_id UUID NOT NULL, \n\tcase_id UUID NOT NULL, \n\tchunk_id UUID NOT NULL, \n\tquote TEXT NOT NULL, \n\tverified BOOLEAN NOT NULL, \n\tverifier_version VARCHAR(16) NOT NULL, \n\tCONSTRAINT pk_citations PRIMARY KEY (id), \n\tCONSTRAINT fk_citations_counter_point_id_counter_points FOREIGN KEY(counter_point_id) REFERENCES counter_points (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_citations_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_citations_chunk_id_knowledge_chunks FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks (id)\n)"
    )
    op.execute("CREATE INDEX ix_citations_case_id ON citations (case_id)")
    op.execute("CREATE INDEX ix_citations_counter_point_id ON citations (counter_point_id)")
    op.execute("CREATE INDEX ix_citations_chunk_id ON citations (chunk_id)")
    op.execute(
        "CREATE TABLE letter_exports (\n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tletter_id UUID NOT NULL, \n\tcase_id UUID NOT NULL, \n\tletter_version INTEGER NOT NULL, \n\tformat VARCHAR(4) NOT NULL, \n\tstorage_key VARCHAR(300) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_letter_exports PRIMARY KEY (id), \n\tCONSTRAINT uq_letter_exports_ver_fmt UNIQUE (letter_id, letter_version, format), \n\tCONSTRAINT fk_letter_exports_letter_id_letters FOREIGN KEY(letter_id) REFERENCES letters (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_letter_exports_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE\n)"
    )
    op.execute("CREATE INDEX ix_letter_exports_case_id ON letter_exports (case_id)")
    op.execute("CREATE INDEX ix_letter_exports_letter_id ON letter_exports (letter_id)")
    op.execute(
        "ALTER TABLE cases ADD CONSTRAINT fk_cases_wording_source FOREIGN KEY(wording_source_id) REFERENCES knowledge_sources (id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS letter_exports CASCADE")
    op.execute("DROP TABLE IF EXISTS citations CASCADE")
    op.execute("DROP TABLE IF EXISTS letters CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS document_pages CASCADE")
    op.execute("DROP TABLE IF EXISTS document_objects CASCADE")
    op.execute("DROP TABLE IF EXISTS counter_points CASCADE")
    op.execute("DROP TABLE IF EXISTS review_items CASCADE")
    op.execute("DROP TABLE IF EXISTS line_items CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_sources CASCADE")
    op.execute("DROP TABLE IF EXISTS job_steps CASCADE")
    op.execute("DROP TABLE IF EXISTS extracted_fields CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS decision_reasons CASCADE")
    op.execute("DROP TABLE IF EXISTS analyses CASCADE")
    op.execute("DROP TABLE IF EXISTS ai_calls CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS consents CASCADE")
    op.execute("DROP TABLE IF EXISTS cases CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS rules CASCADE")
    op.execute("DROP TABLE IF EXISTS rate_limit_buckets CASCADE")
    op.execute("DROP TABLE IF EXISTS outbox CASCADE")
    op.execute("DROP TABLE IF EXISTS idempotency_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS email_challenges CASCADE")
    op.execute("DROP TABLE IF EXISTS consent_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
