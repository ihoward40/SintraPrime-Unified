"""Gate 4B production-authority mappings for the disposable external-action sandbox."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ExternalActionAuthorityBase(DeclarativeBase):
    pass


class ExternalActionIntent(ExternalActionAuthorityBase):
    __tablename__ = "external_action_intents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "principal_id", "idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    principal_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    service_identity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    mission_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    schedule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    adapter_id: Mapped[str] = mapped_column(String(120), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    risk_class: Mapped[str] = mapped_column(String(8), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    canonical_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    preflight_receipt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_confirmation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExternalActionApproval(ExternalActionAuthorityBase):
    __tablename__ = "external_action_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    principal_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(120), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalActionEvidence(ExternalActionAuthorityBase):
    __tablename__ = "external_action_evidence"
    __table_args__ = (UniqueConstraint("intent_id", "sequence_no"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalExecutionKillSwitch(ExternalActionAuthorityBase):
    __tablename__ = "external_execution_kill_switches"

    scope_key: Mapped[str] = mapped_column(String(180), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    adapter_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SandboxEchoEffect(ExternalActionAuthorityBase):
    __tablename__ = "sandbox_echo_effects"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    compensated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
