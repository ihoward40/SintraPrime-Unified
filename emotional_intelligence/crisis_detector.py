"""
Crisis Detector — Identifies and responds to crisis situations for legal clients.
Always refers to emergency services (911, crisis hotlines) for immediate danger.
Human review flagging for SEVERE and IMMEDIATE crisis levels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class CrisisType(str, Enum):
    FINANCIAL_EMERGENCY = "financial_emergency"
    HOUSING_CRISIS = "housing_crisis"
    FAMILY_CRISIS = "family_crisis"
    MENTAL_HEALTH_CONCERN = "mental_health_concern"
    LEGAL_EMERGENCY = "legal_emergency"
    DOMESTIC_VIOLENCE = "domestic_violence_indicator"
    NONE = "none"


class CrisisLevel(str, Enum):
    NONE = "NONE"
    CONCERN = "CONCERN"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    IMMEDIATE = "IMMEDIATE"


@dataclass
class Resource:
    name: str
    phone: str
    url: Optional[str] = None
    available_24_7: bool = True
    description: str = ""


@dataclass
class CrisisAssessment:
    crisis_types: List[CrisisType] = field(default_factory=list)
    level: CrisisLevel = CrisisLevel.NONE
    confidence: float = 0.0
    flagged_phrases: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_human_review: bool = False

    def to_dict(self) -> dict:
        return {
            "crisis_types": [ct.value for ct in self.crisis_types],
            "level": self.level.value,
            "confidence": self.confidence,
            "flagged_phrases": self.flagged_phrases,
            "requires_human_review": self.requires_human_review,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TriageResult:
    urgency: str
    recommended_steps: List[str]
    estimated_time_sensitivity: str
    refer_to_attorney_immediately: bool = False
    call_911: bool = False


# ──────────────────────────────────────────────────────────────
# Crisis keyword patterns
# ──────────────────────────────────────────────────────────────

_MENTAL_HEALTH_PHRASES = [
    "want to die", "end my life", "kill myself", "suicidal", "suicide",
    "don't want to live", "can't go on", "end it all", "no reason to live",
    "better off dead", "hurt myself", "self-harm", "cutting",
    "give up on everything", "worthless", "hopeless and helpless",
]

_DOMESTIC_VIOLENCE_PHRASES = [
    "hit me", "beats me", "physically abused", "he hurt me", "she hurt me",
    "domestic violence", "dv", "being abused", "in danger",
    "afraid of my partner", "afraid of my spouse", "threatens me",
    "threatened to kill", "has a weapon", "unsafe at home",
    "restraining order", "protective order", "stalking", "being stalked",
]

_HOUSING_CRISIS_PHRASES = [
    "lose my house", "losing my home", "being evicted", "eviction notice",
    "can't pay rent", "homeless", "living in my car", "no place to go",
    "foreclosure", "bank taking my home", "out on the street",
    "no housing", "shelter", "kicked out", "lockout",
]

_FINANCIAL_EMERGENCY_PHRASES = [
    "can't eat", "no food", "utilities shut off", "electricity cut off",
    "bank account frozen", "wage garnishment", "wages garnished",
    "wages are being garnished", "garnished wages", "being garnished",
    "can't buy food", "cannot buy food", "can't afford food",
    "car repossessed", "repo", "can't buy medicine", "can't afford medication",
    "zero dollars", "completely broke", "nothing left",
    "emergency funds", "no money whatsoever",
]

_FAMILY_CRISIS_PHRASES = [
    "taking my kids", "lose custody", "child services", "cps",
    "children removed", "child abduction", "my child is missing",
    "runaway child", "divorce emergency", "custody emergency",
    "children in danger", "child abuse reported",
]

_LEGAL_EMERGENCY_PHRASES = [
    "court tomorrow", "hearing today", "deadline today", "warrant",
    "being arrested", "police at my door", "immigration raid",
    "deportation order", "deported tomorrow", "statute expires today",
    "contempt of court", "bail hearing", "criminal emergency",
    "statute of limitations runs out", "appeal deadline today",
]

# Jurisdiction-based resources
_CRISIS_RESOURCES: Dict[str, Dict[str, List[Resource]]] = {
    "national": {
        "mental_health_concern": [
            Resource(
                name="National Suicide Prevention Lifeline",
                phone="988",
                url="https://988lifeline.org",
                description="24/7 free and confidential support",
            ),
            Resource(
                name="Crisis Text Line",
                phone="Text HOME to 741741",
                url="https://www.crisistextline.org",
                description="Text-based crisis support",
            ),
        ],
        "domestic_violence_indicator": [
            Resource(
                name="National Domestic Violence Hotline",
                phone="1-800-799-7233",
                url="https://www.thehotline.org",
                description="24/7 confidential support for DV survivors",
            ),
            Resource(
                name="National Sexual Assault Hotline",
                phone="1-800-656-4673",
                url="https://www.rainn.org",
                description="RAINN — crisis support",
            ),
        ],
        "housing_crisis": [
            Resource(
                name="HUD Housing Counseling",
                phone="1-800-569-4287",
                url="https://www.hud.gov",
                description="Free housing counseling",
            ),
            Resource(
                name="National Low Income Housing Coalition",
                phone="202-662-1530",
                url="https://nlihc.org",
                description="Housing advocacy resources",
            ),
        ],
        "financial_emergency": [
            Resource(
                name="National Foundation for Credit Counseling",
                phone="1-800-388-2227",
                url="https://www.nfcc.org",
                description="Free financial counseling",
            ),
            Resource(
                name="Benefits.gov",
                phone="N/A",
                url="https://www.benefits.gov",
                description="Find federal benefit programs",
            ),
        ],
        "legal_emergency": [
            Resource(
                name="Legal Services Corporation",
                phone="N/A",
                url="https://www.lsc.gov/find-legal-aid",
                description="Find free legal aid in your area",
            ),
            Resource(
                name="LawHelp.org",
                phone="N/A",
                url="https://www.lawhelp.org",
                description="Free legal information and aid finder",
            ),
        ],
        "family_crisis": [
            Resource(
                name="Childhelp National Child Abuse Hotline",
                phone="1-800-422-4453",
                url="https://www.childhelp.org",
                description="24/7 crisis intervention for children",
            ),
            Resource(
                name="National Runaway Safeline",
                phone="1-800-786-2929",
                url="https://www.1800runaway.org",
                description="Crisis support for runaway youth",
            ),
        ],
    }
}


class CrisisDetector:
    """
    Identifies and responds to crisis situations.
    Always prioritizes safety above all else.
    """

    def __init__(self):
        self._flagged_users: Dict[str, List[CrisisAssessment]] = {}

    def assess(self, text: str) -> CrisisAssessment:
        """
        Identifies crisis types present in the text.
        Returns CrisisAssessment with types, level, and flagged phrases.
        """
        normalized = text.lower()
        found_types: List[CrisisType] = []
        flagged_phrases: List[str] = []

        def check_phrases(phrases, crisis_type):
            for phrase in phrases:
                if phrase in normalized:
                    found_types.append(crisis_type)
                    flagged_phrases.append(phrase)
                    break

        check_phrases(_MENTAL_HEALTH_PHRASES, CrisisType.MENTAL_HEALTH_CONCERN)
        check_phrases(_DOMESTIC_VIOLENCE_PHRASES, CrisisType.DOMESTIC_VIOLENCE)
        check_phrases(_HOUSING_CRISIS_PHRASES, CrisisType.HOUSING_CRISIS)
        check_phrases(_FINANCIAL_EMERGENCY_PHRASES, CrisisType.FINANCIAL_EMERGENCY)
        check_phrases(_FAMILY_CRISIS_PHRASES, CrisisType.FAMILY_CRISIS)
        check_phrases(_LEGAL_EMERGENCY_PHRASES, CrisisType.LEGAL_EMERGENCY)

        if not found_types:
            found_types = [CrisisType.NONE]

        assessment = CrisisAssessment(
            crisis_types=found_types,
            flagged_phrases=flagged_phrases,
            confidence=min(len(flagged_phrases) * 0.25 + 0.5, 1.0) if flagged_phrases else 0.0,
        )
        assessment.level = self.crisis_level(assessment)
        assessment.requires_human_review = assessment.level in (
            CrisisLevel.SEVERE,
            CrisisLevel.IMMEDIATE,
        )
        return assessment

    def crisis_level(self, assessment: CrisisAssessment) -> CrisisLevel:
        """
        Determines the crisis severity level.
        IMMEDIATE > SEVERE > MODERATE > CONCERN > NONE
        """
        types = assessment.crisis_types

        # Immediate danger
        if CrisisType.MENTAL_HEALTH_CONCERN in types:
            return CrisisLevel.IMMEDIATE
        if CrisisType.DOMESTIC_VIOLENCE in types:
            return CrisisLevel.IMMEDIATE

        # Severe — multiple crises or housing/family
        if len(types) >= 3:
            return CrisisLevel.SEVERE
        if CrisisType.HOUSING_CRISIS in types and CrisisType.FINANCIAL_EMERGENCY in types:
            return CrisisLevel.SEVERE
        if CrisisType.FAMILY_CRISIS in types and len(types) >= 2:
            return CrisisLevel.SEVERE

        # Moderate — single acute crisis
        if CrisisType.HOUSING_CRISIS in types:
            return CrisisLevel.MODERATE
        if CrisisType.FAMILY_CRISIS in types:
            return CrisisLevel.MODERATE
        if CrisisType.LEGAL_EMERGENCY in types:
            return CrisisLevel.MODERATE
        if CrisisType.FINANCIAL_EMERGENCY in types:
            return CrisisLevel.MODERATE

        if CrisisType.NONE in types:
            return CrisisLevel.NONE

        return CrisisLevel.CONCERN

    def get_resources(
        self, crisis_type: str, jurisdiction: str = "national"
    ) -> List[Resource]:
        """Returns crisis hotlines, legal aid, and shelters for a given crisis type."""
        national = _CRISIS_RESOURCES.get("national", {})
        resources = national.get(crisis_type, [])

        # Always include 911 note for immediate crises
        if crisis_type in ("mental_health_concern", "domestic_violence_indicator"):
            resources = [
                Resource(
                    name="Emergency Services",
                    phone="911",
                    description="For immediate danger — call 911",
                )
            ] + resources

        return resources

    def generate_crisis_response(self, assessment: CrisisAssessment) -> str:
        """Generates an appropriate first response for a detected crisis."""
        level = assessment.level

        if level == CrisisLevel.IMMEDIATE:
            if CrisisType.MENTAL_HEALTH_CONCERN in assessment.crisis_types:
                return (
                    "🆘 **Your safety is the most important thing right now.**\n\n"
                    "I'm very concerned about what you've shared. Please know that you matter "
                    "and there are people who want to help you through this moment.\n\n"
                    "**Please reach out right now:**\n"
                    "📞 **988 Suicide & Crisis Lifeline** — Call or text **988** (free, 24/7)\n"
                    "💬 **Crisis Text Line** — Text HOME to **741741**\n"
                    "🚨 If you are in immediate danger, please call **911**\n\n"
                    "I'm still here for your legal questions whenever you're ready. "
                    "Your wellbeing comes first."
                )
            if CrisisType.DOMESTIC_VIOLENCE in assessment.crisis_types:
                return (
                    "🆘 **Your safety is the priority right now.**\n\n"
                    "What you're describing sounds dangerous, and I want you to know "
                    "that what's happening to you is not your fault.\n\n"
                    "**Please reach out for immediate support:**\n"
                    "📞 **National DV Hotline**: 1-800-799-7233 (24/7, confidential)\n"
                    "💬 Text START to 88788\n"
                    "🚨 If you are in immediate danger, please call **911**\n\n"
                    "There is legal protection available to you. "
                    "I can help with that once I know you're safe."
                )

        if level == CrisisLevel.SEVERE:
            return (
                "I can hear that you're dealing with an overwhelming number of serious issues "
                "at once, and I want you to know that we're going to work through this together.\n\n"
                "**Immediate resources that may help:**\n"
                + self._format_resources(assessment)
                + "\n\nLet's focus on the most urgent issue first. What feels most pressing to you right now?"
            )

        if level == CrisisLevel.MODERATE:
            return (
                "This is a serious situation and I understand why you're stressed. "
                "Let's make sure you have the right support.\n\n"
                + self._format_resources(assessment)
                + "\n\nLet me help you understand your options and next steps."
            )

        return "Thank you for sharing this with me. Let me help you navigate your situation."

    def flag_for_human_review(
        self, user_id: str, assessment: CrisisAssessment
    ) -> None:
        """Alerts human oversight for severe/immediate crisis situations."""
        if user_id not in self._flagged_users:
            self._flagged_users[user_id] = []
        self._flagged_users[user_id].append(assessment)
        # In production: send alert to human oversight queue
        # For now: log to console/monitoring
        print(
            f"[CRISIS ALERT] User {user_id} flagged for human review. "
            f"Level: {assessment.level.value}, "
            f"Types: {[ct.value for ct in assessment.crisis_types]}"
        )

    def legal_emergency_triage(self, description: str) -> TriageResult:
        """
        Triages a legal emergency description.
        Returns urgency, recommended next steps, and time sensitivity.
        """
        normalized = description.lower()
        steps = []
        urgency = "moderate"
        time_sensitivity = "within the week"
        refer_attorney = False
        call_911 = False

        if any(p in normalized for p in ["today", "tomorrow", "this morning", "right now"]):
            urgency = "critical"
            time_sensitivity = "within hours"
            refer_attorney = True
            steps.append("Contact a licensed attorney immediately — today")
            steps.append("Call your local bar association's emergency referral line")

        if "warrant" in normalized or "arrested" in normalized:
            urgency = "critical"
            call_911 = False  # Don't call 911 — call lawyer
            refer_attorney = True
            steps.insert(0, "Exercise your right to remain silent")
            steps.insert(1, "Request an attorney immediately before speaking to police")

        if "deportation" in normalized or "immigration" in normalized:
            urgency = "critical"
            time_sensitivity = "within hours"
            steps.append("Contact an immigration attorney immediately")
            steps.append("Document all immigration paperwork you have")

        if "custody" in normalized or "children" in normalized:
            urgency = "high"
            time_sensitivity = "within 24-48 hours"
            refer_attorney = True
            steps.append("Document the current situation with timestamps")
            steps.append("Contact a family law attorney as soon as possible")

        if not steps:
            steps = [
                "Document all relevant facts and dates",
                "Gather any written communications or documents",
                "Consult with a qualified attorney",
            ]
            urgency = "moderate"
            time_sensitivity = "within the week"

        return TriageResult(
            urgency=urgency,
            recommended_steps=steps,
            estimated_time_sensitivity=time_sensitivity,
            refer_to_attorney_immediately=refer_attorney,
            call_911=call_911,
        )

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _format_resources(self, assessment: CrisisAssessment) -> str:
        lines = []
        for crisis_type in assessment.crisis_types:
            if crisis_type == CrisisType.NONE:
                continue
            resources = self.get_resources(crisis_type.value)
            for r in resources[:2]:  # Top 2 per crisis type
                lines.append(f"• **{r.name}**: {r.phone}")
        return "\n".join(lines) if lines else ""
