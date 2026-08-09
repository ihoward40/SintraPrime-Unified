"""Tests for the VibeVoice-Realtime-0.5B provider adapter (Phase 2A-1).

This host has neither ``torch``/``transformers`` installed nor any model
weights downloaded (see ``artifacts/voice/SP_VOICE_002_PHASE2A_CERTIFICATION.md``).
These tests therefore certify the *adapter/preflight logic*, not real
inference. Where hardware-branch logic (CUDA vs. CPU-only) needs to be
exercised, a minimal fake ``torch`` module is injected into ``sys.modules``
for the duration of the test only — this is not a real PyTorch install and
performs no computation; it exists purely to test our own branching logic
against both possible ``torch.cuda.is_available()`` outcomes.
"""

from __future__ import annotations

import sys
import types

import pytest

from voice_runtime.capabilities import SpeechCapability
from voice_runtime.models import SpeechSynthesisRequest, TenantContext
from voice_runtime.preflight import PreflightState
from voice_runtime.providers.vibevoice_realtime import (
    OFFICIAL_MODEL_ID,
    SynthesisCancelledError,
    VibeVoiceRealtimeConfig,
    VibeVoiceRealtimeProvider,
)


@pytest.fixture(autouse=True)
def _clean_torch_transformers_modules():
    """Ensure a clean sys.modules state around fake-module injection tests."""

    saved = {
        name: sys.modules.pop(name, None)
        for name in ("torch", "transformers", "huggingface_hub")
    }
    yield
    for name, module in saved.items():
        sys.modules.pop(name, None)
        if module is not None:
            sys.modules[name] = module


def _install_fake_torch(cuda_available: bool) -> None:
    fake_torch = types.ModuleType("torch")
    fake_cuda = types.SimpleNamespace(is_available=lambda: cuda_available)
    fake_torch.cuda = fake_cuda  # type: ignore[attr-defined]
    sys.modules["torch"] = fake_torch


def _install_fake_transformers() -> None:
    sys.modules["transformers"] = types.ModuleType("transformers")


def test_module_import_does_not_require_torch_or_transformers():
    """Importing the provider module itself must not require torch/transformers
    (they are only imported lazily, inside preflight()/_ensure_model_loaded())."""

    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules

    import importlib

    module = importlib.import_module("voice_runtime.providers.vibevoice_realtime")
    assert module.OFFICIAL_MODEL_ID == "microsoft/VibeVoice-Realtime-0.5B"
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules


def test_official_model_id_is_correct():
    assert OFFICIAL_MODEL_ID == "microsoft/VibeVoice-Realtime-0.5B"


def test_provider_declares_tts_capabilities_only():
    provider = VibeVoiceRealtimeProvider()
    assert provider.capabilities == frozenset(
        {SpeechCapability.TTS, SpeechCapability.STREAMING_TTS}
    )
    assert SpeechCapability.ASR not in provider.capabilities
    assert SpeechCapability.MULTI_SPEAKER_TTS not in provider.capabilities
    assert SpeechCapability.SPEAKER_PROFILE not in provider.capabilities


def test_preflight_reports_dependency_missing_without_torch():
    """On this host (no torch/transformers installed), preflight must
    report DEPENDENCY_MISSING, not crash or silently claim availability."""

    provider = VibeVoiceRealtimeProvider()
    result = provider.preflight()
    assert result.state == PreflightState.DEPENDENCY_MISSING
    assert not result.usable
    assert "torch" in result.detail or "transformers" in result.detail


def test_preflight_reports_transformers_missing_when_only_torch_present():
    _install_fake_torch(cuda_available=False)
    # transformers deliberately not installed

    provider = VibeVoiceRealtimeProvider()
    result = provider.preflight()
    assert result.state == PreflightState.DEPENDENCY_MISSING
    assert "transformers" in result.detail


def test_preflight_reports_model_missing_with_nonexistent_model_path(tmp_path):
    _install_fake_torch(cuda_available=False)
    _install_fake_transformers()

    missing_path = str(tmp_path / "does-not-exist")
    provider = VibeVoiceRealtimeProvider(VibeVoiceRealtimeConfig(model_path=missing_path))

    result = provider.preflight()
    assert result.state == PreflightState.MODEL_MISSING
    assert not result.usable
    assert "does not exist locally" in result.detail


