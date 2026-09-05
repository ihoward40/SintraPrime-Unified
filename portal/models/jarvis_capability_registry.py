"""JARVIS-001-B2-B2 Capability Registry models.

Immutable capability contract record; append-only lifecycle transition ledger;
transactionally maintained current-state projection; current registry revision authoritative.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID


class LifecycleStatus(enum.StrEnum):
    """Capability lifecycle states (granted trust level)."""
    DISCOVERED = "DISCOVERED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    SANDBOXED = "SANDBOXED"
    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"


class EffectiveStatus(enum.StrEnum):
    """Derived execution status (computed from lifecycle + dependencies)."""
    DISCOVERED = "DISCOVERED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    SANDBOXED = "SANDBOXED"
    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"
    QUARANTINED_BY_DEPENDENCY = "QUARANTINED_BY_DEPENDENCY"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"


class RevocationReason(enum.StrEnum):
    """Reasons for capability revocation."""
    SECURITY_ISSUE = "SECURITY_ISSUE"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    SUPERSEDED = "SUPERSEDED"
    MANUAL_REVOCATION = "MANUAL_REVOCATION"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"


class TransitionAuthority(enum.StrEnum):
    """Authority types for lifecycle transitions."""
    REVIEWER = "REVIEWER"
    PRINCIPAL = "PRINCIPAL"
    CAPABILITY_OWNER = "CAPABILITY_OWNER"
    GOVERNED_CONTROLLER = "GOVERNED_CONTROLLER"
    INDEPENDENT_CERTIFIER = "INDEPENDENT_CERTIFIER"
    GOVERNING_AUTHORITY = "GOVERNING_AUTHORITY"
    DESIGNATED_REVOKER = "DESIGNATED_REVOKER"
    SAFETY_CONTROLLER = "SAFETY_CONTROLLER"


class CapabilityRegistration(Base):
    """Immutable capability contract record with current lifecycle state projection.

    This is the authoritative current state. Historical transitions are in CapabilityTransition.
    Registry revision provides optimistic concurrency control.
    """
    __tablename__ = "capability_registrations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "capability_id", "capability_version",
            name="uq_capability_registration_tenant_id_version"
        ),
        UniqueConstraint(
            "tenant_id", "contract_hash",
            name="uq_capability_registration_tenant_contract_hash"
        ),
        Index("ix_capability_registration_tenant_lifecycle", "tenant_id", "lifecycle_state"),
        Index("ix_capability_registration_tenant_effective", "tenant_id", "effective_state"),
        Index("ix_capability_registration_tenant_capability", "tenant_id", "capability_id"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Immutable contract identity
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex

    # Ownership
    owner_principal: Mapped[uuid.UUID] = mapped_column(PortableUUID, nullable=False)

    # Current lifecycle state (granted trust level from transition ledger)
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False, default=LifecycleStatus.DISCOVERED.value)
    lifecycle_state_effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Derived execution state (computed from lifecycle_state + dependency health)
    effective_state: Mapped[str] = mapped_column(String(64), nullable=False, default=LifecycleStatus.DISCOVERED.value)
    effective_state_computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    effective_executable: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Version chain
    supersedes: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Previous version

    # Dependencies (capability_ids, not versions)
    dependency_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Executor and adapter references
    executor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Policy references (set at APPROVED transition)
    approval_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_policy_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Optimistic concurrency control
    registry_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CapabilityTransition(Base):
    """Append-only lifecycle transition ledger with hash chain integrity.

    Records all state changes with cryptographic tamper detection.
    No updates or deletes allowed.
    """
    __tablename__ = "capability_transitions"
    __table_args__ = (
        Index("ix_capability_transition_tenant_capability", "tenant_id", "capability_id", "capability_version"),
        Index("ix_capability_transition_hash_chain", "previous_transition_hash"),
    )

    # Primary key
    transition_id: Mapped[uuid.UUID] = mapped_column(
        "id", PortableUUID, primary_key=True, default=uuid.uuid4
    )

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Capability identity
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Transition
    from_status: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)

    # Authority
    actor_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, nullable=False)
    authority: Mapped[str] = mapped_column(String(64), nullable=False)  # TransitionAuthority enum

    # Reason (used for revocations and quarantines)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamp
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Hash chain for tamper detection
    previous_transition_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
