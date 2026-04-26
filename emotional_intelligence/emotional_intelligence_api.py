"""
Emotional Intelligence API — FastAPI router for EI layer endpoints.
Exposes sentiment analysis, empathy adaptation, crisis detection,
client health, and jargon simplification via REST API.
"""

from __future__ import annotations

from typing import Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Provide stub classes for environments without FastAPI
    class BaseModel:  # type: ignore
        pass
    def Field(*args, **kwargs):  # type: ignore
        return None
    class APIRouter:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def post(self, *args, **kwargs):
            return lambda f: f
        def get(self, *args, **kwargs):
            return lambda f: f

from .sentiment_analyzer import SentimentAnalyzer
from .empathy_engine import EmpathyEngine
from .crisis_detector import CrisisDetector
from .client_relationship_manager import ClientRelationshipManager
from .response_formatter import ResponseFormatter
from .communication_style_adapter import CommunicationStyleAdapter

# ──────────────────────────────────────────────────────────────
# Service singletons
# ──────────────────────────────────────────────────────────────

_sentiment_analyzer = SentimentAnalyzer()
_empathy_engine = EmpathyEngine()
_crisis_detector = CrisisDetector()
_relationship_manager = ClientRelationshipManager()
_response_formatter = ResponseFormatter()
_style_adapter = CommunicationStyleAdapter()

# ──────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze")
    user_id: Optional[str] = Field(None, description="User ID for session tracking")


class AnalyzeResponse(BaseModel):
    sentiment: str
    confidence: float
    emotions: Dict[str, float]
    urgency_level: str
    distress_detected: bool
    confusion_detected: bool
    anger_detected: bool


class AdaptResponseRequest(BaseModel):
    original_response: str = Field(..., description="The original response to adapt")
    text: str = Field(..., description="The client's input text (used for sentiment)")
    situation_type: Optional[str] = Field(None, description="Situation type: divorce, eviction, debt, criminal, estate")


class AdaptResponseResponse(BaseModel):
    adapted_response: str
    sentiment: str
    empathy_injected: bool


class CrisisCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    user_id: Optional[str] = Field(None)


class CrisisCheckResponse(BaseModel):
    crisis_types: List[str]
    crisis_level: str
    requires_human_review: bool
    crisis_response: str
    resources: List[Dict]


class SimplifyRequest(BaseModel):
    text: str = Field(..., description="Legal text to simplify")
    target_reading_grade: Optional[int] = Field(8, ge=1, le=18)


class SimplifyResponse(BaseModel):
    original: str
    simplified: str
    jargon_replaced: bool


class ClientHealthResponse(BaseModel):
    user_id: str
    satisfaction: float
    engagement: str
    trust_score: float
    interaction_frequency: float
    unresolved_issues: int
    sentiment_trend: str
    retention_risk: float
    last_interaction: Optional[str]


class ResourceResponse(BaseModel):
    crisis_type: str
    jurisdiction: str
    resources: List[Dict]


# ──────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────

