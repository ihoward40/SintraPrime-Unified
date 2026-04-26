"""
Communication Style Adapter — Learns and adapts to each client's communication preferences.
Detects: formal/casual, technical/plain, verbose/concise, direct/collaborative.
Personalizes every interaction for better client experience.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FormalityLevel(str, Enum):
    FORMAL = "formal"
    SEMI_FORMAL = "semi_formal"
    CASUAL = "casual"


class TechnicalLevel(str, Enum):
    TECHNICAL = "technical"
    MIXED = "mixed"
    PLAIN = "plain"


class VerbosityLevel(str, Enum):
    VERBOSE = "verbose"
    BALANCED = "balanced"
    CONCISE = "concise"


class DirectnessLevel(str, Enum):
    DIRECT = "direct"
    COLLABORATIVE = "collaborative"


@dataclass
class CommunicationStyle:
    formality: FormalityLevel = FormalityLevel.SEMI_FORMAL
    technicality: TechnicalLevel = TechnicalLevel.MIXED
    verbosity: VerbosityLevel = VerbosityLevel.BALANCED
    directness: DirectnessLevel = DirectnessLevel.COLLABORATIVE
    preferred_name: Optional[str] = None
    reading_grade_level: int = 10  # Flesch-Kincaid grade
    sample_count: int = 0

    def to_dict(self) -> dict:
        return {
            "formality": self.formality.value,
            "technicality": self.technicality.value,
            "verbosity": self.verbosity.value,
            "directness": self.directness.value,
            "preferred_name": self.preferred_name,
            "reading_grade_level": self.reading_grade_level,
            "sample_count": self.sample_count,
        }


# ──────────────────────────────────────────────────────────────
# Indicators for style detection
# ──────────────────────────────────────────────────────────────

_FORMAL_INDICATORS = [
    "dear", "sincerely", "respectfully", "pursuant to", "whereas",
    "hereinafter", "please be advised", "i would like to",
    "i am writing to", "kindly", "regarding", "per our conversation",
]

_CASUAL_INDICATORS = [
    "hey", "hi there", "what's up", "gonna", "wanna", "kinda", "sorta",
    "asap", "btw", "fyi", "yeah", "nope", "ok", "okay", "gotta", "y'all",
    "lol", "omg", "totally", "literally", "basically",
]

_TECHNICAL_INDICATORS = [
    "statute", "jurisdiction", "plaintiff", "defendant", "injunction",
    "precedent", "constitutional", "promissory", "fiduciary",
    "encumbrance", "tort", "negligence", "indemnification",
    "subrogation", "escheatment", "res judicata",
]

_PLAIN_INDICATORS = [
    "in other words", "simply put", "basically", "what i mean is",
    "in plain english", "to put it simply", "can you explain",
    "what does that mean", "i don't understand",
]

_DIRECT_INDICATORS = [
    "just tell me", "bottom line", "what do i do", "short version",
    "just the facts", "don't need details", "quick answer",
    "get to the point", "tldr",
]

_COLLABORATIVE_INDICATORS = [
    "what do you think", "could we", "would you recommend",
    "what are my options", "help me understand", "can we discuss",
    "i'd like your opinion", "what would you suggest",
]


class CommunicationStyleAdapter:
    """
    Learns and adapts to each client's communication preferences.
    Stores style profiles per user in memory.
    """

    def __init__(self):
        self._style_profiles: Dict[str, CommunicationStyle] = {}

    def detect_style(self, messages: List[str]) -> CommunicationStyle:
        """
        Learns communication style from a list of messages.
        Returns a CommunicationStyle profile.
        """
        combined = " ".join(messages).lower()
        word_count = len(combined.split())

        # Formality
        formal_score = sum(1 for ind in _FORMAL_INDICATORS if ind in combined)
        casual_score = sum(1 for ind in _CASUAL_INDICATORS if ind in combined)
        if formal_score > casual_score * 1.5:
            formality = FormalityLevel.FORMAL
        elif casual_score > formal_score * 1.5:
            formality = FormalityLevel.CASUAL
        else:
            formality = FormalityLevel.SEMI_FORMAL

        # Technicality
        tech_score = sum(1 for ind in _TECHNICAL_INDICATORS if ind in combined)
        plain_score = sum(1 for ind in _PLAIN_INDICATORS if ind in combined)
        if tech_score > plain_score * 2:
            technicality = TechnicalLevel.TECHNICAL
        elif plain_score > tech_score:
            technicality = TechnicalLevel.PLAIN
        else:
            technicality = TechnicalLevel.MIXED

        # Verbosity (avg words per message)
        avg_words = word_count / max(len(messages), 1)
        if avg_words > 80:
            verbosity = VerbosityLevel.VERBOSE
        elif avg_words < 20:
            verbosity = VerbosityLevel.CONCISE
        else:
            verbosity = VerbosityLevel.BALANCED

        # Directness
        direct_score = sum(1 for ind in _DIRECT_INDICATORS if ind in combined)
        collab_score = sum(1 for ind in _COLLABORATIVE_INDICATORS if ind in combined)
        directness = (
            DirectnessLevel.DIRECT
            if direct_score > collab_score
            else DirectnessLevel.COLLABORATIVE
        )

        # Reading grade estimate
        grade = self._estimate_reading_grade(combined)

        return CommunicationStyle(
            formality=formality,
            technicality=technicality,
            verbosity=verbosity,
            directness=directness,
            reading_grade_level=grade,
            sample_count=len(messages),
        )

    def adapt(self, response: str, style: CommunicationStyle) -> str:
        """Rewrites response to match the detected communication style."""
        result = response

        # Apply technicality adaptation
        if style.technicality == TechnicalLevel.PLAIN:
            result = self._simplify_language(result)

        # Apply verbosity adaptation
        if style.verbosity == VerbosityLevel.CONCISE:
            result = self._make_concise(result)

        # Apply formality adaptation
        if style.formality == FormalityLevel.CASUAL:
            result = self._make_casual(result)
        elif style.formality == FormalityLevel.FORMAL:
            result = self._make_formal(result)

        return result

    def adjust_reading_level(self, text: str, target_grade: int) -> str:
        """
        Adjusts text to approximate target Flesch-Kincaid grade level.
        Simplifies for lower grades, preserves complexity for higher grades.
        """
        current_grade = self._estimate_reading_grade(text)

        if target_grade <= 6:
            # Very simple: short sentences, common words
            return self._simplify_to_elementary(text)
        elif target_grade <= 9:
            return self._simplify_language(text)
        elif target_grade >= 14:
            # Professional/legal level — preserve as-is
            return text
        return text

    def format_for_audience(self, content: str, audience_type: str) -> str:
        """
        Formats content appropriately for different audiences.
        audience_type: 'attorney', 'client', 'court'
        """
        if audience_type == "attorney":
            return self._format_for_attorney(content)
        elif audience_type == "client":
            return self._format_for_client(content)
        elif audience_type == "court":
            return self._format_for_court(content)
        return content

    def use_preferred_name(self, text: str, user_profile: Any) -> str:
        """Personalizes salutations using preferred name from user profile."""
        name = None
        if hasattr(user_profile, "preferred_name"):
            name = user_profile.preferred_name
        elif isinstance(user_profile, dict):
            name = user_profile.get("preferred_name") or user_profile.get("first_name")

        if not name:
            return text

        # Replace generic openings with personalized ones
        text = re.sub(
            r"^(Dear Client|Hello|Hi there|Good (morning|afternoon|evening)),?",
            f"Hi {name},",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        return text

    def save_style_profile(self, user_id: str, style: CommunicationStyle) -> None:
        """Persists style profile for a user."""
        self._style_profiles[user_id] = style

    def load_style_profile(self, user_id: str) -> Optional[CommunicationStyle]:
        """Loads a stored style profile."""
        return self._style_profiles.get(user_id)

    def update_style_profile(
        self, user_id: str, new_messages: List[str]
    ) -> CommunicationStyle:
        """Updates an existing style profile with new messages."""
        existing = self._style_profiles.get(user_id)
        new_style = self.detect_style(new_messages)

        if existing:
            # Blend: weight existing more heavily
            new_style.sample_count = existing.sample_count + len(new_messages)

        self._style_profiles[user_id] = new_style
        return new_style

    # ──────────────────────────────────────────────────────────
    # Internal formatting helpers
    # ──────────────────────────────────────────────────────────

    def _simplify_language(self, text: str) -> str:
        replacements = {
            "utilize": "use",
            "commence": "start",
            "terminate": "end",
            "subsequent": "next",
            "prior to": "before",
            "in the event that": "if",
            "with respect to": "about",
            "in accordance with": "following",
            "notwithstanding": "despite",
            "endeavor": "try",
            "facilitate": "help",
            "ascertain": "find out",
            "in lieu of": "instead of",
            "pursuant to": "under",
            "hereinafter": "from now on",
        }
        result = text
        for word, simple in replacements.items():
            result = re.sub(
                rf"\b{re.escape(word)}\b", simple, result, flags=re.IGNORECASE
            )
        return result

    def _simplify_to_elementary(self, text: str) -> str:
        """Very basic simplification for low reading level."""
        text = self._simplify_language(text)
        # Break long sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        simplified = []
        for sent in sentences:
            if len(sent.split()) > 20:
                # Add a break after conjunctions
                sent = re.sub(r",\s*(and|but|because|so|however)\s+", r". \1 ", sent)
            simplified.append(sent)
        return " ".join(simplified)

    def _make_concise(self, text: str) -> str:
        """Removes filler phrases to make text more concise."""
        fillers = [
            r"\bIt is important to note that\b",
            r"\bPlease be advised that\b",
            r"\bIt should be noted that\b",
            r"\bAs you may be aware,?\b",
            r"\bIn terms of\b",
            r"\bAt this point in time\b",
            r"\bdue to the fact that\b",
            r"\bin the near future\b",
        ]
        result = text
        for filler in fillers:
            result = re.sub(filler, "", result, flags=re.IGNORECASE)
        # Collapse multiple spaces
        result = re.sub(r" {2,}", " ", result).strip()
        return result

    def _make_casual(self, text: str) -> str:
        replacements = {
            "Dear Client": "Hi",
            "I would like to": "I'd like to",
            "You should be aware": "Just so you know",
            "Please do not hesitate": "Feel free",
            "Thank you for your correspondence": "Thanks for reaching out",
            "I am writing to inform you": "I wanted to let you know",
        }
        result = text
        for formal, casual in replacements.items():
            result = result.replace(formal, casual)
        return result

    def _make_formal(self, text: str) -> str:
        replacements = {
            "gonna": "going to",
            "wanna": "want to",
            "gotta": "need to",
            "kinda": "somewhat",
            "sorta": "somewhat",
            "yeah": "yes",
            "nope": "no",
            "ok": "acknowledged",
            "asap": "as soon as possible",
            "btw": "by the way",
        }
        result = text
        for casual, formal in replacements.items():
            result = re.sub(rf"\b{casual}\b", formal, result, flags=re.IGNORECASE)
        return result

    def _format_for_attorney(self, content: str) -> str:
        return f"**Legal Summary**\n\n{content}\n\n*This analysis is provided for attorney review and professional use.*"

    def _format_for_client(self, content: str) -> str:
        simplified = self._simplify_language(content)
        return f"Here's what this means for you:\n\n{simplified}\n\n*If you have any questions, please don't hesitate to ask.*"

    def _format_for_court(self, content: str) -> str:
        return f"STATEMENT FOR THE RECORD:\n\n{content}"

    def _estimate_reading_grade(self, text: str) -> int:
        """Approximate Flesch-Kincaid grade level."""
        words = text.split()
        sentences = re.split(r"[.!?]+", text)
        sentences = [s for s in sentences if s.strip()]

        if not words or not sentences:
            return 10

        avg_sentence_length = len(words) / len(sentences)
        # Approximate syllable count (heuristic: 1 syllable per vowel cluster)
        syllable_count = sum(
            max(1, len(re.findall(r"[aeiouAEIOU]+", word))) for word in words
        )
        avg_syllables_per_word = syllable_count / len(words)

        grade = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
        return max(1, min(int(round(grade)), 18))
