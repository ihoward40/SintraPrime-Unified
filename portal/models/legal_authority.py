"""SQLAlchemy persistence models for future legal authority storage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from portal.database import Base
from portal.models.types import PortableUUIDString, PortableUUID


class LegalAuthorityRecord(Base):
    __tablename__ = "legal_authorities"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    authority_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_classification: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    citation: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    court_or_agency: Mapped[str | None] = mapped_column(String(256), nullable=True)
    docket_or_bill_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    repeal_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    authority_weight: Mapped[int] = mapped_column(nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_legal_authorities_jurisdiction_type", "jurisdiction", "authority_type"),
    )


class JurisdictionRuleRecord(Base):
    __tablename__ = "jurisdiction_rules"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    rule_statement: Mapped[str] = mapped_column(Text, nullable=False)
    rule_logic: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    authority_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(nullable=False, default=True)
    effective_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exceptions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    conflicting_rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supersedes_rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    superseded_by_rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (Index("ix_jurisdiction_rules_lookup", "jurisdiction", "domain", "topic"),)


class ProfessionalReviewRecord(Base):
    __tablename__ = "professional_reviews"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reviewer_role: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_identity: Mapped[str | None] = mapped_column(String(256), nullable=True)
    review_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    findings: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_professional_reviews_object", "object_type", "object_id"),)
