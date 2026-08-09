"""Deterministic mock speech provider.

Used for tests and as a safe, always-available default provider. Performs
no real audio inference, no model loading, and no network/filesystem I/O —
every ASR result is a fixed transcript derived deterministically from the
request, and every TTS result is a synthetic artifact reference with a
content hash computed from the input text (not real audio bytes).
"""

from __future__ import annotations

from ..capabilities import SpeechCapability
from ..models import (
    SpeechArtifact,
    SpeechRecognitionRequest,
    SpeechSynthesisRequest,
    StructuredTranscript,
    TranscriptSegment,
)
from ..preflight import PreflightResult
from ..provenance import SpeechProvenance, content_hash
from .base import BaseSpeechProvider


class MockSpeechProvider(BaseSpeechProvider):
    """Always-available, deterministic mock ASR/TTS provider.

    Every output is clearly a simulation: transcripts are literal fixed
    strings, and synthesized "audio" is represented by a ``mock://``
    reference with no underlying audio bytes ever produced.
    """

    provider_id = "mock"
    provider_version = "1.0.0"
    _capabilities = frozenset(
        {
            SpeechCapability.ASR,
            SpeechCapability.TTS,
            SpeechCapability.STREAMING_TTS,
            SpeechCapability.AUDIO_NORMALIZATION,
        }
    )

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def preflight(self) -> PreflightResult:
        if not self._enabled:
            return PreflightResult.disabled()
        return PreflightResult.available(detail="mock provider requires no dependencies")

    def health(self) -> str:
        return "ok (mock, no real inference)"

    def recognize(self, request: SpeechRecognitionRequest) -> StructuredTranscript:
        source_desc = request.audio.reference or "<inline-bytes>"
        text = f"[mock transcript for {source_desc}]"
        input_bytes = request.audio.inline_bytes or source_desc.encode("utf-8")
        provenance = SpeechProvenance(
            request_id=request.request_id,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            model_id="mock-asr-v1",
            input_hash=content_hash(input_bytes),
            output_hash=content_hash(text),
            tenant_id=request.tenant.tenant_id,
            principal_id=request.tenant.principal_id,
            correlation_id=request.tenant.correlation_id,
        )
        return StructuredTranscript(
            text=text,
            segments=(
                TranscriptSegment(
                    text=text,
                    start_seconds=0.0,
                    end_seconds=1.0,
                    speaker_label="speaker-1",
                    confidence=1.0,
                ),
            ),
            provider_id=self.provider_id,
            model_id="mock-asr-v1",
            request_id=request.request_id,
            provenance=provenance,
            language=request.language,
            confidence=1.0,
        )

    def synthesize(self, request: SpeechSynthesisRequest) -> SpeechArtifact:
        reference = f"mock://synthesized/{request.request_id}"
        output_hash = content_hash(request.text)
        provenance = SpeechProvenance(
            request_id=request.request_id,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            model_id="mock-tts-v1",
            input_hash=content_hash(request.text),
            output_hash=output_hash,
            tenant_id=request.tenant.tenant_id,
            principal_id=request.tenant.principal_id,
            correlation_id=request.tenant.correlation_id,
        )
        return SpeechArtifact(
            reference=reference,
            mime_type=request.output_format,
            provider_id=self.provider_id,
            model_id="mock-tts-v1",
            request_id=request.request_id,
            provenance=provenance,
            speaker_profile_id=request.voice_profile_id,
            duration_seconds=0.0,
            content_hash=output_hash,
        )
