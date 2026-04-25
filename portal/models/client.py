"""
Client profile and Matter (engagement/retainer) models.
Each client belongs to one tenant. A matter links a client to a set of cases.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, String, Text, func, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Type: individual or organization
    client_type: Mapped[str]        = mapped_column(String(20), nullable=False, default="individual")  # individual | organization

    # Individual
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ssn_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)  # last 4 digits only

    # Organization
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ein: Mapped[Optional[str]]          = mapped_column(String(20), nullable=True)  # employer identification number
    contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Contact
    email: Mapped[Optional[str]]     = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]]     = mapped_column(String(50), nullable=True)
    alt_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fax: Mapped[Optional[str]]       = mapped_column(String(50), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]]          = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]]         = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)
    country: Mapped[str]                 = mapped_column(String(2), default="US")

    # Portal access
    portal_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    portal_access: Mapped[bool]                 = mapped_column(Boolean, default=False)

    # Assigned attorney
    primary_attorney_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Client status
    status: Mapped[str]           = mapped_column(String(20), default="active")  # prospect | active | inactive | archived
    intake_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]]  = mapped_column(JSONB, nullable=True, default=list)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Full-text search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)

    # Timestamps
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    matters: Mapped[List["Matter"]]   = relationship("Matter", back_populates="client", lazy="select")
    primary_attorney: Mapped[Optional["User"]] = relationship("User", foreign_keys=[primary_attorney_id])
    portal_user: Mapped[Optional["User"]]      = relationship("User", foreign_keys=[portal_user_id])

    __table_args__ = (
        Index("ix_clients_tenant_id", "tenant_id"),
        Index("ix_clients_email", "email"),
        Index("ix_clients_status", "status"),
        Index("ix_clients_search", "search_vector", postgresql_using="gin"),
        Index("ix_clients_deleted", "deleted_at"),
    )

    @property
    def display_name(self) -> str:
        if self.client_type == "organization":
            return self.company_name or "Unknown Organization"
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown Client"


class Matter(Base):
    """
    A matter represents a specific legal engagement between a client and the firm.
    Cases are grouped under matters.
    """
    __tablename__ = "matters"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    matter_number: Mapped[str]      = mapped_column(String(50), nullable=False)  # e.g., "2024-001"
    title: Mapped[str]              = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    practice_area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str]             = mapped_column(String(20), default="active")  # active | closed | archived

    # Fee structure
    billing_type: Mapped[str]       = mapped_column(String(20), default="hourly")  # hourly | flat_fee | contingency | retainer
    hourly_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    flat_fee: Mapped[Optional[float]]    = mapped_column(Numeric(10, 2), nullable=True)
    retainer_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    contingency_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Staff
    responsible_attorney_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    billing_attorney_id: Mapped[Optional[uuid.UUID]]     = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="matters")
    responsible_attorney: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_attorney_id])
    billing_attorney: Mapped[Optional["User"]]     = relationship("User", foreign_keys=[billing_attorney_id])

    __table_args__ = (
        Index("ix_matters_client_id", "client_id"),
        Index("ix_matters_tenant_id", "tenant_id"),
        Index("ix_matters_status", "status"),
    )
