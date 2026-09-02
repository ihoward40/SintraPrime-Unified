"""Persistent creditor and UCC matter-intelligence records."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID


class MatterParty(Base):
    __tablename__ = "matter_parties"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[uuid.UUID] = mapped_column(String(40), nullable=False)
    display_name: Mapped[uuid.UUID] = mapped_column(String(255), nullable=False)
    contact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    identifier_redacted: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterAccount(Base):
    __tablename__ = "matter_accounts"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_type: Mapped[uuid.UUID] = mapped_column(String(50), nullable=False)
    account_reference_redacted: Mapped[uuid.UUID | None] = mapped_column(String(128), nullable=True)
    creditor_party_id: Mapped[str | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    collector_party_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    furnisher_party_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    servicer_party_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    assignee_party_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    status: Mapped[uuid.UUID] = mapped_column(String(30), nullable=False, default="open")
    details_redacted: Mapped[dict | None] = mapped_column(
        "details", JSON, nullable=True, default=dict
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterFiling(Base):
    __tablename__ = "matter_filings"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filing_kind: Mapped[uuid.UUID] = mapped_column(String(50), nullable=False)
    filing_number_redacted: Mapped[uuid.UUID | None] = mapped_column(String(128), nullable=True)
    filing_office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filing_jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    filed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    debtor_name_redacted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secured_party_id: Mapped[str | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    status: Mapped[uuid.UUID] = mapped_column(String(30), nullable=False, default="reported")
    details_redacted: Mapped[dict | None] = mapped_column(
        "details", JSON, nullable=True, default=dict
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterCommunication(Base):
    __tablename__ = "matter_communications"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    communication_type: Mapped[uuid.UUID] = mapped_column(String(40), nullable=False)
    direction: Mapped[uuid.UUID] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sender_party_id: Mapped[str | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    recipient_party_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_parties.id"), nullable=True
    )
    subject_redacted: Mapped[uuid.UUID | None] = mapped_column(String(500), nullable=True)
    content_redacted: Mapped[uuid.UUID | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(
        PortableUUID, ForeignKey("documents.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterDispute(Base):
    __tablename__ = "matter_disputes"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("matter_accounts.id"), nullable=True
    )
    dispute_type: Mapped[uuid.UUID] = mapped_column(String(50), nullable=False)
    status: Mapped[uuid.UUID] = mapped_column(String(30), nullable=False, default="open")
    submitted_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    details_redacted: Mapped[dict | None] = mapped_column(
        "details", JSON, nullable=True, default=dict
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterAttachment(Base):
    __tablename__ = "matter_attachments"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("documents.id"), nullable=True
    )
    label_redacted: Mapped[uuid.UUID] = mapped_column(String(255), nullable=False)
    attachment_kind: Mapped[uuid.UUID] = mapped_column(String(40), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(40), nullable=False, default="UNCLASSIFIED")
    redaction_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="REDACTION_REQUIRED"
    )
    metadata_redacted: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterAssessment(Base):
    __tablename__ = "matter_assessments"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_type: Mapped[uuid.UUID] = mapped_column(String(50), nullable=False)
    title: Mapped[uuid.UUID] = mapped_column(String(255), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_SUBMITTED")
    reviewer_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewer_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MatterAssessmentVersion(Base):
    __tablename__ = "matter_assessment_versions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID,
        ForeignKey("matter_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    facts_redacted: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    conclusions_redacted: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MatterAuditEvent(Base):
    __tablename__ = "matter_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details_redacted: Mapped[dict | None] = mapped_column(
        "details", JSON, nullable=True, default=dict
    )
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