router = APIRouter(prefix="/ei", tags=["Emotional Intelligence"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_sentiment(request: AnalyzeRequest):
    """
    Analyze the sentiment and emotional state of client text.
    Returns: sentiment, confidence, per-emotion scores, urgency, and crisis flags.
    """
    result = _sentiment_analyzer.analyze(request.text)

    if request.user_id:
        _sentiment_analyzer.track_sentiment_trend(
            request.user_id, [request.text]
        )

    return AnalyzeResponse(
        sentiment=result.sentiment.value,
        confidence=result.confidence,
        emotions=result.emotions,
        urgency_level=result.urgency_level.value,
        distress_detected=_sentiment_analyzer.detect_distress(request.text),
        confusion_detected=_sentiment_analyzer.detect_confusion(request.text),
        anger_detected=_sentiment_analyzer.detect_anger(request.text),
    )


@router.post("/adapt-response", response_model=AdaptResponseResponse)
async def adapt_response(request: AdaptResponseRequest):
    """
    Adapt an existing response with empathy based on detected client sentiment.
    Validates feelings before providing information — Pi AI style.
    """
    sentiment = _sentiment_analyzer.analyze(request.text)
    adapted = _empathy_engine.adapt_response(request.original_response, sentiment)

    # Add situation-specific empathy if provided
    if request.situation_type:
        situation_empathy = _empathy_engine.get_situation_empathy(request.situation_type)
        if situation_empathy not in adapted:
            adapted = situation_empathy + "\n\n" + adapted

    empathy_injected = adapted != request.original_response

    return AdaptResponseResponse(
        adapted_response=adapted,
        sentiment=sentiment.sentiment.value,
        empathy_injected=empathy_injected,
    )


@router.post("/crisis-check", response_model=CrisisCheckResponse)
async def crisis_check(request: CrisisCheckRequest):
    """
    Check text for crisis indicators.
    Flags domestic violence, mental health concerns, housing crises, and legal emergencies.
    Always refers to emergency services for immediate danger.
    """
    assessment = _crisis_detector.assess(request.text)
    crisis_response = _crisis_detector.generate_crisis_response(assessment)

    if request.user_id and assessment.requires_human_review:
        _crisis_detector.flag_for_human_review(request.user_id, assessment)

    # Get resources for all detected crisis types
    all_resources = []
    for crisis_type in assessment.crisis_types:
        if crisis_type.value != "none":
            resources = _crisis_detector.get_resources(crisis_type.value)
            for r in resources:
                all_resources.append({
                    "name": r.name,
                    "phone": r.phone,
                    "url": r.url,
                    "description": r.description,
                    "available_24_7": r.available_24_7,
                })

    return CrisisCheckResponse(
        crisis_types=[ct.value for ct in assessment.crisis_types],
        crisis_level=assessment.level.value,
        requires_human_review=assessment.requires_human_review,
        crisis_response=crisis_response,
        resources=all_resources,
    )


@router.get("/client/{user_id}/health", response_model=ClientHealthResponse)
async def get_client_health(user_id: str):
    """
    Get relationship health metrics for a client.
    Returns: satisfaction, engagement, trust score, retention risk, and sentiment trend.
    """
    health = _relationship_manager.get_relationship_health(user_id)
    risk = _relationship_manager.retention_risk(user_id)

    return ClientHealthResponse(
        user_id=user_id,
        satisfaction=health.satisfaction,
        engagement=health.engagement.value,
        trust_score=health.trust_score,
        interaction_frequency=health.interaction_frequency,
        unresolved_issues=health.unresolved_issues,
        sentiment_trend=health.sentiment_trend,
        retention_risk=risk,
        last_interaction=(
            health.last_interaction.isoformat() if health.last_interaction else None
        ),
    )


@router.post("/simplify", response_model=SimplifyResponse)
async def simplify_legal_text(request: SimplifyRequest):
    """
    Simplify legal jargon into plain English.
    Optionally targets a specific reading grade level.
    """
    simplified = _empathy_engine.simplify_jargon(request.text)

    if request.target_reading_grade and request.target_reading_grade <= 9:
        simplified = _style_adapter.adjust_reading_level(
            simplified, request.target_reading_grade
        )

    return SimplifyResponse(
        original=request.text,
        simplified=simplified,
        jargon_replaced=simplified != request.text,
    )


@router.get("/resources/{crisis_type}/{jurisdiction}", response_model=ResourceResponse)
async def get_crisis_resources(crisis_type: str, jurisdiction: str):
    """
    Get crisis resources for a specific crisis type and jurisdiction.
    Returns: hotlines, legal aid organizations, shelters, and support services.
    """
    resources = _crisis_detector.get_resources(crisis_type, jurisdiction)

    return ResourceResponse(
        crisis_type=crisis_type,
        jurisdiction=jurisdiction,
        resources=[
            {
                "name": r.name,
                "phone": r.phone,
                "url": r.url,
                "description": r.description,
                "available_24_7": r.available_24_7,
            }
            for r in resources
        ],
    )


def get_router() -> APIRouter:
    """Returns the FastAPI router for registration in the main app."""
    return router
