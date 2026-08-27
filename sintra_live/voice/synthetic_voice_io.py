"""Synthetic voice input/output adapters for offline integration."""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SyntheticVoiceInput:
    """Immutable synthetic voice input."""
    principal_id: str
    session_id: str
    transcript: str
    confidence: float
    timestamp: float
    language: str = "en-US"
    request_id: str = ""

    def __post_init__(self):
        if not self.request_id:
            content = f"{self.principal_id}|{self.session_id}|{self.transcript}|{self.timestamp}"
            object.__setattr__(self, 'request_id', hashlib.sha256(content.encode()).hexdigest()[:16])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "session_id": self.session_id,
            "transcript": self.transcript,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "language": self.language,
            "request_id": self.request_id
        }


@dataclass(frozen=True)
class SyntheticVoiceOutput:
    """Immutable synthetic voice output."""
    text: str
    language: str = "en-US"
    voice_profile: str = "sintra-standard"
    timestamp: float = 0.0
    output_hash: str = ""

    def __post_init__(self):
        if not self.output_hash:
            content = f"{self.text}|{self.language}|{self.voice_profile}|{self.timestamp}"
            object.__setattr__(self, 'output_hash', hashlib.sha256(content.encode()).hexdigest()[:16])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "voice_profile": self.voice_profile,
            "timestamp": self.timestamp,
            "output_hash": self.output_hash
        }


class SyntheticVoiceInputAdapter:
    """Reads synthetic voice input from test fixtures."""

    def __init__(self, fixture: Dict[str, Any]):
        self.fixture = fixture

    def capture(self) -> SyntheticVoiceInput:
        return SyntheticVoiceInput(
            principal_id=self.fixture.get("principal_id", "principal-001"),
            session_id=self.fixture.get("session_id", "session-001"),
            transcript=self.fixture.get("transcript", "Give me a status briefing and prepare one safe action."),
            confidence=self.fixture.get("confidence", 0.99),
            timestamp=self.fixture.get("timestamp", time.time()),
            language=self.fixture.get("language", "en-US")
        )

    def validate(self, voice_input: SyntheticVoiceInput) -> bool:
        return (
            voice_input.confidence >= 0.95 and
            len(voice_input.transcript) > 0 and
            len(voice_input.principal_id) > 0
        )


class SyntheticVoiceOutputAdapter:
    """Generates synthetic voice output for Principal Brief."""

    def __init__(self, voice_profile: str = "sintra-standard"):
        self.voice_profile = voice_profile

    def speak(self, brief_text: str, language: str = "en-US") -> SyntheticVoiceOutput:
        return SyntheticVoiceOutput(
            text=brief_text,
            language=language,
            voice_profile=self.voice_profile,
            timestamp=time.time()
        )

    def speak_json(self, brief_dict: Dict[str, Any], language: str = "en-US") -> SyntheticVoiceOutput:
        brief_text = json.dumps(brief_dict, sort_keys=True, separators=(",", ":"))
        return self.speak(brief_text, language)


def create_voice_fixture(principal_id: str = "principal-001", session_id: str = "session-001") -> Dict[str, Any]:
    """Create a standard synthetic voice input fixture."""
    return {
        "principal_id": principal_id,
        "session_id": session_id,
        "transcript": "Give me a status briefing and prepare one safe action.",
        "confidence": 0.99,
        "timestamp": time.time(),
        "language": "en-US"
    }


def create_approval_fixture(principal_id: str = "principal-001", session_id: str = "session-001") -> Dict[str, Any]:
    """Create a standard synthetic approval fixture."""
    return {
        "principal_id": principal_id,
        "session_id": session_id,
        "approval_phrase": "Yes, I approve.",
        "confidence": 0.99,
        "timestamp": time.time()
    }