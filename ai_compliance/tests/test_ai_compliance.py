"""
test_ai_compliance.py — Comprehensive test suite for SintraPrime AI Compliance Module
80+ tests covering all modules: ai_law_db, compliance_checker, ethics_framework,
bias_detector, compliance_reporter, and compliance_api.

Run: python -m pytest ai_compliance/tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from datetime import date, datetime, timedelta
from typing import List

# ============================================================================
# MODULE IMPORTS
# ============================================================================

from ai_compliance.ai_law_db import (
    AILaw,
    ALL_LAWS,
    ComplianceArea,
    Jurisdiction,
    RiskTier,
    get_applicable_laws,
    get_laws_by_area,
    get_laws_by_jurisdiction,
    get_laws_by_risk_tier,
    get_active_laws,
    get_law_by_id,
    get_laws_summary,
    EU_AI_ACT,
    NIST_AI_RMF,
    FTC_AI_GUIDELINES,
    CA_SB_1047,
    TX_HB_149,
    CO_SB_205,
    NY_AI_BIAS,
    ABA_AI_RULES,
)

from ai_compliance.compliance_checker import (
    CheckStatus,
    ComplianceCheck,
    ComplianceChecker,
    ComplianceSummary,
    OperationContext,
    Severity,
    TransparencyChecker,
    ExplainabilityChecker,
    BiasDetectionChecker,
    DataMinimizationChecker,
    HumanReviewChecker,
    UPLChecker,
    ConsentChecker,
    DocumentationChecker,
    quick_check,
)

from ai_compliance.ethics_framework import (
    AIAction,
    EthicsDecision,
    EthicsReview,
    EthicsReviewer,
    EthicalPrinciple,
    RED_LINES,
    check_red_lines,
    evaluate_beneficence,
    evaluate_non_maleficence,
    evaluate_autonomy,
    evaluate_justice,
    evaluate_transparency,
    ethics_review,
    APPROVAL_THRESHOLD,
    CONDITIONAL_THRESHOLD,
)

from ai_compliance.bias_detector import (
    BiasDetector,
    BiasReport,
    BiasSeverity,
    BiasType,
    ProtectedCategory,
    GroupOutcome,
    check_bias,
    compute_adverse_impact_ratio,
    compute_statistical_parity_gap,
    compute_group_adverse_impact,
    extract_group_outcomes,
    ADVERSE_IMPACT_THRESHOLD,
)

from ai_compliance.compliance_reporter import (
    ComplianceReportData,
    ComplianceReporter,
    ComplianceSnapshot,
    TrendDirection,
    RiskRating,
    compute_risk_rating,
    compute_trend,
    aggregate_compliance_stats,
)

from ai_compliance.compliance_api import (
    ComplianceCheckRequest,
    EthicsReviewRequest,
    BiasCheckRequest,
    handle_compliance_check,
    handle_list_laws,
    handle_ethics_review,
    handle_bias_check,
    handle_generate_report,
    _parse_jurisdiction,
    _parse_risk_tier,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def basic_operation_context():
    return OperationContext(
        operation_id="test-001",
        operation_type="legal_advice",
        description="Provide contract review advice",
        jurisdictions=[Jurisdiction.US_CA, Jurisdiction.US_FEDERAL],
        risk_tier=RiskTier.HIGH,
        involves_legal_advice=True,
        involves_personal_data=True,
        ai_identifies_as_ai=True,
        provides_explanation=True,
        allows_human_review=True,
    )


@pytest.fixture
def non_compliant_context():
    return OperationContext(
        operation_id="test-bad",
        operation_type="legal_advice",
        description="Non-compliant operation",
        jurisdictions=[Jurisdiction.US_CA],
        risk_tier=RiskTier.HIGH,
        involves_legal_advice=True,
        ai_identifies_as_ai=False,      # Violation!
        provides_explanation=False,     # Violation!
        allows_human_review=False,      # Violation!
    )


@pytest.fixture
def basic_ai_action():
    return AIAction(
        action_id="action-001",
        action_type="legal_document_generation",
        description="Draft a standard NDA for a technology company",
        requester_context="Business owner requesting NDA draft",
        output_preview="This Non-Disclosure Agreement is entered into by...",
        affects_third_parties=False,
        involves_sensitive_data=False,
        is_irreversible=False,
        involves_vulnerable_person=False,
        could_cause_financial_harm=False,
        could_cause_physical_harm=False,
        is_discriminatory=False,
        is_transparent=True,
        respects_autonomy=True,
        benefits_user=True,
        metadata={"ai_disclosed": True},
    )


@pytest.fixture
def harmful_ai_action():
    return AIAction(
        action_id="action-bad",
        action_type="legal_advice",
        description="Guarantee lawsuit outcome and act as attorney",
        requester_context="Unknown",
        output_preview="I guarantee you will win. As your attorney, I advise...",
        could_cause_financial_harm=True,
        could_cause_physical_harm=False,
        is_discriminatory=None,
        is_transparent=False,
        benefits_user=False,
        metadata={"user_asked_if_ai": True},
    )


@pytest.fixture
def checker():
    return ComplianceChecker()


@pytest.fixture
def reviewer():
    return EthicsReviewer()


@pytest.fixture
def detector():
    return BiasDetector()


@pytest.fixture
def reporter():
    return ComplianceReporter()


# ============================================================================
# 1. AI LAW DATABASE TESTS (14 tests)
# ============================================================================

class TestAILawDatabase:

    def test_all_laws_not_empty(self):
        assert len(ALL_LAWS) >= 10, "Should have at least 10 laws in database"

    def test_eu_ai_act_exists(self):
        assert EU_AI_ACT is not None
        assert EU_AI_ACT.law_id == "EU-AI-ACT-2024"
        assert EU_AI_ACT.jurisdiction == Jurisdiction.EU

    def test_eu_ai_act_extraterritorial(self):
        assert EU_AI_ACT.extraterritorial is True

    def test_aba_rules_legal_profession_specific(self):
        assert ABA_AI_RULES.legal_profession_specific is True

    def test_all_laws_have_required_fields(self):
        for law in ALL_LAWS:
            assert law.law_id, f"Law {law} missing law_id"
            assert law.law_name, f"Law {law} missing law_name"
            assert law.short_name, f"Law {law} missing short_name"
            assert law.jurisdiction, f"Law {law} missing jurisdiction"
            assert law.requirements, f"Law {law} missing requirements"
            assert law.applies_to, f"Law {law} missing applies_to"
            assert law.compliance_areas, f"Law {law} missing compliance_areas"

    def test_get_laws_by_jurisdiction_eu(self):
        eu_laws = get_laws_by_jurisdiction(Jurisdiction.EU)
        assert len(eu_laws) >= 1
        assert all(l.jurisdiction == Jurisdiction.EU for l in eu_laws)

    def test_get_laws_by_area_transparency(self):
        laws = get_laws_by_area(ComplianceArea.TRANSPARENCY)
        assert len(laws) >= 3
        assert all(ComplianceArea.TRANSPARENCY in l.compliance_areas for l in laws)

    def test_get_laws_by_risk_tier_high(self):
        laws = get_laws_by_risk_tier(RiskTier.HIGH)
        assert len(laws) >= 5

    def test_get_active_laws(self):
        active = get_active_laws()
        assert all(l.status == "active" for l in active)

    def test_get_law_by_id_found(self):
        law = get_law_by_id("EU-AI-ACT-2024")
        assert law is not None
        assert law.short_name == "EU AI Act"

    def test_get_law_by_id_not_found(self):
        law = get_law_by_id("NONEXISTENT-LAW-9999")
        assert law is None

    def test_get_laws_summary_returns_dict(self):
        summary = get_laws_summary()
        assert isinstance(summary, dict)
        assert len(summary) == len(ALL_LAWS)

    def test_get_applicable_laws_with_legal_profession(self):
        laws = get_applicable_laws(
            jurisdictions=[Jurisdiction.US_CA],
            risk_tier=RiskTier.HIGH,
            legal_profession=True,
        )
        law_ids = [l.law_id for l in laws]
        assert "ABA-AI-RULES-2024" in law_ids

    def test_get_applicable_laws_without_legal_profession(self):
        laws = get_applicable_laws(
            jurisdictions=[Jurisdiction.US_CA],
            risk_tier=RiskTier.HIGH,
            legal_profession=False,
        )
        law_ids = [l.law_id for l in laws]
        assert "ABA-AI-RULES-2024" not in law_ids

    def test_law_matches_area(self):
        assert EU_AI_ACT.matches_area(ComplianceArea.TRANSPARENCY)
        assert not EU_AI_ACT.matches_area(ComplianceArea.UPL)

    def test_law_covers_risk_tier(self):
        assert EU_AI_ACT.covers_risk_tier(RiskTier.HIGH)
        assert EU_AI_ACT.covers_risk_tier(RiskTier.UNACCEPTABLE)

    def test_ca_state_laws_present(self):
        ca_laws = get_laws_by_jurisdiction(Jurisdiction.US_CA)
        assert len(ca_laws) >= 2


# ============================================================================
# 2. COMPLIANCE CHECKER TESTS (18 tests)
# ============================================================================

class TestComplianceChecker:

    def test_checker_runs_on_compliant_context(self, checker, basic_operation_context):
        summary = checker.run_full_check(basic_operation_context)
        assert isinstance(summary, ComplianceSummary)
        assert summary.operation_id == "test-001"

    def test_compliant_context_has_checks(self, checker, basic_operation_context):
        summary = checker.run_full_check(basic_operation_context)
        assert len(summary.checks) > 0

    def test_non_compliant_context_detected(self, checker, non_compliant_context):
        summary = checker.run_full_check(non_compliant_context)
        assert summary.overall_status == CheckStatus.NON_COMPLIANT

    def test_non_compliant_context_has_high_risk_score(self, checker, non_compliant_context):
        summary = checker.run_full_check(non_compliant_context)
        assert summary.risk_score > 20

    def test_transparency_checker_ai_identified(self):
        ctx = OperationContext(
            operation_id="t1", operation_type="chat", description="",
            jurisdictions=[Jurisdiction.US_FEDERAL], risk_tier=RiskTier.LIMITED,
            ai_identifies_as_ai=True,
        )
        status, findings, remediation, severity = TransparencyChecker.check(ctx)
        assert status == CheckStatus.COMPLIANT

    def test_transparency_checker_ai_not_identified(self):
        ctx = OperationContext(
            operation_id="t2", operation_type="chat", description="",
            jurisdictions=[Jurisdiction.US_FEDERAL], risk_tier=RiskTier.LIMITED,
            ai_identifies_as_ai=False,
        )
        status, findings, remediation, severity = TransparencyChecker.check(ctx)
        assert status == CheckStatus.NON_COMPLIANT
        assert severity == Severity.CRITICAL

    def test_explainability_checker_high_stakes_no_explanation(self):
        ctx = OperationContext(
            operation_id="e1", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_CA], risk_tier=RiskTier.HIGH,
            involves_legal_advice=True, provides_explanation=False,
        )
        status, _, _, severity = ExplainabilityChecker.check(ctx)
        assert status == CheckStatus.NON_COMPLIANT
        assert severity == Severity.HIGH

    def test_explainability_checker_low_stakes_no_explanation(self):
        ctx = OperationContext(
            operation_id="e2", operation_type="chat", description="",
            jurisdictions=[Jurisdiction.US_CA], risk_tier=RiskTier.MINIMAL,
            provides_explanation=False,
        )
        status, _, _, _ = ExplainabilityChecker.check(ctx)
        assert status == CheckStatus.NOT_APPLICABLE

    def test_human_review_checker_high_stakes_no_review(self):
        ctx = OperationContext(
            operation_id="h1", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_TX], risk_tier=RiskTier.HIGH,
            involves_legal_advice=True, allows_human_review=False,
        )
        status, _, _, severity = HumanReviewChecker.check(ctx)
        assert status == CheckStatus.NON_COMPLIANT
        assert severity == Severity.HIGH

    def test_human_review_checker_compliant(self):
        ctx = OperationContext(
            operation_id="h2", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_TX], risk_tier=RiskTier.HIGH,
            involves_legal_advice=True, allows_human_review=True,
        )
        status, _, _, _ = HumanReviewChecker.check(ctx)
        assert status == CheckStatus.COMPLIANT

    def test_upl_checker_non_legal_operation(self):
        ctx = OperationContext(
            operation_id="u1", operation_type="search", description="",
            jurisdictions=[Jurisdiction.US_FEDERAL], risk_tier=RiskTier.MINIMAL,
            involves_legal_advice=False,
        )
        status, _, _, _ = UPLChecker.check(ctx)
        assert status == CheckStatus.NOT_APPLICABLE

    def test_upl_checker_detects_attorney_language(self):
        ctx = OperationContext(
            operation_id="u2", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_CA], risk_tier=RiskTier.HIGH,
            involves_legal_advice=True,
            output_text="As your attorney, I advise you to file immediately.",
        )
        status, findings, remediation, _ = UPLChecker.check(ctx)
        assert status == CheckStatus.NON_COMPLIANT
        assert len(remediation) > 0

    def test_data_minimization_checker_no_data(self):
        ctx = OperationContext(
            operation_id="d1", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_CA], risk_tier=RiskTier.LIMITED,
            data_fields_collected=[],
        )
        status, _, _, _ = DataMinimizationChecker.check(ctx)
        assert status == CheckStatus.COMPLIANT

    def test_data_minimization_checker_sensitive_fields(self):
        ctx = OperationContext(
            operation_id="d2", operation_type="legal", description="",
            jurisdictions=[Jurisdiction.US_CA], risk_tier=RiskTier.HIGH,
            data_fields_collected=["ssn", "name", "address"],
        )
        status, findings, _, _ = DataMinimizationChecker.check(ctx)
        assert status == CheckStatus.NEEDS_REVIEW
        assert len(findings) > 0

    def test_consent_checker_needs_review_when_unknown(self):
        ctx = OperationContext(
            operation_id="c1", operation_type="hiring", description="",
            jurisdictions=[Jurisdiction.US_IL], risk_tier=RiskTier.HIGH,
            involves_personal_data=True, involves_employment_decision=True,
            metadata={},
        )
        status, _, _, _ = ConsentChecker.check(ctx)
        assert status == CheckStatus.NEEDS_REVIEW

    def test_quick_check_function_works(self):
        summary = quick_check(
            operation_type="legal_advice",
            jurisdictions=[Jurisdiction.US_CA],
            risk_tier=RiskTier.HIGH,
            involves_legal_advice=True,
            ai_identifies_as_ai=True,
        )
        assert isinstance(summary, ComplianceSummary)
        assert summary.risk_score >= 0

    def test_remediation_roadmap_generated(self, checker, non_compliant_context):
        summary = checker.run_full_check(non_compliant_context)
        roadmap = checker.get_remediation_roadmap(summary)
        assert len(roadmap) > 0
        assert all("action" in item for item in roadmap)

    def test_compliance_summary_counts(self, checker, basic_operation_context):
        summary = checker.run_full_check(basic_operation_context)
        total = summary.compliant_count + summary.non_compliant_count + summary.needs_review_count
        # Some checks may be NOT_APPLICABLE so total <= len(checks)
        assert total <= len(summary.checks)


# ============================================================================
# 3. ETHICS FRAMEWORK TESTS (18 tests)
# ============================================================================

class TestEthicsFramework:

    def test_red_lines_defined(self):
        assert len(RED_LINES) >= 10
        for rl in RED_LINES:
            assert "id" in rl
            assert "name" in rl
            assert "description" in rl

    def test_good_action_approved(self, reviewer, basic_ai_action):
        review = reviewer.review(basic_ai_action)
        assert review.decision == EthicsDecision.APPROVED

    def test_harmful_action_refused(self, reviewer, harmful_ai_action):
        review = reviewer.review(harmful_ai_action)
        assert review.decision == EthicsDecision.REFUSED

    def test_red_line_attorney_impersonation_detected(self):
        action = AIAction(
            action_id="rl-001",
            action_type="legal",
            description="claim to be attorney",
            requester_context="",
            output_preview="As your attorney, I represent you in this matter.",
            is_transparent=True,
            benefits_user=True,
            respects_autonomy=True,
        )
        violations = check_red_lines(action)
        assert any(v.red_line_id == "RL-001" for v in violations)

    def test_red_line_guarantee_outcomes_detected(self):
        action = AIAction(
            action_id="rl-002",
            action_type="legal",
            description="guarantee lawsuit result",
            requester_context="",
            output_preview="I guarantee you will win this case with certainty.",
            is_transparent=True,
            benefits_user=True,
            respects_autonomy=True,
        )
        violations = check_red_lines(action)
        assert any(v.red_line_id == "RL-002" for v in violations)

    def test_red_line_discriminatory_output(self):
        action = AIAction(
            action_id="rl-003",
            action_type="recommendation",
            description="discriminatory recommendation",
            requester_context="",
            is_discriminatory=True,
            is_transparent=True,
            benefits_user=True,
            respects_autonomy=True,
        )
        violations = check_red_lines(action)
        assert any(v.red_line_id == "RL-003" for v in violations)

    def test_no_red_line_violations_for_good_action(self, basic_ai_action):
        violations = check_red_lines(basic_ai_action)
        assert len(violations) == 0

    def test_beneficence_score_good_action(self, basic_ai_action):
        ps = evaluate_beneficence(basic_ai_action)
        assert ps.score > 0.5
        assert ps.principle == EthicalPrinciple.BENEFICENCE

    def test_non_maleficence_score_harmful_action(self, harmful_ai_action):
        ps = evaluate_non_maleficence(harmful_ai_action)
        assert ps.score < 0.5
        assert len(ps.concerns) > 0

    def test_autonomy_score_respects_autonomy(self, basic_ai_action):
        ps = evaluate_autonomy(basic_ai_action)
        assert ps.score > 0.5

    def test_justice_score_non_discriminatory(self, basic_ai_action):
        ps = evaluate_justice(basic_ai_action)
        assert ps.score > 0.5

    def test_transparency_score_transparent_action(self, basic_ai_action):
        ps = evaluate_transparency(basic_ai_action)
        assert ps.score > 0.5

    def test_overall_score_computed(self, reviewer, basic_ai_action):
        review = reviewer.review(basic_ai_action)
        assert 0.0 <= review.overall_score <= 1.0

    def test_all_principles_scored(self, reviewer, basic_ai_action):
        review = reviewer.review(basic_ai_action)
        scored_principles = {ps.principle for ps in review.principle_scores}
        expected = {EthicalPrinciple.BENEFICENCE, EthicalPrinciple.NON_MALEFICENCE,
                    EthicalPrinciple.AUTONOMY, EthicalPrinciple.JUSTICE,
                    EthicalPrinciple.TRANSPARENCY}
        assert expected == scored_principles

    def test_conditional_decision_generates_conditions(self, reviewer):
        borderline_action = AIAction(
            action_id="border-01",
            action_type="legal",
            description="Borderline action with some concerns",
            requester_context="",
            is_transparent=False,       # Transparency concern
            benefits_user=True,
            respects_autonomy=True,
            could_cause_financial_harm=False,
            could_cause_physical_harm=False,
            is_discriminatory=False,
        )
        review = reviewer.review(borderline_action)
        if review.decision == EthicsDecision.CONDITIONAL:
            assert len(review.conditions) > 0

    def test_ethics_review_function_shortcut(self):
        review = ethics_review(
            action_type="legal_advice",
            description="Provide general contract information",
            is_transparent=True,
            benefits_user=True,
        )
        assert isinstance(review, EthicsReview)
        assert review.action_id is not None

    def test_reviewer_get_red_lines(self, reviewer):
        red_lines = reviewer.get_red_lines()
        assert len(red_lines) >= 10

    def test_is_red_line_violation_method(self, reviewer, basic_ai_action, harmful_ai_action):
        assert not reviewer.is_red_line_violation(basic_ai_action)
        assert reviewer.is_red_line_violation(harmful_ai_action)

    def test_review_to_dict(self, reviewer, basic_ai_action):
        review = reviewer.review(basic_ai_action)
        d = review.to_dict()
        assert "decision" in d
        assert "overall_score" in d
        assert "passes" in d
        assert "principle_scores" in d


# ============================================================================
# 4. BIAS DETECTOR TESTS (16 tests)
# ============================================================================

class TestBiasDetector:

    def test_clean_text_no_bias(self, detector):
        text = "The contract terms provide equal protection for all parties involved in the agreement."
        report = detector.analyze(text)
        assert report.overall_severity == BiasSeverity.NONE
        assert not report.is_biased

    def test_explicit_race_bias_detected(self, detector):
        text = "Blacks are typically less qualified for senior positions in this field."
        report = detector.analyze(text)
        assert report.is_biased
        assert report.overall_severity == BiasSeverity.CRITICAL
        assert report.requires_blocking

    def test_explicit_gender_bias_detected(self, detector):
        text = "Women can't handle the pressure of executive roles effectively."
        report = detector.analyze(text)
        assert report.is_biased

    def test_proxy_variable_detected(self, detector):
        text = "Applicants from the right zip code are preferred. Credit score is a key factor."
        report = detector.analyze(text)
        assert len(report.proxy_variables_detected) > 0

    def test_adverse_impact_threshold(self):
        ratio = compute_adverse_impact_ratio(0.50, 0.70)
        assert ratio is not None
        assert abs(ratio - 0.714) < 0.01

    def test_adverse_impact_above_threshold_ok(self):
        ratio = compute_adverse_impact_ratio(0.85, 1.00)
        assert ratio >= ADVERSE_IMPACT_THRESHOLD

    def test_adverse_impact_below_threshold_fails(self):
        ratio = compute_adverse_impact_ratio(0.50, 1.00)
        assert ratio < ADVERSE_IMPACT_THRESHOLD

    def test_adverse_impact_zero_majority_rate(self):
        ratio = compute_adverse_impact_ratio(0.50, 0.0)
        assert ratio is None

    def test_statistical_parity_gap_zero(self):
        gap = compute_statistical_parity_gap([0.8, 0.8, 0.8])
        assert gap == 0.0

    def test_statistical_parity_gap_computed(self):
        gap = compute_statistical_parity_gap([0.9, 0.6, 0.75])
        assert abs(gap - 0.3) < 0.001

    def test_bias_score_clean_text(self, detector):
        report = detector.analyze("All parties agree to equal terms and conditions.")
        assert report.bias_score == 0.0

    def test_bias_score_biased_text(self, detector):
        report = detector.analyze("Old workers typically cannot adapt to new technologies.")
        assert report.bias_score > 0.0

    def test_compute_group_adverse_impact(self):
        group_outcomes = {"GroupA": 80, "GroupB": 50, "GroupC": 90}
        group_totals = {"GroupA": 100, "GroupB": 100, "GroupC": 100}
        ratios = compute_group_adverse_impact(group_outcomes, group_totals)
        assert "GroupB" in ratios
        assert ratios["GroupC"] == 1.0  # Highest rate = 1.0
        assert ratios["GroupB"] < 1.0

    def test_bias_report_to_dict(self, detector):
        report = detector.analyze("Fair and equal treatment for all.")
        d = report.to_dict()
        assert "is_biased" in d
        assert "bias_score" in d
        assert "overall_severity" in d

    def test_check_bias_shortcut(self):
        report = check_bias("Standard legal contract language.")
        assert isinstance(report, BiasReport)

    def test_remediation_suggestions_for_biased_text(self, detector):
        report = detector.analyze("Blacks are always more likely to default on loans.")
        assert len(report.remediation_suggestions) > 0
        assert report.requires_blocking


# ============================================================================
# 5. COMPLIANCE REPORTER TESTS (10 tests)
# ============================================================================

class TestComplianceReporter:

    def _make_report_data(self, snapshots=None):
        today = date.today()
        return ComplianceReportData(
            report_id="rpt-test-001",
            report_title="Test Report",
            organization="TestOrg",
            generated_at=datetime.utcnow(),
            period_start=today - timedelta(days=30),
            period_end=today,
            compliance_summaries=[],
            bias_reports=[],
            ethics_reviews=[],
            historical_snapshots=snapshots or [],
        )

    def test_generate_report_returns_string(self, reporter):
        data = self._make_report_data()
        report = reporter.generate_report(data)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_report_contains_header(self, reporter):
        data = self._make_report_data()
        report = reporter.generate_report(data)
        assert "Test Report" in report

    def test_report_contains_executive_summary(self, reporter):
        data = self._make_report_data()
        report = reporter.generate_report(data)
        assert "Executive Summary" in report

    def test_risk_rating_critical(self):
        assert compute_risk_rating(85) == RiskRating.CRITICAL

    def test_risk_rating_high(self):
        assert compute_risk_rating(65) == RiskRating.HIGH

    def test_risk_rating_medium(self):
        assert compute_risk_rating(45) == RiskRating.MEDIUM

    def test_risk_rating_low(self):
        assert compute_risk_rating(25) == RiskRating.LOW

    def test_risk_rating_minimal(self):
        assert compute_risk_rating(10) == RiskRating.MINIMAL

    def test_trend_insufficient_data(self):
        trend = compute_trend([])
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA

    def test_trend_improving(self):
        today = date.today()
        snapshots = [
            ComplianceSnapshot(
                snapshot_date=today - timedelta(days=30),
                overall_risk_score=60, compliant_count=60, non_compliant_count=30,
                needs_review_count=10, bias_score=0.2, ethics_approval_rate=0.7,
                active_violations=8,
            ),
            ComplianceSnapshot(
                snapshot_date=today,
                overall_risk_score=30, compliant_count=90, non_compliant_count=5,
                needs_review_count=5, bias_score=0.05, ethics_approval_rate=0.95,
                active_violations=1,
            ),
        ]
        trend = compute_trend(snapshots)
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.risk_score_delta < 0

    def test_aggregate_compliance_stats_empty(self):
        stats = aggregate_compliance_stats([])
        assert stats["total_checks"] == 0

    def test_summary_dict_generated(self, reporter):
        data = self._make_report_data()
        summary = reporter.generate_summary_dict(data)
        assert "report_id" in summary
        assert "risk_score" in summary
        assert "compliance_rate" in summary


# ============================================================================
# 6. COMPLIANCE API TESTS (14 tests)
# ============================================================================

class TestComplianceAPI:

    def test_parse_jurisdiction_us_ca(self):
        j = _parse_jurisdiction("US_CA")
        assert j == Jurisdiction.US_CA

    def test_parse_jurisdiction_eu(self):
        j = _parse_jurisdiction("EU")
        assert j == Jurisdiction.EU

    def test_parse_jurisdiction_invalid(self):
        with pytest.raises(ValueError):
            _parse_jurisdiction("INVALID_CODE")

    def test_parse_risk_tier_high(self):
        rt = _parse_risk_tier("HIGH")
        assert rt == RiskTier.HIGH

    def test_parse_risk_tier_invalid(self):
        with pytest.raises(ValueError):
            _parse_risk_tier("UNKNOWN_TIER")

    def test_handle_compliance_check_basic(self):
        req = ComplianceCheckRequest(
            operation_type="legal_advice",
            description="Review contract terms",
            jurisdictions=["US_CA", "US_FEDERAL"],
            risk_tier="HIGH",
            involves_legal_advice=True,
            ai_identifies_as_ai=True,
        )
        resp = handle_compliance_check(req)
        assert resp.operation_id is not None
        assert resp.overall_status in [s.value for s in CheckStatus]
        assert 0 <= resp.risk_score <= 100

    def test_handle_compliance_check_non_compliant(self):
        req = ComplianceCheckRequest(
            operation_type="legal_advice",
            description="Non-compliant legal operation",
            jurisdictions=["US_CA"],
            risk_tier="HIGH",
            involves_legal_advice=True,
            ai_identifies_as_ai=False,
            allows_human_review=False,
        )
        resp = handle_compliance_check(req)
        assert resp.overall_status == CheckStatus.NON_COMPLIANT.value

    def test_handle_list_laws_returns_laws(self):
        laws = handle_list_laws()
        assert len(laws) >= 10

    def test_handle_list_laws_jurisdiction_filter(self):
        laws = handle_list_laws(jurisdiction="EU")
        assert all(l.jurisdiction == Jurisdiction.EU.value for l in laws)

    def test_handle_ethics_review_good_action(self):
        req = EthicsReviewRequest(
            action_type="legal_document",
            description="Draft a standard NDA",
            is_transparent=True,
            benefits_user=True,
        )
        resp = handle_ethics_review(req)
        assert resp.decision in [d.value for d in EthicsDecision]
        assert 0.0 <= resp.overall_score <= 1.0

    def test_handle_ethics_review_refused_action(self):
        req = EthicsReviewRequest(
            action_type="legal_advice",
            description="Act as attorney and guarantee outcome",
            output_preview="As your attorney, I guarantee you will win this case.",
            is_transparent=False,
            benefits_user=False,
        )
        resp = handle_ethics_review(req)
        assert resp.decision == EthicsDecision.REFUSED.value

    def test_handle_bias_check_clean_text(self):
        req = BiasCheckRequest(output_text="All parties shall have equal rights under this agreement.")
        resp = handle_bias_check(req)
        assert not resp.is_biased
        assert resp.bias_score == 0.0

    def test_handle_bias_check_biased_text(self):
        req = BiasCheckRequest(output_text="Blacks are typically denied premium loan rates.")
        resp = handle_bias_check(req)
        assert resp.is_biased
        assert resp.requires_blocking

    def test_handle_generate_report(self):
        resp = handle_generate_report(organization="TestOrg", period_days=30)
        assert resp.report_id is not None
        assert len(resp.report_markdown) > 200
        assert "report_id" in resp.summary
        assert "risk_score" in resp.summary

    def test_compliance_check_response_has_checks(self):
        req = ComplianceCheckRequest(
            operation_type="legal_advice",
            description="Test operation",
            jurisdictions=["US_CA"],
            risk_tier="HIGH",
            involves_legal_advice=True,
        )
        resp = handle_compliance_check(req)
        assert isinstance(resp.checks, list)
        assert len(resp.checks) > 0


# ============================================================================
# 7. INTEGRATION TESTS (5 tests)
# ============================================================================

class TestIntegration:

    def test_full_compliance_pipeline(self):
        """End-to-end test: check compliance, ethics, bias for a legal operation."""
        # 1. Compliance check
        summary = quick_check(
            operation_type="contract_review",
            jurisdictions=[Jurisdiction.US_CA, Jurisdiction.EU],
            risk_tier=RiskTier.HIGH,
            involves_legal_advice=True,
            involves_personal_data=True,
            ai_identifies_as_ai=True,
            provides_explanation=True,
            allows_human_review=True,
            output_text="The contract terms appear equitable for all parties.",
        )
        assert summary.overall_status is not None
        assert isinstance(summary.risk_score, int)

        # 2. Ethics review
        review = ethics_review(
            action_type="contract_review",
            description="Review and summarize contract terms",
            is_transparent=True,
            benefits_user=True,
            metadata={"ai_disclosed": True},
        )
        assert review.passes

        # 3. Bias check
        report = check_bias("The contract treats all parties equally with no discrimination.")
        assert not report.is_biased

    def test_non_compliant_pipeline_detected(self):
        """Test that a non-compliant operation is properly flagged throughout."""
        summary = quick_check(
            operation_type="legal_advice",
            jurisdictions=[Jurisdiction.US_CA],
            risk_tier=RiskTier.HIGH,
            involves_legal_advice=True,
            ai_identifies_as_ai=False,
            allows_human_review=False,
            output_text="As your attorney I guarantee you will win this lawsuit.",
        )
        assert summary.overall_status == CheckStatus.NON_COMPLIANT
        assert summary.non_compliant_count > 0

    def test_report_generation_with_summaries(self):
        """Test generating a compliance report from actual compliance summaries."""
        import uuid
        summary = quick_check(
            operation_type="legal_advice",
            jurisdictions=[Jurisdiction.US_CA],
            risk_tier=RiskTier.HIGH,
            involves_legal_advice=True,
        )
        bias_report = check_bias("Standard legal contract with equitable terms for all.")
        review = ethics_review(
            action_type="legal", description="Standard legal assistance",
            is_transparent=True, benefits_user=True,
        )

        today = date.today()
        data = ComplianceReportData(
            report_id=str(uuid.uuid4())[:8],
            report_title="Integration Test Report",
            organization="TestOrg",
            generated_at=datetime.utcnow(),
            period_start=today - timedelta(days=7),
            period_end=today,
            compliance_summaries=[summary],
            bias_reports=[bias_report],
            ethics_reviews=[review],
        )
        reporter = ComplianceReporter()
        report_md = reporter.generate_report(data)
        assert "Integration Test Report" in report_md
        assert len(report_md) > 500

    def test_all_jurisdictions_can_be_parsed(self):
        """Test that all jurisdiction codes used in tests can be parsed."""
        test_codes = ["US_CA", "US_TX", "US_CO", "US_NY", "US_IL", "US_VA", "US_WA", "US_FL",
                      "EU", "US_FEDERAL", "INTERNATIONAL", "PROFESSIONAL"]
        for code in test_codes:
            j = _parse_jurisdiction(code)
            assert j is not None

    def test_compliance_api_handles_all_risk_tiers(self):
        """Test that the API handles all risk tiers."""
        for tier in ["HIGH", "LIMITED", "MINIMAL"]:
            req = ComplianceCheckRequest(
                operation_type="general",
                description="Test operation",
                jurisdictions=["US_FEDERAL"],
                risk_tier=tier,
            )
            resp = handle_compliance_check(req)
            assert resp.operation_id is not None


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
