"""Speech-runtime capability model.

Capabilities are declared explicitly by providers instead of relying on
name-based or type-based provider checks. The registry and router only ever
reason about capabilities, never about specific provider identities, so new
providers (including future VibeVoice adapters) can be added without
touching routing logic.
"""

from __future__ import annotations

from enum import Enum


class SpeechCapability(str, Enum):
    """A single speech/audio computation capability a provider may support."""

    ASR = "asr"
    """Speech-to-text / automatic speech recognition."""

    TTS = "tts"
    """Basic text-to-speech synthesis."""

    STREAMING_TTS = "streaming_tts"
    """Low-latency, incrementally-streamed text-to-speech synthesis."""

    LONG_FORM_TTS = "long_form_tts"
    """Long-form (multi-minute) speech synthesis."""

    MULTI_SPEAKER_TTS = "multi_speaker_tts"
    """Multi-speaker / multi-voice synthesis (e.g. podcast-style scripts)."""

    SPEAKER_DIARIZATION = "speaker_diarization"
    """Identify and separate distinct speakers within a single audio stream."""

    AUDIO_NORMALIZATION = "audio_normalization"
    """Audio preprocessing: normalization, noise reduction, format conversion."""

    SPEAKER_PROFILE = "speaker_profile"
    """Enrollment/lookup of a governed speaker profile (consent-gated)."""


#: Ordered tuple of all known capabilities, used for deterministic iteration
#: (e.g. when reporting the full capability matrix for a provider).
ALL_CAPABILITIES: tuple[SpeechCapability, ...] = tuple(SpeechCapability)
