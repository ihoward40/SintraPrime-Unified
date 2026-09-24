from datetime import date, timedelta

from legal_intelligence.capital_control_validation import (
    CapitalControlValidationEngine,
    ControlObservation,
)
from legal_intelligence.capital_rule_registry import (
    CapitalRuleRecord,
    CapitalRuleRegistryEngine,
)


def test_control_validation_flags_excessive_false_negatives():
    engine = CapitalControlValidationEngine()
    observations = []
    observations.extend(ControlObservation("RULE-1", True, True) for _ in range(8))
    observations.extend(ControlObservation("RULE-1", False, False) for _ in range(8))
    observations.extend(ControlObservation("RULE-1", False, True) for _ in range(4))

    report = engine.validate(
        "RULE-1",
        observations,
        minimum_complete_observations=20,
        max_false_negative_rate=0.20,
    )

    assert report.classification == "REVALIDATE_OR_REDESIGN"
    assert "FALSE_NEGATIVE_RATE_EXCESSIVE" in report.findings
    assert report.false_negative_rate == 0.333333


def test_control_validation_can_validate_for_continued_use():
    engine = CapitalControlValidationEngine()
    observations = []
    observations.extend(ControlObservation("RULE-2", True, True) for _ in range(8))
    observations.extend(ControlObservation("RULE-2", True, False) for _ in range(2))
    observations.extend(ControlObservation("RULE-2", False, False) for _ in range(9))
    observations.extend(ControlObservation("RULE-2", False, True) for _ in range(1))

    report = engine.validate("RULE-2", observations, minimum_complete_observations=20)

    assert report.classification == "VALIDATED_FOR_CONTINUED_USE"
    assert report.false_positive_rate is not None
    assert report.false_negative_rate is not None


def test_rule_registry_flags_overdue_review_without_destroying_record_validity():
    engine = CapitalRuleRegistryEngine()
    rule = CapitalRuleRecord(
        rule_id="EW-COLL-001",
        version="1.0",
        owner="risk-owner",
        category="EARLY_WARNING",
        rationale="Detect collection-rate deterioration.",
        source="SP-CAPITAL-EARLY-WARNING-001",
        effective_date=date(2026, 1, 1),
        review_due_date=date(2026, 6, 30),
        status="ACTIVE",
        retirement_criteria=["replacement validated"],
    )

    decision = engine.validate(rule, as_of=date(2026, 9, 14))

    assert decision.valid is True
    assert "RULE_REVIEW_OVERDUE" in decision.findings


def test_rule_registry_blocks_superseded_rule_without_replacement():
    engine = CapitalRuleRegistryEngine()
    rule = CapitalRuleRecord(
        rule_id="STRESS-LIQ-001",
        version="2.0",
        owner="risk-owner",
        category="STRESS_ASSUMPTION",
        rationale="Liquidity shock assumption.",
        source="committee-approved stress methodology",
        effective_date=date.today() - timedelta(days=30),
        review_due_date=date.today() + timedelta(days=60),
        status="SUPERSEDED",
        retirement_criteria=["new assumption validated"],
    )

    decision = engine.validate(rule)

    assert decision.valid is False
    assert "REPLACEMENT_RULE_REQUIRED" in decision.findings


def test_rule_retirement_requires_evidence_and_replacement_decision():
    engine = CapitalRuleRegistryEngine()
    rule = CapitalRuleRecord(
        rule_id="UW-DSCR-001",
        version="1.0",
        owner="credit-owner",
        category="UNDERWRITING_THRESHOLD",
        rationale="Minimum debt-service coverage threshold.",
        source="capital policy",
        effective_date=date.today() - timedelta(days=100),
        review_due_date=date.today() + timedelta(days=100),
        status="ACTIVE",
        retirement_criteria=["replacement threshold validated"],
    )

    blocked = engine.retirement_ready(rule, evidence=[])
    assert blocked.valid is False
    assert "RETIREMENT_EVIDENCE_REQUIRED" in blocked.findings

    rule.replacement_rule_id = "UW-DSCR-002"
    ready = engine.retirement_ready(rule, evidence=["validation-report-22"])
    assert ready.valid is True
    assert ready.status == "RETIREMENT_READY"
