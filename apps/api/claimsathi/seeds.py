"""Idempotent seeds. Run: python -m claimsathi.seeds --env local

- consent v1-draft: the notice text is PENDING LEGAL REVIEW (readiness CI-07).
- rules: RULE-PATTERNS, plus RULE-MC-01 pointing at the evidence source for this environment.
  local/test use the SYNTHETIC fixture SAMPLE-REG-001. prod points at the real IRDAI Master Circular and
  stays `disabled_pending_verification` until an admin ingests the official PDF and verifies the quote.
- knowledge: local/test ingest only SYNTHETIC fixtures from eval/fixtures/knowledge.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path

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
            version="1",
            effective_from=date(2024, 1, 1),
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
    s.commit()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env", choices=["local", "test", "prod"], default="local")
    args = p.parse_args()
    sf = make_session_factory(get_settings().database_url)
    with sf() as s:
        seed(s, args.env)
    print(f"seeded ({args.env})")


if __name__ == "__main__":
    main()
