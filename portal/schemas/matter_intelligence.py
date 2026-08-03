"""API schemas for persistent matter intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MatterPartyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(
        pattern=r"^(CLIENT|CREDITOR|COLLECTOR|FURNISHER|SERVICER|ASSIGNEE|SECURED_PARTY|DEBTOR|OTHER)$"
    )
    display_name: str = Field(min_length=1, max_length=255)
    contact_summary: str | None = None
    identifier: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatterAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_type: str = Field(min_length=2, max_length=50)
    account_reference: str | None = Field(default=None, max_length=128)
    creditor_party_id: str | None = None
    collector_party_id: str | None = None
    furnisher_party_id: str | None = None
    servicer_party_id: str | None = None
    assignee_party_id: str | None = None
    status: str = Field(default="open", max_length=30)
    details: dict[str, Any] = Field(default_factory=dict)


class MatterFilingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filing_kind: str = Field(min_length=2, max_length=50)
    filing_number: str | None = Field(default=None, max_length=128)
    filing_office: str | None = None
    filing_jurisdiction: str | None = Field(default=None, max_length=32)
    filed_on: datetime | None = None
    debtor_name: str | None = None
    secured_party_id: str | None = None
    status: str = Field(default="reported", max_length=30)
    details: dict[str, Any] = Field(default_factory=dict)


class MatterCommunicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    communication_type: str = Field(min_length=2, max_length=40)
    direction: str = Field(pattern=r"^(inbound|outbound|internal|unknown)$")
    occurred_at: datetime
    sender_party_id: str | None = None
    recipient_party_id: str | None = None
    subject: str | None = None
    content: str | None = None
    source_document_id: str | None = None


class MatterDisputeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str | None = None
    dispute_type: str = Field(min_length=2, max_length=50)
    status: str = Field(default="open", max_length=30)
    submitted_on: datetime | None = None
    responded_on: datetime | None = None
    summary: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class MatterAttachmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str | None = None
    label: str = Field(min_length=1, max_length=255)
    attachment_kind: str = Field(min_length=2, max_length=40)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[A-Fa-f0-9]{64}$")
    classification: str = Field(default="UNCLASSIFIED", max_length=40)
    redaction_status: str = Field(default="REDACTION_REQUIRED", max_length=30)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatterAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    facts: dict[str, Any] = Field(default_factory=dict)
    conclusions: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class MatterAssessmentVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: dict[str, Any] = Field(default_factory=dict)
    conclusions: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class MatterAssessmentReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: str = Field(
        pattern=r"^(IN_REVIEW|APPROVED_WITH_CONDITIONS|APPROVED|REJECTED|CHANGES_REQUESTED)$"
    )
    notes: str = Field(min_length=1)


class MatterIntelligenceListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
