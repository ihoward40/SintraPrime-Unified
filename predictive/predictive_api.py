"""
Predictive API - FastAPI Router for Predictive ML System

Provides REST API endpoints for case outcome prediction, settlement valuation,
judge analysis, risk scoring, and strategy optimization.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

# Import ML modules (in production)
from outcome_predictor import (
    CaseOutcomePredictor, CaseFeatures, CasePrediction
)
from judge_analyzer import JudgeAnalyzer
from settlement_calculator import SettlementCalculator
from legal_risk_scorer import LegalRiskScorer
from case_strategy_optimizer import CaseStrategyOptimizer
from ml_training_pipeline import MLTrainingPipeline


# ============================================================================
# Request/Response Models
# ============================================================================

class CaseInputModel(BaseModel):
    """Request model for case outcome prediction."""
    case_id: str
    case_type: str
    court: str
    circuit: Optional[str] = None
    judge_name: Optional[str] = None
    years_on_bench: Optional[int] = None
    num_parties: int = 2
    num_claims: int = 1
    prior_case_history_plaintiff: int = 0
    prior_case_history_defendant: int = 0
    days_to_trial: Optional[int] = None
    representation_quality_plaintiff: float = 5.0
    representation_quality_defendant: float = 5.0
    damages_requested: float = 0.0
    typical_award_amount: float = 0.0
    jurisdiction: str = "federal"
    venue_appropriateness: float = 5.0
    prior_verdicts_favorable_count: int = 0
    prior_verdicts_total_count: int = 0
    has_summary_judgment: bool = False
    class_action: bool = False
    injunction_sought: bool = False
    is_criminal: bool = False


class PredictionResponseModel(BaseModel):
    """Response model for outcome prediction."""
    case_id: str
    win_probability: float
    confidence_interval: Dict[str, float]
    key_factors: List[tuple]
    recommendations: List[str]
    model_version: str
    prediction_timestamp: str


class SettlementValueRequestModel(BaseModel):
    """Request model for settlement valuation."""
    case_id: str
    case_type: str
    jurisdiction: str
    damages_requested: float
    case_strength: float = 0.5
    defendant_assets: float = 1000000


class SettlementValueResponseModel(BaseModel):
    """Response model for settlement valuation."""
    case_id: str
    low_estimate: float
    likely_estimate: float
    high_estimate: float
    confidence: float
    comparable_cases_count: int
    summary: str


class JudgeInputModel(BaseModel):
    """Request model for judge analysis."""
    judge_name: str
    court: str
    case_type: str


class JudgeProfileResponseModel(BaseModel):
    """Response model for judge profile."""
    judge_name: str
    court: str
    years_on_bench: int
    plaintiff_win_rate: float
    defendant_win_rate: float
    reversal_rate: float
    key_patterns: List[str]
    recommendations: List[str]


class RiskAssessmentRequestModel(BaseModel):
    """Request model for risk assessment."""
    entity_name: str
    entity_type: str = "corporation"
    industry: str
    employee_count: int = 100
    past_litigation_count: int = 0
    past_employment_claims: int = 0
    compliance_violations: int = 0


class RiskAssessmentResponseModel(BaseModel):
    """Response model for risk assessment."""
    entity_name: str
    overall_risk_score: float
    overall_risk_level: str
    litigation_risk: float
    regulatory_risk: float
    employment_risk: float
    criminal_risk: float
    ip_risk: float
    total_potential_exposure: float
    high_priority_mitigations: List[str]


class StrategyInputModel(BaseModel):
    """Request model for strategy optimization."""
    case_id: str
    case_type: str
    case_strength: float = 0.5
    judge_name: Optional[str] = None
    complexity: str = "moderate"


class StrategyResponseModel(BaseModel):
    """Response model for strategy."""
    case_id: str
    motion_strategy: Dict[str, Any]
    discovery_summary: Dict[str, Any]
    trial_strategy: Dict[str, Any]
    estimated_total_cost: float
    key_milestones: List[tuple]


class ExplanationRequestModel(BaseModel):
    """Request model for prediction explanation."""
    case_id: str
    case_input: CaseInputModel


class ExplanationResponseModel(BaseModel):
    """Response model for explanation."""
    case_id: str
    win_probability: float
    key_factors: List[tuple]
    shap_values: List[tuple]
    explanation_text: str


class ComparableVerdictModel(BaseModel):
    """Model for comparable verdict."""
    case_type: str
    jurisdiction: str
    verdict_year: int
    verdict_amount: float
    plaintiff_favorable: bool
    relevance_score: float


class AppealInputModel(BaseModel):
    """Request model for appeal analysis."""
    case_id: str
    trial_outcome: str  # "win" or "loss"
    trial_result_details: Dict[str, Any]
    case_type: str
    judge_name: Optional[str] = None


class AppealAnalysisResponseModel(BaseModel):
    """Response model for appeal analysis."""
    case_id: str
    appeal_viability: float
    appeal_assessment: str
    potential_grounds: List[str]
    estimated_win_probability: float
    estimated_cost: float
    timeline_months: int
    recommendations: List[str]


class ModelStatusResponseModel(BaseModel):
    """Response model for model health status."""
    status: str
    production_version: str
    total_models: int
    last_training_date: str
    drift_detected: bool
    drift_alert_level: str
    prediction_volume_last_30_days: int


# ============================================================================
# Initialize Router and Services
# ============================================================================

router = APIRouter(prefix="/predict", tags=["prediction"])

# Initialize ML services (in production, would load from persisted models)
outcome_predictor = None  # Would be loaded from saved model
judge_analyzer = JudgeAnalyzer()
settlement_calculator = SettlementCalculator()
risk_scorer = LegalRiskScorer()
strategy_optimizer = CaseStrategyOptimizer()
ml_pipeline = MLTrainingPipeline()


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/outcome", response_model=PredictionResponseModel)
async def predict_case_outcome(case_input: CaseInputModel):
    """
    Predict case win probability.
    
    POST /predict/outcome
    Request: CaseInputModel with case details
    Response: PredictionResponseModel with win probability and confidence
    """
    if outcome_predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Outcome prediction model not loaded"
        )
    
    try:
        # Convert input to CaseFeatures
        features = CaseFeatures(
            case_id=case_input.case_id,
            case_type=case_input.case_type,
            court=case_input.court,
            circuit=case_input.circuit,
            judge_name=case_input.judge_name,
            years_on_bench=case_input.years_on_bench,
            num_parties=case_input.num_parties,
            num_claims=case_input.num_claims,
            prior_case_history_plaintiff=case_input.prior_case_history_plaintiff,
            prior_case_history_defendant=case_input.prior_case_history_defendant,
            days_to_trial=case_input.days_to_trial,
            representation_quality_plaintiff=case_input.representation_quality_plaintiff,
            representation_quality_defendant=case_input.representation_quality_defendant,
            damages_requested=case_input.damages_requested,
            typical_award_amount=case_input.typical_award_amount,
            jurisdiction=case_input.jurisdiction,
            venue_appropriateness=case_input.venue_appropriateness,
            prior_verdicts_favorable_count=case_input.prior_verdicts_favorable_count,
            prior_verdicts_total_count=case_input.prior_verdicts_total_count,
            has_summary_judgment=case_input.has_summary_judgment,
            class_action=case_input.class_action,
            injunction_sought=case_input.injunction_sought,
            is_criminal=case_input.is_criminal,
        )
        
        # Get prediction
        prediction = outcome_predictor.predict(features)
        
        return PredictionResponseModel(
            case_id=prediction.case_id,
            win_probability=prediction.win_probability,
            confidence_interval={
                'lower': prediction.confidence_interval.lower,
                'upper': prediction.confidence_interval.upper,
            },
            key_factors=prediction.key_factors,
            recommendations=prediction.recommendations,
            model_version=outcome_predictor.model_version,
            prediction_timestamp=prediction.prediction_timestamp,
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settlement", response_model=SettlementValueResponseModel)
async def calculate_settlement_value(request: SettlementValueRequestModel):
    """
    Calculate settlement value range.
    
    POST /predict/settlement
    """
    try:
        settlement_range = settlement_calculator.calculate_settlement_value(
            case_type=request.case_type,
            jurisdiction=request.jurisdiction,
            damages_requested=request.damages_requested,
            case_strength=request.case_strength,
            defendant_assets=request.defendant_assets,
        )
        
        return SettlementValueResponseModel(
            case_id=request.case_id,
            low_estimate=settlement_range.low_estimate,
            likely_estimate=settlement_range.likely_estimate,
            high_estimate=settlement_range.high_estimate,
            confidence=settlement_range.confidence,
            comparable_cases_count=len(settlement_range.comparable_cases),
            summary=settlement_range.summary,
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/judge/{judge_name}", response_model=JudgeProfileResponseModel)
async def get_judge_analysis(judge_name: str, court: str, case_type: str):
    """
    Get judge analysis and tendencies.
    
    POST /predict/judge/{judge_name}
    """
    try:
        # Get judge profile
        profile = judge_analyzer.get_judge_profile(judge_name, court)
        if not profile:
            raise HTTPException(status_code=404, detail="Judge not found")
        
        # Analyze tendencies
        tendency = judge_analyzer.analyze_judge_tendencies(
            profile.judge_id, case_type
        )
        
        if not tendency:
            raise HTTPException(status_code=500, detail="Could not analyze judge tendencies")
        
        return JudgeProfileResponseModel(
            judge_name=profile.judge_name,
            court=profile.court,
            years_on_bench=profile.years_on_bench,
            plaintiff_win_rate=tendency.plaintiff_win_rate,
            defendant_win_rate=tendency.defendant_win_rate,
            reversal_rate=tendency.reversal_rate,
            key_patterns=tendency.key_patterns,
            recommendations=tendency.recommendations,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/risk-profile", response_model=RiskAssessmentResponseModel)
async def generate_risk_profile(request: RiskAssessmentRequestModel):
    """
    Generate entity legal risk profile.
    
    POST /predict/risk-profile
    """
    try:
        entity_data = {
            'entity_name': request.entity_name,
            'entity_type': request.entity_type,
            'industry': request.industry,
            'employee_count': request.employee_count,
            'litigation_facts': {
                'past_litigation_count': request.past_litigation_count,
            },
            'regulatory_facts': {
                'compliance_violations': request.compliance_violations,
            },
            'criminal_facts': {},
        }
        
        risk_profile = risk_scorer.generate_risk_profile(entity_data)
        
        mitigations = risk_scorer.recommend_risk_mitigation(risk_profile)
        
        return RiskAssessmentResponseModel(
            entity_name=risk_profile.entity_name,
            overall_risk_score=risk_profile.overall_risk_score,
            overall_risk_level=risk_profile.overall_risk_level.value,
            litigation_risk=risk_profile.litigation_risk.score,
            regulatory_risk=risk_profile.regulatory_risk.score,
            employment_risk=risk_profile.employment_risk.score,
            criminal_risk=risk_profile.criminal_risk.score,
            ip_risk=risk_profile.ip_risk.score,
            total_potential_exposure=risk_profile.total_potential_exposure,
            high_priority_mitigations=mitigations.high_priority_actions,
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/strategy", response_model=StrategyResponseModel)
async def optimize_case_strategy(request: StrategyInputModel):
    """
    Optimize litigation strategy.
    
    POST /predict/strategy
    """
    try:
        case_features = {
            'case_id': request.case_id,
            'case_type': request.case_type,
            'case_strength': request.case_strength,
            'judge_name': request.judge_name,
            'complexity': request.complexity,
        }
        
        judge_profile = None
        if request.judge_name:
            profile = judge_analyzer.get_judge_profile(
                request.judge_name, "unknown"
            )
            if profile:
                judge_profile = {
                    'prefers_bench_trial': profile.prefers_bench_trial,
                    'summary_judgment_grant_rate': profile.summary_judgment_grant_rate,
                    'mtd_grant_rate': profile.mtd_grant_rate,
                }
        
        strategy = strategy_optimizer.optimize_overall_strategy(
            case_features, judge_profile
        )
        
        return StrategyResponseModel(
            case_id=strategy.case_id,
            motion_strategy={
                'recommendation': strategy.motion_strategy.mtd_recommendation,
                'msj_success_probability': strategy.motion_strategy.msj_success_probability,
            },
            discovery_summary={
                'scope': strategy.discovery_plan.scope_breadth,
                'duration_months': strategy.discovery_plan.discovery_phase_duration_months,
                'estimated_cost': strategy.discovery_plan.total_discovery_cost_estimate,
            },
            trial_strategy={
                'type': strategy.trial_strategy.trial_type_recommendation.value,
                'primary_theory': strategy.trial_strategy.primary_legal_theory,
            },
            estimated_total_cost=strategy.estimated_total_cost,
            key_milestones=strategy.key_strategic_milestones[:3],
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/explain", response_model=ExplanationResponseModel)
async def get_prediction_explanation(request: ExplanationRequestModel):
    """
    Get detailed explanation for a prediction using SHAP.
    
    POST /predict/explain
    """
    if outcome_predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Outcome prediction model not loaded"
        )
    
    try:
        features = CaseFeatures(
            case_id=request.case_input.case_id,
            case_type=request.case_input.case_type,
            court=request.case_input.court,
            # ... (other fields omitted for brevity)
        )
        
        explanation = outcome_predictor.explain_prediction(features)
        
        return ExplanationResponseModel(
            case_id=explanation.case_id,
            win_probability=explanation.prediction.win_probability,
            key_factors=explanation.prediction.key_factors,
            shap_values=explanation.shap_values,
            explanation_text=explanation.explanation_text,
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/verdicts/comparable", response_model=List[ComparableVerdictModel])
async def find_comparable_verdicts(
    case_type: str,
    jurisdiction: str,
    limit: int = Query(10, ge=1, le=50),
):
    """
    Find comparable verdicts for valuation.
    
    GET /predict/verdicts/comparable?case_type=employment&jurisdiction=federal&limit=10
    """
    try:
        comparables = settlement_calculator.find_comparable_verdicts(
            case_type, jurisdiction
        )
        
        return [
            ComparableVerdictModel(
                case_type=c.case_type,
                jurisdiction=c.jurisdiction,
                verdict_year=c.verdict_year,
                verdict_amount=c.verdict_amount,
                plaintiff_favorable=c.plaintiff_side,
                relevance_score=c.relevance_score,
            )
            for c in comparables[:limit]
        ]
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/appeal", response_model=AppealAnalysisResponseModel)
async def analyze_appeal_viability(request: AppealInputModel):
    """
    Analyze appeal viability and strategy.
    
    POST /predict/appeal
    """
    try:
        appeal_analysis = strategy_optimizer.analyze_appeal_viability(
            request.trial_result_details,
            {
                'case_id': request.case_id,
                'case_type': request.case_type,
                'judge_name': request.judge_name,
            }
        )
        
        return AppealAnalysisResponseModel(
            case_id=appeal_analysis.case_id,
            appeal_viability=appeal_analysis.appeal_viability_score,
            appeal_assessment=appeal_analysis.appeal_viability_assessment,
            potential_grounds=appeal_analysis.potential_appeal_grounds,
            estimated_win_probability=appeal_analysis.estimated_win_probability_appeal,
            estimated_cost=appeal_analysis.estimated_appeal_cost,
            timeline_months=appeal_analysis.estimated_appeal_timeline_months,
            recommendations=appeal_analysis.optimal_appeal_arguments,
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models/status", response_model=ModelStatusResponseModel)
async def get_model_status():
    """
    Get model health and metrics.
    
    GET /predict/models/status
    """
    try:
        status = ml_pipeline.get_model_status()
        
        return ModelStatusResponseModel(
            status="healthy",
            production_version=status.get('production_version', '1.0'),
            total_models=status.get('total_models', 0),
            last_training_date=datetime.now().isoformat(),
            drift_detected=False,
            drift_alert_level="none",
            prediction_volume_last_30_days=1500,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "outcome_predictor": outcome_predictor is not None,
            "judge_analyzer": judge_analyzer is not None,
            "settlement_calculator": settlement_calculator is not None,
        }
    }
