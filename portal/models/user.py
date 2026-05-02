"""
User, Role, Permission, and Tenant models.
Supports multi-tenancy — every user belongs to exactly one tenant (firm).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# ── Tenant (Firm) ─────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]             = mapped_column(String(255), nullable=False)
    slug: Mapped[str]             = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)  # custom domain
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str]    = mapped_column(String(7), default="#1a56db")
    secondary_color: Mapped[str]  = mapped_column(String(7), default="#7e3af2")

    # Subscription / quota
    storage_quota_gb: Mapped[int] = mapped_column(Integer, default=100)
    user_quota: Mapped[int]       = mapped_column(Integer, default=50)
    plan: Mapped[str]             = mapped_column(String(50), default="professional")
    is_active: Mapped[bool]       = mapped_column(Boolean, default=True)

    # Contact
    email: Mapped[str | None]  = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None]  = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stripe
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Settings (JSON blob for flexibility)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    users: Mapped[list[User]] = relationship("User", back_populates="tenant", lazy="select")

    __table_args__ = (
        Index("ix_tenants_slug", "slug"),
        Index("ix_tenants_active", "is_active"),
    )


# ── Role ──────────────────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]              = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str]      = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool]        = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    permissions: Mapped[list[Permission]] = relationship(
        "Permission", secondary="role_permissions", lazy="selectin"
    )
    users: Mapped[list[User]] = relationship("User", back_populates="role_ref")


# ── Permission ────────────────────────────────────────────────────────────────

class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]            = mapped_column(String(100), unique=True, nullable=False)
    resource: Mapped[str]        = mapped_column(String(50), nullable=False)
    action: Mapped[str]          = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Role ↔ Permission join table ─────────────────────────────────────────────

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]            = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)

    email: Mapped[str]               = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool]     = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    hashed_password: Mapped[str]     = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    first_name: Mapped[str]          = mapped_column(String(100), nullable=False)
    last_name: Mapped[str]           = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None]     = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None]     = mapped_column(String(100), nullable=True)  # e.g., "Senior Attorney"
    bar_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # MFA
    mfa_enabled: Mapped[bool]        = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_backup_codes: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list of hashed codes

    # Account state
    is_active: Mapped[bool]          = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool]          = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Password reset
    reset_token: Mapped[str | None]         = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Invite
    invite_token: Mapped[str | None]         = mapped_column(String(255), nullable=True)
    invite_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notification preferences
    notify_email: Mapped[bool]       = mapped_column(Boolean, default=True)
    notify_sms: Mapped[bool]         = mapped_column(Boolean, default=False)
    notify_push: Mapped[bool]        = mapped_column(Boolean, default=True)

    # Timestamps
    last_login_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None]       = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime]               = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]               = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None]     = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped[Tenant]        = relationship("Tenant", back_populates="users")
    role_ref: Mapped[Role]        = relationship("Role", back_populates="users", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_active", "is_active"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ── User ↔ Permission overrides ───────────────────────────────────────────────

class UserPermissionAssoc(Base):
    """Extra per-user permission overrides (additions or restrictions)."""
    __tablename__ = "user_permissions"

    user_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    granted: Mapped[bool]            = mapped_column(Boolean, default=True)  # False = explicit deny
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
