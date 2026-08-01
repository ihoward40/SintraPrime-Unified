"""AI-OS agent registry ORM models (M-001, schema-parity scope only).

These models exist so the ORM ``create_all`` path and the raw-SQL migration in
``portal/migrations/ai_os/0001_agents_and_versions`` can be proven materially
equivalent on PostgreSQL. They define schema only.

Explicitly NOT provided by M-001 (not authorized):
  * seeding or activation of any agent
  * invocation behavior
  * service-layer registry operations
  * API routes
  * AI-OS permissions

Governance invariants encoded in the schema:
  * ``agent_id`` is immutable and unique per tenant.
  * Agents are inactive by default and a ``seed`` agent can never be active.
  * Retirement is a status change; there is no hard-delete path.
  * Version rows are immutable: no ``updated_at``, no ``deleted_at``, and no
    application-side update or delete helper is provided.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID

AGENT_STATUS_SEED = "seed"
AGENT_STATUS_ACTIVE = "active"
AGENT_STATUS_RETIRED = "retired"
AGENT_STATUSES = (AGENT_STATUS_SEED, AGENT_STATUS_ACTIVE, AGENT_STATUS_RETIRED)


class AIOSAgent(Base):
    """Tenant-scoped, governed AI-OS agent record. Inactive by default."""

    __tablename__ = "ai_os_agents"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Stable logical identifier. Immutable once written.",
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'seed'"),
        doc="seed | active | retired. Retirement replaces deletion.",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
        doc="Never true for a seed or retired agent; activation is separately gated.",
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID,
        ForeignKey(
            "ai_os_agent_versions.id",
            ondelete="RESTRICT",
            name="fk_ai_os_agents_current_version",
            use_alter=True,
        ),
        nullable=True,
        doc=(
            "Deferred FK emitted as ALTER TABLE ADD CONSTRAINT, matching the "
            "PostgreSQL migration override. SQLite cannot ALTER ADD CONSTRAINT, "
            "so the constraint is absent there by design."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # No updated_at and no deleted_at: retirement is a governed status change.

    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_id", name="uq_ai_os_agents_tenant_agent"),
        CheckConstraint(
            "status IN ('seed', 'active', 'retired')",
            name="ck_ai_os_agents_status",
        ),
        CheckConstraint(
            "status <> 'seed' OR active = FALSE",
            name="ck_ai_os_agents_seed_inactive",
        ),
        CheckConstraint(
            "status <> 'retired' OR active = FALSE",
            name="ck_ai_os_agents_retired_inactive",
        ),
        Index("ix_ai_os_agents_tenant", "tenant_id"),
        Index("ix_ai_os_agents_tenant_status", "tenant_id", "status"),
    )


class AIOSAgentVersion(Base):
    """Immutable, hash-identified version of an AI-OS agent definition."""

    __tablename__ = "ai_os_agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_row_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("ai_os_agents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    semver: Mapped[str] = mapped_column(String(32), nullable=False)
    definition: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Canonical JSON text of the agent definition. Hashed verbatim.",
    )
    definition_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Intentionally immutable: no updated_at, no deleted_at, no delete helper.

    __table_args__ = (
        UniqueConstraint(
            "agent_row_id",
            "semver",
            name="uq_ai_os_agent_versions_agent_semver",
        ),
        UniqueConstraint(
            "agent_row_id",
            "definition_sha256",
            name="uq_ai_os_agent_versions_agent_hash",
        ),
        Index("ix_ai_os_agent_versions_agent", "agent_row_id"),
    )
