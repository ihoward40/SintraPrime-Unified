"""Certification tests for SP-TRANSACTION-CAPACITY-001."""

import pytest

from legal_intelligence.transaction_capacity_gate import (
    GateDecision,
    TransactionCapacityGate,
    TransactionCapacityGateError,
)
from legal_intelligence.rare_legal_levers import RareLegalLeverageEngine


def _uacc_records_context():
    """UACC first-case context: secured auto finance, evidence request posture.

    The test intentionally does NOT assume that sale notices, disposition records,
    GAP refunds, or deficiency accounting prove a violation.  Those are requested
    records and remain missing evidence until produced.
    """
    return {
        "transaction_type": "secured_auto_finance",
        "jurisdiction": ["New Jersey"],
        "parties": [
            {"name": "consumer", "capacity": "consumer_obligor"},
            {"name": "United Auto Credit Corporation", "capacity": "secured_creditor_or_servicer"},
        ],
        "obligations": [
            {
                "obligor": "consumer",
                "basis": "retail_installment_contract",
                "subject": "2015 Ford Taurus account",
            }
        ],
        "governing_law": [
            "UCC Article 9 as adopted by the governing state",
            "applicable retail installment and consumer-protection law",
        ],
        "evidence": [
            "retail_installment_contract",
            "account_history_partial",
            "repossession_or_chargeoff_history",
            "disposition_occurred",
            "credit_reporting",
            "consumer_report",
        ],
        "facts": ["vehicle", "repossession_sale", "seller_arranged_credit"],
        "output_purpose": "records_demand",
        "theories": [
            {
                "name": "collateral_disposition_and_deficiency_accounting",
                "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
                "required_evidence": [
                    "sale_notice",
                    "sale_result",
                    "deficiency_ledger",
                ],
            },
            {
                "name": "gap_addon_refund_review",
                "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
                "required_evidence": ["gap_or_addon_contracts", "refund_accounting"],
            },
            {
                "name": "consumer_reporting_accuracy",
                "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
                "required_evidence": ["furnisher_reporting_history"],
            },
        ],
    }


def test_missing_context_blocks_governed_action():
    gate = TransactionCapacityGate()
    with pytest.raises(TransactionCapacityGateError) as exc:
        gate.enforce("SEND_DEMAND_LETTER", {})
    assert exc.value.report.decision == GateDecision.BLOCK
    assert exc.value.report.findings[0].code == "TC001_CONTEXT_REQUIRED"


def test_unsupported_theory_is_quarantined_and_blocks():
    gate = TransactionCapacityGate()
    context = {
        "transaction_type": "consumer_credit",
        "parties": [{"name": "consumer", "capacity": "obligor"}],
        "obligations": [{"obligor": "consumer", "basis": "credit_agreement"}],
        "governing_law": ["applicable consumer law"],
        "evidence": ["credit_agreement"],
        "theories": [
            {
                "name": "secret_treasury_account_pays_bill",
                "classification": "UNSUPPORTED",
            }
        ],
    }
    report = gate.evaluate("SEND_DEMAND_LETTER", {"transaction_context": context})
    assert report.decision == GateDecision.BLOCK
    assert "secret_treasury_account_pays_bill" in report.quarantined_theories


def test_uacc_records_demand_passes_with_limits_for_missing_records():
    gate = TransactionCapacityGate()
    report = gate.evaluate(
        "SEND_DEMAND_LETTER",
        {"transaction_context": _uacc_records_context()},
    )
    assert report.decision == GateDecision.PASS_WITH_LIMITS
    assert "collateral_disposition_and_deficiency_accounting" in report.permitted_theories
    assert any("sale_notice" in item for item in report.missing_evidence)
    assert not report.quarantined_theories


def test_uacc_merits_claim_blocks_until_required_evidence_exists():
    gate = TransactionCapacityGate()
    context = _uacc_records_context()
    context["output_purpose"] = "demand"
    report = gate.evaluate("SEND_DEMAND_LETTER", {"transaction_context": context})
    assert report.decision == GateDecision.BLOCK
    assert any(f.code == "TC010_EVIDENCE_REQUIRED" for f in report.findings)


def test_suretyship_requires_actual_secondary_liability_evidence():
    gate = TransactionCapacityGate()
    context = {
        "transaction_type": "negotiable_instrument",
        "parties": [
            {"name": "A", "capacity": "principal_obligor"},
            {"name": "B", "capacity": "alleged_secondary_obligor"},
        ],
        "obligations": [{"obligor": "A", "basis": "instrument"}],
        "governing_law": ["UCC Article 3"],
        "evidence": ["instrument"],
        "theories": [
            {
                "name": "suretyship",
                "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
            }
        ],
    }
    report = gate.evaluate("SEND_DEMAND_LETTER", {"transaction_context": context})
    assert report.decision == GateDecision.BLOCK
    assert any(f.code == "TC011_SURETY_ELEMENTS" for f in report.findings)


def test_deposit_account_control_requires_bank_control_evidence():
    gate = TransactionCapacityGate()
    context = {
        "transaction_type": "deposit_account_security_interest",
        "parties": [
            {"name": "debtor", "capacity": "debtor"},
            {"name": "claimant", "capacity": "secured_party"},
            {"name": "bank", "capacity": "depositary_bank"},
        ],
        "obligations": [{"obligor": "debtor", "basis": "security_agreement"}],
        "governing_law": ["UCC Article 9"],
        "evidence": ["security_agreement"],
        "theories": [
            {
                "name": "deposit_account_control",
                "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
            }
        ],
    }
    report = gate.evaluate("SEND_DEMAND_LETTER", {"transaction_context": context})
    assert report.decision == GateDecision.BLOCK
    assert any(f.code == "TC012_DEPOSIT_CONTROL" for f in report.findings)


def test_uacc_context_surfaces_underused_legal_levers_without_turning_them_into_merits_findings():
    levers = RareLegalLeverageEngine().suggest(_uacc_records_context())
    ids = {lever.lever_id for lever in levers}
    assert "LEV-UCC-9-210" in ids
    assert "LEV-UCC-9-616" in ids
    assert "LEV-UCC-9-602" in ids
    assert "LEV-NJ-DEFICIENCY-PRESUMPTION" in ids
    assert "LEV-FTC-HOLDER-RULE" in ids
    assert "LEV-REGV-1022-43" in ids
