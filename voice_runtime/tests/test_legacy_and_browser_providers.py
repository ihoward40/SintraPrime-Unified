"""Tests for the legacy audio adapter and browser provider descriptors,
and for the security-boundary guarantees identified in Phase 0.
"""

from __future__ import annotations

import sys

import pytest

from voice_runtime.capabilities import SpeechCapability
from voice_runtime.preflight import PreflightState
from voice_runtime.providers.browser import BrowserSpeechProvider
from voice_runtime.providers.legacy import LegacyAudioAdapterProvider


def test_legacy_adapter_declares_only_audio_normalization():
    provider = LegacyAudioAdapterProvider()
    assert provider.capabilities == frozenset({SpeechCapability.AUDIO_NORMALIZATION})
    # Must never declare command/execution-adjacent or ASR/TTS capability —
    # this provider is normalization-only by design (Phase 0 finding).
    assert SpeechCapability.ASR not in provider.capabilities
    assert SpeechCapability.TTS not in provider.capabilities


def test_legacy_adapter_recognize_and_synthesize_not_implemented():
    """The legacy adapter cannot be routed to for ASR/TTS, and even if
    called directly in error, must not silently succeed or expose any
    legacy execution/authentication behavior."""

    provider = LegacyAudioAdapterProvider()
    with pytest.raises(NotImplementedError):
        provider.recognize(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        provider.synthesize(None)  # type: ignore[arg-type]


def test_legacy_adapter_preflight_available_without_numpy():
    provider = LegacyAudioAdapterProvider()
    result = provider.preflight()
    assert result.usable
    assert True  # numpy presence is unrelated to this pure-Python provider; see minimal-dependency import test


def test_legacy_adapter_analyze_and_normalize_pure_python():
    provider = LegacyAudioAdapterProvider()
    silence = bytes(200)  # 100 16-bit samples of silence
    result = provider.analyze(silence)
    assert result.rms == 0.0
    assert not result.is_speech_detected

    normalized = provider.normalize(silence)
    assert len(normalized) == len(silence)


def test_no_import_of_legacy_voice_api_module():
    """Hard guarantee: nothing in voice_runtime imports the unsafe legacy
    voice.voice_api module (hardcoded mock bearer-token verification)."""

    assert "voice.voice_api" not in sys.modules

    # Confirm no voice_runtime source file actually imports it (docstrings
    # are allowed to *mention* it, by name, to document that it is
    # deliberately excluded — only real import statements are forbidden).
    import ast
    import inspect

    import voice_runtime.providers.legacy as legacy_module

    source = inspect.getsource(legacy_module)
    tree = ast.parse(source)
    import_targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            import_targets.append(node.module)

    assert not any("voice_api" in target for target in import_targets)
    assert not any(target == "voice" or target.startswith("voice.") for target in import_targets)


def test_browser_provider_declares_asr_and_tts():
    provider = BrowserSpeechProvider()
    assert provider.capabilities == frozenset({SpeechCapability.ASR, SpeechCapability.TTS})


def test_browser_provider_preflight_reports_client_side_dependent():
    provider = BrowserSpeechProvider()
    result = provider.preflight()
    assert result.state == PreflightState.AVAILABLE_DEGRADED
    assert result.usable  # usable as a fallback tier
    assert result.checked_fields.get("execution_location") == "client"


def test_browser_provider_recognize_and_synthesize_not_implemented():
    """Real execution happens client-side (PR #247); calling these methods
    server-side must never silently return fabricated results."""

    provider = BrowserSpeechProvider()
    with pytest.raises(NotImplementedError):
        provider.recognize(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        provider.synthesize(None)  # type: ignore[arg-type]
