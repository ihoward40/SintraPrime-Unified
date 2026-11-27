from datetime import datetime, timedelta, timezone

import pytest

from legal_intelligence.capital_case_management import CapitalCaseManagementEngine
from legal_intelligence.capital_override import CapitalOverrideEngine


def test_case_requires_owner_and_closure_authority():
    engine = CapitalCaseManagementEngine()
    with pytest.raises(ValueError, match="CASE_OWNER_REQUIRED"):
        engine.open_case({"case_id": "C1", "severity": "HIGH", "closure_authority": "checker"})
    with pytest.raises(ValueError, match="CASE_CLOSURE_AUTHORITY_REQUIRED"):
        engine.open_case({"case_id": "C1", "severity": "HIGH", "owner": "servicer"})


def test_case_sla_and_closure_evidence():
    engine = CapitalCaseManagementEngine()
    opened = datetime(2026, 9, 14, tzinfo=timezone.utc)
    case = engine.open_case({
        "case_id": "C2",
        "source_signal_id": "SIG-1",
        "facility_id": "FAC-1",
        "severity": "CRITICAL",
        "owner": "servicer-a",
        "closure_authority": "principal-b",
        "opened_at": opened.isoformat(),
        "evidence_checklist": ["bank_recon", "collateral_refresh"],
        "remediation_plan": ["restore reserve", "refresh valuation"],
        "reopen_triggers": ["reserve_shortfall_returns"],
    })
    report = engine.evaluate(case, now=(opened + timedelta(hours=5)).isoformat())
    assert report["overdue"] is True
    assert report["status"] == "SLA_BREACH"
    assert set(report["missing_evidence"]) == {"bank_recon", "collateral_refresh"}

    case.satisfied_evidence = ["bank_recon", "collateral_refresh"]
    bad_close = engine.can_close(case, actor="wrong-actor")
    assert bad_close["can_close"] is False
    assert "CLOSURE_AUTHORITY_MISMATCH" in bad_close["issues"]

    ok_close = engine.can_close(case, actor="principal-b")
    assert ok_close["can_close"] is True


def test_closed_case_reopens_on_returned_trigger_or_invalidated_evidence():
    engine = CapitalCaseManagementEngine()
    assert engine.should_reopen(trigger_returned=True)["reopen"] is True
    assert engine.should_reopen(evidence_invalidated=True)["reopen"] is True
    assert engine.should_reopen(override_expired=True)["reopen"] is True


def _override_context():
    return {
        "override_id": "OVR-1",
        "override_type": "FUNDING_FREEZE_RELEASE",
        "subject_id": "FAC-1",
        "reason_code": "TEMP_LIQUIDITY_RECOVERY",
        "rationale": "Documented recovery with compensating controls.",
        "requested_by": "maker-a",
        "approved_by": "principal-b",
        "approval_authority": "capital-policy-committee",
        "effective_at": "2026-09-14T00:00:00+00:00",
        "expires_at": "2026-09-30T00:00:00+00:00",
        "re_review_at": "2026-09-21T00:00:00+00:00",
        "policy_id": "IKE-CAPITAL",
        "policy_version": "2026.09.1",
        "compensating_controls": ["daily_liquidity_monitoring", "no_limit_increase"],
    }


def test_override_blocks_self_approval_and_missing_controls():
    engine = CapitalOverrideEngine()
    context = _override_context()
    context["approved_by"] = context["requested_by"]
    with pytest.raises(ValueError, match="OVERRIDE_SELF_APPROVAL_PROHIBITED"):
        engine.create(context)

    context = _override_context()
    context["compensating_controls"] = []
    with pytest.raises(ValueError, match="OVERRIDE_COMPENSATING_CONTROLS_REQUIRED"):
        engine.create(context)


def test_override_expires_and_cannot_silently_roll_forward():
    engine = CapitalOverrideEngine()
    override = engine.create(_override_context())
    during_review = engine.evaluate(override, now="2026-09-22T00:00:00+00:00")
    assert during_review["status"] == "REVIEW_DUE"
    assert "MANDATORY_REREVIEW" in during_review["actions"]

    expired = engine.evaluate(override, now="2026-10-01T00:00:00+00:00")
    assert expired["status"] == "EXPIRED"
    assert "REINSTATE_UNDERLYING_CONTROL" in expired["actions"]
    assert "REOPEN_ASSOCIATED_CASE" in expired["actions"]


def test_funding_freeze_release_requires_full_recheck():
    engine = CapitalOverrideEngine()
    denied = engine.can_release_funding_freeze({
        "underlying_trigger_resolved": True,
        "case_owner_recommendation": True,
        "independent_approval": False,
        "current_policy_evaluation_passed": True,
        "stress_test_passed": True,
    })
    assert denied["release_allowed"] is False
    assert "INDEPENDENT_APPROVAL_REQUIRED" in denied["issues"]

    approved = engine.can_release_funding_freeze({
        "underlying_trigger_resolved": True,
        "case_owner_recommendation": True,
        "independent_approval": True,
        "current_policy_evaluation_passed": True,
        "stress_test_passed": True,
    })
    assert approved["release_allowed"] is True
