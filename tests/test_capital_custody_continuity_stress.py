from legal_intelligence.capital_custody import CapitalCustodyEngine
from legal_intelligence.capital_continuity import CapitalContinuityEngine
from legal_intelligence.capital_stress import CapitalStressEngine


def test_custody_blocks_self_approval_and_role_collision():
    report = CapitalCustodyEngine().evaluate({
        "action_type": "funding",
        "maker": "alice",
        "checker": "alice",
        "approver": "carol",
    })
    assert report.allowed is False
    assert "SELF_APPROVAL_OR_ROLE_COLLISION" in report.violations


def test_custody_requires_independent_anchor_actor():
    report = CapitalCustodyEngine().evaluate({
        "action_type": "journal_anchor",
        "maker": "alice",
        "checker": "bob",
        "approver": "carol",
        "anchor_actor": "carol",
    })
    assert report.allowed is False
    assert "ANCHOR_ROLE_NOT_INDEPENDENT" in report.violations


def test_continuity_reports_missing_reconstruction_components():
    report = CapitalContinuityEngine().evaluate({
        "available_components": ["bank_source_records", "capital_ledger_export"]
    })
    assert report.reconstructable is False
    assert "external_anchor_receipt" in report.missing_components
    assert "facility_register" in report.missing_components


def test_continuity_passes_with_complete_package():
    engine = CapitalContinuityEngine()
    report = engine.evaluate({"available_components": sorted(engine.REQUIRED_COMPONENTS)})
    assert report.reconstructable is True
    assert report.missing_components == []


def test_stress_engine_finds_breaches_and_zero_safe_deployment():
    report = CapitalStressEngine().evaluate({
        "scenario_name": "severe",
        "collateral_value": 100000,
        "expected_collections": 20000,
        "available_liquidity": 30000,
        "available_reserves": 25000,
        "delinquent_exposure": 10000,
        "top_customer_exposure": 25000,
        "total_exposure": 90000,
        "collateral_value_shock_pct": 25,
        "collection_rate_shock_pct": 40,
        "liquidity_shock_pct": 50,
        "delinquency_increase_pct": 100,
        "top_customer_exposure_increase_pct": 20,
        "reserve_floor": 20000,
        "minimum_liquidity": 20000,
        "max_top_customer_pct": 25,
    })
    assert "LIQUIDITY_MINIMUM_BREACH" in report.breaches
    assert "CUSTOMER_CONCENTRATION_BREACH" in report.breaches
    assert "COLLATERAL_COVERAGE_BREACH" in report.breaches
    assert report.safe_deployable_capital == 0.0


def test_stress_engine_returns_positive_headroom_when_limits_hold():
    report = CapitalStressEngine().evaluate({
        "scenario_name": "moderate",
        "collateral_value": 200000,
        "expected_collections": 20000,
        "available_liquidity": 80000,
        "available_reserves": 70000,
        "delinquent_exposure": 5000,
        "top_customer_exposure": 10000,
        "total_exposure": 100000,
        "collateral_value_shock_pct": 10,
        "collection_rate_shock_pct": 10,
        "liquidity_shock_pct": 10,
        "delinquency_increase_pct": 20,
        "top_customer_exposure_increase_pct": 10,
        "reserve_floor": 30000,
        "minimum_liquidity": 30000,
        "max_top_customer_pct": 20,
    })
    assert report.breaches == []
    assert report.safe_deployable_capital > 0
