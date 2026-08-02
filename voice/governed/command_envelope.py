"""Immutable voice command envelope for SP-VOICE-001 — Governed Voice Operations.

Every voice-originated request is normalized into a single frozen, typed
structure equivalent to the typed-request command envelope. The envelope is the
only object that crosses the governance boundary; voice never carries authority
of its own.

Design invariants (see SP-VOICE-001 directive §2):
- Immutable after creation (``frozen=True``).
- Correlation ID propagated through all downstream agents, tools, logs, receipts.
- Raw transcript and normalized intent preserved separately.
- Transcription confidence is NEVER treated as authorization.

Naming conventions mirror ``portal/auth/correlation.py`` ID generation style.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class VoiceSource(StrEnum):
    """Origin transport of a voice command. No source implies authority."""

    DESKTOP_VOICE = "desktop_voice"
    REMOTE_VOICE = "remote_voice"
    TRANSCRIPT_IMPORT = "transcript_import"


class RiskClass(StrEnum):
    """Deterministic policy-first risk classes (directive §3)."""

    READ = "read"
    DRAFT = "draft"
    WRITE = "write"
    SENSITIVE_WRITE = "sensitive_write"
    PROHIBITED = "prohibited"


class ConfirmationState(StrEnum):
    """Lifecycle of a confirmation requirement (directive §2 / §4)."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    CONFIRMED = "confirmed"
    DENIED = "denied"
    EXPIRED = "expired"


def generate_command_id() -> str:
    """Generate a secure, unique voice command identifier (``vcmd-...``)."""
    return f"vcmd-{secrets.token_hex(4)}-{uuid.uuid4()}"


def generate_session_id() -> str:
    """Generate a secure, unique voice session identifier (``vsess-...``)."""
    return f"vsess-{secrets.token_hex(4)}-{uuid.uuid4()}"


def generate_correlation_id() -> str:
    """Generate a correlation identifier (``corr-...``), matching auth style."""
    return f"corr-{secrets.token_hex(4)}-{uuid.uuid4()}"


@dataclass(frozen=True)
class VoiceCommandEnvelope:
    """Immutable, typed representation of a single voice-originated request.

    The envelope carries no execution capability. It is a request record that
    existing SintraPrime policy inspects to decide, record, approve, execute, or
    refuse. ``risk_class`` and ``confirmation_state`` are populated by the
    deterministic classifier and policy layers, never by the caller's claim.
    """

    command_id: str
    session_id: str
    principal_id: str
    source: VoiceSource
    raw_transcript: str
    normalized_intent: str
    requested_capability: str | None
    target_resource: str | None
    risk_class: RiskClass
    confirmation_state: ConfirmationState
    correlation_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def with_confirmation_state(self, state: ConfirmationState) -> VoiceCommandEnvelope:
        """Return a NEW envelope with an updated confirmation state.

        The original is never mutated — the state machine advances by producing
        successive immutable envelopes, preserving a tamper-evident chain.
        """
        return replace(self, confirmation_state=state)

    def as_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "session_id": self.session_id,
            "principal_id": self.principal_id,
            "source": str(self.source),
            "raw_transcript": self.raw_transcript,
            "normalized_intent": self.normalized_intent,
            "requested_capability": self.requested_capability,
            "target_resource": self.target_resource,
            "risk_class": str(self.risk_class),
            "confirmation_state": str(self.confirmation_state),
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
        }


def create_envelope(
    *,
    session_id: str,
    principal_id: str,
    source: VoiceSource,
    raw_transcript: str,
    normalized_intent: str,
    risk_class: RiskClass,
    confirmation_state: ConfirmationState,
    requested_capability: str | None = None,
    target_resource: str | None = None,
    correlation_id: str | None = None,
    command_id: str | None = None,
) -> VoiceCommandEnvelope:
    """Build a fully-formed immutable envelope, generating IDs when absent.

    ``principal_id`` and ``raw_transcript`` must be non-empty; a voice request
    without an attributable principal is not a governable request.
    """
    if not isinstance(principal_id, str) or not principal_id.strip():
        raise ValueError("principal_id must be a non-empty string")
    if not isinstance(raw_transcript, str) or not raw_transcript.strip():
        raise ValueError("raw_transcript must be a non-empty string")
    return VoiceCommandEnvelope(
        command_id=command_id or generate_command_id(),
        session_id=session_id,
        principal_id=principal_id.strip(),
        source=VoiceSource(source),
        raw_transcript=raw_transcript,
        normalized_intent=normalized_intent,
        requested_capability=requested_capability,
        target_resource=target_resource,
        risk_class=RiskClass(risk_class),
        confirmation_state=ConfirmationState(confirmation_state),
        correlation_id=correlation_id or generate_correlation_id(),
    )
