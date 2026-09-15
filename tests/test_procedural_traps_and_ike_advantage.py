"""Certification tests for SP-PROCEDURAL-TRAPS-001 and SP-IKE-ADVANTAGE-001."""

from legal_intelligence.ike_advantage import IKEAdvantageEngine
from legal_intelligence.procedural_traps import ProceduralTrapScanner


def _trap_ids(ctx):
    return {item.trap_id for item in ProceduralTrapScanner().scan(ctx)}


def test_uacc_context_surfaces_accounting_notice_deficiency_and_assignee_traps():
    ctx = {
        "transaction_type": "secured_auto_finance",
        "matter_status": "prelitigation",
        "jurisdiction": ["New Jersey"],
        "parties": [
            {"name": "consumer", "capacity": "debtor"},
            {"name": "UACC", "capacity": "assignee_servicer"},
        ],
        "evidence": ["security_agreement", "disposition_occurred", "assigned_contract"],
        "facts": ["repossession_sale", "assignment"],
    }
    ids = _trap_ids(ctx)
    assert "PTR-UCC-9-210" in ids
    assert "PTR-UCC-9-611-614" in ids
    assert "PTR-UCC-9-616" in ids
    assert "PTR-UCC-9-404" in ids
    assert "PTR-FRCP-36" not in ids


def test_federal_litigation_surfaces_admissions_counterclaim_and_foundation_traps():
    ctx = {
        "transaction_type": "consumer_credit",
        "matter_status": "litigation",
        "jurisdiction": ["federal"],
        "parties": [{"name": "consumer", "capacity": "defendant"}],
        "facts": ["pending_action", "esi"],
        "evidence": ["emails"],
    }
    ids = _trap_ids(ctx)
    assert "PTR-FRCP-36" in ids
    assert "PTR-FRCP-13A" in ids
    assert "PTR-FRCP-30B6" in ids
    assert "PTR-FRCP-37E" in ids
    assert "PTR-FRE-FOUNDATION" in ids


def test_ike_advantage_contains_evidence_and_regulatory_moat_controls():
    engine = IKEAdvantageEngine()
    ids = {item.control_id for item in engine.competitive_controls()}
    assert "IKE-MOAT-001" in ids
    assert "IKE-MOAT-004" in ids
    assert "IKE-MOAT-006" in ids


def test_private_treasury_blueprint_separates_own_funds_from_customer_money():
    steps = IKEAdvantageEngine().private_treasury_blueprint()
    assert len(steps) >= 10
    assert any("own" in step.boundary.lower() and "customer" in step.boundary.lower() for step in steps)
    assert any("regulated partner" in step.name.lower() for step in steps)


def test_customer_money_and_financial_services_raise_regulatory_flags():
    engine = IKEAdvantageEngine()
    flags = engine.regulated_activity_flags({
        "holds_customer_funds": True,
        "activities": ["bill_pay", "consumer_lending", "debt_adjustment"],
    })
    assert "MONEY_TRANSMISSION_OR_CUSTOMER_FUNDS_REVIEW_REQUIRED" in flags
    assert "LENDING_AND_USURY_LICENSE_REVIEW_REQUIRED" in flags
    assert "DEBT_ADJUSTMENT_LICENSE_REVIEW_REQUIRED" in flags


def test_own_funds_treasury_only_does_not_raise_money_transmission_flag():
    flags = IKEAdvantageEngine().regulated_activity_flags({
        "holds_customer_funds": False,
        "activities": ["own_funds_treasury", "cash_forecasting", "bank_reconciliation"],
    })
    assert "MONEY_TRANSMISSION_OR_CUSTOMER_FUNDS_REVIEW_REQUIRED" not in flags
