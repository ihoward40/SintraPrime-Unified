"""Certification tests for SP-PRIVATE-CAPITAL-001."""

from legal_intelligence.private_capital import CapitalDecision, PrivateCapitalEngine


def test_internal_affiliate_loan_requires_documentation_but_can_pass_conditionally():
    report = PrivateCapitalEngine().evaluate(
        {
            "transaction_class": "affiliate_to_affiliate_loan",
            "parties": [
                {"name": "IKE Solutions LLC", "capacity": "lender"},
                {"name": "affiliate", "capacity": "borrower"},
            ],
            "amount": 10000,
            "related_parties": True,
            "interest_rate": 5.0,
            "current_law_verified": True,
        }
    )
    assert report.decision == CapitalDecision.PASS_WITH_CONDITIONS
    assert "written promissory note or facility agreement" in report.required_documents
    assert "related-party approval/conflict record" in report.required_documents
    assert report.beneficial_suggestions


def test_public_consumer_lending_is_blocked_without_license_or_partner():
    report = PrivateCapitalEngine().evaluate(
        {
            "transaction_class": "consumer_lending",
            "parties": [{"name": "IKE", "capacity": "proposed_lender"}],
            "amount": 5000,
            "public_facing": True,
            "consumer_borrower": True,
            "interest_rate": 12.0,
            "current_law_verified": True,
            "licensed_or_regulated_partner": False,
        }
    )
    assert report.decision == CapitalDecision.BLOCK
    assert any(x.code == "PC010_LICENSE_FIREWALL" for x in report.findings)


def test_interest_bearing_transaction_blocks_until_current_rate_law_verified():
    report = PrivateCapitalEngine().evaluate(
        {
            "transaction_class": "owner_loan",
            "parties": [
                {"name": "owner", "capacity": "lender"},
                {"name": "IKE", "capacity": "borrower"},
            ],
            "amount": 2500,
            "interest_rate": 8.0,
            "current_law_verified": False,
        }
    )
    assert report.decision == CapitalDecision.BLOCK
    assert any(x.code == "PC011_RATE_VERIFICATION" for x in report.findings)


def test_secured_internal_advance_requires_attachment_and_priority_workpapers():
    report = PrivateCapitalEngine().evaluate(
        {
            "transaction_class": "secured_internal_advance",
            "parties": [
                {"name": "trust", "capacity": "lender"},
                {"name": "affiliate", "capacity": "borrower"},
            ],
            "amount": 15000,
            "collateral": ["accounts_receivable"],
        }
    )
    assert "security agreement with specific collateral description" in report.required_documents
    assert "perfection/priority analysis" in report.required_documents
    assert any("Article 9" in x for x in report.legal_reviews)


def test_reserve_requirement_is_policy_not_bank_reserve_claim():
    result = PrivateCapitalEngine.reserve_requirement(
        {
            "monthly_fixed_obligations": 4000,
            "target_reserve_months": 3,
            "committed_undrawn_advances": 2000,
            "tax_reserve_required": 1000,
        }
    )
    assert result["policy_reserve_floor"] == 15000.0
    assert "not a statutory capital or bank reserve requirement" in result["caveat"]
