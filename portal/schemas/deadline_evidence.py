"""Schemas for matter deadlines and evidence graph operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MatterDeadlineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    deadline_type: str = Field(min_length=2, max_length=40)
    source_kind: str = Field(pattern=r"^(STATUTORY|CONTRACTUAL|PROCEDURAL|UCC|CUSTOM)$")
    trigger_at: datetime | None = None
    due_at: datetime | None = None
    timezone_name: str = Field(min_length=1, max_length=64)
    calendar_type: str = Field(pattern=r"^(CALENDAR_DAYS|BUSINESS_DAYS)$")
    calculation_status: str = Field(
        pattern=r"^(CALCULATED|HUMAN_REVIEW_REQUIRED|CONFLICTING|INSUFFICIENT_FACTS)$"
    )
    calculation_rule_id: str | None = None
    authority_ids: list[str] = Field(default_factory=list)
    trigger_basis: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    days_count: int | None = Field(default=None, ge=0)
    mailing_days: int = Field(default=0, ge=0)
    holidays: list[str] = Field(default_factory=list)


class MatterDeadlineCalculate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    deadline_type: str = Field(min_length=2, max_length=40)
    source_kind: str = Field(pattern=r"^(STATUTORY|CONTRACTUAL|PROCEDURAL|UCC|CUSTOM)$")
    trigger_at: datetime
    timezone_name: str = Field(min_length=1, max_length=64)
    calendar_type: str = Field(pattern=r"^(CALENDAR_DAYS|BUSINESS_DAYS)$")
    days_count: int = Field(ge=0)
    mailing_days: int = Field(default=0, ge=0)
    holidays: list[str] = Field(default_factory=list)
    calculation_rule_id: str | None = None
    authority_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    trigger_basis: dict[str, Any] = Field(default_factory=dict)


class MatterEvidenceNodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_type: str = Field(pattern=r"^(CLAIM|FACT|DOCUMENT|COMMUNICATION|AUTHORITY|RULE|DEADLINE)$")
    title: str = Field(min_length=1, max_length=255)
    statement: str | None = None
    evidence_status: str = Field(pattern=r"^(PROVEN|MISSING|DISPUTED|UNSUPPORTED|UNREVIEWED)$")
    source_document_id: str | None = None
    source_authority_id: str | None = None
    source_rule_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class MatterEvidenceLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_node_id: str
    target_node_id: str
    relationship_type: str = Field(
        pattern=r"^(SUPPORTS|CONTRADICTS|DERIVED_FROM|REQUIRES|REFUTES|CORROBORATES)$"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str | None = None


class MatterEvidenceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: str = Field(
        pattern=r"^(IN_REVIEW|APPROVED_WITH_CONDITIONS|APPROVED|REJECTED|CHANGES_REQUESTED)$"
    )
    notes: str = Field(min_length=1)


class MatterIntelligenceListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
