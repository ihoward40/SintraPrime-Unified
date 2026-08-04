"""Read-only projection schemas for Mission Control Foundation.

These Pydantic models are the wire contract for the read-only projection
endpoints exposed by the Mission Control router. They are pure read models —
no write or mutation fields are defined.

The schemas project three ADR-002 concerns:

1. Intent ledger — command records, lifecycle events, receipts.
2. Execution-state — run-control projections, transition events.
3. Correlation/causation — causal chains linking intents to dispatch
   attempts and execution outcomes.

The Sigma continuation condition (ADR-002 Section 2.5 — executor continuation
after lease expiry during Brain unavailability) is surfaced as a read-only
gate status, never as a mutation surface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Intent projection ─────────────────────────────────────────────────────────


class CommandEventProjection(BaseModel):
    """Single lifecycle event from the command's hash-chained event log."""

    id: str
    sequence: int
    event_type: str
    state: str
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str | None = None
    event_hash: str
    created_at: datetime | None = None


class CommandReceiptProjection(BaseModel):
    """Immutable receipt linking the command outcome to audit/evidence."""

    id: str
    receipt_type: str
    receipt_hash: str
    audit_log_id: str | None = None
    evidence_refs: list[Any] = Field(default_factory=list)
    created_at: datetime | None = None


class CommandProjection(BaseModel):
    """Read-only projection of a Mission Control command (intent record)."""

    id: str
    tenant_id: str
    requested_by: str
    command_type: str
    target_type: str
    target_id: str
    idempotency_key: str
    request_hash: str
    state: str
    reason_code: str | None = None
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    audit_log_id: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    events: list[CommandEventProjection] = Field(default_factory=list)
    receipts: list[CommandReceiptProjection] = Field(default_factory=list)


class CommandListResponse(BaseModel):
    """Paginated list of command projections."""

    items: list[CommandProjection]
    total: int
    limit: int
    offset: int


# ── Execution-state projection ────────────────────────────────────────────────


class RunControlEventProjection(BaseModel):
    """Single transition event from the run-control hash-chained event log."""

    id: str
    sequence: int
    event_type: str
    previous_state: str
    new_state: str
    previous_version: int
    new_version: int
    principal_id: str | None = None
    command_id: str | None = None
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    workflow_status_observed_at: datetime | None = None
    previous_event_hash: str | None = None
    event_hash: str
    event_schema_version: int = 1
    created_at: datetime | None = None


class RunControlProjection(BaseModel):
    """Read-only projection of a Mission Control run-control record."""

    id: str
    tenant_id: str
    workflow_id: str
    command_id: str | None = None
    state: str
    workflow_status_snapshot: str
    workflow_status_observed_at: datetime | None = None
    workflow_source: str | None = None
    workflow_version_snapshot: int | None = None
    state_version: int
    projection_schema_version: int
    pause_reason: str | None = None
    requested_by: str | None = None
    requested_at: datetime | None = None
    confirmation_ref: str | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    paused_at: datetime | None = None
    failed_at: datetime | None = None
    timed_out_at: datetime | None = None
    superseded_at: datetime | None = None
    incident_id: str | None = None
    recovery_ref: str | None = None
    terminal_reason_code: str | None = None
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    events: list[RunControlEventProjection] = Field(default_factory=list)


class RunControlListResponse(BaseModel):
    """Paginated list of run-control projections."""

    items: list[RunControlProjection]
    total: int
    limit: int
    offset: int


# ── Correlation / causation chain ─────────────────────────────────────────────


class CausationLink(BaseModel):
    """A single link in a causation chain.

    Links are assembled from command events, run-control events, and command
    receipts. The chain shows the causal progression from intent ingestion
    through dispatch to terminal state.
    """

    source_type: Literal["command_event", "run_control_event", "receipt"]
    source_id: str
    sequence: int
    event_type: str
    state: str
    hash: str
    previous_hash: str | None = None
    created_at: datetime | None = None
    command_id: str | None = None
    run_control_id: str | None = None


class CausationChain(BaseModel):
    """Ordered causation chain for a given command/intent.

    The chain starts at the command's first event and follows the hash chain
    through events, receipts, and any linked run-control transitions.
    """

    command_id: str
    tenant_id: str
    command_type: str
    command_state: str
    links: list[CausationLink] = Field(default_factory=list)


# ── Sigma gate status ─────────────────────────────────────────────────────────


class SigmaGateStatus(BaseModel):
    """Read-only status of the SIGMA_LEASE_EXPIRY_CONTINUATION_GATE.

    The gate is defined by ADR-002 Section 2.5 (Sigma condition). It blocks
    cancellation controls until explicit criteria for executor continuation
    after lease expiry during Brain unavailability are defined and
    implemented.

    This is a read-only status — no mutation surface is exposed.
    """

    gate_id: Literal["SIGMA_LEASE_EXPIRY_CONTINUATION_GATE"] = (
        "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE"
    )
    state: Literal["BLOCKED", "DEFINED", "SATISFIED"]
    description: str
    criteria: list[str]
    cancellation_controls: Literal["DISABLED", "ENABLED"] = "DISABLED"
    blocking_phase_3b: bool = True


class CancellationControlStatus(BaseModel):
    """Read-only status of all cancellation control surfaces.

    All three ADR-002 cancellation scopes (execution, tenant, platform) are
    reported as DISABLED. This is a read-only projection — no mutation
    endpoint exists.
    """

    execution_scoped: Literal["DISABLED", "ENABLED"] = "DISABLED"
    tenant_scoped: Literal["DISABLED", "ENABLED"] = "DISABLED"
    platform_break_glass: Literal["DISABLED", "ENABLED"] = "DISABLED"
    gate: SigmaGateStatus
    reason: str = (
        "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE is BLOCKED. Cancellation controls are disabled until the gate is SATISFIED."
    )
