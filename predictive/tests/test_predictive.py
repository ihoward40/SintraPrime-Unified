"""
Comprehensive Tests for Predictive ML System

Tests for outcome prediction, judge analysis, settlement calculation,
risk scoring, strategy optimization, and ML training pipeline.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from outcome_predictor import (
    CaseOutcomePredictor, CaseFeatures, CasePrediction, ModelMetrics
)
from judge_analyzer import JudgeAnalyzer, JudgeProfile
from settlement_calculator import SettlementCalculator, SettlementRange
from legal_risk_scorer import LegalRiskScorer, RiskLevel
from case_strategy_optimizer import CaseStrategyOptimizer
from ml_training_pipeline import MLTrainingPipeline


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_case_features():
    """Create sample case features for testing."""
    return CaseFeatures(
        case_id='test_001',
        case_type='employment',
        court='federal',
        circuit='2nd',
        judge_name='Judge Sarah Mitchell',
        years_on_bench=12,
        num_parties=2,
        num_claims=2,
        prior_case_history_plaintiff=3,
        prior_case_history_defendant=2,
        days_to_trial=365,
        representation_quality_plaintiff=7.5,
        representation_quality_defendant=6.0,
        damages_requested=500000,
        typical_award_amount=350000,
        jurisdiction='federal',
        venue_appropriateness=7.0,
        prior_verdicts_favorable_count=3,
        prior_verdicts_total_count=5,
        has_summary_judgment=False,
        class_action=False,
        injunction_sought=True,
        is_criminal=False,
    )


@pytest.fixture
def sample_training_data():
    """Create sample training data."""
    np.random.seed(42)
    n_samples = 200
    
    data = {
        'case_id': [f'case_{i}' for i in range(n_samples)],
        'case_type': np.random.choice(['civil_rights', 'contract', 'tort', 'employment'], n_samples),
        'court': np.random.choice(['federal', 'state'], n_samples),
        'num_parties': np.random.randint(2, 8, n_samples),
        'num_claims': np.random.randint(1, 6, n_samples),
        'damages_requested': np.random.exponential(500000, n_samples),
        'years_on_bench': np.random.randint(2, 35, n_samples),
        'representation_quality_plaintiff': np.random.uniform(1, 10, n_samples),
        'representation_quality_defendant': np.random.uniform(1, 10, n_samples),
        'days_to_trial': np.random.randint(30, 1000, n_samples),
        'outcome': np.random.binomial(1, 0.5, n_samples),
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def outcome_predictor_model():
    """Create and train outcome predictor."""
    predictor = CaseOutcomePredictor(model_version='1.0')
    return predictor


@pytest.fixture
def judge_analyzer():
    """Create judge analyzer."""
    return JudgeAnalyzer()


@pytest.fixture
def settlement_calculator():
    """Create settlement calculator."""
    return SettlementCalculator()


@pytest.fixture
def risk_scorer():
    """Create risk scorer."""
    return LegalRiskScorer()


@pytest.fixture
def strategy_optimizer():
    """Create strategy optimizer."""
    return CaseStrategyOptimizer()


@pytest.fixture
def ml_pipeline():
    """Create ML training pipeline."""
    return MLTrainingPipeline()


# ============================================================================
# Case Features Tests (5 tests)
# ============================================================================

def test_case_features_creation():
    """Test creation of CaseFeatures object."""
    features = CaseFeatures(
        case_id='test_001',
        case_type='contract',
        court='federal',
    )
    assert features.case_id == 'test_001'
    assert features.case_type == 'contract'
    assert features.court == 'federal'
    assert features.num_parties == 2  # Default


def test_case_features_to_dict():
    """Test CaseFeatures.to_dict() conversion."""
    features = CaseFeatures(
        case_id='test_001',
        case_type='tort',
        court='state',
    )
    features_dict = features.to_dict()
    assert isinstance(features_dict, dict)
    assert features_dict['case_id'] == 'test_001'
    assert features_dict['case_type'] == 'tort'


def test_case_features_defaults():
    """Test default values in CaseFeatures."""
    features = CaseFeatures(case_id='test', case_type='test', court='federal')
    assert features.num_parties == 2
    assert features.num_claims == 1
    assert features.representation_quality_plaintiff == 5.0
    assert features.has_summary_judgment == False
    assert features.is_criminal == False


def test_case_features_criminal_case():
    """Test CaseFeatures with criminal case type."""
    features = CaseFeatures(
        case_id='test_criminal',
        case_type='criminal',
        court='state',
        is_criminal=True,
    )
    assert features.is_criminal == True
    assert features.case_type == 'criminal'


def test_case_features_class_action():
    """Test CaseFeatures with class action designation."""
    features = CaseFeatures(
        case_id='test_class',
        case_type='employment',
        court='federal',
        class_action=True,
        num_parties=50,
    )
    assert features.class_action == True
    assert features.num_parties == 50


# ============================================================================
# Outcome Predictor Tests (15 tests)
# ============================================================================

def test_outcome_predictor_initialization():
    """Test outcome predictor initialization."""
    predictor = CaseOutcomePredictor(model_version='1.0')
    assert predictor.model_version == '1.0'
    assert not predictor.is_trained
    assert predictor.ensemble_weights['gradient_boosting'] == 0.5


def test_outcome_predictor_custom_weights():
    """Test outcome predictor with custom ensemble weights."""
    weights = {
        'gradient_boosting': 0.6,
        'random_forest': 0.3,
        'logistic_regression': 0.1,
    }
    predictor = CaseOutcomePredictor(weights=weights)
    assert predictor.ensemble_weights == weights


def test_feature_engineering_basic():
    """Test basic feature engineering."""
    predictor = CaseOutcomePredictor()
    features = CaseFeatures(
        case_id='test',
        case_type='employment',
        court='federal',
        num_parties=2,
    )
    engineered = predictor._engineer_features(features)
    assert engineered.shape[0] == 1
    assert engineered.shape[1] > 0  # Should have multiple features


def test_feature_engineering_all_case_types():
    """Test feature engineering with all case types."""
    predictor = CaseOutcomePredictor()
    case_types = ['civil_rights', 'contract', 'tort', 'criminal', 'family', 'ip']
    
    for case_type in case_types:
        features = CaseFeatures(
            case_id=f'test_{case_type}',
            case_type=case_type,
            court='federal',
        )
        engineered = predictor._engineer_features(features)
        assert engineered.shape[0] == 1


def test_confidence_interval_calculation():
    """Test confidence interval calculation."""
    predictor = CaseOutcomePredictor()
    predictions = np.array([0.4, 0.5, 0.6])
    ci = predictor._get_confidence_interval(predictions)
    
    assert ci.lower <= ci.upper
    assert 0 <= ci.lower <= 1
    assert 0 <= ci.upper <= 1
    assert ci.confidence_level == 0.95


def test_confidence_interval_95_percent():
    """Test 95% confidence interval."""
    predictor = CaseOutcomePredictor()
    predictions = np.array([0.5] * 10)
    ci = predictor._get_confidence_interval(predictions, confidence=0.95)
    assert ci.confidence_level == 0.95


def test_confidence_interval_99_percent():
    """Test 99% confidence interval."""
    predictor = CaseOutcomePredictor()
    predictions = np.array([0.5] * 10)
    ci = predictor._get_confidence_interval(predictions, confidence=0.99)
    assert ci.confidence_level == 0.99


def test_key_factors_extraction():
    """Test extraction of key factors influencing prediction."""
    predictor = CaseOutcomePredictor()
    features = CaseFeatures(
        case_id='test',
        case_type='employment',
        court='federal',
        representation_quality_plaintiff=8.5,
        prior_case_history_plaintiff=5,
        prior_case_history_defendant=2,
    )
    factors = predictor._get_key_factors(features, 0.65)
    
    assert isinstance(factors, list)
    assert len(factors) <= 5
    for factor_name, impact_score in factors:
        assert isinstance(factor_name, str)
        assert isinstance(impact_score, float)


def test_recommendations_generation_strong_case():
    """Test recommendations for strong case."""
    predictor = CaseOutcomePredictor()
    features = CaseFeatures(
        case_id='test_strong',
        case_type='contract',
        court='federal',
    )
    factors = [('Good Factor', 0.5)]
    recommendations = predictor._generate_recommendations(0.85, factors)
    
    assert len(recommendations) > 0
    assert any('strong' in r.lower() or 'aggressive' in r.lower() for r in recommendations)


def test_recommendations_generation_weak_case():
    """Test recommendations for weak case."""
    predictor = CaseOutcomePredictor()
    features = CaseFeatures(
        case_id='test_weak',
        case_type='tort',
        court='federal',
    )
    factors = [('Bad Factor', -0.5)]
    recommendations = predictor._generate_recommendations(0.25, factors)
    
    assert len(recommendations) > 0
    assert any('settlement' in r.lower() or 'risk' in r.lower() for r in recommendations)


def test_model_training(sample_training_data):
    """Test model training."""
    predictor = CaseOutcomePredictor()
    metrics = predictor.train(sample_training_data)
    
    assert predictor.is_trained
    assert isinstance(metrics, ModelMetrics)
    assert 0 <= metrics.roc_auc <= 1
    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.f1 <= 1


def test_model_evaluation_metrics(sample_training_data):
    """Test model evaluation metrics."""
    predictor = CaseOutcomePredictor()
    metrics = predictor.train(sample_training_data)
    
    assert metrics.roc_auc > 0.5  # Better than random
    assert len(metrics.cv_scores) == 5  # 5-fold CV
    assert metrics.brier_score >= 0


def test_prediction_without_training():
    """Test that prediction fails if model not trained."""
    predictor = CaseOutcomePredictor()
    features = CaseFeatures(case_id='test', case_type='employment', court='federal')
    
    with pytest.raises(ValueError):
        predictor.predict(features)


def test_prediction_probability_bounds(sample_training_data):
    """Test that predictions are in valid probability bounds."""
    predictor = CaseOutcomePredictor()
    predictor.train(sample_training_data)
    
    features = CaseFeatures(case_id='test', case_type='employment', court='federal')
    prediction = predictor.predict(features)
    
    assert 0 <= prediction.win_probability <= 1


# ============================================================================
# Judge Analyzer Tests (10 tests)
# ============================================================================

def test_judge_analyzer_initialization(judge_analyzer):
    """Test judge analyzer initialization."""
    assert judge_analyzer is not None
    assert len(judge_analyzer.judge_database) > 0


def test_judge_profile_retrieval(judge_analyzer):
    """Test retrieving judge profile."""
    profile = judge_analyzer.get_judge_profile(
        'Judge Sarah Mitchell',
        'U.S. District Court'
    )
    assert profile is not None
    assert profile.judge_name == 'Judge Sarah Mitchell'


def test_judge_profile_not_found(judge_analyzer):
    """Test behavior when judge not found."""
    profile = judge_analyzer.get_judge_profile(
        'Judge Non Existent',
        'Unknown Court'
    )
    assert profile is None


def test_judge_tendency_analysis(judge_analyzer):
    """Test judge tendency analysis."""
    tendency = judge_analyzer.analyze_judge_tendencies('judge_001', 'employment')
    
    assert tendency is not None
    assert 0 <= tendency.plaintiff_win_rate <= 1
    assert 0 <= tendency.defendant_win_rate <= 1
    assert tendency.plaintiff_win_rate + tendency.defendant_win_rate == 1.0


def test_judge_win_rate_calculation(judge_analyzer):
    """Test win rate calculation for specific party."""
    plaintiff_rate = judge_analyzer.get_win_rate('judge_001', 'employment', 'plaintiff')
    defendant_rate = judge_analyzer.get_win_rate('judge_001', 'employment', 'defendant')
    
    assert 0 <= plaintiff_rate <= 1
    assert 0 <= defendant_rate <= 1
    assert plaintiff_rate + defendant_rate == 1.0


def test_judge_strategy_recommendations(judge_analyzer):
    """Test strategy recommendations based on judge."""
    recommendations = judge_analyzer.recommend_strategy('judge_001', 'employment')
    
    assert recommendations is not None
    assert recommendations.trial_type_recommendation in ['bench', 'jury', 'either']
    assert len(recommendations.legal_theory_emphasis) > 0


def test_judge_comparison(judge_analyzer):
    """Test judge comparison."""
    comparison = judge_analyzer.compare_judges(['judge_001', 'judge_002'])
    
    assert comparison is not None
    assert len(comparison.judge_ids) == 2
    assert comparison.most_plaintiff_friendly in comparison.judge_names
    assert comparison.most_defendant_friendly in comparison.judge_names


def test_judge_benchmark_memo_recommendations(judge_analyzer):
    """Test bench memo recommendations."""
    recommendations = judge_analyzer.get_bench_memo_recommendations('judge_001', 'employment')
    
    assert len(recommendations) > 0
    assert isinstance(recommendations, list)
    assert all(isinstance(r, str) for r in recommendations)


def test_judge_profiles_initialization(judge_analyzer):
    """Test that judge database is properly initialized."""
    assert 'judge_001' in judge_analyzer.judge_database
    assert 'judge_002' in judge_analyzer.judge_database
    assert 'judge_003' in judge_analyzer.judge_database


def test_judge_characteristic_trends(judge_analyzer):
    """Test judge characteristic trends."""
    profile = judge_analyzer.judge_database['judge_001']
    
    # Judge Mitchell should be plaintiff-friendly
    assert profile.civil_rights_plaintiff_win_rate > 0.6
    assert profile.summary_judgment_grant_rate < 0.45
    assert profile.class_certification_grant_rate > 0.5


# ============================================================================
# Settlement Calculator Tests (8 tests)
# ============================================================================

def test_settlement_calculator_initialization(settlement_calculator):
    """Test settlement calculator initialization."""
    assert settlement_calculator is not None
    assert len(settlement_calculator.verdict_database) > 0


def test_comparable_verdicts_retrieval(settlement_calculator):
    """Test retrieval of comparable verdicts."""
    comparables = settlement_calculator.find_comparable_verdicts(
        'employment', 'federal'
    )
    
    assert len(comparables) > 0
    assert all(v.case_type == 'employment' for v in comparables)


def test_settlement_value_calculation(settlement_calculator):
    """Test settlement value calculation."""
    settlement_range = settlement_calculator.calculate_settlement_value(
        case_type='employment',
        jurisdiction='federal',
        damages_requested=500000,
        case_strength=0.65,
    )
    
    assert settlement_range.low_estimate < settlement_range.likely_estimate
    assert settlement_range.likely_estimate < settlement_range.high_estimate
    assert 0 <= settlement_range.confidence <= 1


def test_settlement_range_ordering(settlement_calculator):
    """Test that settlement range is properly ordered."""
    settlement_range = settlement_calculator.calculate_settlement_value(
        case_type='contract',
        jurisdiction='federal',
        damages_requested=1000000,
        case_strength=0.7,
    )
    
    assert settlement_range.low_estimate >= 0
    assert settlement_range.likely_estimate >= settlement_range.low_estimate
    assert settlement_range.high_estimate >= settlement_range.likely_estimate


def test_trial_npv_analysis(settlement_calculator):
    """Test NPV analysis for trial."""
    npv = settlement_calculator.calculate_trial_npv(
        win_probability=0.65,
        expected_damages=500000,
        trial_costs=150000,
    )
    
    assert npv.trial_expected_value > 0
    assert npv.npv_trial > 0
    assert isinstance(npv.recommendation, str)


def test_negotiation_strategy_generation(settlement_calculator):
    """Test negotiation strategy generation."""
    settlement_range = settlement_calculator.calculate_settlement_value(
        'employment', 'federal', 500000, 0.6
    )
    npv = settlement_calculator.calculate_trial_npv(0.6, 300000)
    
    strategy = settlement_calculator.recommend_negotiation_strategy(
        settlement_range, npv, {'maximize_recovery': 0.7}
    )
    
    assert strategy.initial_demand > settlement_range.likely_estimate
    assert strategy.walkaway_floor <= strategy.initial_demand
    assert len(strategy.negotiation_phases) > 0


def test_attorney_fee_impact(settlement_calculator):
    """Test attorney fee impact calculation."""
    fee_impact = settlement_calculator.calculate_attorney_fee_impact(
        500000, 'contingency_33'
    )
    
    assert fee_impact['gross_settlement'] == 500000
    assert fee_impact['attorney_fee'] > 0
    assert fee_impact['net_recovery'] < fee_impact['gross_settlement']
    assert fee_impact['recovery_percentage'] > 0.6


def test_time_value_impact(settlement_calculator):
    """Test time value of money impact."""
    impact = settlement_calculator.calculate_time_value_impact(
        settlement_today=400000,
        trial_value_future=500000,
        months_until_trial=36,
    )
    
    assert impact['settlement_today'] > 0
    assert impact['trial_value_future'] > 0
    assert impact['discounted_trial_value'] < impact['trial_value_future']


# ============================================================================
# Risk Scorer Tests (8 tests)
# ============================================================================

def test_risk_scorer_initialization(risk_scorer):
    """Test risk scorer initialization."""
    assert risk_scorer is not None
    assert len(risk_scorer.risk_factors_db) > 0


def test_litigation_risk_assessment(risk_scorer):
    """Test litigation risk assessment."""
    risk_score = risk_scorer.assess_litigation_risk({
        'recent_lawsuits': 1,
        'past_litigation_count': 3,
        'industry_litigation_rate': 0.6,
        'damages_exposure': 500000,
    })
    
    assert 0 <= risk_score.score <= 100
    assert risk_score.risk_level in [RiskLevel.MINIMAL, RiskLevel.LOW, RiskLevel.MODERATE, 
                                      RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert 0 <= risk_score.probability <= 1


def test_regulatory_risk_assessment(risk_scorer):
    """Test regulatory risk assessment."""
    risk_score = risk_scorer.assess_regulatory_risk(
        'finance',
        {'compliance_violations': 1, 'compliance_program_score': 3}
    )
    
    assert 0 <= risk_score.score <= 100
    assert len(risk_score.key_drivers) > 0


def test_employment_risk_assessment(risk_scorer):
    """Test employment risk assessment."""
    risk_score = risk_scorer.assess_employment_risk(
        employee_count=500,
        past_claims=2,
        industry='hospitality'
    )
    
    assert 0 <= risk_score.score <= 100
    assert risk_score.potential_damages > 0


def test_comprehensive_risk_profile(risk_scorer):
    """Test comprehensive risk profile generation."""
    entity_data = {
        'entity_name': 'Test Corporation',
        'entity_type': 'corporation',
        'industry': 'finance',
        'employee_count': 250,
        'litigation_facts': {'past_litigation_count': 1},
        'regulatory_facts': {'compliance_violations': 0},
        'criminal_facts': {},
        'ip_facts': {'patent_disputes': 0},
    }
    
    profile = risk_scorer.generate_risk_profile(entity_data)
    
    assert profile.entity_name == 'Test Corporation'
    assert profile.overall_risk_score >= 0
    assert profile.total_potential_exposure > 0


def test_risk_mitigation_planning(risk_scorer):
    """Test risk mitigation planning."""
    entity_data = {
        'entity_name': 'Test Corp',
        'entity_type': 'corporation',
        'industry': 'healthcare',
        'employee_count': 100,
        'litigation_facts': {'past_litigation_count': 2},
        'regulatory_facts': {'compliance_violations': 1},
        'criminal_facts': {},
        'ip_facts': {},
    }
    
    profile = risk_scorer.generate_risk_profile(entity_data)
    mitigation = risk_scorer.recommend_risk_mitigation(profile)
    
    assert len(mitigation.high_priority_actions) > 0
    assert len(mitigation.medium_priority_actions) >= 0
    assert mitigation.estimated_mitigation_cost > 0


def test_risk_level_classification(risk_scorer):
    """Test risk level classification."""
    levels = [
        (5, RiskLevel.MINIMAL),
        (20, RiskLevel.LOW),
        (40, RiskLevel.MODERATE),
        (60, RiskLevel.HIGH),
        (85, RiskLevel.CRITICAL),
    ]
    
    for score, expected_level in levels:
        level = risk_scorer._score_to_level(score)
        assert level == expected_level


# ============================================================================
# Strategy Optimizer Tests (6 tests)
# ============================================================================

def test_strategy_optimizer_initialization(strategy_optimizer):
    """Test strategy optimizer initialization."""
    assert strategy_optimizer is not None
    assert len(strategy_optimizer.case_strategies) == 0


def test_motion_strategy_optimization(strategy_optimizer):
    """Test motion strategy optimization."""
    case_features = {
        'case_id': 'test_001',
        'case_type': 'employment',
        'case_strength': 0.65,
    }
    
    motion_strategy = strategy_optimizer.optimize_motion_strategy(case_features)
    
    assert motion_strategy.mtd_recommendation in ['file', 'defer', 'avoid', 'standard']
    assert 0 <= motion_strategy.mtd_success_probability <= 1
    assert len(motion_strategy.mtd_legal_theories) > 0


def test_discovery_plan_optimization(strategy_optimizer):
    """Test discovery plan optimization."""
    case_features = {
        'case_id': 'test_001',
        'case_type': 'contract',
        'complexity': 'moderate',
        'num_parties': 2,
    }
    
    discovery_plan = strategy_optimizer.optimize_discovery_plan(case_features)
    
    assert discovery_plan.scope_breadth in ['narrow', 'standard', 'aggressive']
    assert discovery_plan.discovery_phase_duration_months > 0
    assert discovery_plan.total_discovery_cost_estimate > 0


def test_trial_strategy_optimization(strategy_optimizer):
    """Test trial strategy optimization."""
    case_features = {
        'case_id': 'test_001',
        'case_type': 'tort',
        'case_strength': 0.7,
    }
    
    trial_strategy = strategy_optimizer.recommend_trial_strategy(case_features)
    
    assert trial_strategy.trial_type_recommendation.value in ['bench', 'jury', 'either']
    assert len(trial_strategy.primary_legal_theory) > 0
    assert len(trial_strategy.key_facts_to_emphasize) > 0


def test_appeal_analysis(strategy_optimizer):
    """Test appeal viability analysis."""
    case_features = {
        'case_id': 'test_001',
        'case_type': 'employment',
        'judge_name': 'Judge Smith',
    }
    trial_outcome = {'verdict': 'loss', 'margin': 0.1}
    
    appeal_analysis = strategy_optimizer.analyze_appeal_viability(
        trial_outcome, case_features
    )
    
    assert 0 <= appeal_analysis.appeal_viability_score <= 1
    assert appeal_analysis.appeal_viability_assessment in ['strong', 'moderate', 'weak', 'not viable']
    assert len(appeal_analysis.potential_appeal_grounds) > 0


def test_comprehensive_strategy_optimization(strategy_optimizer):
    """Test comprehensive strategy optimization."""
    case_features = {
        'case_id': 'test_001',
        'case_name': 'Test v. Defendant',
        'case_type': 'employment',
        'case_strength': 0.65,
        'complexity': 'moderate',
    }
    
    strategy = strategy_optimizer.optimize_overall_strategy(case_features)
    
    assert strategy.case_id == 'test_001'
    assert strategy.motion_strategy is not None
    assert strategy.discovery_plan is not None
    assert strategy.trial_strategy is not None
    assert strategy.estimated_total_cost > 0


# ============================================================================
# ML Training Pipeline Tests (5 tests)
# ============================================================================

def test_ml_pipeline_initialization(ml_pipeline):
    """Test ML training pipeline initialization."""
    assert ml_pipeline is not None
    assert len(ml_pipeline.trained_models) == 0


def test_data_ingestion(ml_pipeline):
    """Test data ingestion from CourtListener."""
    data = ml_pipeline.ingest_data('courtlistener', limit=100)
    
    assert isinstance(data, pd.DataFrame)
    assert len(data) > 0
    assert 'case_id' in data.columns
    assert 'outcome' in data.columns


def test_data_cleaning_and_normalization(ml_pipeline, sample_training_data):
    """Test data cleaning and normalization."""
    clean_data = ml_pipeline.clean_and_normalize_data(sample_training_data)
    
    assert clean_data is not None
    assert len(clean_data) > 0
    # Check no NaN values in numeric columns
    assert not clean_data.select_dtypes(include=['number']).isna().any().any()


def test_temporal_train_test_split(ml_pipeline, sample_training_data):
    """Test temporal train/test split."""
    train, test = ml_pipeline.create_train_test_split_temporal(
        sample_training_data, test_fraction=0.2
    )
    
    assert len(train) + len(test) == len(sample_training_data)
    assert len(test) / len(sample_training_data) == pytest.approx(0.2, rel=0.1)


def test_model_training_and_evaluation(ml_pipeline, sample_training_data):
    """Test model training and evaluation."""
    eval_report = ml_pipeline.train_outcome_model(sample_training_data, '1.0')
    
    assert eval_report is not None
    assert '1.0' in ml_pipeline.trained_models
    assert 0 <= eval_report.roc_auc <= 1
    assert len(eval_report.cv_fold_scores) > 0


# ============================================================================
# Integration Tests (3 tests)
# ============================================================================

def test_end_to_end_case_prediction(sample_case_features, sample_training_data):
    """Test end-to-end case prediction workflow."""
    predictor = CaseOutcomePredictor()
    predictor.train(sample_training_data)
    
    prediction = predictor.predict(sample_case_features)
    
    assert isinstance(prediction, CasePrediction)
    assert 0 <= prediction.win_probability <= 1
    assert len(prediction.recommendations) > 0


def test_judge_impact_on_case_prediction(
    judge_analyzer, sample_case_features
):
    """Test how judge profile impacts case prediction."""
    tendency = judge_analyzer.analyze_judge_tendencies(
        'judge_001', 'employment'
    )
    
    assert tendency.plaintiff_win_rate > 0.6  # Judge Mitchell is plaintiff-friendly


def test_settlement_and_appeal_workflow(settlement_calculator, strategy_optimizer):
    """Test settlement valuation and appeal analysis workflow."""
    settlement_range = settlement_calculator.calculate_settlement_value(
        'employment', 'federal', 500000, 0.65
    )
    
    trial_outcome = {'verdict': 'loss'}
    case_features = {'case_id': 'test', 'case_type': 'employment'}
    
    appeal = strategy_optimizer.analyze_appeal_viability(trial_outcome, case_features)
    
    assert settlement_range.likely_estimate > 0
    assert appeal.appeal_viability_score >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
