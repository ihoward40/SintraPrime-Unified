"""Speech-runtime provenance record construction.

This module builds provenance metadata for every ASR/TTS operation. It does
**not** implement a competing audit ledger — it is designed so that
existing SintraPrime receipt/audit services (e.g. the hash-chained
``VoiceCommandEvent``/``VoiceCommandReceipt`` pattern in
``portal/models/voice_command.py``) can consume a ``SpeechProvenance``
record as an input when a speech operation is part of a governed voice
command flow. No network/database I/O happens here.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _new_provenance_id() -> str:
    return f"vprov-{uuid.uuid4().hex}"


def content_hash(data: bytes | str) -> str:
    """Deterministic SHA-256 hex digest for provenance input/output hashing.

    Accepts either raw bytes or text (encoded as UTF-8) so callers can hash
    a transcript string or raw audio bytes with the same helper.
    """

    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class RoutingDecisionRef:
    """A lightweight, serializable reference back to a routing decision.

    Kept intentionally small (not the full ``RoutingDecision`` object) so
    provenance records stay cheap to store/transmit; the full decision can
    still be looked up/logged separately by request_id if needed.
    """

    requested_capability: str
    selected_provider_id: str | None
    considered_provider_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeechProvenance:
    """Provenance metadata attached to every speech-runtime output.

    Every field here is intentionally neutral/serializable (str/float/None)
    so this can be embedded directly into a JSON payload consumed by the
    existing audit/receipt subsystem without any speech-runtime-specific
    deserialization logic.
    """

    provenance_id: str = field(default_factory=_new_provenance_id)
    request_id: str = ""
    provider_id: str = ""
    provider_version: str = ""
    model_id: str | None = None
    input_hash: str = ""
    output_hash: str | None = None
    tenant_id: str = ""
    principal_id: str = ""
    correlation_id: str | None = None
    routing: RoutingDecisionRef | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict suitable for existing audit/receipt storage."""

        return {
            "provenance_id": self.provenance_id,
            "request_id": self.request_id,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "model_id": self.model_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "correlation_id": self.correlation_id,
            "routing": (
                {
                    "requested_capability": self.routing.requested_capability,
                    "selected_provider_id": self.routing.selected_provider_id,
                    "considered_provider_ids": list(self.routing.considered_provider_ids),
                }
                if self.routing is not None
                else None
            ),
            "created_at": self.created_at.isoformat(),
        }
