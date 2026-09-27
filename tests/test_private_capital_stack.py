"""Certification tests for the private-capital operating stack."""

from legal_intelligence.capital_ledger import CapitalLedgerEngine
from legal_intelligence.credit_committee import CreditCommitteeEngine
from legal_intelligence.receivables import ReceivablesEngine
from legal_intelligence.related_party import RelatedPartyEngine
from legal_intelligence.private_capital_docs import PrivateCapitalDocsEngine
from legal_intelligence.capital_risk import CapitalRiskEngine


def test_capital_ledger_funding_is_balanced():
    entry = CapitalLedgerEngine().funding_entry(
        entry_id="E1",
        facility_id="F1",
        amount=1000,
        source_ref="bank-proof-1",
        approved_by="principal",
    )
    assert entry.balanced
    assert CapitalLedgerEngine().validate_entry(entry) == []


def test_capital_ledger_flags_reserve_and_delinquency():
    snap = CapitalLedgerEngine().snapshot({
        "facility_id": "F1",
        "principal_outstanding": 5000,
        "collateral_value": 4000,
        "reserve_required": 2000,
        "reserve_available": 1000,
        "days_past_due": 35,
    })
    assert snap.status == "EXCEPTION"
    assert "RESERVE_SHORTFALL" in snap.exception_codes
    assert "DELINQUENCY_30_PLUS" in snap.exception_codes
    assert "UNDERCOLLATERALIZED" in snap.exception_codes


def test_credit_committee_blocks_weak_related_party_request():
    report = CreditCommitteeEngine().evaluate({
        "debt_service_coverage_ratio": 0.8,
        "liquidity_months": 0.5,
        "secured": True,
        "collateral_coverage_ratio": 0.7,
        "borrower_concentration_pct": 50,
        "requested_amount": 20000,
        "policy_limit": 10000,
        "approver_limit": 5000,
        "related_party": True,
        "independent_benefit_documented": False,
        "interest_bearing": True,
        "current_law_verified": False,
    })
    assert report.decision == "DECLINE_OR_PRINCIPAL_EXCEPTION"
    assert report.score < 50
    assert report.beneficial_suggestions


def test_receivables_engine_applies_ineligibility_concentration_and_overadvance():
    report = ReceivablesEngine().calculate({
        "advance_rate": 0.8,
        "customer_concentration_limit_pct": 50,
        "current_advance": 900,
        "trailing_credit_sales": 10000,
        "trailing_dilution": 800,
        "receivables": [
            {"receivable_id": "R1", "customer": "A", "amount": 1000, "days_outstanding": 30},
            {"receivable_id": "R2", "customer": "B", "amount": 500, "days_outstanding": 120},
        ],
    })
    assert any(x["receivable_id"] == "R2" for x in report.ineligible)
    assert report.borrowing_base <= 800
    assert report.overadvance > 0
    assert report.dilution_pct == 8.0


def test_related_party_firewall_blocks_missing_fairness_and_authority():
    report = RelatedPartyEngine().evaluate({
        "lender": "Trust",
        "borrower": "IKE Solutions",
        "relationship": "affiliate",
        "trustee_involved": True,
        "common_control": True,
        "independent_benefit_documented": False,
        "fair_terms_documented": False,
        "governing_documents_checked": False,
    })
    assert report.decision == "BLOCK"
    assert "INDEPENDENT_BENEFIT_NOT_DOCUMENTED" in report.conflicts
    assert "FAIR_TERMS_NOT_DOCUMENTED" in report.conflicts
    assert "GOVERNING_DOCUMENT_AUTHORITY_NOT_VERIFIED" in report.conflicts


def test_private_capital_docs_require_controlled_fields():
    engine = PrivateCapitalDocsEngine()
    report = engine.validate_payload("promissory_note", {
        "lender": "Trust",
        "borrower": "IKE Solutions",
        "capacity": "affiliate borrower",
        "principal": 10000,
    })
    assert not report["valid"]
    assert "funding_date" in report["missing_fields"]
    assert report["beneficial_suggestions"]


def test_capital_risk_blocks_concentration_and_reserve_breach():
    report = CapitalRiskEngine().evaluate({
        "max_single_borrower_pct": 40,
        "max_affiliate_group_pct": 60,
        "max_collateral_class_pct": 80,
        "reserve_available": 1000,
        "reserve_required": 2000,
        "exposures": [
            {"borrower": "IKE", "affiliate_group": "Howard Group", "collateral_class": "receivables", "amount": 8000},
            {"borrower": "Affiliate B", "affiliate_group": "Howard Group", "collateral_class": "receivables", "amount": 2000},
        ],
    })
    assert report.decision == "BLOCK_NEW_ADVANCES"
    assert any(x.startswith("SINGLE_BORROWER_LIMIT") for x in report.limit_breaches)
    assert any(x.startswith("AFFILIATE_GROUP_LIMIT") for x in report.limit_breaches)
    assert "RESERVE_FLOOR_BREACH" in report.limit_breaches
