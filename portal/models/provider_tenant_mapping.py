"""Provider tenant mapping model — server-side mapping of Stripe provider IDs to tenants."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ProviderTenantMapping(Base):
    """Server-side mapping of Stripe Connect account IDs or customer IDs to tenants.

    Unknown, inactive, conflicting, or ambiguous mappings must fail closed.
    One Stripe customer may NOT map to multiple active tenants simultaneously.
    """

    __tablename__ = "provider_tenant_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deactivated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    deactivation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "uq_active_provider_account",
            "provider",
            "provider_account_id",
            postgresql_where="provider_account_id IS NOT NULL AND mapping_status = 'active'",
            unique=True,
        ),
        Index(
            "uq_active_provider_customer",
            "provider",
            "provider_customer_id",
            postgresql_where="provider_customer_id IS NOT NULL AND mapping_status = 'active'",
            unique=True,
        ),
    )
