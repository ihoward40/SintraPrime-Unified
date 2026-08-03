"""Pydantic models for legal authorities, rules, reviews, and conflicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from legal_authority.constants import (
    AUTHORITY_HIERARCHY,
    REVIEW_STATES,
    RULE_STATUSES,
    SOURCE_CLASSIFICATIONS,
    SUPPORTED_JURISDICTIONS,
    VERIFICATION_STATES,
)


class LegalAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    jurisdiction: str
    authority_type: str
    source_classification: str
    citation: str
    title: str
    court_or_agency: str | None = None
    docket_or_bill_number: str | None = None
    source_url: str | None = None
    source_document_id: str | None = None
    publication_date: date | None = None
    effective_date: date | None = None
    repeal_date: date | None = None
    last_verified_at: datetime | None = None
    verified_by: str | None = None
    verification_status: str
    authority_weight: int
    summary: str
    quoted_text: str | None = None
    limitations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    content_hash: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, value: str) -> str:
        if value not in SUPPORTED_JURISDICTIONS:
            raise ValueError(f"unsupported jurisdiction: {value}")
        return value

    @field_validator("authority_type")
    @classmethod
    def validate_authority_type(cls, value: str) -> str:
        if value not in AUTHORITY_HIERARCHY:
            raise ValueError(f"invalid authority type: {value}")
        return value

    @field_validator("source_classification")
    @classmethod
    def validate_source_classification(cls, value: str) -> str:
        if value not in SOURCE_CLASSIFICATIONS:
            raise ValueError(f"invalid source classification: {value}")
        return value

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATES:
            raise ValueError(f"invalid verification status: {value}")
        return value

    @field_validator("citation", "title", "summary")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @model_validator(mode="after")
    def validate_weight_and_dates(self) -> LegalAuthority:
        expected = AUTHORITY_HIERARCHY[self.authority_type]
        if self.authority_weight != expected:
            raise ValueError("authority_weight must match authority_type hierarchy")
        if self.repeal_date and self.effective_date and self.repeal_date <= self.effective_date:
            raise ValueError("repeal_date must be after effective_date")
        if self.source_classification == "UNVERIFIED_PRIVATE_LAW_CLAIM":
            if self.verification_status not in {"UNVERIFIED", "HUMAN_REVIEW_REQUIRED"}:
                raise ValueError("unsupported private claims cannot be verified")
        return self


class JurisdictionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    jurisdiction: str
    domain: str
    topic: str
    rule_statement: str
    rule_logic: dict[str, Any]
    authority_ids: list[str]
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    effective_from: date | None = None
    effective_to: date | None = None
    exceptions: list[dict[str, Any]] = Field(default_factory=list)
    conflicting_rule_ids: list[str] = Field(default_factory=list)
    supersedes_rule_ids: list[str] = Field(default_factory=list)
    superseded_by_rule_ids: list[str] = Field(default_factory=list)
    version: str
    created_at: datetime
    updated_at: datetime

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, value: str) -> str:
        if value not in SUPPORTED_JURISDICTIONS:
            raise ValueError(f"unsupported jurisdiction: {value}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in RULE_STATUSES:
            raise ValueError(f"invalid rule status: {value}")
        return value

    @field_validator("authority_ids")
    @classmethod
    def require_authorities(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("rule must cite at least one authority")
        return value

    @model_validator(mode="after")
    def validate_rule(self) -> JurisdictionRule:
        if self.effective_to and self.effective_from and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        if not isinstance(self.rule_logic.get("conditions", []), list):
            raise ValueError("rule_logic.conditions must be a list")
        if not isinstance(self.rule_logic.get("conclusion"), str):
            raise ValueError("rule_logic.conclusion must be a string")
        if self.status == "QUARANTINED" and not self.requires_human_review:
            raise ValueError("quarantined rules require human review")
        return self


class ProfessionalReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    object_type: str
    object_id: str
    reviewer_role: str
    reviewer_identity: str | None = None
    review_status: str
    findings: str
    conditions: list[str] = Field(default_factory=list)
    reviewed_at: datetime | None = None

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        if value not in REVIEW_STATES:
            raise ValueError(f"invalid review status: {value}")
        return value


class ConflictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    issue: str
    jurisdiction: str
    competing_rules: list[str]
    competing_authorities: list[str]
    authority_ranking: list[dict[str, Any]]
    date_relationship: str
    factual_distinctions: list[str]
    unresolved_questions: list[str]
    recommended_controlling_rule: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    human_review_required: bool


class RuleSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_rule: JurisdictionRule | None
    candidate_rule_ids: list[str]
    conflicts: list[ConflictRecord]
    verification_status: str
    human_review_required: bool
    explanation: str
    as_of_date: date
    limitations: list[str]
    authorities: list[LegalAuthority]
