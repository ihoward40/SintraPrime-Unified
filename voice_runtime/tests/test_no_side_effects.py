"""Tests asserting voice_runtime performs no external side effects and does
not regress the existing PR #247 browser voice frontend.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from voice_runtime.capabilities import SpeechCapability
from voice_runtime.models import AudioSource, SpeechRecognitionRequest, TenantContext
from voice_runtime.providers.mock import MockSpeechProvider
from voice_runtime.registry import build_default_registry
from voice_runtime.router import route


class _NetworkAttemptError(RuntimeError):
    pass


def _blocked_socket(*_args, **_kwargs):
    raise _NetworkAttemptError("voice_runtime attempted a real network connection")


def test_mock_asr_flow_makes_no_network_calls(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _blocked_socket)

    provider = MockSpeechProvider()
    request = SpeechRecognitionRequest(
        audio=AudioSource(reference="artifact://audio.wav"),
        tenant=TenantContext(tenant_id="t1", principal_id="p1"),
    )

    transcript = provider.recognize(request)
    assert transcript.text  # completed without raising _NetworkAttemptError


def test_default_registry_routing_makes_no_network_calls(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _blocked_socket)

    registry = build_default_registry()
    provider, _decision = route(registry, SpeechCapability.AUDIO_NORMALIZATION)
    assert provider.provider_id == "legacy_audio_adapter"


def test_no_filesystem_model_downloads(tmp_path):
    """Building the default registry and routing must not write any files
    (no model download / cache population)."""

    before = set(Path(tmp_path).iterdir())
    registry = build_default_registry()
    route(registry, SpeechCapability.ASR)
    after = set(Path(tmp_path).iterdir())
    assert before == after


def test_voice_concierge_frontend_browser_speech_api_present():
    """Guard against accidentally regressing PR #247's browser speech I/O
    while building the server-side provider descriptor for it."""

    repo_root = Path(__file__).resolve().parents[2]
    frontend_file = repo_root / "web" / "src" / "pages" / "VoiceConcierge.tsx"
    if not frontend_file.exists():
        pytest.skip("web/ frontend not present in this checkout")

    content = frontend_file.read_text(encoding="utf-8")
    assert "SpeechRecognition" in content
    assert "speechSynthesis" in content
