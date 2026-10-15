"""Deterministic safety components: citation verifier (AI-004), number scanner (AI-005), values, audit (FR-015)."""

from __future__ import annotations

from datetime import date

import pytest

from claimsathi.core.values import format_inr, parse_amount_paise, parse_date
from claimsathi.rules.audit import audit_item, clause_key, identifiers
from claimsathi.verify.citations import verify_quote
from claimsathi.verify.numbers import drop_ungrounded_sentences, tokens, ungrounded

CHUNK = (
    "Para 17(b) Where a claim is rejected, or any part of a claim is disallowed, the insurer shall inform the "
    "claimant in writing and shall give reference to the specific terms and conditions of the policy document "
    "relied upon for each amount disallowed."
)
QUOTE = "shall give reference to the specific terms and conditions of the policy document"


@pytest.mark.req("AI-004")
class TestCitationVerifier:
    def test_exact_quote_passes(self) -> None:
        assert verify_quote(chunk_id="c1", quote=QUOTE, provided_chunks={"c1": CHUNK}).ok

    def test_whitespace_curly_quotes_and_latin_case_normalised(self) -> None:
        q = "  SHALL give   reference to the ‘specific’ terms and conditions of the policy document"
        chunk = CHUNK.replace("specific", "'specific'")
        assert verify_quote(chunk_id="c1", quote=q, provided_chunks={"c1": chunk}).ok

    def test_chunk_not_provided_fails(self) -> None:
        r = verify_quote(chunk_id="other", quote=QUOTE, provided_chunks={"c1": CHUNK})
        assert (r.ok, r.reason) == (False, "chunk_not_provided")

    def test_paraphrase_fails(self) -> None:
        r = verify_quote(
            chunk_id="c1",
            quote="insurers must always explain every policy clause they rely on",
            provided_chunks={"c1": CHUNK},
        )
        assert (r.ok, r.reason) == (False, "quote_not_in_chunk")

    def test_too_short_fails(self) -> None:
        r = verify_quote(chunk_id="c1", quote="the insurer shall", provided_chunks={"c1": CHUNK})
        assert (r.ok, r.reason) == (False, "quote_too_short")

    def test_indic_text_is_not_case_folded_but_matches_exactly(self) -> None:
        chunk = "વીમા કંપનીએ દરેક કપાત માટે પૉલિસીની ચોક્કસ શરત જણાવવી જોઈએ અને તે લખિતમાં આપવી જોઈએ"
        q = "દરેક કપાત માટે પૉલિસીની ચોક્કસ શરત જણાવવી જોઈએ અને તે લખિતમાં"
        assert verify_quote(chunk_id="g", quote=q, provided_chunks={"g": chunk}).ok


@pytest.mark.req("AI-005")
class TestNumberScanner:
    def test_tokens_normalise_amounts_dates_and_clauses(self) -> None:
        t = tokens("Paid ₹2,10,500 on 10/09/2026 under Clause 4.7")
        assert {"210500", "2026-09-10", "clause:4.7"} <= t

    def test_gujarati_and_devanagari_digits(self) -> None:
        assert "18400" in tokens("કપાત ₹૧૮,૪૦૦") and "18400" in tokens("कटौती ₹१८,४००")

    def test_ungrounded_amount_detected(self) -> None:
        assert ungrounded("Please pay ₹99,999.", allowed={"210500"}) == {"99999"}

    def test_sentence_with_invented_number_removed(self) -> None:
        text, removed = drop_ungrounded_sentences(
            "You were paid ₹2,10,500. The law caps this at 40%.", allowed=tokens("₹2,10,500")
        )
        assert removed == 1 and "40" not in text and "2,10,500" in text


class TestValues:
    @pytest.mark.parametrize(
        ("raw", "paise"),
        [("Rs. 2,64,820", 26482000), ("₹18,400", 1840000), ("INR 1250.50", 125050), ("1,250/-", 125000), ("abc", None)],
    )
    def test_parse_amount(self, raw: str, paise: int | None) -> None:
        assert parse_amount_paise(raw) == paise

    def test_parse_date_dmy_and_invalid(self) -> None:
        assert parse_date("10/09/2026") == date(2026, 9, 10)
        assert parse_date("31/02/2026") is None

    @pytest.mark.parametrize(
        ("paise", "text"), [(26482000, "₹2,64,820"), (125000, "₹1,250"), (99, "₹0.99"), (1234567800, "₹1,23,45,678")]
    )
    def test_format_inr_indian_grouping(self, paise: int, text: str) -> None:
        assert format_inr(paise) == text


@pytest.mark.req("FR-015")
class TestAudit:
    @pytest.mark.parametrize("clause", [None, "", "none", "N/A", "as per policy terms", "non-payable"])
    def test_no_clause_cited(self, clause: str | None) -> None:
        assert audit_item(clause_cited=clause, wording_clause_keys={"4.7"}).status == "NO_CLAUSE_CITED"

    def test_clause_found_is_cannot_assess_until_counterpoints_exist(self) -> None:
        r = audit_item(clause_cited="Clause 4.7", wording_clause_keys={"4.7", "2.4(b)"})
        assert (r.status, r.clause_key) == ("CANNOT_ASSESS", "4.7")

    def test_clause_not_found(self) -> None:
        assert audit_item(clause_cited="Clause 9.9", wording_clause_keys={"4.7"}).status == "CLAUSE_NOT_FOUND"

    def test_limited_mode_never_claims_not_found(self) -> None:
        assert audit_item(clause_cited="Clause 9.9", wording_clause_keys=None).status == "CANNOT_ASSESS"

    def test_clause_keys(self) -> None:
        assert [clause_key(i) for i in identifiers("see Para 17(b) and Clause 2.4(b)")][:2] == ["17(b)", "2.4(b)"]
