"""Pydantic models for legal authorities, rules, reviews, challenges, and conflicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from legal_authority.constants import (
    AUDIT_EVENT_TYPES,
    AUTHORITY_HIERARCHY,
    CHALLENGE_STATES,
    CHALLENGE_TYPES,
    CREDENTIAL_VERIFICATION_STATES,
    MANUAL_REVIEW_STATES,
    REVIEW_STATES,
    REVIEWER_ROLES,
    RULE_CATEGORIES,
    RULE_STATUSES,
    SOURCE_AVAILABILITY_STATES,
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
    last_checked_at: datetime | None = None
    next_review_at: datetime | None = None
    expected_review_frequency_days: int | None = Field(default=None, ge=1)
    source_availability_status: str = "UNKNOWN"
    current_hash: str | None = None
    change_detected: bool = False
    manual_review_status: str = "NOT_REQUIRED"
    supersession_candidate: str | None = None
    broken_link_status: str | None = None
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

    @field_validator("source_availability_status")
    @classmethod
    def validate_source_availability_status(cls, value: str) -> str:
        if value not in SOURCE_AVAILABILITY_STATES:
            raise ValueError(f"invalid source availability status: {value}")
        return value

    @field_validator("manual_review_status")
    @classmethod
    def validate_manual_review_status(cls, value: str) -> str:
        if value not in MANUAL_REVIEW_STATES:
            raise ValueError(f"invalid manual review status: {value}")
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
        if self.change_detected and self.manual_review_status == "NOT_REQUIRED":
            raise ValueError("changed sources require manual review tracking")
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
    rule_category: str = "STATE_RULE"
    review_status: str = "NOT_SUBMITTED"
    critical_deficiencies: list[str] = Field(default_factory=list)
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

    @field_validator("rule_category")
    @classmethod
    def validate_rule_category(cls, value: str) -> str:
        if value not in RULE_CATEGORIES:
            raise ValueError(f"invalid rule category: {value}")
        return value

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        if value not in REVIEW_STATES:
            raise ValueError(f"invalid review status: {value}")
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
        if self.review_status == "APPROVED" and self.requires_human_review:
            raise ValueError("approved rules cannot retain requires_human_review")
        return self


class ProfessionalReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    object_type: str
    object_id: str
    jurisdiction: str
    domain: str
    reviewer_role: str
    reviewer_identity: str | None = None
    declared_credentials: str | None = None
    credential_verification_status: str = "NOT_VERIFIED"
    review_status: str
    findings: str
    conditions: list[str] = Field(default_factory=list)
    reviewed_authorities: list[str] = Field(default_factory=list)
    rejected_authorities: list[str] = Field(default_factory=list)
    approval_scope: str | None = None
    effective_date: date | None = None
    expires_at: datetime | None = None
    digital_signature: str | None = None
    audit_event_id: str | None = None
    reviewed_at: datetime | None = None

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, value: str) -> str:
        if value not in SUPPORTED_JURISDICTIONS:
            raise ValueError(f"unsupported jurisdiction: {value}")
        return value

    @field_validator("reviewer_role")
    @classmethod
    def validate_reviewer_role(cls, value: str) -> str:
        if value not in REVIEWER_ROLES:
            raise ValueError(f"invalid reviewer role: {value}")
        return value

    @field_validator("credential_verification_status")
    @classmethod
    def validate_credential_state(cls, value: str) -> str:
        if value not in CREDENTIAL_VERIFICATION_STATES:
            raise ValueError(f"invalid credential verification status: {value}")
        return value

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, value: str) -> str:
        if value not in REVIEW_STATES:
            raise ValueError(f"invalid review status: {value}")
        return value

    @model_validator(mode="after")
    def validate_approval(self) -> ProfessionalReview:
        if self.review_status in {"APPROVED", "APPROVED_WITH_CONDITIONS"}:
            if self.reviewer_role == "CPA" and self.domain != "accounting":
                raise ValueError("CPA approval is limited to accounting rules")
            if self.domain != "accounting" and self.reviewer_role != "LICENSED_ATTORNEY":
                raise ValueError("only licensed attorneys may approve legal rules")
            if not self.digital_signature:
                raise ValueError("approved reviews require an authenticated approval event")
        return self


class LegalChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    object_type: str
    object_id: str
    jurisdiction: str
    domain: str
    challenge_type: str
    challenge_state: str
    submitted_by_role: str
    submitted_by_identity: str | None = None
    issue: str
    original_snapshot: dict[str, Any]
    challenged_version: dict[str, Any]
    evidence_submitted: list[dict[str, Any]] = Field(default_factory=list)
    reviewer_decision: str | None = None
    corrected_version: dict[str, Any] | None = None
    audit_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, value: str) -> str:
        if value not in SUPPORTED_JURISDICTIONS:
            raise ValueError(f"unsupported jurisdiction: {value}")
        return value

    @field_validator("challenge_type")
    @classmethod
    def validate_challenge_type(cls, value: str) -> str:
        if value not in CHALLENGE_TYPES:
            raise ValueError(f"invalid challenge type: {value}")
        return value

    @field_validator("challenge_state")
    @classmethod
    def validate_challenge_state(cls, value: str) -> str:
        if value not in CHALLENGE_STATES:
            raise ValueError(f"invalid challenge state: {value}")
        return value

    @field_validator("submitted_by_role")
    @classmethod
    def validate_submitter_role(cls, value: str) -> str:
        if value not in REVIEWER_ROLES:
            raise ValueError(f"invalid submitter role: {value}")
        return value


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: str
    object_type: str
    object_id: str
    actor_role: str
    actor_identity: str | None = None
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in AUDIT_EVENT_TYPES:
            raise ValueError(f"invalid audit event type: {value}")
        return value

    @field_validator("actor_role")
    @classmethod
    def validate_actor_role(cls, value: str) -> str:
        if value not in REVIEWER_ROLES:
            raise ValueError(f"invalid actor role: {value}")
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


class SourceRefreshResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authority_id: str
    stale: bool
    hash_changed: bool
    source_available: bool
    review_required: bool
    previous_hash: str | None = None
    current_hash: str | None = None
    warnings: list[str] = Field(default_factory=list)
    audit_event: AuditEvent | None = None
