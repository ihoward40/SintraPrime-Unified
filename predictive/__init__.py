"""
SintraPrime-Unified Predictive ML System

Comprehensive machine learning system for legal case outcome prediction,
settlement valuation, judicial intelligence, risk assessment, and litigation strategy optimization.
"""

from .outcome_predictor import (
    CaseOutcomePredictor,
    CasePrediction,
    CaseFeatures,
    PredictionExplanation,
    ScenarioComparison,
    ModelMetrics,
)

from .judge_analyzer import (
    JudgeAnalyzer,
    JudgeProfile,
    TendencyReport,
    StrategyRecommendations,
    JudgeComparison,
)

from .settlement_calculator import (
    SettlementCalculator,
    SettlementRange,
    NPVAnalysis,
    ComparableVerdict,
    NegotiationStrategy,
)

from .legal_risk_scorer import (
    LegalRiskScorer,
    RiskProfile,
    RiskScore,
    MitigationPlan,
    RiskDimension,
)

from .case_strategy_optimizer import (
    CaseStrategyOptimizer,
    StrategyReport,
    MotionStrategy,
    DiscoveryPlan,
    TrialStrategy,
    AppealAnalysis,
)

from .ml_training_pipeline import (
    MLTrainingPipeline,
    ModelRegistry,
    DriftReport,
    EvalReport,
)

__version__ = "1.0.0"
__author__ = "SintraPrime Legal AI"

__all__ = [
    # Outcome Predictor
    "CaseOutcomePredictor",
    "CasePrediction",
    "CaseFeatures",
    "PredictionExplanation",
    "ScenarioComparison",
    "ModelMetrics",
    # Judge Analyzer
    "JudgeAnalyzer",
    "JudgeProfile",
    "TendencyReport",
    "StrategyRecommendations",
    "JudgeComparison",
    # Settlement Calculator
    "SettlementCalculator",
    "SettlementRange",
    "NPVAnalysis",
    "ComparableVerdict",
    "NegotiationStrategy",
    # Risk Scorer
    "LegalRiskScorer",
    "RiskProfile",
    "RiskScore",
    "MitigationPlan",
    "RiskDimension",
    # Strategy Optimizer
    "CaseStrategyOptimizer",
    "StrategyReport",
    "MotionStrategy",
    "DiscoveryPlan",
    "TrialStrategy",
    "AppealAnalysis",
    # ML Training
    "MLTrainingPipeline",
    "ModelRegistry",
    "DriftReport",
    "EvalReport",
]
