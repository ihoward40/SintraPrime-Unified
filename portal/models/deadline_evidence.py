"""Persistent deadline and evidence-graph records for matter intelligence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID


class MatterDeadline(Base):
    __tablename__ = "matter_deadlines"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[uuid.UUID] = mapped_column(String(255), nullable=False)
    deadline_type: Mapped[uuid.UUID] = mapped_column(String(40), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    trigger_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_type: Mapped[str] = mapped_column(String(24), nullable=False)
    calculation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    calculation_rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    authority_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trigger_basis_redacted: Mapped[dict | None] = mapped_column(
        "trigger_basis", JSON, nullable=True, default=dict
    )
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_SUBMITTED")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterDeadlineVersion(Base):
    __tablename__ = "matter_deadline_versions"
    __table_args__ = (
        UniqueConstraint("deadline_id", "version_number", name="uq_matter_deadline_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deadline_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("matter_deadlines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    calculation_inputs_redacted: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MatterEvidenceNode(Base):
    __tablename__ = "matter_evidence_nodes"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type: Mapped[uuid.UUID] = mapped_column(String(32), nullable=False)
    title: Mapped[uuid.UUID] = mapped_column(String(255), nullable=False)
    statement_redacted: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(
        PortableUUID, ForeignKey("documents.id"), nullable=True
    )
    source_authority_id: Mapped[uuid.UUID | None] = mapped_column(String(128), nullable=True)
    source_rule_id: Mapped[uuid.UUID | None] = mapped_column(String(128), nullable=True)
    provenance_redacted: Mapped[dict | None] = mapped_column(
        "provenance", JSON, nullable=True, default=dict
    )
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_SUBMITTED")
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterEvidenceLink(Base):
    __tablename__ = "matter_evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matter_evidence_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matter_evidence_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[uuid.UUID] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    notes_redacted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MatterEvidenceFinding(Base):
    __tablename__ = "matter_evidence_findings"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_type: Mapped[uuid.UUID] = mapped_column(String(32), nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_evidence_nodes.id", ondelete="CASCADE"), nullable=True
    )
    related_node_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_evidence_nodes.id", ondelete="CASCADE"), nullable=True
    )
    summary_redacted: Mapped[uuid.UUID] = mapped_column(Text, nullable=False)
    status: Mapped[uuid.UUID] = mapped_column(String(24), nullable=False, default="OPEN")
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
