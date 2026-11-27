from legal_intelligence.capital_committee_pack import CapitalCommitteePackEngine
from legal_intelligence.capital_risk_trends import CapitalRiskTrendsEngine


def test_risk_trends_detect_deterioration_and_waiver_dependency():
    report = CapitalRiskTrendsEngine().analyze([
        {
            "period": "2026-07",
            "sla_breaches": 1,
            "reopened_cases": 0,
            "overrides": 1,
            "waivers": 1,
            "aged_waivers": 0,
            "collateral_coverage": 1.4,
            "reserve_headroom": 5000,
            "policy_exceptions": 1,
            "top_concentration_pct": 20,
        },
        {
            "period": "2026-08",
            "sla_breaches": 3,
            "reopened_cases": 2,
            "overrides": 4,
            "waivers": 3,
            "aged_waivers": 2,
            "collateral_coverage": 1.1,
            "reserve_headroom": 1000,
            "policy_exceptions": 4,
            "top_concentration_pct": 38,
        },
    ])
    assert report.direction == "DETERIORATING"
    assert "COLLATERAL_COVERAGE_ERODING" in report.deterioration_flags
    assert report.waiver_dependency_score >= 60
    assert report.beneficial_suggestions


def test_risk_trends_no_data_is_explicit():
    report = CapitalRiskTrendsEngine().analyze([])
    assert report.direction == "NO_DATA"
    assert "NO_HISTORY" in report.deterioration_flags


def test_committee_pack_blocks_complete_status_when_sections_missing():
    pack = CapitalCommitteePackEngine().assemble({"period": "2026-08", "dashboard": {}})
    assert pack.status == "INCOMPLETE"
    assert any(item.startswith("MISSING_SECTION:") for item in pack.unresolved_exceptions)


def test_committee_pack_surfaces_management_decisions_and_evidence():
    pack = CapitalCommitteePackEngine().assemble({
        "period": "2026-08",
        "dashboard": {
            "total_exposure": 50000,
            "available_liquidity": 12000,
            "reserve_shortfall": 2500,
            "source_ref": "BANK-STMT-2026-08",
        },
        "risk_trends": {"direction": "DETERIORATING", "evidence_ref": "TREND-2026-08"},
        "cases": [
            {"case_id": "C-1", "status": "OPEN", "severity": "CRITICAL", "evidence_refs": ["CASE-EV-1"]}
        ],
        "overrides": [
            {"override_id": "O-1", "status": "ACTIVE"},
            {"override_id": "O-2", "status": "EXPIRED"},
        ],
        "stress_results": {"status": "BLOCK_NEW_ADVANCES", "source_ref": "STRESS-2026-08"},
        "workout_recoveries": [],
        "policy_changes": [],
        "audit_exceptions": [{"code": "A-1"}],
        "decision_journal_anchor": {"anchor_ref": "ANCHOR-2026-08"},
    })
    assert pack.status == "READY_WITH_CRITICAL_ITEMS"
    assert "REVIEW_CRITICAL_CASES" in pack.decisions_required
    assert "APPROVE_PORTFOLIO_RISK_REMEDIATION_PLAN" in pack.decisions_required
    assert "REVIEW_STRESS_BREACH_AND_FUNDING_POSTURE" in pack.decisions_required
    assert "ADDRESS_RESERVE_SHORTFALL" in pack.decisions_required
    assert "BANK-STMT-2026-08" in pack.evidence_index
    assert "ANCHOR-2026-08" in pack.evidence_index
    assert pack.beneficial_suggestions