def test_preflight_reports_model_available_with_real_local_path(tmp_path):
    _install_fake_torch(cuda_available=False)
    _install_fake_transformers()

    model_dir = tmp_path / "vibevoice-realtime-0.5b"
    model_dir.mkdir()
    provider = VibeVoiceRealtimeProvider(VibeVoiceRealtimeConfig(model_path=str(model_dir)))

    result = provider.preflight()
    # Dependencies present (fake) + model path exists -> hardware branch
    # decides AVAILABLE vs AVAILABLE_DEGRADED; either way must be usable.
    assert result.usable
    assert result.state in (PreflightState.AVAILABLE, PreflightState.AVAILABLE_DEGRADED)


def test_preflight_cpu_only_reports_available_degraded(tmp_path):
    _install_fake_torch(cuda_available=False)
    _install_fake_transformers()

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    provider = VibeVoiceRealtimeProvider(VibeVoiceRealtimeConfig(model_path=str(model_dir)))

    result = provider.preflight()
    assert result.state == PreflightState.AVAILABLE_DEGRADED
    assert result.usable
    assert "real-time" in result.detail.lower() or "cuda" in result.detail.lower()


def test_preflight_cuda_available_reports_available(tmp_path):
    _install_fake_torch(cuda_available=True)
    _install_fake_transformers()

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    provider = VibeVoiceRealtimeProvider(VibeVoiceRealtimeConfig(model_path=str(model_dir)))

    result = provider.preflight()
    assert result.state == PreflightState.AVAILABLE


def test_preflight_explicit_cpu_preference_forces_degraded_even_with_cuda(tmp_path):
    _install_fake_torch(cuda_available=True)
    _install_fake_transformers()

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    provider = VibeVoiceRealtimeProvider(
        VibeVoiceRealtimeConfig(model_path=str(model_dir), device_preference="cpu")
    )

    result = provider.preflight()
    assert result.state == PreflightState.AVAILABLE_DEGRADED


def test_recognize_not_supported():
    provider = VibeVoiceRealtimeProvider()
    with pytest.raises(NotImplementedError):
        provider.recognize(None)  # type: ignore[arg-type]


def test_synthesize_raises_when_dependencies_missing():
    """On this (real, unmodified) host, dependencies genuinely are absent —
    synthesize() must fail loudly and clearly, never silently fabricate a
    result or attempt a network download."""

    provider = VibeVoiceRealtimeProvider()
    request = SpeechSynthesisRequest(
        text="SintraPrime local voice runtime certification test.",
        tenant=TenantContext(tenant_id="t1", principal_id="p1"),
    )

    with pytest.raises(RuntimeError):
        provider.synthesize(request)


def test_synthesize_rejects_empty_text():
    provider = VibeVoiceRealtimeProvider()
    request = SpeechSynthesisRequest(text="", tenant=TenantContext(tenant_id="t1", principal_id="p1"))

    with pytest.raises(ValueError, match="must not be empty"):
        provider.synthesize(request)


def test_synthesize_honors_cancel_event_before_invocation():
    class _AlreadyCancelled:
        def is_set(self) -> bool:
            return True

    provider = VibeVoiceRealtimeProvider()
    request = SpeechSynthesisRequest(
        text="SintraPrime local voice runtime certification test.",
        tenant=TenantContext(tenant_id="t1", principal_id="p1"),
    )

    with pytest.raises(SynthesisCancelledError):
        provider.synthesize(request, cancel_event=_AlreadyCancelled())


def test_no_model_download_attempted_without_local_files():
    """Never-download guarantee: with no model_path and no huggingface_hub
    cache hit, preflight must report MODEL_MISSING, never attempt network
    access to fetch the model."""

    _install_fake_torch(cuda_available=False)
    _install_fake_transformers()
    # huggingface_hub deliberately absent -> falls back to explicit
    # "configure model_path" guidance rather than guessing/downloading.

    provider = VibeVoiceRealtimeProvider()  # no model_path configured
    result = provider.preflight()
    assert result.state == PreflightState.MODEL_MISSING
    assert not result.usable


def test_health_reports_preflight_summary():
    provider = VibeVoiceRealtimeProvider()
    health = provider.health()
    assert PreflightState.DEPENDENCY_MISSING.value in health
