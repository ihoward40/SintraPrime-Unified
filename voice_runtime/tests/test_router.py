"""Tests for voice_runtime.router deterministic routing/fallback behavior."""

from __future__ import annotations

import pytest

from voice_runtime.capabilities import SpeechCapability
from voice_runtime.errors import ProviderUnavailableError, UnsupportedCapabilityError
from voice_runtime.preflight import PreflightResult
from voice_runtime.providers.base import BaseSpeechProvider
from voice_runtime.providers.mock import MockSpeechProvider
from voice_runtime.registry import ProviderRegistry
from voice_runtime.router import route


class _AlwaysUnavailableProvider(BaseSpeechProvider):
    provider_id = "always_unavailable"
    provider_version = "1.0.0"
    _capabilities = frozenset({SpeechCapability.ASR})

    def preflight(self) -> PreflightResult:
        return PreflightResult.dependency_missing("some-optional-package")


def test_route_selects_only_candidate():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider())

    provider, decision = route(registry, SpeechCapability.ASR)

    assert provider.provider_id == "mock"
    assert decision.selected_provider_id == "mock"
    assert decision.requested_capability == SpeechCapability.ASR
    assert decision.considered_provider_ids == ("mock",)
    assert decision.rejected == ()


def test_route_falls_back_past_unavailable_provider():
    registry = ProviderRegistry()
    registry.register(_AlwaysUnavailableProvider(), priority=10)
    registry.register(MockSpeechProvider(), priority=100)

    provider, decision = route(registry, SpeechCapability.ASR)

    assert provider.provider_id == "mock"
    assert decision.considered_provider_ids == ("always_unavailable", "mock")
    assert len(decision.rejected) == 1
    assert decision.rejected[0].provider_id == "always_unavailable"
    assert "some-optional-package" in decision.rejected[0].reason


def test_route_unsupported_capability_raises_typed_error():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider())

    with pytest.raises(UnsupportedCapabilityError) as exc_info:
        route(registry, SpeechCapability.SPEAKER_DIARIZATION)

    assert exc_info.value.capability == SpeechCapability.SPEAKER_DIARIZATION


def test_route_all_providers_unavailable_raises_typed_error():
    registry = ProviderRegistry()
    registry.register(_AlwaysUnavailableProvider())

    with pytest.raises(ProviderUnavailableError) as exc_info:
        route(registry, SpeechCapability.ASR)

    assert exc_info.value.capability == SpeechCapability.ASR
    assert "always_unavailable" in exc_info.value.reasons


def test_route_disabled_provider_is_skipped():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider(), enabled=False)

    with pytest.raises(ProviderUnavailableError):
        route(registry, SpeechCapability.ASR)


def test_route_honors_explicit_preferred_provider():
    registry = ProviderRegistry()
    registry.register(_AlwaysUnavailableProvider(), priority=1)
    mock = MockSpeechProvider()
    registry.register(mock, priority=100)

    provider, decision = route(registry, SpeechCapability.ASR, preferred_provider_id="mock")

    assert provider is mock
    assert decision.selected_provider_id == "mock"


def test_route_preferred_provider_unusable_falls_back():
    registry = ProviderRegistry()
    registry.register(_AlwaysUnavailableProvider(), priority=1)
    registry.register(MockSpeechProvider(), priority=100)

    provider, decision = route(
        registry, SpeechCapability.ASR, preferred_provider_id="always_unavailable"
    )

    assert provider.provider_id == "mock"
    assert any(r.provider_id == "always_unavailable" for r in decision.rejected)
