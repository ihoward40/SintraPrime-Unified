"""
Observatory SQLAlchemy models for the SintraPrime Portal.

Defines the persistence layer for agents, missions, events (hash-chained),
approvals, evidence, artifacts, and incidents. Uses async-compatible
SQLAlchemy 2.0 mapped columns and works with both SQLite and PostgreSQL.
"""

from __future__ import annotations


import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, TypeDecorator, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portal.database import Base


class PortableUUID(TypeDecorator):
    """UUID that stores as native UUID on PostgreSQL and String(36) on SQLite."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return PGUUID(as_uuid=True)
        return String(36)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        return str(value)

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


# ── Chain Verification Result ────────────────────────────────────────────────


class VerificationFailureReason(str, Enum):
    """Structured failure reasons for chain verification.

    Each reason identifies a specific integrity violation, enabling
    precise diagnostics without weakening the verification logic.
    """
    EVENT_HASH_MISMATCH = "EVENT_HASH_MISMATCH"
    PREVIOUS_HASH_MISMATCH = "PREVIOUS_HASH_MISMATCH"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    INVALID_GENESIS = "INVALID_GENESIS"
    RUN_HEAD_MISSING = "RUN_HEAD_MISSING"
    RUN_HEAD_SEQUENCE_MISMATCH = "RUN_HEAD_SEQUENCE_MISMATCH"
    RUN_HEAD_HASH_MISMATCH = "RUN_HEAD_HASH_MISMATCH"
    UNSUPPORTED_HASH_VERSION = "UNSUPPORTED_HASH_VERSION"


@dataclass
class ChainVerificationResult:
    """Structured result from chain verification.

    The `valid` field provides backward-compatible boolean semantics.
    The `reason` field provides diagnostic detail when verification fails.
    The `run_id`, `sequence`, and `event_id` fields identify the failing
    event when applicable.
    """
    valid: bool
    reason: VerificationFailureReason | None = None
    run_id: str | None = None
    sequence: int | None = None
    event_id: uuid.UUID | None = None
    detail: str | None = None


# ── Agent ──────────────────────────────────────────────────────────────────────


class Agent(Base):
    """Registered observatory agent."""

    __tablename__ = "observatory_agents"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Mission ────────────────────────────────────────────────────────────────────


class Mission(Base):
    """An observatory mission."""

    __tablename__ = "observatory_missions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="QUEUED", index=True)
    governance_gates_required: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    governance_gates_passed: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    agents: Mapped[list["MissionAgent"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


# ── Mission-Agent association ──────────────────────────────────────────────────


class MissionAgent(Base):
    """Association between a mission and an agent."""

    __tablename__ = "observatory_mission_agents"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    mission: Mapped["Mission"] = relationship(back_populates="agents")

    __table_args__ = (
        Index("ix_observatory_mission_agents_pair", "mission_id", "agent_id"),
    )


# ── Run Head (hash-chain serialization point) ──────────────────────────────────


class ObservatoryRunHead(Base):
    """Authoritative serialization point for one run's hash chain.

    Each run_id has exactly one row. The row is locked with SELECT ... FOR UPDATE
    before any event insert, ensuring that concurrent event submissions serialize
    correctly on PostgreSQL. SQLite's GIL provides equivalent serialization.

    The run head records the last_sequence and last_event_hash so that the next
    event in the run can chain to it deterministically, without needing to
    query the events table for the "latest event" — which would be a race
    condition under concurrent access.
    """

    __tablename__ = "observatory_run_heads"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sequence: Mapped[int] = mapped_column(nullable=False, default=0)
    last_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    __table_args__ = (
        CheckConstraint(
            "(last_sequence = 0 AND last_event_hash IS NULL) OR "
            "(last_sequence > 0 AND last_event_hash IS NOT NULL)",
            name="ck_observatory_run_heads_consistent_state",
        ),
    )


# ── Event (hash-chained) ──────────────────────────────────────────────────────


class ObservatoryEvent(Base):
    """Immutable, hash-chained observatory event.

    Each event carries an event_hash (SHA-256 of canonical payload) and a
    previous_hash linking to the preceding event WITHIN THE SAME RUN, forming
    an append-only chain per run_id.

    Genesis rule: The first event in any run has sequence=1, previous_hash=null.
    The event_hash is computed from the canonical payload and the empty
    previous_hash value.
    """

    __tablename__ = "observatory_events"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(nullable=False, index=True)
    hash_version: Mapped[int] = mapped_column(nullable=False, default=2, server_default="2", index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=True, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    payload_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("uq_observatory_event_run_sequence", "run_id", "sequence", unique=True),
        Index("ix_observatory_event_run_id_seq", "run_id", "sequence"),
        CheckConstraint("sequence >= 1", name="ck_observatory_event_sequence_positive"),
    )

    @staticmethod
    def canonical_timestamp(dt: datetime) -> str:
        """Produce a canonical ISO-8601 timestamp string for hash computation.

        Delegates to event_canonicalization.canonical_timestamp().
        See that module for rules and documentation.
        """
        from portal.services.event_canonicalization import canonical_timestamp as _ct
        return _ct(dt)

    @staticmethod
    def compute_hash_v1(
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str | None,
        timestamp: str,
        mission_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Compute SHA-256 event hash using v1 formula (legacy).

        Delegates to event_canonicalization.compute_hash_v1().
        This function is FROZEN. Do not modify.
        """
        from portal.services.event_canonicalization import compute_hash_v1 as _v1
        return _v1(
            event_type=event_type, payload=payload, previous_hash=previous_hash,
            timestamp=timestamp, mission_id=mission_id, agent_id=agent_id,
        )

    @staticmethod
    def compute_hash_v2(
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str | None,
        timestamp: str,
        mission_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        sequence: int | None = None,
    ) -> str:
        """Compute SHA-256 event hash using v2 formula (run-scoped).

        Delegates to event_canonicalization.compute_hash_v2().
        This function is FROZEN. Do not modify.
        """
        from portal.services.event_canonicalization import compute_hash_v2 as _v2
        return _v2(
            event_type=event_type, payload=payload, previous_hash=previous_hash,
            timestamp=timestamp, mission_id=mission_id, agent_id=agent_id,
            run_id=run_id, sequence=sequence,
        )

    @staticmethod
    def compute_hash(
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str | None,
        timestamp: str,
        mission_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        sequence: int | None = None,
        hash_version: int = 2,
    ) -> str:
        """Dispatch to the correct hash formula based on hash_version.

        Delegates to event_canonicalization.compute_hash().
        """
        from portal.services.event_canonicalization import compute_hash as _ch
        return _ch(
            event_type=event_type, payload=payload, previous_hash=previous_hash,
            timestamp=timestamp, mission_id=mission_id, agent_id=agent_id,
            run_id=run_id, sequence=sequence, hash_version=hash_version,
        )

    @staticmethod
    def verify_event_hash(
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str | None,
        timestamp: str,
        stored_hash: str,
        mission_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        sequence: int | None = None,
        hash_version: int = 2,
    ) -> bool:
        """Verify an event's stored hash against the expected computation.

        Delegates to event_canonicalization.verify_event_hash().
        Unknown hash_version always returns False (fail closed).
        """
        from portal.services.event_canonicalization import verify_event_hash as _veh
        return _veh(
            event_type=event_type, payload=payload, previous_hash=previous_hash,
            timestamp=timestamp, stored_hash=stored_hash, mission_id=mission_id,
            agent_id=agent_id, run_id=run_id, sequence=sequence,
            hash_version=hash_version,
        )


