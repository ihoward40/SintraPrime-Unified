"""Tests for voice_runtime.registry.ProviderRegistry."""

from __future__ import annotations

import pytest

from voice_runtime.capabilities import SpeechCapability
from voice_runtime.errors import DuplicateProviderError, UnknownProviderError
from voice_runtime.preflight import PreflightResult
from voice_runtime.providers.base import BaseSpeechProvider
from voice_runtime.providers.mock import MockSpeechProvider
from voice_runtime.registry import ProviderRegistry, build_default_registry


class _StubProvider(BaseSpeechProvider):
    provider_id = "stub"
    provider_version = "1.0.0"
    _capabilities = frozenset({SpeechCapability.ASR})


def test_register_and_get():
    registry = ProviderRegistry()
    provider = MockSpeechProvider()
    registry.register(provider)

    assert registry.get("mock") is provider
    assert registry.provider_ids() == ("mock",)


def test_duplicate_registration_rejected():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider())

    with pytest.raises(DuplicateProviderError):
        registry.register(MockSpeechProvider())


def test_unknown_provider_lookup_raises():
    registry = ProviderRegistry()

    with pytest.raises(UnknownProviderError):
        registry.get("does-not-exist")


def test_capability_map_reports_all_providers():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider())
    registry.register(_StubProvider())

    capability_map = registry.capability_map()
    assert capability_map["mock"] >= {SpeechCapability.ASR, SpeechCapability.TTS}
    assert capability_map["stub"] == {SpeechCapability.ASR}


def test_providers_for_capability_deterministic_priority_order():
    registry = ProviderRegistry()
    registry.register(_StubProvider(), priority=50)
    registry.register(MockSpeechProvider(), priority=10)

    providers = registry.providers_for_capability(SpeechCapability.ASR)
    assert [p.provider_id for p in providers] == ["mock", "stub"]


def test_disabled_provider_reported_in_preflight_map():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider(), enabled=False)

    preflight = registry.preflight_map()["mock"]
    assert preflight.state == PreflightResult.disabled().state
    assert not preflight.usable


def test_set_enabled_toggles_state():
    registry = ProviderRegistry()
    registry.register(MockSpeechProvider())
    assert registry.is_enabled("mock")

    registry.set_enabled("mock", False)
    assert not registry.is_enabled("mock")
    assert not registry.preflight_map()["mock"].usable


def test_build_default_registry_has_expected_providers():
    registry = build_default_registry()

    assert set(registry.provider_ids()) == {"legacy_audio_adapter", "browser_native", "mock"}
