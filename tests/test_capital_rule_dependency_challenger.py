from legal_intelligence.capital_champion_challenger import (
    CapitalChampionChallengerEngine,
    RuleTestObservation,
)
from legal_intelligence.capital_rule_dependency import (
    CapitalRuleDependencyEngine,
    RuleDependency,
)


def test_dependency_engine_blocks_unresolved_high_critical_dependencies():
    engine = CapitalRuleDependencyEngine()
    dependencies = [
        RuleDependency(
            rule_id="RULE-EWS-001",
            rule_version="1.0",
            dependent_type="ALERT",
            dependent_id="ALERT-COLLECTION-DECLINE",
            dependency_kind="TRIGGERS",
            criticality="HIGH",
        ),
        RuleDependency(
            rule_id="RULE-EWS-001",
            rule_version="1.0",
            dependent_type="COMMITTEE_REPORT",
            dependent_id="MONTHLY-RISK-PACK",
            dependency_kind="REFERENCES",
            criticality="CRITICAL",
        ),
    ]
    report = engine.impact_report("RULE-EWS-001", "1.0", dependencies)
    assert report.status == "BLOCK_CHANGE"
    assert set(report.blocking_dependencies) == {"ALERT-COLLECTION-DECLINE", "MONTHLY-RISK-PACK"}
    assert "UNRESOLVED_HIGH_CRITICAL_DEPENDENCIES" in report.findings


def test_dependency_engine_allows_change_after_dependencies_resolved():
    engine = CapitalRuleDependencyEngine()
    dependencies = [
        RuleDependency(
            rule_id="RULE-STRESS-001",
            rule_version="2.0",
            dependent_type="STRESS_SCENARIO",
            dependent_id="LIQUIDITY-SHOCK",
            dependency_kind="READS",
            criticality="HIGH",
        )
    ]
    report = engine.impact_report(
        "RULE-STRESS-001",
        "2.0",
        dependencies,
        resolved_dependents=["LIQUIDITY-SHOCK"],
    )
    assert report.status == "READY_FOR_GOVERNED_CHANGE"
    assert not report.blocking_dependencies


def test_missing_dependency_records_are_unknown_not_safe():
    report = CapitalRuleDependencyEngine().impact_report("RULE-X", "1", [])
    assert report.status == "NO_DEPENDENCIES_RECORDED"
    assert "DEPENDENCY_COVERAGE_NOT_PROVEN" in report.findings


def _shadow_population():
    rows = []
    # 10 bad outcomes: champion catches 6, challenger catches 9.
    for i in range(10):
        rows.append(
            RuleTestObservation(
                observation_id=f"BAD-{i}",
                bad_outcome_observed=True,
                champion_triggered=i < 6,
                challenger_triggered=i < 9,
                champion_latency_ms=100,
                challenger_latency_ms=80,
                champion_operational_cost=5.0,
                challenger_operational_cost=4.0,
            )
        )
    # 20 good outcomes: champion false-positives 5, challenger false-positives 3.
    for i in range(20):
        rows.append(
            RuleTestObservation(
                observation_id=f"GOOD-{i}",
                bad_outcome_observed=False,
                champion_triggered=i < 5,
                challenger_triggered=i < 3,
                champion_latency_ms=100,
                challenger_latency_ms=80,
                champion_operational_cost=5.0,
                challenger_operational_cost=4.0,
            )
        )
    return rows


def test_challenger_can_be_performance_eligible_but_not_production_authorized():
    engine = CapitalChampionChallengerEngine()
    report = engine.compare(
        champion_rule_id="RULE-EWS-001",
        champion_version="1.0",
        challenger_rule_id="RULE-EWS-001",
        challenger_version="2.0-candidate",
        observations=_shadow_population(),
    )
    assert report.recommendation == "CHALLENGER_ELIGIBLE_FOR_GOVERNED_PROMOTION"
    assert report.production_authority is False
    assert report.challenger.false_negative_rate < report.champion.false_negative_rate
    assert report.challenger.false_positive_rate < report.champion.false_positive_rate


def test_promotion_requires_dependency_registry_and_governance_approval():
    engine = CapitalChampionChallengerEngine()
    report = engine.compare(
        champion_rule_id="RULE-EWS-001",
        champion_version="1.0",
        challenger_rule_id="RULE-EWS-001",
        challenger_version="2.0-candidate",
        observations=_shadow_population(),
    )
    ready, findings = engine.promotion_ready(
        report,
        dependency_review_passed=False,
        registry_entry_ready=False,
        governance_approval_ref=None,
    )
    assert ready is False
    assert "DEPENDENCY_REVIEW_REQUIRED" in findings
    assert "RULE_REGISTRY_ENTRY_REQUIRED" in findings
    assert "GOVERNANCE_APPROVAL_REQUIRED" in findings


def test_false_negative_regression_blocks_challenger():
    rows = []
    for i in range(20):
        bad = i < 10
        rows.append(
            RuleTestObservation(
                observation_id=str(i),
                bad_outcome_observed=bad,
                champion_triggered=bad,
                challenger_triggered=(bad and i < 5),
            )
        )
    report = CapitalChampionChallengerEngine().compare(
        champion_rule_id="RULE-A",
        champion_version="1",
        challenger_rule_id="RULE-A",
        challenger_version="2-candidate",
        observations=rows,
    )
    assert report.recommendation == "RETAIN_CHAMPION"
    assert "CHALLENGER_FALSE_NEGATIVE_REGRESSION" in report.findings
