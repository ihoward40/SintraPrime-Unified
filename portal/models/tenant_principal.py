"""Tenant Principal — constitutional Principal identity authority.

A single durable record per tenant that names the user who is the constitutional
Principal for Mission Control approval authority. This record is NOT derived
from RBAC roles and is NOT self-service writable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TenantPrincipal(Base):
    __tablename__ = "tenant_principals"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    established_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    establishment_source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="bootstrap",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_principals_tenant_id"),
        UniqueConstraint(
            "principal_user_id", "tenant_id",
            name="uq_tenant_principals_user_tenant",
        ),
    )
