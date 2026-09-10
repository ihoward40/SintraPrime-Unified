"""Tests for the mock provider's ASR/TTS behavior, models, and provenance."""

from __future__ import annotations

from voice_runtime.models import (
    AudioSource,
    SpeechRecognitionRequest,
    SpeechSynthesisRequest,
    TenantContext,
)
from voice_runtime.preflight import PreflightState
from voice_runtime.provenance import content_hash
from voice_runtime.providers.mock import MockSpeechProvider


def _tenant() -> TenantContext:
    return TenantContext(tenant_id="tenant-1", principal_id="user-1", correlation_id="corr-1")


def test_mock_provider_preflight_available():
    provider = MockSpeechProvider()
    result = provider.preflight()
    assert result.state == PreflightState.AVAILABLE
    assert result.usable


def test_mock_provider_disabled_preflight():
    provider = MockSpeechProvider(enabled=False)
    result = provider.preflight()
    assert result.state == PreflightState.DISABLED
    assert not result.usable


def test_mock_recognize_produces_structured_transcript():
    provider = MockSpeechProvider()
    request = SpeechRecognitionRequest(
        audio=AudioSource(reference="artifact://some-audio.wav"),
        tenant=_tenant(),
    )

    transcript = provider.recognize(request)

    assert transcript.text
    assert transcript.provider_id == "mock"
    assert transcript.request_id == request.request_id
    assert len(transcript.segments) == 1
    assert transcript.provenance.tenant_id == "tenant-1"
    assert transcript.provenance.principal_id == "user-1"
    assert transcript.provenance.correlation_id == "corr-1"
    assert transcript.provenance.provider_id == "mock"
    assert transcript.provenance.input_hash == content_hash("artifact://some-audio.wav")
    assert transcript.provenance.output_hash == content_hash(transcript.text)


def test_mock_recognize_with_inline_bytes():
    provider = MockSpeechProvider()
    request = SpeechRecognitionRequest(
        audio=AudioSource(inline_bytes=b"\x00\x01\x02\x03"),
        tenant=_tenant(),
    )

    transcript = provider.recognize(request)
    assert transcript.provenance.input_hash == content_hash(b"\x00\x01\x02\x03")


def test_mock_synthesize_produces_speech_artifact():
    provider = MockSpeechProvider()
    request = SpeechSynthesisRequest(text="hello world", tenant=_tenant(), voice_profile_id="voice-a")

    artifact = provider.synthesize(request)

    assert artifact.reference.startswith("mock://")
    assert artifact.provider_id == "mock"
    assert artifact.request_id == request.request_id
    assert artifact.speaker_profile_id == "voice-a"
    assert artifact.content_hash == content_hash("hello world")
    assert artifact.provenance.output_hash == artifact.content_hash


def test_mock_provider_no_real_audio_bytes_produced():
    """The mock provider must never produce real synthesized audio bytes —
    only a reference string, confirming no real inference occurs."""

    provider = MockSpeechProvider()
    request = SpeechSynthesisRequest(text="hello", tenant=_tenant())

    artifact = provider.synthesize(request)

    assert artifact.reference == f"mock://synthesized/{request.request_id}"
    assert artifact.duration_seconds == 0.0
