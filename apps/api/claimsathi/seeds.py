"""Idempotent seeds. Run: python -m claimsathi.seeds --env local

- consent v1-draft: the notice text is PENDING LEGAL REVIEW (readiness CI-07).
- rules: RULE-PATTERNS, plus RULE-MC-01 pointing at the evidence source for this environment.
  local/test use the SYNTHETIC fixture SAMPLE-REG-001. prod points at the real IRDAI Master Circular and
  stays `disabled_pending_verification` until an admin ingests the official PDF and verifies the quote.
- knowledge: local/test ingest only SYNTHETIC fixtures from eval/fixtures/knowledge.
- escalation (FR-020/021): RULE-ESC-01..06 cite the Insurance Ombudsman Rules, 2017. They are enabled in
  local/test, marked pending legal review (OQ-10), and stay `disabled_pending_verification` in prod until a
  reviewer verifies them. RULE-DEADLINES holds the deadline parameters and the month/year interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimsathi.core.config import get_settings
from claimsathi.core.db import make_session_factory
from claimsathi.knowledge.ingest import ingest_text
from claimsathi.models import ConsentVersion, Rule
from claimsathi.rules.audit import DEFAULT_IDENTIFIER_PATTERNS

FIXTURES = Path(__file__).resolve().parents[3] / "eval" / "fixtures" / "knowledge"
CONSENT_VERSION = "v1-draft"
STATEMENT_17B = (
    "Your insurer did not cite a specific policy clause for this deduction. The rule below requires "
    "insurers to give the specific policy term relied on, so you can ask for it."
)


ESC_RULES = {
    "RULE-ESC-01": ("Insurance Ombudsman Rules, 2017, Rule 14(3)(a)", {"check": "representation_logged"}),
    "RULE-ESC-02": ("Insurance Ombudsman Rules, 2017, Rule 14(3)(a)", {"check": "reply_or_one_month", "months": 1}),
    "RULE-ESC-03": (
        "Insurance Ombudsman Rules, 2017, Rule 14(3)(b) and 14(4)",
        {"check": "within_one_year", "years": 1},
    ),
    "RULE-ESC-04": ("Insurance Ombudsman Rules, 2017, Rule 14(5)", {"check": "not_in_court"}),
    "RULE-ESC-05": (
        "Insurance Ombudsman Rules, 2017, Rule 17(3)",
        {"check": "amount_cap", "cap_paise": 50_00_000 * 100},
    ),
    "RULE-ESC-06": ("Insurance Ombudsman Rules, 2017, Rule 14(1) and 14(2)", {"check": "complainant_signs"}),
}
DEADLINE_PARAMS = {
    "insurer_response_days": 14,  # VERIFY-PRIMARY (OQ-05)
    "eligibility_months": 1,
    "limitation_years": 1,
    "award_months": 3,
    "month_rule": "same day number next month; last day of that month if the day does not exist (OQ-10)",
}


STATEMENT_MC02 = (
    "Your claim was fully rejected. The rule below says a full rejection needs the approval of the insurer's "
    "claims review committee, so you can ask the insurer to confirm that approval."
)
STATEMENT_MC03 = (
    "Your policy had more than 60 months of continuous cover before this admission. The rule below says that "
    "after 60 months a claim can't be contested for non-disclosure, except for established fraud."
)
STATEMENT_MC05 = (
    "If the missing papers are hospital documents, the rule below says the insurer should collect them directly "
    "from the hospital, so ask the insurer to do that instead of rejecting your claim."
)
# FR-018 evidence map: DRAFT, authored for the MVP and pending domain review (decision D-H). Never model-made.
EVIDENCE_MAP = {
    "base": ["decision_letter", "policy_schedule", "policy_wording", "discharge_summary", "final_bill"],
    "by_category": {
        "ped_waiting": ["doctor_certificate_first_diagnosis", "previous_policy_schedules"],
        "non_disclosure": ["doctor_certificate_first_diagnosis", "previous_policy_schedules"],
        "specific_waiting": ["previous_policy_schedules", "doctor_certificate_first_diagnosis"],
        "initial_waiting": ["previous_policy_schedules"],
        "room_rent_proportionate": ["hospital_tariff_sheet", "room_category_record"],
        "reasonable_customary": ["hospital_tariff_sheet"],
        "non_payable_items": ["itemised_hospital_bill"],
        "not_medically_necessary": ["treating_doctor_note_necessity"],
        "documents_or_intimation": ["proof_documents_submitted", "intimation_proof"],
        "policy_not_in_force": ["premium_payment_receipts"],
    },
}


def _regulatory_rules(env: str) -> dict[str, dict[str, Any]]:
    """RULE-MC-02/03/05 (PRD FR-016 deterministic checks). Local/test cite the SYNTHETIC regulation; prod stays
    disabled until the official Master Circular is ingested and each quote is verified."""
    if env in ("local", "test"):
        src = "SAMPLE-REG-001"
        quotes = {
            "RULE-MC-02": (
                "17(a)",
                "No claim shall be fully rejected by an insurer under this synthetic regulation "
                "without the approval of its claims review panel",
            ),
            "RULE-MC-03": (
                "13",
                "no claim shall be contested by the insurer on the ground of non-disclosure or "
                "misrepresentation, except on the ground of established fraud",
            ),
            "RULE-MC-05": (
                "17(c)",
                "The insurer shall collect the hospital documents it needs directly from the hospital",
            ),
        }
    else:
        src = "IRDAI/HLT/CIR/PRO/84/5/2024"
        quotes = {"RULE-MC-02": ("17(a)", ""), "RULE-MC-03": ("13", ""), "RULE-MC-05": ("17(c)", "")}
    statements = {"RULE-MC-02": STATEMENT_MC02, "RULE-MC-03": STATEMENT_MC03, "RULE-MC-05": STATEMENT_MC05}
    extra: dict[str, dict[str, Any]] = {
        "RULE-MC-03": {"min_months": 60, "categories": ["non_disclosure", "ped_waiting"]},
        "RULE-MC-05": {"categories": ["documents_or_intimation"]},
    }
    return {
        key: {
            "evidence": {"source_identifier": src, "clause_key": clause, "quote": quote},
            "statement_en": statements[key],
            **extra.get(key, {}),
        }
        for key, (clause, quote) in quotes.items()
    }


def _seed_regulatory_rules(s: Session, env: str) -> None:
    local = env in ("local", "test")
    for key, params in _regulatory_rules(env).items():
        ev = params["evidence"]
        source_ref = f"{ev['source_identifier']} Para {ev['clause_key']}" if local else None
        if s.scalar(select(Rule).where(Rule.rule_key == key)) is None:
            s.add(
                Rule(
                    rule_key=key,
                    version=1,
                    kind="regulatory",
                    status="enabled" if local else "disabled_pending_verification",
                    source_ref=source_ref,
                    verified_by="seed:local (SYNTHETIC fixture)" if local else None,
                    params=params,
                )
            )
    if s.scalar(select(Rule).where(Rule.rule_key == "RULE-EVIDENCE")) is None:
        s.add(
            Rule(
                rule_key="RULE-EVIDENCE",
                version=1,
                kind="evidence_map",
                status="enabled",
                source_ref="ClaimSathi evidence map v1 (DRAFT, pending domain review D-H)",
                verified_by="seed (pending domain review)",
                params=EVIDENCE_MAP,
            )
        )


def _seed_escalation_rules(s: Session, env: str) -> None:
    local = env in ("local", "test")
    for key, (source, params) in ESC_RULES.items():
        if s.scalar(select(Rule).where(Rule.rule_key == key)) is None:
            s.add(
                Rule(
                    rule_key=key,
                    version=1,
                    kind="procedural",
                    status="enabled" if local else "disabled_pending_verification",
                    source_ref=source,
                    verified_by="seed:local (pending legal review OQ-10)" if local else None,
                    params=params,
                )
            )
    if s.scalar(select(Rule).where(Rule.rule_key == "RULE-DEADLINES")) is None:
        s.add(
            Rule(
                rule_key="RULE-DEADLINES",
                version=1,
                kind="limit",
                status="enabled",
                source_ref="Insurance Ombudsman Rules, 2017, Rules 14(3) and 17(4); response days VERIFY-PRIMARY",
                params=DEADLINE_PARAMS,
            )
        )


def seed(s: Session, env: str) -> None:
    if s.get(ConsentVersion, CONSENT_VERSION) is None:
        s.add(
            ConsentVersion(
                version=CONSENT_VERSION,
                purposes=["processing", "reminders"],
                notice_sha256=hashlib.sha256(b"consent-notice-v1-draft").digest(),
            )
        )
    if s.scalar(select(Rule).where(Rule.rule_key == "RULE-PATTERNS")) is None:
        s.add(
            Rule(
                rule_key="RULE-PATTERNS",
                version=1,
                kind="pattern",
                status="enabled",
                params={"identifier_patterns": list(DEFAULT_IDENTIFIER_PATTERNS)},
            )
        )
    if env in ("local", "test"):
        ingest_text(
            s,
            type="regulation",
            issuer="SYNTHETIC test regulator",
            identifier="SAMPLE-REG-001",
            title="Sample Regulation 001 (SYNTHETIC, not a real regulation)",
            version="2",
            effective_from=date(2025, 1, 1),
            synthetic=True,
            attested_by="seed:synthetic-fixture",
            text=(FIXTURES / "SAMPLE-REG-001.txt").read_text(encoding="utf-8"),
        )
        ingest_text(
            s,
            type="policy_wording",
            issuer="Sample Health Insurance Co. Ltd.",
            identifier="SAMPLE-WORDING-001",
            title="Sample policy wording (SYNTHETIC)",
            version="1",
            effective_from=date(2023, 4, 1),
            synthetic=True,
            attested_by="seed:synthetic-fixture",
            text=(FIXTURES / "SAMPLE-WORDING-001-v1.txt").read_text(encoding="utf-8"),
        )
        evidence = {
            "source_identifier": "SAMPLE-REG-001",
            "clause_key": "17(b)",
            "quote": (
                "shall give reference to the specific terms and conditions of the policy document "
                "relied upon for each amount disallowed"
            ),
        }
        status, source_ref, verified_by = "enabled", "SAMPLE-REG-001 Para 17(b) (SYNTHETIC fixture)", "seed:local"
    else:
        evidence = {
            "source_identifier": "IRDAI/HLT/CIR/PRO/84/5/2024",
            "clause_key": "17(b)",
            "quote": "giving reference to the specific terms and conditions of the policy document",
        }
        status, source_ref, verified_by = "disabled_pending_verification", None, None
    if s.scalar(select(Rule).where(Rule.rule_key == "RULE-MC-01")) is None:
        s.add(
            Rule(
                rule_key="RULE-MC-01",
                version=1,
                kind="regulatory",
                status=status,
                source_ref=source_ref,
                verified_by=verified_by,
                params={"evidence": evidence, "statement_en": STATEMENT_17B},
            )
        )
    _seed_escalation_rules(s, env)
    _seed_regulatory_rules(s, env)
    s.commit()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env", choices=["local", "test", "prod"], default="local")
    args = p.parse_args()
    settings = get_settings()
    sf = make_session_factory(settings.database_url)
    with sf() as s:
        seed(s, args.env)
        if settings.admin_bootstrap_email:  # FR-037: the first admin on the allowlist
            from claimsathi.admin.service import seed_bootstrap_admin
            from claimsathi.main_api import build_context

            seed_bootstrap_admin(build_context(settings), s)
    print(f"seeded ({args.env})")


if __name__ == "__main__":
    main()
