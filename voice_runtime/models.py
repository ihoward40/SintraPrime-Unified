"""Provider-neutral speech request/response schemas.

These dataclasses are deliberately independent of any specific provider
(VibeVoice, browser Web Speech API, legacy SintraPrime speech modules, or a
future cloud provider). Providers translate to/from these shapes; nothing
in ``voice_runtime`` outside a provider implementation should ever see a
provider-specific type.

No I/O, no heavy dependencies — pure dataclasses only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .provenance import SpeechProvenance


def _new_request_id() -> str:
    return f"vreq-{uuid.uuid4().hex}"


@dataclass(frozen=True)
class AudioSource:
    """Abstraction over "where the audio bytes come from".

    Exactly one of ``inline_bytes`` or ``reference`` should be set. Using a
    reference (e.g. an artifact store key or file path recorded elsewhere)
    lets large audio payloads be handled without holding raw bytes in every
    layer of the call stack.
    """

    inline_bytes: bytes | None = None
    reference: str | None = None
    mime_type: str = "audio/wav"

    def __post_init__(self) -> None:
        if self.inline_bytes is None and self.reference is None:
            raise ValueError("AudioSource requires either inline_bytes or reference")


@dataclass(frozen=True)
class TenantContext:
    """Tenant/principal correlation metadata carried through every request.

    Mirrors the tenant-isolation contract already enforced by
    ``voice_concierge.governed`` / ``portal`` — this runtime never derives
    tenant/principal identity itself, it only carries whatever the caller
    (which must already be authenticated/authorized upstream) supplies.
    """

    tenant_id: str
    principal_id: str
    correlation_id: str | None = None


@dataclass(frozen=True)
class SpeechRecognitionRequest:
    """A provider-neutral request to transcribe audio to text."""

    audio: AudioSource
    tenant: TenantContext
    language: str = "en"
    hotwords: tuple[str, ...] = ()
    request_id: str = field(default_factory=_new_request_id)


@dataclass(frozen=True)
class TranscriptSegment:
    """One time-bounded segment of a structured transcript."""

    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    speaker_label: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class StructuredTranscript:
    """Provider-neutral structured transcription result."""

    text: str
    segments: tuple[TranscriptSegment, ...]
    provider_id: str
    model_id: str | None
    request_id: str
    provenance: SpeechProvenance
    language: str = "en"
    confidence: float | None = None


@dataclass(frozen=True)
class SpeechSynthesisRequest:
    """A provider-neutral request to synthesize text to speech."""

    text: str
    tenant: TenantContext
    voice_profile_id: str | None = None
    language: str = "en"
    output_format: str = "audio/wav"
    streaming: bool = False
    request_id: str = field(default_factory=_new_request_id)


@dataclass(frozen=True)
class SpeechArtifact:
    """Provider-neutral synthesized-audio artifact with provenance."""

    reference: str
    mime_type: str
    provider_id: str
    model_id: str | None
    request_id: str
    provenance: SpeechProvenance
    speaker_profile_id: str | None = None
    duration_seconds: float | None = None
    content_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
