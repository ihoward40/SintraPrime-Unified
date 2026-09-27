"""Certification tests for hash anchoring, workouts, collateral monitoring, and capital audit."""

from dataclasses import replace

from legal_intelligence.hash_anchor import HashAnchorEngine
from legal_intelligence.workout_recovery import WorkoutRecoveryEngine
from legal_intelligence.collateral_monitor import CollateralMonitorEngine
from legal_intelligence.capital_audit import CapitalAuditEngine


def test_hash_anchor_requires_external_receipt_and_detects_mismatch():
    engine = HashAnchorEngine()
    payload = engine.build_payload(period="2026-09", journal_head_hash="a" * 64, journal_entries=12)
    empty = engine.verify(payload, [])
    assert not empty.valid
    receipt = engine.record_anchor(payload=payload, provider="independent_store", external_reference="ref-1", evidence_ref="evidence-1", anchored_at="2026-09-30T23:59:00+00:00")
    report = engine.verify(payload, [receipt])
    assert report.valid
    tampered = replace(receipt, journal_head_hash="b" * 64)
    bad = engine.verify(payload, [tampered])
    assert not bad.valid
    assert any("HEAD_HASH_MISMATCH" in x for x in bad.findings)


def test_workout_recovery_ranks_expected_net_but_blocks_unverified_enforcement():
    engine = WorkoutRecoveryEngine()
    result = engine.compare({
        "current_balance_verified": True,
        "secured": True,
        "collateral_value_verified": True,
        "current_law_verified": True,
        "scenarios": [
            {"name": "restructure", "gross_recovery": 9000, "direct_costs": 500, "probability": 0.85, "delay_months": 12},
            {"name": "enforcement", "gross_recovery": 10000, "direct_costs": 2500, "probability": 0.75, "delay_months": 6, "legal_review_required": True},
        ],
    })
    assert result["recommended_scenario"] == "restructure"
    blocked = engine.compare({
        "current_balance_verified": True,
        "secured": True,
        "collateral_value_verified": True,
        "current_law_verified": False,
        "scenarios": [{"name": "enforcement", "gross_recovery": 10000, "direct_costs": 1000, "probability": 0.8, "legal_review_required": True}],
    })
    assert blocked["recommended_scenario"] is None
    assert "ENFORCEMENT_CURRENT_LAW_REVIEW_REQUIRED" in blocked["findings"]


def test_collateral_monitor_surfaces_stale_and_perfection_exceptions():
    report = CollateralMonitorEngine().evaluate({
        "collateral_id": "COL-1",
        "valuation_date": "2020-01-01",
        "max_valuation_age_days": 180,
        "secured": True,
        "security_agreement_verified": True,
        "perfection_status_verified": False,
        "insurance_required": True,
        "insurance_verified": False,
        "title_or_ownership_required": True,
        "title_or_ownership_verified": False,
    })
    assert report.status == "EXCEPTION"
    assert "VALUATION_STALE" in report.findings
    assert "PERFECTION_STATUS_NOT_VERIFIED" in report.findings
    assert "INSURANCE_NOT_VERIFIED" in report.findings


def test_capital_audit_requires_anchor_and_core_reconciliations():
    engine = CapitalAuditEngine()
    report = engine.certify({
        "period": "2026-09",
        "ledger_to_bank_reconciled": True,
        "ledger_to_dashboard_reconciled": True,
        "approvals_complete": True,
        "collateral_records_current": True,
        "servicing_exceptions_reviewed": True,
        "journal_chain_valid": True,
        "journal_head_anchored": False,
    })
    assert report.status == "EXCEPTION"
    assert "AUDIT_FAIL:journal_head_anchored" in report.exceptions
    clean = engine.certify({
        "period": "2026-09",
        "ledger_to_bank_reconciled": True,
        "ledger_to_dashboard_reconciled": True,
        "approvals_complete": True,
        "collateral_records_current": True,
        "servicing_exceptions_reviewed": True,
        "journal_chain_valid": True,
        "journal_head_anchored": True,
    })
    assert clean.status == "CERTIFIED"
