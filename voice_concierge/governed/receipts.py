"""Correlated, machine-readable receipts for SP-VOICE-001 (directive §10).

Every request generates a receipt carrying the correlation ID so voice actions
are traceable through downstream agents, tools, logs, and audit. Transcript
content is retained per the configured retention policy; when retention is
``hash_only`` (the default) only a SHA-256 hash of the raw transcript is stored —
never the raw text.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .command_envelope import VoiceCommandEnvelope
from .flags import TranscriptRetention


def transcript_hash(raw_transcript: str) -> str:
    """Return ``sha256:<hex>`` for a raw transcript."""
    digest = hashlib.sha256(raw_transcript.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class VoiceReceipt:
    """Immutable machine-readable receipt for a single voice command."""

    command_id: str
    session_id: str
    source: str
    raw_transcript_hash: str
    normalized_intent: str
    risk_class: str
    policy_decision: str
    confirmation: str
    capability: str | None
    correlation_id: str
    result: str
    artifacts: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    # Only populated when retention policy is FULL; otherwise omitted.
    raw_transcript: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "command_id": self.command_id,
            "session_id": self.session_id,
            "source": self.source,
            "raw_transcript_hash": self.raw_transcript_hash,
            "normalized_intent": self.normalized_intent,
            "risk_class": self.risk_class,
            "policy_decision": self.policy_decision,
            "confirmation": self.confirmation,
            "capability": self.capability,
            "correlation_id": self.correlation_id,
            "result": self.result,
            "artifacts": list(self.artifacts),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
        if self.raw_transcript is not None:
            data["raw_transcript"] = self.raw_transcript
        return data


def build_receipt(
    envelope: VoiceCommandEnvelope,
    *,
    policy_decision: str,
    result: str,
    retention: TranscriptRetention = TranscriptRetention.HASH_ONLY,
    artifacts: list[str] | None = None,
    completed_at: str | None = None,
) -> VoiceReceipt:
    """Build a correlated receipt from an envelope and outcome.

    The correlation ID is copied verbatim from the envelope so the receipt joins
    the same causal chain as the originating request. Raw transcript is included
    only when retention is ``FULL``.
    """
    include_raw = retention == TranscriptRetention.FULL
    return VoiceReceipt(
        command_id=envelope.command_id,
        session_id=envelope.session_id,
        source=str(envelope.source),
        raw_transcript_hash=transcript_hash(envelope.raw_transcript),
        normalized_intent=envelope.normalized_intent,
        risk_class=str(envelope.risk_class),
        policy_decision=policy_decision,
        confirmation=str(envelope.confirmation_state),
        capability=envelope.requested_capability,
        correlation_id=envelope.correlation_id,
        result=result,
        artifacts=list(artifacts or []),
        completed_at=completed_at,
        raw_transcript=envelope.raw_transcript if include_raw else None,
    )
