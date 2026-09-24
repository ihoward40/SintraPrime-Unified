"""Typed error hierarchy for the speech runtime.

All errors raised by ``voice_runtime`` public APIs derive from
``VoiceRuntimeError`` so callers can catch the whole family, or a specific
subtype for typed handling (e.g. distinguishing "no provider supports this
capability" from "the provider that would support it is currently down").
"""

from __future__ import annotations

from .capabilities import SpeechCapability


class VoiceRuntimeError(Exception):
    """Base class for all speech-runtime errors."""


class DuplicateProviderError(VoiceRuntimeError):
    """Raised when a provider is registered under an ID already in use."""

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"a provider is already registered under id={provider_id!r}")


class UnknownProviderError(VoiceRuntimeError):
    """Raised when a provider ID is looked up but not registered."""

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"no provider is registered under id={provider_id!r}")


class UnsupportedCapabilityError(VoiceRuntimeError):
    """Raised when no registered, enabled provider declares a requested capability."""

    def __init__(self, capability: SpeechCapability) -> None:
        self.capability = capability
        super().__init__(f"no provider declares support for capability={capability.value!r}")


class ProviderUnavailableError(VoiceRuntimeError):
    """Raised when the only provider(s) that support a capability are unavailable."""

    def __init__(self, capability: SpeechCapability, reasons: dict[str, str]) -> None:
        self.capability = capability
        self.reasons = dict(reasons)
        detail = "; ".join(f"{pid}: {reason}" for pid, reason in reasons.items()) or "none registered"
        super().__init__(
            f"no available provider for capability={capability.value!r} ({detail})"
        )


class ProviderDisabledError(VoiceRuntimeError):
    """Raised when a specific, explicitly-requested provider is disabled."""

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"provider id={provider_id!r} is disabled")
