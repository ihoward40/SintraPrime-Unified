"""Audit event envelope for structured, tamper-evident audit logging.

Defines the canonical AuditEvent schema and secret redaction utilities.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .correlation import get_current_context


class ActorType(StrEnum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    SYSTEM = "system"
    CLI = "cli"


class Transport(StrEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    BACKGROUND = "background"
    SCHEDULER = "scheduler"
    WEBHOOK = "webhook"
    CLI = "cli"


class Outcome(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILURE = "failure"


# Keys (lowercased) whose values must be redacted from audit metadata/logs.
REDACTED_FIELDS = frozenset({
    "password",
    "token",
    "bearer",
    "secret",
    "private_key",
    "privatekey",
    "cookie",
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "session_id",
    "csrf_token",
})

_REDACTED_VALUE = "[REDACTED]"


def redact_secrets(data: Any) -> Any:
    """Recursively redact secret fields from a dict/list structure."""
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if key_lower in REDACTED_FIELDS:
                redacted[key] = _REDACTED_VALUE
            else:
                redacted[key] = redact_secrets(value)
        return redacted
    if isinstance(data, list):
        return [redact_secrets(item) for item in data]
    return data


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event envelope."""

    schema_version: str
    event_id: str
    request_id: str | None
    correlation_id: str | None
    causation_id: str | None
    occurred_at: str
    actor_id: str | None
    actor_type: str
    tenant_id: str | None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    source_transport: str = "http"
    source_entrypoint: str | None = None
    outcome: str = "success"
    denial_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    integrity_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "source_transport": self.source_transport,
            "source_entrypoint": self.source_entrypoint,
            "outcome": self.outcome,
            "denial_reason": self.denial_reason,
            "metadata": self.metadata,
            "integrity_hash": self.integrity_hash,
        }


def compute_integrity_hash(event: AuditEvent | dict[str, Any]) -> str:
    """Compute a SHA-256 hash over the canonical JSON of the event, excluding the hash field."""
    data = event.as_dict() if isinstance(event, AuditEvent) else dict(event)
    data.pop("integrity_hash", None)
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_audit_event(
    *,
    action: str,
    actor_id: str | None = None,
    actor_type: ActorType = ActorType.USER,
    tenant_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    source_transport: Transport = Transport.HTTP,
    source_entrypoint: str | None = None,
    outcome: Outcome = Outcome.SUCCESS,
    denial_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Build an AuditEvent, auto-populating IDs and timestamps from the current correlation context."""
    ctx = get_current_context()
    request_id = ctx.request_id if ctx else None
    correlation_id = ctx.correlation_id if ctx else None
    causation_id = ctx.causation_id if ctx else None
    # If actor/tenant not explicitly provided, inherit from context.
    effective_actor = actor_id or (ctx.actor_id if ctx else None)
    effective_tenant = tenant_id or (ctx.tenant_id if ctx else None)

    event = AuditEvent(
        schema_version="1.0",
        event_id=str(uuid.uuid4()),
        request_id=request_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        occurred_at=datetime.now(UTC).isoformat(),
        actor_id=effective_actor,
        actor_type=actor_type.value,
        tenant_id=effective_tenant,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        source_transport=source_transport.value,
        source_entrypoint=source_entrypoint,
        outcome=outcome.value,
        denial_reason=denial_reason,
        metadata=redact_secrets(metadata) if metadata else {},
        integrity_hash="",
    )
    return AuditEvent(
        schema_version=event.schema_version,
        event_id=event.event_id,
        request_id=event.request_id,
        correlation_id=event.correlation_id,
        causation_id=event.causation_id,
        occurred_at=event.occurred_at,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        tenant_id=event.tenant_id,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        source_transport=event.source_transport,
        source_entrypoint=event.source_entrypoint,
        outcome=event.outcome,
        denial_reason=event.denial_reason,
        metadata=event.metadata,
        integrity_hash=compute_integrity_hash(event),
    )


def serialize_for_log(event: AuditEvent) -> dict[str, Any]:
    """Produce a safe-to-log dict with secrets redacted."""
    data = event.as_dict()
    data["metadata"] = redact_secrets(data.get("metadata", {}))
    return data
