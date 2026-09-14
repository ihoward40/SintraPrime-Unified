from legal_intelligence.policy_change_control import PolicyChangeControlEngine, PolicyChangeRequest
from legal_intelligence.capital_escalation import CapitalEscalationEngine, EscalationSignal


def test_policy_change_blocks_self_approval_and_missing_impact_analysis():
    engine = PolicyChangeControlEngine()
    req = PolicyChangeRequest(
        change_id="chg-1",
        policy_id="capital-policy",
        from_version="1.0.0",
        to_version="1.1.0",
        requested_by="principal",
        effective_date="2026-10-01",
        changed_fields=("maximum_ltv",),
        rationale="Tighten collateral protection",
        rollback_version="1.0.0",
        affected_facilities=("FAC-1",),
        migration_rule="Apply at next review",
        grandfather_existing=False,
        reunderwrite_required=True,
        impact_analysis_complete=False,
        approval_authority="Principal",
        approved_by="principal",
    )
    report = engine.evaluate(req)
    assert report.decision == "BLOCK"
    assert "POLICY_IMPACT_ANALYSIS_REQUIRED" in report.blocking_reasons
    assert "POLICY_SELF_APPROVAL_PROHIBITED" in report.blocking_reasons


def test_policy_change_requires_affected_facilities_for_material_change():
    engine = PolicyChangeControlEngine()
    req = PolicyChangeRequest(
        change_id="chg-2",
        policy_id="capital-policy",
        from_version="1.0.0",
        to_version="1.1.0",
        requested_by="maker",
        effective_date="2026-10-01",
        changed_fields=("reserve_floor",),
        rationale="Increase reserve protection",
        rollback_version="1.0.0",
        affected_facilities=(),
        migration_rule="Immediate",
        grandfather_existing=False,
        reunderwrite_required=False,
        impact_analysis_complete=True,
        approval_authority="Principal",
        approved_by="approver",
    )
    report = engine.evaluate(req)
    assert report.decision == "BLOCK"
    assert "AFFECTED_FACILITY_INVENTORY_REQUIRED" in report.blocking_reasons


def test_high_insurance_lapse_routes_collateral_principal_and_freeze():
    engine = CapitalEscalationEngine()
    result = engine.route(EscalationSignal(
        signal_id="sig-1",
        source_module="SP-CAPITAL-EARLY-WARNING-001",
        subject_id="FAC-9",
        severity="HIGH",
        signal_type="INSURANCE_LAPSE",
        policy_id="capital-policy",
        policy_version="2.0.0",
        evidence_refs=("insurance-expired.pdf",),
    ))
    assert "COLLATERAL_REFRESH" in result.routes
    assert "PRINCIPAL_REVIEW" in result.routes
    assert result.funding_status == "FREEZE_NEW_ADVANCES_PENDING_REVIEW"
    assert result.principal_review_required is True


def test_critical_default_risk_routes_workout_and_audit_exception():
    engine = CapitalEscalationEngine()
    result = engine.route(EscalationSignal(
        signal_id="sig-2",
        source_module="SP-CAPITAL-EARLY-WARNING-001",
        subject_id="FAC-10",
        severity="CRITICAL",
        signal_type="DEFAULT_RISK_HIGH",
        policy_id="capital-policy",
        policy_version="2.0.0",
        evidence_refs=("servicing.json",),
    ))
    assert "WORKOUT_RECOVERY_ANALYSIS" in result.routes
    assert "AUDIT_EXCEPTION" in result.routes
    assert result.workout_review_required is True
    assert result.funding_status == "FREEZE_NEW_ADVANCES_PENDING_REVIEW"
