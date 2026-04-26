"""
Empathy Engine — Pi AI-inspired empathetic response generation.
Never minimizes feelings. Always validates first, then informs.
Inspired by: Pi AI by Inflection, Human-centered AI design, Legal client psychology.
"""

from __future__ import annotations

import random
import re
from typing import Dict, List, Optional
from .sentiment_analyzer import SentimentResult, SentimentType, UrgencyLevel


# ──────────────────────────────────────────────────────────────
# Empathy acknowledgment templates
# ──────────────────────────────────────────────────────────────

_ACKNOWLEDGMENTS: Dict[str, List[str]] = {
    "fear": [
        "I can hear how frightening this situation feels for you.",
        "It's completely understandable to feel scared — what you're facing is serious.",
        "Your fear makes total sense given what you're going through.",
        "I want you to know that feeling afraid right now is a very human response.",
    ],
    "anger": [
        "I completely understand your frustration — you deserve better than this.",
        "Your anger is valid, and I hear you.",
        "Anyone in your position would feel this way. Let's work through this together.",
        "I'm sorry this situation has pushed you to this point. That's not okay.",
    ],
    "confusion": [
        "Legal language can be incredibly confusing — you're not alone in feeling lost.",
        "This is genuinely complicated, and it makes complete sense that you need clarity.",
        "Let me help break this down into simpler terms. You deserve to understand your situation.",
        "I want to make sure you truly understand what's happening, so let's go step by step.",
    ],
    "frustration": [
        "I hear how exhausted and frustrated you are. This has been a long road.",
        "You've been dealing with this for so long — your frustration is completely justified.",
        "I'm sorry this process has taken so much out of you.",
        "Let's find a way to make this easier and move things forward.",
    ],
    "hope": [
        "It's wonderful that you're feeling hopeful — let's build on that.",
        "Your positive outlook is a real asset as we navigate this.",
        "I'm glad things are starting to look up. Let's keep that momentum going.",
    ],
    "distressed": [
        "I can hear that you're in a really difficult place right now, and I want you to know I'm here.",
        "What you're experiencing sounds incredibly hard. Please know you don't have to face this alone.",
        "I understand this feels overwhelming. Let's take this one step at a time together.",
        "First and foremost — your wellbeing matters. Let's make sure you're safe and supported.",
    ],
    "general": [
        "Thank you for trusting me with this.",
        "I want to make sure I give you the most helpful response possible.",
        "I'm here to help you navigate this, every step of the way.",
    ],
}

# Legal situation empathy templates
_SITUATION_EMPATHY: Dict[str, str] = {
    "divorce": (
        "Going through a divorce is one of the most emotionally difficult experiences anyone can face. "
        "Beyond the legal process, there's grief, uncertainty, and often fear about the future. "
        "I want you to know that your feelings are valid, and we'll work through this carefully and compassionately."
    ),
    "eviction": (
        "The fear of losing your home is one of the most primal and distressing experiences possible. "
        "Housing instability affects every area of your life. I take this seriously and will do everything "
        "possible to help you understand your rights and options."
    ),
    "debt": (
        "Financial crisis creates enormous shame, fear, and stress. Please know that debt problems "
        "are incredibly common and there are real legal pathways forward. You are not defined by your "
        "financial situation, and there is help available."
    ),
    "criminal": (
        "Facing criminal charges can feel terrifying and isolating. The stakes are real, "
        "and I understand why you may feel scared. Every person deserves understanding, fair representation, "
        "and clear information about what's happening."
    ),
    "estate": (
        "Navigating estate and probate matters often means dealing with grief at the same time as "
        "complex legal processes. I'm sorry for your loss and want to help make this process as "
        "clear and manageable as possible."
    ),
    "business_failure": (
        "Watching a business you built struggle or fail is deeply personal and painful. "
        "Beyond the financial impact, there's often a profound sense of loss. "
        "Let's focus on protecting you and finding the best path forward."
    ),
    "domestic_violence": (
        "Your safety is the absolute priority right now. What you're experiencing is not your fault, "
        "and you deserve protection and support. Let's focus first on making sure you and your "
        "loved ones are safe."
    ),
}

# Plain English replacements for legal jargon
_JARGON_MAP: Dict[str, str] = {
    r"\bplaintiff\b": "the person who filed the lawsuit",
    r"\bdefendant\b": "the person being sued",
    r"\blitigant\b": "the person involved in the lawsuit",
    r"\bpetitioner\b": "the person who filed the petition",
    r"\brespondent\b": "the person responding to the petition",
    r"\baffidavit\b": "a sworn written statement",
    r"\bdeposition\b": "recorded out-of-court testimony under oath",
    r"\bdiscovery\b": "the process of sharing evidence between parties",
    r"\bsubpoena\b": "a legal order to appear or produce documents",
    r"\binjunction\b": "a court order to do or stop doing something",
    r"\bstay\b": "a pause or temporary stop of legal proceedings",
    r"\bstipulation\b": "an agreement between the parties",
    r"\bpro se\b": "representing yourself without a lawyer",
    r"\bhabeas corpus\b": "a legal action to challenge unlawful imprisonment",
    r"\bex parte\b": "a hearing with only one side present",
    r"\binterlocutory\b": "a temporary or interim court order",
    r"\bremand\b": "sent back to a lower court",
    r"\bappellate\b": "related to an appeal of a court decision",
    r"\bjurisdiction\b": "the authority of a court to hear a case",
    r"\bstatute of limitations\b": "the legal deadline to file a case",
    r"\btort\b": "a civil wrong that causes harm",
    r"\bnegligence\b": "failure to take reasonable care that causes harm",
    r"\bliability\b": "legal responsibility for something",
    r"\bindemnify\b": "protect someone from financial loss",
    r"\bescrow\b": "money held by a third party until conditions are met",
    r"\bforeclosure\b": "the legal process where a lender takes your property",
    r"\bduress\b": "pressure or threats that force someone to do something",
    r"\bcontingency fee\b": "lawyer's fee paid only if you win the case",
    r"\bsettlement\b": "an agreement to resolve the case without a trial",
    r"\bclass action\b": "a lawsuit filed by a group of people with similar claims",
}

