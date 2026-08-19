"""Durable governed service-identity descriptors."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class GovernedServiceIdentityRecord(Base):
    """Persistent non-secret authority descriptor for delegated service identities."""

    __tablename__ = "governed_service_identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scoped_folders: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "created_by",
            "idempotency_key",
            name="uq_governed_service_identity_idempotency",
        ),
        Index(
            "ix_governed_service_identities_tenant_status_expires",
            "tenant_id",
            "status",
            "expires_at",
        ),
        Index(
            "ix_governed_service_identities_tenant_agent",
            "tenant_id",
            "agent_id",
        ),
    )
