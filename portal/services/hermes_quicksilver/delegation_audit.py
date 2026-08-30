"""Recursive redaction and deterministic serialization for Quicksilver audit events.

Audit events are persisted through the existing SintraPrime ``AuditLog`` model
via the ``portal.services.audit_service.audit`` function. That ledger is an
append-only, hash-chained table owned by the portal. The Quicksilver adapter
prepares a deterministic JSON payload and delegates persistence to that service.

Because persistence requires an async SQLAlchemy session, the adapter exposes a
synchronous ``prepare_record`` helper and an async ``persist_event`` coroutine.
Service callers are responsible for providing the session from the existing
portal dependency layer.
"""

from __future__ import annotations

import json
from typing import Any

from portal.models.hermes_quicksilver import (
    Decision,
    DelegationRequest,
    DelegationResult,
    HermesDelegationAuditEvent,
    ResolvedMapping,
)

# Keys (case-insensitive) whose values must be redacted from audit payloads.
_REDACTED_FIELDS = frozenset({
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
    "chain_of_thought",
    "model_reasoning",
})

_REDACTED_VALUE = "[REDACTED]"

# Known event types for Increment One.
EVENT_PROFILE_DISCOVERY_REQUESTED = "hermes.profile.discovery.requested"
EVENT_PROFILE_DISCOVERY_COMPLETED = "hermes.profile.discovery.completed"
EVENT_PROFILE_DISCOVERY_FAILED = "hermes.profile.discovery.failed"
EVENT_SPECIALIST_MAPPING_VALIDATED = "hermes.specialist.mapping.validated"
EVENT_SPECIALIST_MAPPING_DENIED = "hermes.specialist.mapping.denied"
EVENT_POLICY_HARD_DENIED = "hermes.policy.hard_denied"
EVENT_COMPATIBILITY_REJECTED = "hermes.compatibility.rejected"


class AuditRedactionError(Exception):
    """Raised when a secret is detected in a value that cannot be safely audited."""


class DelegationAuditBuilder:
    """Construct deterministic, recursively redacted audit events."""

    def __init__(self, source_version: str, redaction_version: str = "1.0.0"):
        self.source_version = source_version
        self.redaction_version = redaction_version

    def build(
        self,
        event_type: str,
        request: DelegationRequest,
        result: DelegationResult,
        mapping: ResolvedMapping | None = None,
        approval_reference: str | None = None,
    ) -> HermesDelegationAuditEvent:
        """Build a redacted audit event from a delegation attempt."""
        redacted_context = _redact_secrets(request.context)
        redacted_data = _redact_secrets(result.data)
        redaction_flag = _redaction_occurred(redacted_context) or _redaction_occurred(redacted_data)

        return HermesDelegationAuditEvent(
            event_type=event_type,
            tenant_id=request.tenant_id,
            actor_id=request.actor_id,
            case_id=request.case_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            specialist_id=request.specialist_id,
            hermes_profile_id=(mapping.hermes_profile_id if mapping else None),
            operation=request.operation,
            decision=result.decision,
            policy_reason_code=result.reason_code,
            approval_reference=approval_reference,
            result_status=("completed" if result.decision == Decision.ALLOW else None),
            error_class=None,
            duration_ms=result.duration_ms,
            source_version=self.source_version,
            redaction_version=self.redaction_version,
            metadata={
                "redaction_applied": redaction_flag,
                "context": redacted_context,
                "data": redacted_data,
            },
        )

    def build_denial(
        self,
        event_type: str,
        request: DelegationRequest,
        reason_code: str,
        duration_ms: int = 0,
    ) -> HermesDelegationAuditEvent:
        """Build a redacted audit event for a pre-invocation denial."""
        redacted_context = _redact_secrets(request.context)
        redaction_flag = _redaction_occurred(redacted_context)

        return HermesDelegationAuditEvent(
            event_type=event_type,
            tenant_id=request.tenant_id,
            actor_id=request.actor_id,
            case_id=request.case_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            specialist_id=request.specialist_id,
            hermes_profile_id=None,
            operation=request.operation,
            decision=Decision.DENY,
            policy_reason_code=reason_code,
            approval_reference=None,
            result_status=None,
            error_class=None,
            duration_ms=duration_ms,
            source_version=self.source_version,
            redaction_version=self.redaction_version,
            metadata={
                "redaction_applied": redaction_flag,
                "context": redacted_context,
            },
        )

    @staticmethod
    def serialize(event: HermesDelegationAuditEvent) -> str:
        """Deterministic JSON serialization."""
        return json.dumps(
            event.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def _redact_secrets(data: Any) -> Any:
    """Recursively redact secret fields from dict/list/tuple structures.

    Rejects only values that are not safely serializable (e.g., arbitrary
    non-Pydantic objects without a deterministic representation).
    """
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if key_lower in _REDACTED_FIELDS:
                redacted[key] = _REDACTED_VALUE
            else:
                redacted[key] = _redact_secrets(value)
        return redacted
    if isinstance(data, (list, tuple)):
        return [_redact_secrets(item) for item in data]
    if isinstance(data, str):
        value_lower = data.lower()
        if any(prohibited in value_lower for prohibited in _REDACTED_FIELDS):
            return _REDACTED_VALUE
        return data
    if isinstance(data, (int, float, bool, type(None))):
        return data
    # Reject arbitrary objects that could leak sensitive repr or paths.
    raise AuditRedactionError(
        f"cannot safely audit value of type {type(data).__name__}"
    )


def _redaction_occurred(data: Any) -> bool:
    """Return True if any value in the structure equals the redaction marker."""
    if isinstance(data, dict):
        return any(_redaction_occurred(v) for v in data.values())
    if isinstance(data, (list, tuple)):
        return any(_redaction_occurred(item) for item in data)
    return data == _REDACTED_VALUE
