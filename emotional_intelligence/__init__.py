"""
Emotional Intelligence + Client Relationship Layer for SintraPrime-Unified
Pi AI-inspired empathetic dialogue and human-centered legal AI design.

Legal clients are often stressed, scared, and confused — SintraPrime responds
with empathy, not just information.
"""

from .sentiment_analyzer import SentimentAnalyzer, SentimentResult
from .empathy_engine import EmpathyEngine
from .communication_style_adapter import CommunicationStyleAdapter, CommunicationStyle
from .client_relationship_manager import ClientRelationshipManager
from .crisis_detector import CrisisDetector, CrisisAssessment, CrisisLevel
from .response_formatter import ResponseFormatter

__all__ = [
    "EmotionalIntelligence",
    "SentimentAnalyzer",
    "SentimentResult",
    "EmpathyEngine",
    "CommunicationStyleAdapter",
    "CommunicationStyle",
    "ClientRelationshipManager",
    "CrisisDetector",
    "CrisisAssessment",
    "CrisisLevel",
    "ResponseFormatter",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"
__description__ = "Emotional Intelligence Layer — Empathy meets legal excellence"


class EmotionalIntelligence:
    """
    Master orchestrator for the emotional intelligence layer.
    Combines sentiment analysis, empathy engine, crisis detection,
    and client relationship management into a unified interface.
    """

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.empathy_engine = EmpathyEngine()
        self.style_adapter = CommunicationStyleAdapter()
        self.crisis_detector = CrisisDetector()
        self.relationship_manager = ClientRelationshipManager()
        self.response_formatter = ResponseFormatter()

    def process(self, text: str, user_id: str, original_response: str = "") -> dict:
        """
        Full emotional intelligence pipeline:
        1. Analyze sentiment
        2. Detect crisis
        3. Adapt response with empathy
        4. Format appropriately
        Returns enriched response dict.
        """
        sentiment = self.sentiment_analyzer.analyze(text)
        crisis = self.crisis_detector.assess(text)
        crisis_level = self.crisis_detector.crisis_level(crisis)

        adapted_response = original_response
        if original_response:
            adapted_response = self.empathy_engine.adapt_response(
                original_response, sentiment
            )

        return {
            "sentiment": sentiment,
            "crisis_assessment": crisis,
            "crisis_level": crisis_level.value,
            "adapted_response": adapted_response,
            "user_id": user_id,
        }
