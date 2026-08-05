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

Review corrections applied:
- Centralized redaction utilities (REDACTED, redact_dict, redact_evidence_refs,
  redact_error, redact_ref).
- Split list projections (CommandSummary, RunControlSummary) from detail
  projections (CommandProjection, RunControlProjection) to keep list
  responses lightweight and free of sensitive payloads.
- Freshness metadata (FreshnessMeta, classify_freshness) on every projection
  response so consumers can detect stale reads.
- Causation graph safety metadata (truncated, total_links, warnings) and
  MAX_CAUSATION_LINKS cap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Redaction utilities ──────────────────────────────────────────────────────

REDACTED = "REDACTED"

#: Payload field names that are safe to expose in projections. Any field not
#: in this set is replaced with ``REDACTED`` by :func:`redact_dict`.
EXPOSED_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "workflow_id",
        "workflow_source",
        "state",
        "command_type",
        "target_type",
        "target_id",
    }
)


def redact_dict(data: dict[str, Any], exposed: frozenset[str]) -> dict[str, Any]:
    """Return a copy of *data* where non-exposed values are replaced with REDACTED.

    Keys whose names appear in *exposed* retain their original values; all
    other values are replaced with the ``REDACTED`` sentinel.
    """
    return {key: (value if key in exposed else REDACTED) for key, value in data.items()}


def redact_evidence_refs(refs: list[Any]) -> list[str]:
    """Return a list of REDACTED sentinels matching the length of *refs*.

    The count is preserved so consumers can know how many evidence items exist
    without seeing the actual references.
    """
    return [REDACTED] * len(refs)


def redact_error(text: str | None) -> str | None:
    """Redact a free-text error field, preserving None."""
    if text:
        return REDACTED
    return None


def redact_ref(ref: str | None) -> str | None:
    """Redact a reference field, preserving None."""
    if ref is not None:
        return REDACTED
    return None


# ── Freshness metadata ────────────────────────────────────────────────────────


def _ensure_aware(dt: datetime) -> datetime:
    """Normalize a timezone-naive datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class FreshnessMeta(BaseModel):
    """Freshness metadata describing how current a projection is.

    ``generated_at`` is when the projection was assembled. ``source_updated_at``
    is the latest timestamp from the underlying source records. The ``state``
    field classifies the gap between the two:

    - LIVE: gap <= 5 seconds
    - DELAYED: gap <= 60 seconds
    - STALE: gap > 60 seconds
    - UNKNOWN: source_updated_at is unavailable
    """

    generated_at: datetime
    source_updated_at: datetime | None = None
    freshness_seconds: float | None = None
    state: Literal["LIVE", "DELAYED", "STALE", "UNKNOWN"]


def classify_freshness(
    generated_at: datetime,
    source_updated_at: datetime | None,
) -> FreshnessMeta:
    """Build a FreshnessMeta from the generation and source-update timestamps.

    Timezone-naive datetimes (common from SQLite) are normalized to UTC before
    comparison.
    """
    generated_at = _ensure_aware(generated_at)
    if source_updated_at is None:
        return FreshnessMeta(
            generated_at=generated_at,
            source_updated_at=None,
            freshness_seconds=None,
            state="UNKNOWN",
        )
    source_updated_at = _ensure_aware(source_updated_at)
    delta = (generated_at - source_updated_at).total_seconds()
    if delta <= 5:
        state: Literal["LIVE", "DELAYED", "STALE", "UNKNOWN"] = "LIVE"
    elif delta <= 60:
        state = "DELAYED"
    else:
        state = "STALE"
    return FreshnessMeta(
        generated_at=generated_at,
        source_updated_at=source_updated_at,
        freshness_seconds=delta,
        state=state,
    )


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


class CommandSummary(BaseModel):
    """Lightweight command summary for list responses.

    Excludes payload, events, and receipts. Includes ``event_count`` and
    ``receipt_count`` so consumers can gauge the command's lifecycle depth
    without loading sensitive detail.
    """

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
    audit_log_id: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    event_count: int = 0
    receipt_count: int = 0


class CommandProjection(BaseModel):
    """Read-only detail projection of a Mission Control command (intent record).

    Payloads and metadata are redacted via :func:`redact_dict` so only fields
    in :data:`EXPOSED_PAYLOAD_FIELDS` are visible. Evidence refs are redacted
    to a count-preserving list of REDACTED sentinels.
    """

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
    freshness: FreshnessMeta | None = None


class CommandListResponse(BaseModel):
    """Paginated list of command summaries with freshness metadata."""

    items: list[CommandSummary]
    total: int
    limit: int
    offset: int
    freshness: FreshnessMeta | None = None


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


class RunControlSummary(BaseModel):
    """Lightweight run-control summary for list responses.

    Excludes events and ``last_error``. Includes ``event_count`` so consumers
    can gauge transition depth without loading sensitive detail.
    """

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
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    paused_at: datetime | None = None
    failed_at: datetime | None = None
    timed_out_at: datetime | None = None
    superseded_at: datetime | None = None
    incident_id: str | None = None
    terminal_reason_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    event_count: int = 0


class RunControlProjection(BaseModel):
    """Read-only detail projection of a Mission Control run-control record.

    Sensitive fields (``last_error``, ``confirmation_ref``, ``recovery_ref``)
    are redacted. Event payloads are redacted via :func:`redact_dict`.
    """

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
    freshness: FreshnessMeta | None = None


class RunControlListResponse(BaseModel):
    """Paginated list of run-control summaries with freshness metadata."""

    items: list[RunControlSummary]
    total: int
    limit: int
    offset: int
    freshness: FreshnessMeta | None = None


# ── Correlation / causation chain ─────────────────────────────────────────────

MAX_CAUSATION_LINKS = 500


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

    Safety metadata:
    - ``truncated``: True if the chain exceeded MAX_CAUSATION_LINKS and was cut.
    - ``total_links``: The total number of links before truncation.
    - ``warnings``: Diagnostic warnings (duplicates, missing parents).
    """

    command_id: str
    tenant_id: str
    command_type: str
    command_state: str
    links: list[CausationLink] = Field(default_factory=list)
    truncated: bool = False
    total_links: int = 0
    warnings: list[str] = Field(default_factory=list)
    freshness: FreshnessMeta | None = None


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
