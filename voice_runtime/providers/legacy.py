"""Bounded legacy adapter provider.

Harvests only the specific, reusable algorithms identified in Phase 0
(``artifacts/voice/SP_VOICE_002_COMPONENT_MATRIX.md``) from the legacy
``voice/voice_engine.py`` (``AudioBuffer`` noise-floor/silence-detection
logic) and ``voice/speech_processor.py`` (primary→fallback→offline provider
chain *shape*). It does **not** import the legacy ``voice`` package at all
— none of ``voice/__init__.py``'s lazy exports, none of its module-level
``numpy`` dependency, none of its provider stubs, and critically, none of
its unsafe pieces:

- no legacy credentials (``voice.speech_processor.SpeechConfig`` raw API-key
  fields are not reproduced here);
- no legacy mock authentication (``voice.voice_api.verify_token`` is never
  imported, referenced, or reachable through this provider);
- no legacy direct action/execution behavior (this provider only performs
  audio normalization; it declares no ASR/TTS capability and cannot be
  routed to for those operations).

This provider exists to demonstrate that the *algorithm*, not the
*module*, is what gets reused — matching the Phase-0 finding that the
legacy authority model (raw credentials on dataclasses, no capability
declarations, no governance hooks, global ``logging.basicConfig()`` side
effects) is incompatible with this runtime's architecture even though some
of its underlying math is worth keeping.
"""

from __future__ import annotations

from ..audio.normalization import analyze_pcm16, clip_normalize
from ..capabilities import SpeechCapability
from ..preflight import PreflightResult
from .base import BaseSpeechProvider


class LegacyAudioAdapterProvider(BaseSpeechProvider):
    """Audio-normalization-only provider harvested from legacy ``voice/``.

    Declares **only** ``AUDIO_NORMALIZATION`` — it must never be routed to
    for ASR or TTS, and inherits ``recognize()``/``synthesize()`` from
    ``BaseSpeechProvider`` which raise ``NotImplementedError`` if ever
    invoked in error.
    """

    provider_id = "legacy_audio_adapter"
    provider_version = "1.0.0"
    _capabilities = frozenset({SpeechCapability.AUDIO_NORMALIZATION})

    def __init__(self, *, noise_floor: float = 0.02) -> None:
        self._noise_floor = noise_floor

    def preflight(self) -> PreflightResult:
        # Pure-Python implementation — no optional dependency required.
        return PreflightResult.available(
            detail="pure-Python reimplementation of legacy AudioBuffer logic; no numpy required"
        )

    def health(self) -> str:
        return "ok (pure-Python legacy-derived normalization only)"

    def analyze(self, pcm16_bytes: bytes):
        """Expose the harvested RMS/silence-detection analysis directly.

        Not part of the ``SpeechProvider`` protocol (it isn't ASR/TTS); this
        is a capability-specific helper method callers may use when they
        specifically need audio-normalization behavior, mirroring how
        ``voice_runtime.router`` would select this provider for the
        ``AUDIO_NORMALIZATION`` capability.
        """

        return analyze_pcm16(pcm16_bytes, noise_floor=self._noise_floor)

    def normalize(self, pcm16_bytes: bytes) -> bytes:
        """Expose the harvested clip/normalize step directly."""

        return clip_normalize(pcm16_bytes)