# ── Approval ───────────────────────────────────────────────────────────────────


class Approval(Base):
    """Governance approval record."""

    __tablename__ = "observatory_approvals"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=False, index=True
    )
    gate: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    requester: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Evidence ───────────────────────────────────────────────────────────────────


class Evidence(Base):
    """Evidence submitted for a mission."""

    __tablename__ = "observatory_evidence"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/plain")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


# ── Artifact ──────────────────────────────────────────────────────────────────


class Artifact(Base):
    """Artifact produced by a mission."""

    __tablename__ = "observatory_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Incident ──────────────────────────────────────────────────────────────────


class Incident(Base):
    """Incident record for the observatory."""

    __tablename__ = "observatory_incidents"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("observatory_missions.id"), nullable=True, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


# ── Kill Switch State ──────────────────────────────────────────────────────────


class KillSwitchState(Base):
    """Persistent kill switch state — survives restarts.

    Only one active row may exist at a time. Activation is idempotent.
    Clearing requires explicit authorized action. An active switch prevents
    new executable missions and consequential tool calls. Evidence and
    event-reading endpoints remain available while active. The switch
    fails closed when persistence state cannot be safely determined.
    """

    __tablename__ = "observatory_kill_switch_state"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    activated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    cleared_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    activation_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("observatory_events.id"), nullable=True
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )