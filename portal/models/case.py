"""
Case management models: Case, CaseEvent, CaseDeadline, CaseNote, CaseTask.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

import enum as _enum


class CaseStage(str, _enum.Enum):
    """Lifecycle stages for a legal case."""
    INTAKE = "intake"
    ACTIVE = "active"
    DISCOVERY = "discovery"
    NEGOTIATION = "negotiation"
    TRIAL = "trial"
    APPEAL = "appeal"
    CLOSED = "closed"
    ARCHIVED = "archived"




class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)

    case_number: Mapped[str]        = mapped_column(String(50), nullable=False)
    title: Mapped[str]              = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    practice_area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    case_type: Mapped[Optional[str]]     = mapped_column(String(100), nullable=True)  # litigation | transactional | advisory
    jurisdiction: Mapped[Optional[str]]  = mapped_column(String(200), nullable=True)
    court_name: Mapped[Optional[str]]    = mapped_column(String(300), nullable=True)
    docket_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Stage tracking
    stage: Mapped[str]              = mapped_column(String(30), default="intake")
    # intake | active | discovery | trial | pending | appeal | closed | archived

    # Staff assignments
    lead_attorney_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_staff: Mapped[Optional[list]]          = mapped_column(JSONB, nullable=True, default=list)  # list of user_ids

    # Opposing party (conflict check)
    opposing_party: Mapped[Optional[str]]           = mapped_column(String(500), nullable=True)
    opposing_counsel: Mapped[Optional[str]]         = mapped_column(String(500), nullable=True)

    # Dates
    opened_at: Mapped[Optional[datetime]]           = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]]           = mapped_column(DateTime(timezone=True), nullable=True)
    statute_of_limitations: Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    next_court_date: Mapped[Optional[date]]         = mapped_column(Date, nullable=True)

    # Flags
    is_urgent: Mapped[bool]         = mapped_column(Boolean, default=False)
    is_confidential: Mapped[bool]   = mapped_column(Boolean, default=False)
    conflict_checked: Mapped[bool]  = mapped_column(Boolean, default=False)
    conflict_cleared: Mapped[bool]  = mapped_column(Boolean, default=False)

    # Outcome (when closed)
    outcome: Mapped[Optional[str]]  = mapped_column(String(50), nullable=True)  # won | lost | settled | dismissed
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settlement_amount: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Custom intake form data
    intake_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    tags: Mapped[Optional[list]]        = mapped_column(JSONB, nullable=True, default=list)

    # Full-text search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)

    # Timestamps
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client: Mapped["Client"]             = relationship("Client", foreign_keys=[client_id])
    lead_attorney: Mapped[Optional["User"]] = relationship("User", foreign_keys=[lead_attorney_id])
    events: Mapped[List["CaseEvent"]]    = relationship("CaseEvent", back_populates="case", order_by="CaseEvent.event_date.desc()", lazy="select")
    deadlines: Mapped[List["CaseDeadline"]] = relationship("CaseDeadline", back_populates="case", lazy="select")
    notes: Mapped[List["CaseNote"]]      = relationship("CaseNote", back_populates="case", lazy="select")
    tasks: Mapped[List["CaseTask"]]      = relationship("CaseTask", back_populates="case", lazy="select")

    __table_args__ = (
        Index("ix_cases_tenant_id", "tenant_id"),
        Index("ix_cases_client_id", "client_id"),
        Index("ix_cases_stage", "stage"),
        Index("ix_cases_lead_attorney", "lead_attorney_id"),
        Index("ix_cases_search", "search_vector", postgresql_using="gin"),
        Index("ix_cases_deleted", "deleted_at"),
    )


class CaseEvent(Base):
    """Timeline events for a case (hearings, filings, communications, etc.)."""
    __tablename__ = "case_events"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    event_type: Mapped[str]         = mapped_column(String(50), nullable=False)
    # hearing | filing | correspondence | note | stage_change | assignment | deadline

    title: Mapped[str]              = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    # Renamed from metadata to avoid SQLAlchemy Declarative API collision. Phase 21E.
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped["Case"]            = relationship("Case", back_populates="events")
    creator: Mapped["User"]         = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_case_events_case_id", "case_id"),
        Index("ix_case_events_event_date", "event_date"),
    )


class CaseDeadline(Base):
    """Important deadlines with reminder configuration."""
    __tablename__ = "case_deadlines"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title: Mapped[str]              = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline_type: Mapped[str]      = mapped_column(String(50), nullable=False)
    # court | filing | statute | response | discovery | hearing | custom

    due_date: Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_days: Mapped[list]     = mapped_column(JSONB, default=lambda: [7, 1])  # remind N days before

    is_completed: Mapped[bool]      = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_critical: Mapped[bool]       = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    case: Mapped["Case"]            = relationship("Case", back_populates="deadlines")

    __table_args__ = (
        Index("ix_case_deadlines_case_id", "case_id"),
        Index("ix_case_deadlines_due_date", "due_date"),
        Index("ix_case_deadlines_completed", "is_completed"),
    )


class CaseNote(Base):
    """Private staff notes and client-visible notes on a case."""
    __tablename__ = "case_notes"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title: Mapped[Optional[str]]    = mapped_column(String(500), nullable=True)
    content: Mapped[str]            = mapped_column(Text, nullable=False)
    note_type: Mapped[str]          = mapped_column(String(20), default="private")  # private | client_visible
    pinned: Mapped[bool]            = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case"]            = relationship("Case", back_populates="notes")
    author: Mapped["User"]          = relationship("User", foreign_keys=[created_by])

    __table_args__ = (Index("ix_case_notes_case_id", "case_id"),)


class CaseTask(Base):
    """Actionable tasks assigned to staff members on a case."""
    __tablename__ = "case_tasks"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title: Mapped[str]              = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str]           = mapped_column(String(10), default="medium")  # low | medium | high | critical
    status: Mapped[str]             = mapped_column(String(20), default="todo")    # todo | in_progress | review | done

    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(nullable=True)
    actual_hours: Mapped[Optional[float]]    = mapped_column(nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case"]            = relationship("Case", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])

    __table_args__ = (
        Index("ix_case_tasks_case_id", "case_id"),
        Index("ix_case_tasks_assigned_to", "assigned_to"),
        Index("ix_case_tasks_status", "status"),
    )
