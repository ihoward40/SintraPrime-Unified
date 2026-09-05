"""Durable B2 SQLAlchemy models.

The models persist authority/evidence state without storing credential material.

ORM/migration parity contract (P3):
- Portable column shape, uniques, enum CHECK constraints, and composite indexes
  are carried here so SQLite create_all lanes and the PostgreSQL migration
  describe the same schema.
- PostgreSQL-only hardening (the receipt-payload secret regex CHECK, which uses
  the `::text` cast and `!~*` operator) is migration-owned per the repository
  convention used by portal RLS policies and audit triggers.
- receipt_payload uses JSON with a PostgreSQL JSONB variant for exact type
  parity with jarvis_b2_durability_2026_09_05.sql.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from portal.database import Base

JSONB_VARIANT = JSON().with_variant(JSONB(), "postgresql")

LEASE_STATES = ("ISSUED", "CLAIMED", "CONSUMED", "EXPIRED", "REVOKED")
OPERATION_STATES = (
    "PENDING", "ATTEMPTING", "AWAITING_VERIFICATION", "VERIFIED", "FAILED_VERIFIED",
    "UNKNOWN", "RECONCILING", "RECONCILED", "MANUAL_REVIEW_REQUIRED",
)
MEMORY_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED")
CREDENTIAL_STATUSES = ("ISSUED", "CONSUMED", "REVOKED", "EXPIRED")


def _in_constraint(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    rendered = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({rendered})", name=name)


class JarvisAuthorityLeaseRecord(Base):
    __tablename__ = "jarvis_authority_leases"
    __table_args__ = (
        _in_constraint("lease_state", LEASE_STATES, "ck_jarvis_lease_state"),
        UniqueConstraint("lease_id", "revision", name="uq_jarvis_lease_scope_revision"),
        Index("ix_jarvis_lease_tenant_state", "tenant_id", "lease_state"),
    )
    lease_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    registry_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False)
    approval_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_state: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class JarvisOperationRecord(Base):
    __tablename__ = "jarvis_operations"
    __table_args__ = (
        _in_constraint("state", OPERATION_STATES, "ck_jarvis_operation_state"),
        Index("ix_jarvis_operation_tenant_state", "tenant_id", "state"),
    )
    operation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lease_id: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_grant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_operation_ref: Mapped[str | None] = mapped_column(Text)
    latest_verification_status: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class JarvisActionReceiptRecord(Base):
    __tablename__ = "jarvis_action_receipts"
    __table_args__ = (
        Index("ix_jarvis_receipt_tenant_predecessor", "tenant_id", "previous_receipt_hash"),
    )
    receipt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    previous_receipt_hash: Mapped[str | None] = mapped_column(String(64))
    receipt_payload: Mapped[dict] = mapped_column(JSONB_VARIANT, nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class JarvisOperationalMemoryRecord(Base):
    __tablename__ = "jarvis_operational_memory"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedup_key", name="uq_jarvis_memory_tenant_dedup"),
        _in_constraint("status", MEMORY_STATUSES, "ck_jarvis_memory_status"),
        Index("ix_jarvis_memory_tenant_status", "tenant_id", "status"),
    )
    memory_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_id: Mapped[str | None] = mapped_column(String(64))
    receipt_hash: Mapped[str | None] = mapped_column(String(64))
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_class: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", server_default="OPEN")
    reason_code: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class JarvisCredentialStateRecord(Base):
    __tablename__ = "jarvis_credential_state"
    __table_args__ = (
        _in_constraint("grant_status", CREDENTIAL_STATUSES, "ck_jarvis_credential_status"),
    )
    grant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    lease_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    grant_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ISSUED", server_default="ISSUED")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
