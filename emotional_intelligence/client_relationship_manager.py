"""
Client Relationship Manager — Long-term client relationship tracking and nurturing.
Celebrates milestones, tracks health, and builds lasting trust with legal clients.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class EngagementLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INACTIVE = "inactive"


@dataclass
class Interaction:
    timestamp: datetime
    message: str
    sentiment_score: float  # -1.0 to 1.0
    topic: str = ""
    resolved: bool = False


@dataclass
class ClientProfile:
    user_id: str
    first_name: str
    last_name: str
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    matters: List[str] = field(default_factory=list)
    intake_date: datetime = field(default_factory=datetime.utcnow)
    interactions: List[Interaction] = field(default_factory=list)
    milestones: List[str] = field(default_factory=list)
    satisfaction_scores: List[float] = field(default_factory=list)
    referral_source: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.preferred_name or self.first_name

    @property
    def days_since_intake(self) -> int:
        return (datetime.utcnow() - self.intake_date).days

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "matters": self.matters,
            "intake_date": self.intake_date.isoformat(),
            "interaction_count": len(self.interactions),
            "milestone_count": len(self.milestones),
            "days_since_intake": self.days_since_intake,
        }


@dataclass
class RelationshipHealth:
    satisfaction: float  # 0.0 – 1.0
    engagement: EngagementLevel
    trust_score: float  # 0.0 – 1.0
    interaction_frequency: float  # interactions/week
    unresolved_issues: int
    sentiment_trend: str  # improving, stable, declining
    last_interaction: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "satisfaction": round(self.satisfaction, 3),
            "engagement": self.engagement.value,
            "trust_score": round(self.trust_score, 3),
            "interaction_frequency": round(self.interaction_frequency, 2),
            "unresolved_issues": self.unresolved_issues,
            "sentiment_trend": self.sentiment_trend,
            "last_interaction": (
                self.last_interaction.isoformat() if self.last_interaction else None
            ),
        }


# ──────────────────────────────────────────────────────────────
# Message templates
# ──────────────────────────────────────────────────────────────

_TOUCHPOINT_MESSAGES = [
    "Hi {name}, I wanted to check in and see how you're doing. Is there anything I can help clarify or move forward on?",
    "Hello {name}, just checking in! We haven't connected in a little while. How are you holding up?",
    "Hi {name}, I hope things are going well. If you have any questions or updates on your matter, I'm here.",
    "{name}, it's been a bit since we last spoke. I wanted to reach out and make sure you have everything you need.",
    "Good to hear from you, {name}! Let me know if there's anything I can do to support you right now.",
]

_MILESTONE_MESSAGES = {
    "first_consultation": [
        "Congratulations on taking that first step, {name}. Seeking help takes courage, and I'm glad you did.",
        "Today you took an important step, {name}. I'm honored to be part of your journey.",
    ],
    "document_submitted": [
        "Great work, {name}! Your documents have been submitted. This is a meaningful step forward.",
        "That's a big accomplishment, {name} — the paperwork is done. Now we wait, and I'll keep you updated.",
    ],
    "hearing_completed": [
        "You did it, {name}. The hearing is behind you. No matter the outcome, you showed up and that matters.",
        "The hearing is complete, {name}. That took real courage. We'll review the outcome together.",
    ],
    "case_resolved": [
        "Your case has been resolved, {name}. I hope you can take a moment to breathe — you made it through.",
        "Congratulations on reaching resolution, {name}. This has been a journey, and you persevered.",
    ],
    "settlement_reached": [
        "A settlement has been reached, {name}. That's a real achievement — closure is within reach.",
        "Wonderful news, {name}! A settlement means you can begin to move forward.",
    ],
    "custody_secured": [
        "Your children are with you, {name}. That's everything. Take a moment to appreciate this victory.",
        "The custody order is in place, {name}. Your family is more secure now — you fought hard for this.",
    ],
    "bankruptcy_discharged": [
        "Your discharge is complete, {name}. This is your fresh start — the one you've been working toward.",
        "Congratulations, {name}. Your financial slate has been wiped clean. The next chapter starts today.",
    ],
}

_ANNIVERSARY_MESSAGES = [
    "Hi {name}, it's been {months} months since we first connected. I want you to know how much I appreciate your trust.",
    "{name}, one year ago today you reached out for help. A lot has happened since then — I hope you're in a better place.",
    "This month marks {months} months of working together, {name}. Thank you for letting me be part of your journey.",
]

_REFERRAL_REQUEST_MESSAGES = [
    "Hi {name}, I'm so glad we've been able to help you through this. If you know anyone who could benefit from our services, we'd be honored to help them too.",
    "{name}, your journey has been remarkable. If you ever want to share your experience with a friend or family member who needs legal support, we're always here.",
    "I hope everything continues to go well for you, {name}. If someone in your life ever needs legal guidance, please don't hesitate to refer them — it would mean a lot.",
]

_SATISFACTION_SURVEY_MESSAGES = [
    "Hi {name}, we want to make sure we're serving you as well as possible. Would you take a moment to share how we're doing?",
    "{name}, your feedback means everything to us. On a scale from 1-10, how would you rate your experience with SintraPrime so far?",
    "Hi {name}, quick question — is there anything we could do better or anything you've found especially helpful?",
]


class ClientRelationshipManager:
    """
    Long-term client relationship tracking, milestone recognition,
    and proactive touchpoints for legal clients.
    """

    def __init__(self):
        self._profiles: Dict[str, ClientProfile] = {}

    def onboard_client(
        self, user_id: str, intake_data: Dict[str, Any]
    ) -> ClientProfile:
        """Creates a new client profile from intake data."""
        profile = ClientProfile(
            user_id=user_id,
            first_name=intake_data.get("first_name", ""),
            last_name=intake_data.get("last_name", ""),
            preferred_name=intake_data.get("preferred_name"),
            email=intake_data.get("email"),
            matters=intake_data.get("matters", []),
            referral_source=intake_data.get("referral_source"),
            tags=intake_data.get("tags", []),
        )
        self._profiles[user_id] = profile
        return profile

    def update_relationship(
        self, user_id: str, interaction: Interaction
    ) -> Optional[ClientProfile]:
        """Records a new interaction for the client."""
        profile = self._profiles.get(user_id)
        if not profile:
            return None
        profile.interactions.append(interaction)
        return profile

    def get_relationship_health(self, user_id: str) -> RelationshipHealth:
        """
        Calculates relationship health metrics.
        Returns satisfaction, engagement, trust score, and trends.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return RelationshipHealth(
                satisfaction=0.5,
                engagement=EngagementLevel.LOW,
                trust_score=0.5,
                interaction_frequency=0.0,
                unresolved_issues=0,
                sentiment_trend="unknown",
            )

        interactions = profile.interactions
        satisfaction_scores = profile.satisfaction_scores

        # Satisfaction from survey scores
        satisfaction = (
            sum(satisfaction_scores) / len(satisfaction_scores) / 10
            if satisfaction_scores
            else 0.65
        )

        # Engagement from interaction frequency
        if profile.days_since_intake > 0:
            interactions_per_week = len(interactions) / (profile.days_since_intake / 7)
        else:
            interactions_per_week = 0.0

        if interactions_per_week >= 3:
            engagement = EngagementLevel.HIGH
        elif interactions_per_week >= 1:
            engagement = EngagementLevel.MEDIUM
        elif interactions_per_week > 0:
            engagement = EngagementLevel.LOW
        else:
            engagement = EngagementLevel.INACTIVE

        # Trust score: composite of satisfaction + interaction volume + resolved issues
        resolved = sum(1 for i in interactions if i.resolved)
        resolution_rate = resolved / len(interactions) if interactions else 0.5
        trust_score = min(0.4 * satisfaction + 0.3 * resolution_rate + 0.3 * min(len(interactions) / 20, 1), 1.0)

        # Unresolved issues
        unresolved = sum(1 for i in interactions if not i.resolved)

        # Sentiment trend
        if len(interactions) >= 3:
            recent = interactions[-3:]
            older = interactions[:-3]
            recent_avg = sum(i.sentiment_score for i in recent) / len(recent)
            older_avg = sum(i.sentiment_score for i in older) / len(older) if older else recent_avg
            diff = recent_avg - older_avg
            if diff > 0.15:
                trend = "improving"
            elif diff < -0.15:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        last = interactions[-1].timestamp if interactions else None

        return RelationshipHealth(
            satisfaction=satisfaction,
            engagement=engagement,
            trust_score=trust_score,
            interaction_frequency=interactions_per_week,
            unresolved_issues=unresolved,
            sentiment_trend=trend,
            last_interaction=last,
        )

    def generate_touchpoint(self, user_id: str) -> str:
        """Generates a personalized check-in message."""
        profile = self._profiles.get(user_id)
        name = profile.display_name if profile else "there"
        template = random.choice(_TOUCHPOINT_MESSAGES)
        return template.format(name=name)

    def milestone_acknowledgment(self, user_id: str, milestone: str) -> str:
        """Celebrates a client milestone."""
        profile = self._profiles.get(user_id)
        name = profile.display_name if profile else "there"

        if profile:
            profile.milestones.append(milestone)

        messages = _MILESTONE_MESSAGES.get(milestone, [
            f"Congratulations on reaching this milestone, {name}. This is meaningful progress.",
            f"You've made it to another important step, {name}. Keep going.",
        ])
        return random.choice(messages).format(name=name)

    def anniversary_message(self, user_id: str) -> str:
        """Generates a relationship anniversary message."""
        profile = self._profiles.get(user_id)
        if not profile:
            return "Thank you for being a valued client."

        months = profile.days_since_intake // 30
        name = profile.display_name
        template = random.choice(_ANNIVERSARY_MESSAGES)
        return template.format(name=name, months=months)

    def referral_request(self, user_id: str) -> str:
        """Generates a referral request when appropriate."""
        profile = self._profiles.get(user_id)
        name = profile.display_name if profile else "there"
        template = random.choice(_REFERRAL_REQUEST_MESSAGES)
        return template.format(name=name)

    def satisfaction_survey(self, user_id: str) -> str:
        """Generates a periodic satisfaction check-in."""
        profile = self._profiles.get(user_id)
        name = profile.display_name if profile else "there"
        template = random.choice(_SATISFACTION_SURVEY_MESSAGES)
        return template.format(name=name)

    def retention_risk(self, user_id: str) -> float:
        """
        Predicts the probability that a client may churn (0.0 = no risk, 1.0 = very high risk).
        Based on: engagement level, satisfaction, sentiment trend, days since last interaction.
        """
        health = self.get_relationship_health(user_id)
        profile = self._profiles.get(user_id)

        risk = 0.0

        # Engagement risk
        if health.engagement == EngagementLevel.INACTIVE:
            risk += 0.35
        elif health.engagement == EngagementLevel.LOW:
            risk += 0.20
        elif health.engagement == EngagementLevel.MEDIUM:
            risk += 0.05

        # Satisfaction risk
        if health.satisfaction < 0.5:
            risk += 0.25
        elif health.satisfaction < 0.7:
            risk += 0.10

        # Sentiment trend risk
        if health.sentiment_trend == "declining":
            risk += 0.20
        elif health.sentiment_trend == "stable":
            risk += 0.05

        # Days since last interaction
        if profile and profile.interactions:
            last = profile.interactions[-1].timestamp
            days_since = (datetime.utcnow() - last).days
            if days_since > 30:
                risk += 0.15
            elif days_since > 14:
                risk += 0.05

        return round(min(risk, 1.0), 3)

    def record_satisfaction_score(self, user_id: str, score: float) -> None:
        """Records a satisfaction survey score (1-10)."""
        profile = self._profiles.get(user_id)
        if profile:
            profile.satisfaction_scores.append(score)
