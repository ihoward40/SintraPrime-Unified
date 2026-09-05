"""Tests for provider-neutral models and provenance/content-hash determinism."""

from __future__ import annotations

from voice_runtime.models import (
    AudioSource,
    SpeechArtifact,
    StructuredTranscript,
    TenantContext,
    TranscriptSegment,
)
from voice_runtime.provenance import SpeechProvenance, content_hash


def test_content_hash_deterministic_for_same_input():
    assert content_hash("hello") == content_hash("hello")
    assert content_hash(b"hello") == content_hash("hello")


def test_content_hash_differs_for_different_input():
    assert content_hash("hello") != content_hash("world")


def test_audio_source_requires_bytes_or_reference():
    import pytest

    with pytest.raises(ValueError, match="AudioSource requires"):
        AudioSource()


def test_audio_source_accepts_reference_only():
    source = AudioSource(reference="artifact://x.wav")
    assert source.inline_bytes is None


def test_structured_transcript_roundtrip_fields():
    provenance = SpeechProvenance(
        request_id="vreq-1",
        provider_id="mock",
        provider_version="1.0.0",
        input_hash=content_hash("audio"),
        tenant_id="tenant-1",
        principal_id="user-1",
    )
    transcript = StructuredTranscript(
        text="hello",
        segments=(TranscriptSegment(text="hello", confidence=0.9),),
        provider_id="mock",
        model_id="mock-asr-v1",
        request_id="vreq-1",
        provenance=provenance,
    )
    assert transcript.text == "hello"
    assert transcript.segments[0].confidence == 0.9
    assert transcript.provenance.provider_id == "mock"


def test_speech_artifact_provenance_serializes_to_dict():
    provenance = SpeechProvenance(
        request_id="vreq-2",
        provider_id="mock",
        provider_version="1.0.0",
        tenant_id="tenant-1",
        principal_id="user-1",
        correlation_id="corr-9",
    )
    artifact = SpeechArtifact(
        reference="mock://x",
        mime_type="audio/wav",
        provider_id="mock",
        model_id="mock-tts-v1",
        request_id="vreq-2",
        provenance=provenance,
        content_hash=content_hash("hello"),
    )

    payload = artifact.provenance.to_dict()
    assert payload["request_id"] == "vreq-2"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["correlation_id"] == "corr-9"
    assert "created_at" in payload


def test_tenant_context_is_immutable():
    import dataclasses

    tenant = TenantContext(tenant_id="t1", principal_id="p1")
    assert dataclasses.is_dataclass(tenant)
    try:
        tenant.tenant_id = "other"  # type: ignore[misc]
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    assert raised