# Reassurance templates by situation type
_REASSURANCE: Dict[str, List[str]] = {
    "eviction": [
        "Eviction is a process that takes time — you have rights at every stage.",
        "There are legal protections that may apply to your situation.",
        "Many people successfully avoid eviction with the right information.",
    ],
    "divorce": [
        "Divorce proceedings are designed to be fair to both parties.",
        "Your rights are protected throughout this process.",
        "Many people emerge from divorce in a stronger position than they expected.",
    ],
    "debt": [
        "Bankruptcy law exists specifically to give people a fresh start.",
        "You have more options than you may realize.",
        "Millions of people have successfully resolved debt crises like yours.",
    ],
    "criminal": [
        "You are innocent until proven guilty — that's not just a phrase, it's the law.",
        "There are legal processes designed to protect your rights.",
        "Having clear information about your situation is the first step.",
    ],
    "general": [
        "You've taken an important step by seeking help.",
        "With the right information, most legal situations have a path forward.",
        "I'll help you understand every step of this process.",
    ],
}

# De-escalation phrases
_DE_ESCALATION_OPENERS = [
    "I completely understand why you feel that way, and I want to help.",
    "You have every right to be frustrated. Let me see what I can do.",
    "I hear you. Let's slow down and work through this together.",
    "Your feelings are completely valid. Let me focus on what I can actually do for you right now.",
    "I'm on your side here. Let's figure this out.",
]

# Check-in messages
_CHECK_IN_MESSAGES = [
    "Before we continue, I wanted to check in — how are you holding up?",
    "We've covered a lot. How are you feeling about everything so far?",
    "I want to make sure this is all making sense and not feeling too overwhelming. How are you doing?",
    "Take a moment — this is a lot to process. Is there anything you need me to clarify or slow down on?",
    "I just want to check in — are you okay? This situation sounds very stressful.",
]


class EmpathyEngine:
    """
    Pi AI-inspired empathetic response generation.
    Validates emotions first, then provides information.
    """

    def adapt_response(
        self, original_response: str, sentiment: SentimentResult
    ) -> str:
        """
        Injects empathy into an existing response based on detected sentiment.
        Always validates feelings before providing information.
        """
        acknowledgment = self._get_acknowledgment(sentiment)

        if sentiment.sentiment == SentimentType.DISTRESSED:
            prefix = acknowledgment + "\n\n"
            suffix = "\n\nPlease remember: you don't have to navigate this alone."
            return prefix + original_response + suffix

        if sentiment.sentiment == SentimentType.NEGATIVE:
            prefix = acknowledgment + "\n\n"
            return prefix + original_response

        if sentiment.emotions.get("confusion", 0) > 0.3:
            prefix = acknowledgment + "\n\nLet me explain this as clearly as possible:\n\n"
            return prefix + original_response

        if sentiment.sentiment == SentimentType.POSITIVE:
            prefix = acknowledgment + "\n\n"
            return prefix + original_response

        return original_response

    def acknowledge_emotion(self, emotion: str, context: str = "") -> str:
        """Generates an acknowledgment phrase for the given emotion."""
        options = _ACKNOWLEDGMENTS.get(emotion, _ACKNOWLEDGMENTS["general"])
        base = random.choice(options)
        if context:
            base = base + f" Given what you've shared about {context}, that reaction is completely understandable."
        return base

    def de_escalate(self, text: str) -> str:
        """Produces calming, de-escalating language for angry clients."""
        opener = random.choice(_DE_ESCALATION_OPENERS)
        simplified = self.simplify_jargon(text)
        return f"{opener}\n\n{simplified}"

    def simplify_jargon(self, legal_text: str) -> str:
        """Converts legal jargon to plain English using a curated lexicon."""
        result = legal_text
        for pattern, replacement in _JARGON_MAP.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def add_reassurance(self, text: str, situation_type: str) -> str:
        """Adds appropriate reassurance for the given situation type."""
        phrases = _REASSURANCE.get(situation_type, _REASSURANCE["general"])
        reassurance = random.choice(phrases)
        return f"{text}\n\n💙 {reassurance}"

    def check_in(self, user_id: str) -> str:
        """Generates a periodic wellbeing check-in message."""
        return random.choice(_CHECK_IN_MESSAGES)

    def get_situation_empathy(self, situation_type: str) -> str:
        """Returns a situation-specific empathy statement."""
        return _SITUATION_EMPATHY.get(
            situation_type,
            "I understand this situation is difficult. I'm here to help you through it."
        )

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _get_acknowledgment(self, sentiment: SentimentResult) -> str:
        """Selects the most appropriate acknowledgment based on sentiment."""
        if sentiment.sentiment == SentimentType.DISTRESSED:
            return random.choice(_ACKNOWLEDGMENTS["distressed"])

        # Find dominant emotion
        dominant_emotion = max(sentiment.emotions, key=sentiment.emotions.get)
        if sentiment.emotions[dominant_emotion] > 0.2:
            options = _ACKNOWLEDGMENTS.get(dominant_emotion, _ACKNOWLEDGMENTS["general"])
            return random.choice(options)

        return random.choice(_ACKNOWLEDGMENTS["general"])
