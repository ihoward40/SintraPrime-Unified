"""Provider protocol/base interface for speech-runtime providers.

Providers are the only place a heavy/optional dependency (numpy, torch,
transformers, an external provider SDK, etc.) may ever be imported, and even
then, only inside methods/activation paths that run after this module's
lightweight ``preflight()`` has been consulted — never at module import
time.

Not every provider must implement every capability. A provider that does
not support a capability should simply not declare it in ``capabilities``;
the registry/router enforce that unsupported capabilities are never routed
to a provider that doesn't declare them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..capabilities import SpeechCapability
from ..models import (
    SpeechArtifact,
    SpeechRecognitionRequest,
    SpeechSynthesisRequest,
    StructuredTranscript,
)
from ..preflight import PreflightResult


@runtime_checkable
class SpeechProvider(Protocol):
    """Structural protocol every speech-runtime provider must satisfy.

    Implementations are plain classes (no required base class) — anything
    satisfying this shape can be registered. This keeps provider
    implementations decoupled from ``voice_runtime`` internals and makes it
    trivial to add a future VibeVoice/cloud adapter without inheritance
    coupling.
    """

    @property
    def provider_id(self) -> str:
        """Stable, unique identifier for this provider (e.g. ``"mock"``)."""
        ...

    @property
    def provider_version(self) -> str:
        """Provider implementation version string (not a model version)."""
        ...

    @property
    def capabilities(self) -> frozenset[SpeechCapability]:
        """Capabilities this provider declares support for."""
        ...

    def preflight(self) -> PreflightResult:
        """Check current availability without raising or crashing the app."""
        ...

    def health(self) -> str:
        """Short human-readable health/status summary for diagnostics."""
        ...

    def recognize(self, request: SpeechRecognitionRequest) -> StructuredTranscript:
        """Perform ASR. Only called if ``SpeechCapability.ASR`` is declared."""
        ...

    def synthesize(self, request: SpeechSynthesisRequest) -> SpeechArtifact:
        """Perform TTS. Only called if a TTS-family capability is declared."""
        ...


class BaseSpeechProvider:
    """Convenience base class implementing the boilerplate of the protocol.

    Providers may subclass this instead of implementing ``SpeechProvider``
    from scratch, but subclassing is never required — the registry accepts
    anything structurally satisfying ``SpeechProvider``.
    """

    provider_id: str = "base"
    provider_version: str = "0.0.0"
    _capabilities: frozenset[SpeechCapability] = frozenset()

    @property
    def capabilities(self) -> frozenset[SpeechCapability]:
        return self._capabilities

    def preflight(self) -> PreflightResult:
        return PreflightResult.available()

    def health(self) -> str:
        return "ok"

    def recognize(self, request: SpeechRecognitionRequest) -> StructuredTranscript:
        raise NotImplementedError(
            f"provider {self.provider_id!r} does not implement recognize()"
        )

    def synthesize(self, request: SpeechSynthesisRequest) -> SpeechArtifact:
        raise NotImplementedError(
            f"provider {self.provider_id!r} does not implement synthesize()"
        )
