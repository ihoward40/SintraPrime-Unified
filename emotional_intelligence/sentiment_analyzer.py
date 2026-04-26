"""
Sentiment Analyzer — Real-time emotion and sentiment detection for legal clients.
Uses keyword matching + contextual heuristics. No external API required.
Legal context aware: "I'm going to lose my house" = HIGH distress.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    DISTRESSED = "distressed"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SentimentResult:
    sentiment: SentimentType
    confidence: float  # 0.0 – 1.0
    emotions: Dict[str, float]  # fear, anger, confusion, hope, frustration
    urgency_level: UrgencyLevel
    raw_text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "sentiment": self.sentiment.value,
            "confidence": self.confidence,
            "emotions": self.emotions,
            "urgency_level": self.urgency_level.value,
            "raw_text": self.raw_text[:200],
            "timestamp": self.timestamp.isoformat(),
        }


# ──────────────────────────────────────────────────────────────
# Keyword lexicons (legal-context enriched)
# ──────────────────────────────────────────────────────────────

_FEAR_KEYWORDS = [
    "scared", "afraid", "terrified", "frightened", "worried", "panic",
    "nightmare", "dread", "anxious", "anxiety", "nervous", "lose my house",
    "lose everything", "going to jail", "prison", "arrested", "deported",
    "take my kids", "lose custody", "bankrupt", "sued", "garnish",
]

_ANGER_KEYWORDS = [
    "angry", "furious", "outraged", "livid", "mad", "disgusted", "fed up",
    "ridiculous", "absurd", "unfair", "bullshit", "screw", "hate",
    "incompetent", "useless", "wasted my money", "not helping",
    "terrible", "worst", "fraud", "cheated", "lied", "betrayed",
]

_CONFUSION_KEYWORDS = [
    "confused", "don't understand", "what does", "what is", "explain",
    "clarify", "what does that mean", "lost", "complicated", "unclear",
    "legalese", "jargon", "huh", "what?", "i don't get it", "can you",
    "what happens if", "what should i do", "not sure", "unsure",
    "how does", "why is", "make sense",
]

_HOPE_KEYWORDS = [
    "hope", "hopeful", "optimistic", "better", "things will improve",
    "good chance", "positive", "thankful", "grateful", "appreciate",
    "helpful", "thank you", "great", "excellent", "wonderful",
    "working out", "resolved", "settled", "solution",
]

_FRUSTRATION_KEYWORDS = [
    "frustrated", "tired", "exhausted", "over it", "can't take it",
    "enough", "at my wit", "repeatedly", "again and again", "still waiting",
    "months", "years", "never resolved", "dragging on", "no progress",
    "keeps happening", "stuck", "going in circles",
]

_DISTRESS_PHRASES = [
    "lose my house", "losing my home", "evicted", "homeless",
    "can't feed my kids", "can't eat", "no money", "broke",
    "suicidal", "end it all", "don't want to live", "give up on life",
    "can't go on", "no hope", "nothing left", "desperate",
    "emergency", "immediate help", "right now", "today is the deadline",
    "court tomorrow", "hearing tomorrow", "warrant out", "being deported",
    "taking my children", "restraining order", "domestic violence",
    "abuse", "threatened", "unsafe", "in danger",
]

_POSITIVE_KEYWORDS = [
    "great", "excellent", "wonderful", "amazing", "perfect", "thank",
    "appreciate", "happy", "glad", "pleased", "satisfied", "resolved",
    "good news", "won", "approved", "granted", "accepted",
]

_LEGAL_URGENCY_TRIGGERS = [
    "deadline", "hearing", "court date", "tomorrow", "today", "urgent",
    "emergency", "immediately", "statute of limitations", "runs out",
    "expires", "due date", "time sensitive", "appeal deadline",
    "foreclosure", "eviction notice", "warrant", "arrest",
]


class SentimentAnalyzer:
    """
    Real-time emotion and sentiment detection for legal clients.
    Legal-context aware with no external API dependency.
    """

    def __init__(self):
        self._session_history: Dict[str, List[SentimentResult]] = {}

    # ──────────────────────────────────────────────────────────
    # Core analysis
    # ──────────────────────────────────────────────────────────

    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of input text.
        Returns SentimentResult with sentiment type, confidence,
        per-emotion scores, and urgency level.
        """
        normalized = text.lower()

        emotions = {
            "fear": self._score_keywords(normalized, _FEAR_KEYWORDS),
            "anger": self._score_keywords(normalized, _ANGER_KEYWORDS),
            "confusion": self._score_keywords(normalized, _CONFUSION_KEYWORDS),
            "hope": self._score_keywords(normalized, _HOPE_KEYWORDS),
            "frustration": self._score_keywords(normalized, _FRUSTRATION_KEYWORDS),
        }

        # Determine primary sentiment
        sentiment, confidence = self._classify_sentiment(normalized, emotions)
        urgency = self._assess_urgency(normalized)

        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            emotions=emotions,
            urgency_level=urgency,
            raw_text=text,
        )

    def detect_distress(self, text: str) -> bool:
        """Flags crisis/distress situations."""
        normalized = text.lower()
        for phrase in _DISTRESS_PHRASES:
            if phrase in normalized:
                return True
        # High fear or frustration score also triggers distress
        emotions = {
            "fear": self._score_keywords(normalized, _FEAR_KEYWORDS),
            "frustration": self._score_keywords(normalized, _FRUSTRATION_KEYWORDS),
        }
        return emotions["fear"] > 0.5 or emotions["frustration"] > 0.6

    def detect_confusion(self, text: str) -> bool:
        """Client doesn't understand legal jargon."""
        normalized = text.lower()
        score = self._score_keywords(normalized, _CONFUSION_KEYWORDS)
        return score > 0.25

    def detect_anger(self, text: str) -> bool:
        """Frustrated client needs de-escalation."""
        normalized = text.lower()
        score = self._score_keywords(normalized, _ANGER_KEYWORDS)
        return score > 0.3

    def track_sentiment_trend(
        self, user_id: str, messages: List[str]
    ) -> List[SentimentResult]:
        """Tracks sentiment over a session for a given user."""
        results = [self.analyze(msg) for msg in messages]
        self._session_history[user_id] = results
        return results

    def get_session_trend(self, user_id: str) -> Optional[str]:
        """Summarizes the sentiment trend: improving, declining, stable."""
        history = self._session_history.get(user_id, [])
        if len(history) < 2:
            return "insufficient_data"

        sentiment_scores = {
            SentimentType.POSITIVE: 1.0,
            SentimentType.NEUTRAL: 0.5,
            SentimentType.NEGATIVE: 0.2,
            SentimentType.DISTRESSED: 0.0,
        }

        scores = [sentiment_scores[r.sentiment] for r in history]
        trend = scores[-1] - scores[0]

        if trend > 0.2:
            return "improving"
        elif trend < -0.2:
            return "declining"
        return "stable"

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _score_keywords(self, text: str, keywords: List[str]) -> float:
        """Returns 0.0–1.0 keyword match score."""
        if not text:
            return 0.0
        matches = sum(1 for kw in keywords if kw in text)
        # Normalize: more keywords = higher ceiling, diminishing returns
        raw = min(matches / max(len(keywords) * 0.15, 1), 1.0)
        return round(raw, 4)

    def _classify_sentiment(
        self, text: str, emotions: Dict[str, float]
    ) -> tuple[SentimentType, float]:
        """Classify primary sentiment and confidence score."""
        # Check for distress first (highest priority)
        for phrase in _DISTRESS_PHRASES:
            if phrase in text:
                return SentimentType.DISTRESSED, 0.92

        # High fear → distressed
        if emotions["fear"] > 0.4:
            return SentimentType.DISTRESSED, min(0.6 + emotions["fear"] * 0.4, 0.95)

        # High anger
        if emotions["anger"] > 0.35:
            return SentimentType.NEGATIVE, min(0.55 + emotions["anger"] * 0.45, 0.95)

        # High frustration
        if emotions["frustration"] > 0.35:
            return SentimentType.NEGATIVE, min(0.5 + emotions["frustration"] * 0.4, 0.90)

        # Hope signals positive
        if emotions["hope"] > 0.3:
            pos_score = self._score_keywords(text, _POSITIVE_KEYWORDS)
            return SentimentType.POSITIVE, min(0.55 + pos_score * 0.4, 0.95)

        # Confusion → neutral leaning negative
        if emotions["confusion"] > 0.3:
            return SentimentType.NEUTRAL, 0.60

        # Positive keywords
        pos_score = self._score_keywords(text, _POSITIVE_KEYWORDS)
        if pos_score > 0.2:
            return SentimentType.POSITIVE, min(0.5 + pos_score * 0.5, 0.90)

        return SentimentType.NEUTRAL, 0.55

    def _assess_urgency(self, text: str) -> UrgencyLevel:
        """Assess urgency from text."""
        urgency_score = self._score_keywords(text, _LEGAL_URGENCY_TRIGGERS)
        distress_hit = any(p in text for p in _DISTRESS_PHRASES)

        if distress_hit and urgency_score > 0.3:
            return UrgencyLevel.CRITICAL
        if distress_hit or urgency_score > 0.4:
            return UrgencyLevel.HIGH
        if urgency_score > 0.2:
            return UrgencyLevel.MEDIUM
        return UrgencyLevel.LOW
