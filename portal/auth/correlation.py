"""Correlation context authority for request/audit traceability.

Provides immutable CorrelationContext objects and contextvar-based storage
for concurrent request isolation. Prevents tenant/actor override from
untrusted client input.
"""

from __future__ import annotations

import contextvars
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

# Contextvar for per-request/per-connection correlation context.
# This is safe for concurrent async requests — each task sees its own value.
_correlation_context: contextvars.ContextVar[CorrelationContext | None] = contextvars.ContextVar(
    "_correlation_context", default=None
)

# Valid identifier pattern: UUID, or alphanumeric with dashes/undersderscores, max 128 chars.
_VALID_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_MAX_IDENTIFIER_LEN = 128


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable correlation context carried through a request/task lifecycle."""

    request_id: str
    correlation_id: str
    causation_id: str | None = None
    actor_id: str | None = None
    tenant_id: str | None = None
    invocation_type: str = "request"
    source_transport: str = "http"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "actor_id": self.actor_id,
            "tenant_id": self.tenant_id,
            "invocation_type": self.invocation_type,
            "source_transport": self.source_transport,
            "timestamp": self.timestamp,
        }


def _is_valid_identifier(value: Any) -> bool:
    """Check if a value is a non-empty string matching the identifier pattern."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped or len(stripped) > _MAX_IDENTIFIER_LEN:
        return False
    return bool(_VALID_IDENTIFIER.match(stripped))


def generate_request_id() -> str:
    """Generate a secure, unique request identifier."""
    prefix = secrets.token_hex(4)
    suffix = str(uuid.uuid4())
    return f"req-{prefix}-{suffix}"


def generate_correlation_id() -> str:
    """Generate a secure, unique correlation identifier."""
    prefix = secrets.token_hex(4)
    suffix = str(uuid.uuid4())
    return f"corr-{prefix}-{suffix}"


def accept_inbound_identifier(value: str | None) -> str:
    """Accept a valid inbound identifier, or generate a new one if missing/invalid/malformed."""
    if value is None:
        return generate_request_id()
    if not _is_valid_identifier(value):
        return generate_request_id()
    return value.strip()


def prevent_tenant_override(trusted_tenant_id: str, client_supplied: str | None) -> str:
    """Return the trusted tenant ID, ignoring any client-supplied value.

    The client can NEVER override the tenant identity derived from trusted claims.
    """
    if not isinstance(trusted_tenant_id, str) or not trusted_tenant_id.strip():
        raise ValueError("trusted_tenant_id must be a non-empty string")
    return trusted_tenant_id.strip()


def prevent_actor_override(trusted_actor_id: str, client_supplied: str | None) -> str:
    """Return the trusted actor ID, ignoring any client-supplied value."""
    if not isinstance(trusted_actor_id, str) or not trusted_actor_id.strip():
        raise ValueError("trusted_actor_id must be a non-empty string")
    return trusted_actor_id.strip()


def get_current_context() -> CorrelationContext | None:
    """Return the current CorrelationContext from contextvars, or None."""
    return _correlation_context.get()


def bind_context(ctx: CorrelationContext) -> _ContextBinder:
    """Return a context manager that sets and cleans up the contextvar."""
    return _ContextBinder(ctx)


class _ContextBinder:
    """Context manager that binds a CorrelationContext to the contextvar."""

    def __init__(self, ctx: CorrelationContext) -> None:
        self._ctx = ctx
        self._token: contextvars.Token[CorrelationContext | None] | None = None

    def __enter__(self) -> CorrelationContext:
        self._token = _correlation_context.set(self._ctx)
        return self._ctx

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._token is not None:
            _correlation_context.reset(self._token)
            self._token = None


def clear_context() -> None:
    """Explicitly clear the current correlation context."""
    _correlation_context.set(None)


def propagate_to_child(parent: CorrelationContext, invocation_type: str = "service") -> CorrelationContext:
    """Create a child context for nested service calls.

    The child gets a new request_id but preserves the correlation_id.
    The causation_id is set to the parent request_id to maintain the causal chain.
    Actor and tenant are inherited from the parent.
    """
    return CorrelationContext(
        request_id=generate_request_id(),
        correlation_id=parent.correlation_id,
        causation_id=parent.request_id,
        actor_id=parent.actor_id,
        tenant_id=parent.tenant_id,
        invocation_type=invocation_type,
        source_transport=parent.source_transport,
        timestamp=datetime.now(UTC).isoformat(),
    )


def create_context(
    *,
    actor_id: str | None = None,
    tenant_id: str | None = None,
    invocation_type: str = "request",
    source_transport: str = "http",
    inbound_request_id: str | None = None,
    inbound_correlation_id: str | None = None,
    causation_id: str | None = None,
) -> CorrelationContext:
    """Create a new CorrelationContext, accepting valid inbound IDs or generating new ones."""
    return CorrelationContext(
        request_id=accept_inbound_identifier(inbound_request_id),
        correlation_id=accept_inbound_identifier(inbound_correlation_id),
        causation_id=causation_id.strip() if isinstance(causation_id, str) and causation_id.strip() else None,
        actor_id=actor_id,
        tenant_id=tenant_id,
        invocation_type=invocation_type,
        source_transport=source_transport,
    )
