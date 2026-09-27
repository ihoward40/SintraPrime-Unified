from datetime import date

from legal_intelligence.capital_outcome_review import CapitalOutcomeReviewEngine
from legal_intelligence.capital_lessons_learned import CapitalLessonsLearnedEngine


def test_outcome_review_effective_when_risk_metrics_improve():
    report = CapitalOutcomeReviewEngine().review(
        {
            "decision_id": "DEC-100",
            "effective_date": date(2026, 1, 1),
            "review_date": date(2026, 2, 15),
            "action_completed": True,
            "expected_result": "Improve reserve and collateral headroom",
            "pre_metrics": {
                "reserve_headroom": 100,
                "delinquency": 10,
                "concentration": 40,
                "collateral_coverage": 1.05,
                "sla_breaches": 4,
                "waiver_dependency": 30,
                "stress_headroom": 50,
            },
            "post_metrics": {
                "reserve_headroom": 150,
                "delinquency": 5,
                "concentration": 35,
                "collateral_coverage": 1.20,
                "sla_breaches": 2,
                "waiver_dependency": 20,
                "stress_headroom": 75,
            },
        }
    )
    assert report.classification == "EFFECTIVE"
    assert report.improved_count == 7
    assert report.worsened_count == 0


def test_outcome_review_ineffective_when_metrics_only_worsen():
    report = CapitalOutcomeReviewEngine().review(
        {
            "decision_id": "DEC-101",
            "effective_date": date(2026, 1, 1),
            "review_date": date(2026, 3, 1),
            "action_completed": True,
            "expected_result": "Reduce risk",
            "pre_metrics": {"reserve_headroom": 100, "delinquency": 5},
            "post_metrics": {"reserve_headroom": 80, "delinquency": 8},
        }
    )
    assert report.classification == "INEFFECTIVE"
    assert report.worsened_count == 2


def test_outcome_review_too_early_respects_observation_window():
    report = CapitalOutcomeReviewEngine().review(
        {
            "decision_id": "DEC-102",
            "effective_date": date(2026, 2, 1),
            "review_date": date(2026, 2, 10),
            "minimum_observation_days": 30,
            "action_completed": True,
            "expected_result": "Improve collateral coverage",
            "pre_metrics": {"collateral_coverage": 1.0},
            "post_metrics": {"collateral_coverage": 1.1},
        }
    )
    assert report.classification == "TOO_EARLY_TO_TELL"


def test_lessons_learned_converts_ineffective_outcome_into_candidates():
    lesson = CapitalLessonsLearnedEngine().derive(
        {
            "lesson_id": "LESSON-1",
            "decision_id": "DEC-101",
            "outcome_classification": "INEFFECTIVE",
            "problem_statement": "Collections did not recover after waiver",
            "root_cause": "Underwriting assumptions were too optimistic",
            "lesson": "Tighten assumptions and add earlier collections deterioration signal",
            "failure_domain": "UNDERWRITING",
            "evidence_refs": ["committee-pack-2026-02", "ledger-snapshot-2026-02"],
        }
    )
    assert lesson.status == "ACTION_REQUIRED"
    assert lesson.underwriting_adjustments
    assert lesson.early_warning_candidates
    payload = CapitalLessonsLearnedEngine().adoption_payload(lesson)
    assert payload["requires_separate_approval"] is True


def test_lessons_do_not_auto_apply_policy_changes():
    engine = CapitalLessonsLearnedEngine()
    lesson = engine.derive(
        {
            "lesson_id": "LESSON-2",
            "decision_id": "DEC-103",
            "outcome_classification": "PARTIALLY_EFFECTIVE",
            "problem_statement": "Reserve improved but concentration worsened",
            "root_cause": "Policy permitted excessive concentration",
            "lesson": "Review concentration ceiling",
            "failure_domain": "POLICY",
            "evidence_refs": ["risk-trends-2026-03"],
        }
    )
    payload = engine.adoption_payload(lesson)
    assert lesson.policy_change_candidates
    assert payload["requires_separate_approval"] is True
