from legal_intelligence.capital_policy_engine import CapitalPolicy, CapitalPolicyEngine
from legal_intelligence.capital_early_warning import CapitalEarlyWarningEngine


def policy():
    return CapitalPolicy(
        policy_id="IKE-CAPITAL",
        policy_version="2026.09",
        effective_date="2026-09-14",
        reserve_floor_amount=10000,
        reserve_floor_ratio=0.15,
        dscr_minimum=1.25,
        ltv_maximum=0.75,
        borrower_concentration_max=0.25,
        affiliate_group_concentration_max=0.40,
        collateral_class_concentration_max=0.50,
        receivable_customer_concentration_max=0.20,
        maker_checker_threshold=5000,
        revaluation_frequency_days=90,
        maximum_delinquency_days=30,
        stress_buffer_ratio=0.05,
        liquidity_buffer_ratio=0.20,
        override_authorities=("Principal", "Credit Committee"),
    )


def test_policy_version_and_thresholds_are_traceable():
    p = policy()
    engine = CapitalPolicyEngine()
    assert engine.validate_policy(p) == []
    assert engine.threshold(p, "dscr_minimum") == 1.25
    report = engine.evaluate(p, {
        "reserve_available": 20000,
        "total_exposure": 50000,
        "dscr": 1.5,
        "ltv": 0.60,
        "days_past_due": 0,
        "liquidity_ratio": 0.30,
        "borrower_concentration": 0.10,
        "affiliate_group_concentration": 0.20,
        "collateral_class_concentration": 0.30,
        "receivable_customer_concentration": 0.10,
        "collateral_valuation_age_days": 20,
        "transaction_amount": 6000,
        "independent_checker_present": True,
    })
    assert report.status == "COMPLIANT"
    assert report.policy_version == "2026.09"


def test_policy_engine_blocks_inconsistent_risk_limits():
    p = policy()
    report = CapitalPolicyEngine().evaluate(p, {
        "reserve_available": 5000,
        "total_exposure": 50000,
        "dscr": 1.0,
        "ltv": 0.90,
        "days_past_due": 45,
        "liquidity_ratio": 0.10,
        "borrower_concentration": 0.35,
        "collateral_valuation_age_days": 100,
        "transaction_amount": 10000,
        "independent_checker_present": False,
    })
    assert report.status == "BREACH"
    for code in ["RESERVE_POLICY_BREACH", "DSCR_POLICY_BREACH", "LTV_POLICY_BREACH", "DELINQUENCY_POLICY_BREACH", "MAKER_CHECKER_REQUIRED"]:
        assert code in report.breaches


def test_early_warning_detects_pre_default_deterioration():
    p = policy()
    report = CapitalEarlyWarningEngine().scan(
        policy=p,
        prior={
            "collection_rate": 0.95,
            "days_sales_outstanding": 35,
            "collateral_coverage_ratio": 1.6,
            "liquidity_ratio": 0.35,
        },
        current={
            "collection_rate": 0.78,
            "days_sales_outstanding": 45,
            "collateral_coverage_ratio": 1.3,
            "liquidity_ratio": 0.25,
            "covenant_waivers_rolling_12m": 2,
            "receivable_customer_concentration": 0.19,
            "insurance_status": "active",
            "perfection_expiry_days": 75,
            "policy_exceptions_rolling_6m": 3,
            "days_past_due": 20,
            "reserve_ratio": 0.18,
        },
    )
    codes = {x.code for x in report.signals}
    assert report.watch_level == "HIGH"
    assert "EWS_COLLECTION_DECLINE" in codes
    assert "EWS_DSO_RISING" in codes
    assert "EWS_REPEAT_COVENANT_WAIVERS" in codes
    assert "EWS_PERFECTION_EXPIRING" in codes
    assert "EWS_RECURRING_POLICY_EXCEPTIONS" in codes
    assert report.policy_version == "2026.09"


def test_early_warning_escalates_insurance_lapse_to_critical():
    report = CapitalEarlyWarningEngine().scan(
        policy=policy(),
        current={"insurance_status": "lapsed", "perfection_expiry_days": 20},
    )
    assert report.watch_level == "CRITICAL"
    codes = {x.code for x in report.signals}
    assert "EWS_INSURANCE_LAPSE" in codes
    assert "EWS_PERFECTION_EXPIRING" in codes
