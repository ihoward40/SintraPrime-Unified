"""
Observatory Pydantic v2 schemas for the SintraPrime Portal.

Defines request/response models for all observatory endpoints including
events, missions, agents, approvals, governance gates, evidence, artifacts,
and incidents.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────


class MissionStatus(str, Enum):
    """Status lifecycle for a mission."""

    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    EXECUTING = "EXECUTING"
    TESTING = "TESTING"
    VERIFYING = "VERIFYING"
    WAITING_FOR_AGENT = "WAITING_FOR_AGENT"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_CONDITIONS = "COMPLETED_WITH_CONDITIONS"


class EventType(str, Enum):
    """Observatory event types (blueprint Section 10)."""

    # Mission lifecycle
    MISSION_CREATED = "MISSION_CREATED"
    MISSION_STARTED = "MISSION_STARTED"
    MISSION_COMPLETED = "MISSION_COMPLETED"
    MISSION_FAILED = "MISSION_FAILED"
    MISSION_CANCELED = "MISSION_CANCELED"
    MISSION_PAUSED = "MISSION_PAUSED"
    MISSION_RESUMED = "MISSION_RESUMED"
    MISSION_STATUS_CHANGED = "MISSION_STATUS_CHANGED"

    # Agent events
    AGENT_REGISTERED = "AGENT_REGISTERED"
    AGENT_DEREGISTERED = "AGENT_DEREGISTERED"
    AGENT_HEARTBEAT = "AGENT_HEARTBEAT"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"
    AGENT_UNASSIGNED = "AGENT_UNASSIGNED"
    AGENT_ERROR = "AGENT_ERROR"

    # Governance gates
    GOVERNANCE_GATE_PASSED = "GOVERNANCE_GATE_PASSED"
    GOVERNANCE_GATE_FAILED = "GOVERNANCE_GATE_FAILED"
    GOVERNANCE_GATE_PENDING = "GOVERNANCE_GATE_PENDING"

    # Approval / human-in-the-loop
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_DENIED = "APPROVAL_DENIED"

    # Evidence & artifacts
    EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    ARTIFACT_UPDATED = "ARTIFACT_UPDATED"

    # Kill switch
    KILL_SWITCH_ACTIVATED = "KILL_SWITCH_ACTIVATED"
    KILL_SWITCH_CLEARED = "KILL_SWITCH_CLEARED"

    # Incidents
    INCIDENT_CREATED = "INCIDENT_CREATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    INCIDENT_ESCALATED = "INCIDENT_ESCALATED"

    # System
    SYSTEM_ALERT = "SYSTEM_ALERT"
    DATA_MASKING_APPLIED = "DATA_MASKING_APPLIED"


class GovernanceGate(str, Enum):
    """Governance gates G-01 through G-10."""

    G_01 = "G-01"  # Mission scope validated
    G_02 = "G-02"  # Agent authorization verified
    G_03 = "G-03"  # Data access policy checked
    G_04 = "G-04"  # Output quality threshold met
    G_05 = "G-05"  # Human approval obtained
    G_06 = "G-06"  # Compliance review passed
    G_07 = "G-07"  # Security scan completed
    G_08 = "G-08"  # Impact assessment approved
    G_09 = "G-09"  # Rollback plan verified
    G_10 = "G-10"  # Final sign-off received


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


# ── Base mixins ───────────────────────────────────────────────────────────────


class TimestampMixin(BaseModel):
    """Common timestamp fields."""

    created_at: datetime | None = None
    updated_at: datetime | None = None


class IDMixin(BaseModel):
    """Common ID field."""

    id: str


# ── Agent schemas ─────────────────────────────────────────────────────────────


class AgentRegisterRequest(BaseModel):
    """Register a new agent with the observatory."""

    agent_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=256)
    agent_type: str = Field(..., min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class AgentResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    agent_type: str
    status: str
    capabilities: list[str]
    metadata_: dict[str, Any] | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Mission schemas ───────────────────────────────────────────────────────────


class MissionCreateRequest(BaseModel):
    """Create a new mission."""

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    objective: str | None = None
    agent_ids: list[str] = Field(default_factory=list)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    governance_gates_required: list[GovernanceGate] = Field(default_factory=list)


class MissionUpdateRequest(BaseModel):
    """Update mission fields."""

    title: str | None = None
    description: str | None = None
    objective: str | None = None
    status: MissionStatus | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class MissionResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    objective: str | None = None
    status: MissionStatus
    agent_ids: list[str] = Field(default_factory=list)
    governance_gates_required: list[str] = Field(default_factory=list)
    governance_gates_passed: list[str] = Field(default_factory=list)
    metadata_: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Event schemas ─────────────────────────────────────────────────────────────


class EventCreateRequest(BaseModel):
    """Ingest a new observatory event."""

    event_type: EventType
    mission_id: str | None = None
    agent_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    timestamp: datetime | None = None

    @field_validator("event_type", mode="before")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if isinstance(v, str) and v not in EventType.__members__:
            raise ValueError(f"Invalid event type: {v}")
        return v


class EventResponse(BaseModel):
    id: str
    event_type: str
    mission_id: str | None = None
    agent_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata_: dict[str, Any] | None = None
    event_hash: str
    previous_hash: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class EventStreamMessage(BaseModel):
    """SSE / WebSocket message format."""

    id: str
    event_type: str
    mission_id: str | None = None
    agent_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


# ── Approval schemas ──────────────────────────────────────────────────────────


class ApprovalCreateRequest(BaseModel):
    """Request approval for a governance gate or mission action."""

    mission_id: str
    gate: GovernanceGate | None = None
    requester: str = Field(..., min_length=1)
    reason: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class ApprovalDecisionRequest(BaseModel):
    """Approve or deny a pending approval."""

    decision: ApprovalStatus
    reviewer: str = Field(..., min_length=1)
    notes: str | None = None


class ApprovalResponse(BaseModel):
    id: str
    mission_id: str
    gate: str | None = None
    requester: str
    reviewer: str | None = None
    status: ApprovalStatus
    reason: str | None = None
    notes: str | None = None
    metadata_: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Evidence schemas ──────────────────────────────────────────────────────────


class EvidenceCreateRequest(BaseModel):
    """Submit evidence for a mission."""

    mission_id: str
    source: str = Field(..., min_length=1)
    content_type: str = Field(default="text/plain")
    content_hash: str = Field(..., min_length=1)
    description: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class EvidenceResponse(BaseModel):
    id: str
    mission_id: str
    source: str
    content_type: str
    content_hash: str
    description: str | None = None
    verified: bool = False
    metadata_: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Artifact schemas ──────────────────────────────────────────────────────────


class ArtifactCreateRequest(BaseModel):
    """Create an artifact produced by a mission."""

    mission_id: str
    name: str = Field(..., min_length=1, max_length=256)
    artifact_type: str = Field(..., min_length=1, max_length=64)
    uri: str | None = None
    content_hash: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class ArtifactResponse(BaseModel):
    id: str
    mission_id: str
    name: str
    artifact_type: str
    uri: str | None = None
    content_hash: str | None = None
    metadata_: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Incident schemas ──────────────────────────────────────────────────────────


class IncidentCreateRequest(BaseModel):
    """Report an incident."""

    mission_id: str | None = None
    agent_id: str | None = None
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class IncidentUpdateRequest(BaseModel):
    """Update an incident."""

    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    resolution: str | None = None


class IncidentResponse(BaseModel):
    id: str
    mission_id: str | None = None
    agent_id: str | None = None
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str | None = None
    resolution: str | None = None
    metadata_: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Kill switch ────────────────────────────────────────────────────────────────


class KillSwitchRequest(BaseModel):
    """Activate the emergency kill switch.

    G-B1: the activating identity is derived from the authenticated principal
    at the router boundary; `activated_by` is retained only for backward
    compatibility and is NOT trusted as authorization.
    """

    reason: str = Field(..., min_length=1)
    activated_by: str | None = Field(default=None, min_length=1)
    scope: str = Field(default="all")  # "all", mission_id, or agent_id


class KillSwitchResponse(BaseModel):
    activated: bool
    reason: str
    activated_by: str
    scope: str
    timestamp: datetime
    events_affected: int = 0


class KillSwitchClearRequest(BaseModel):
    """Clear (deactivate) the kill switch — requires authorized principal.

    G-B1: the clearing identity is derived from the authenticated principal;
    `cleared_by` is retained only for backward compatibility and is NOT trusted.
    """

    cleared_by: str | None = Field(default=None, min_length=1)
    reason: str = Field(default="")


class KillSwitchStatusResponse(BaseModel):
    """Current kill switch state — loaded from persistent storage on startup."""

    is_active: bool
    reason: str | None = None
    activated_by: str | None = None
    activated_at: datetime | None = None
    cleared_by: str | None = None
    cleared_at: datetime | None = None
    scope: str | None = None


# ── Governance gate check ─────────────────────────────────────────────────────


class GovernanceGateCheckRequest(BaseModel):
    """Check whether a mission passes a governance gate."""

    mission_id: str
    gate: GovernanceGate
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class GovernanceGateCheckResponse(BaseModel):
    mission_id: str
    gate: str
    passed: bool
    reason: str | None = None
    checked_at: datetime | None = None


# ── Replay ────────────────────────────────────────────────────────────────────


class ReplayRequest(BaseModel):
    """Request event replay from a given point."""

    from_hash: str | None = None
    from_timestamp: datetime | None = None
    mission_id: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class ReplayResponse(BaseModel):
    events: list[EventResponse]
    total: int
    truncated: bool = False


# ── List / pagination ─────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 50