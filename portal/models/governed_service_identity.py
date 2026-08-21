"""Durable governed service-identity descriptors."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, cast, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from ..database import Base


class UUIDAuthorityCompatibleString(TypeDecorator[str]):
    """Keep ORM VARCHAR identity metadata while safely reading raw UUID authority.

    The application ORM still models tenant/user identities as ``VARCHAR(36)`` for
    legacy metadata compatibility, while the certified raw PostgreSQL authority uses
    native UUID columns. Comparisons therefore cast the persisted column to text at
    the query boundary instead of changing either already-certified schema.
    """

    impl = String
    cache_ok = True

    class Comparator(TypeDecorator.Comparator[Any]):
        def __eq__(self, other: object):  # type: ignore[override]
            return cast(self.expr, String(36)) == str(other)

    comparator_factory = Comparator

    def __init__(self, length: int = 36) -> None:
        super().__init__(length=length)

    def process_result_value(self, value: object, dialect: object) -> str | None:
        del dialect
        return None if value is None else str(value)


class GovernedServiceIdentityRecord(Base):
    """Persistent non-secret authority descriptor for delegated service identities."""

    __tablename__ = "governed_service_identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        UUIDAuthorityCompatibleString(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        UUIDAuthorityCompatibleString(36),
        ForeignKey("users.id"),
        nullable=False,
    )
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
