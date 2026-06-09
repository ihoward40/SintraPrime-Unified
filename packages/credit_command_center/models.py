"""Data models for the Credit Command Center service.

All models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# ── Enums ────────────────────────────────────────────────────────────────────


class ServiceTier(StrEnum):
    """Service tier a client has purchased."""

    AUDIT = "audit"
    BLUEPRINT = "blueprint"
    VAULT = "vault"


class CaseStatus(StrEnum):
    """Lifecycle status of a client case."""

    INTAKE = "intake"
    EVIDENCE_COLLECTION = "evidence_collection"
    ANALYSIS = "analysis"
    REVIEW = "review"
    DELIVERED = "delivered"
    ARCHIVED = "archived"


class FindingCategory(StrEnum):
    """Category for a finding in the 7-category scorecard."""

    CREDIT = "credit"
    COLLECTION_DEFENSE = "collection_defense"
    HOUSING = "housing"
    EMPLOYMENT = "employment"
    DOCUMENTATION = "documentation"
    EVIDENCE = "evidence"
    FOLLOW_UP = "follow_up"


class ConfidenceLevel(StrEnum):
    """Confidence in an evidence item or finding."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PENDING_OCR = "pending_ocr"


class Bureau(StrEnum):
    """Credit bureau."""

    EQUIFAX = "equifax"
    TRANSUNION = "transunion"
    EXPERIAN = "experian"


class AccountStatus(StrEnum):
    """Status of a credit account."""

    OPEN = "open"
    CLOSED = "closed"
    COLLECTIONS = "collections"
    DISPUTED = "disputed"
    PAID = "paid"
    CHARGE_OFF = "charge_off"


class ScorecardRating(StrEnum):
    """Overall rating derived from scorecard total."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    HIGH_RISK = "high_risk"


# ── Models ───────────────────────────────────────────────────────────────────


class ClientCase(BaseModel):
    """A single client case through the Credit Command Center pipeline."""

    case_id: str = Field(..., description="Format: C-0001")
    client_name: str
    email: str
    tier: ServiceTier = ServiceTier.AUDIT
    status: CaseStatus = CaseStatus.INTAKE
    scorecard_total: int | None = Field(None, ge=0, le=70)
    scorecard_rating: ScorecardRating | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, v: str) -> str:
        if not v or not v.startswith("C-"):
            raise ValueError("case_id must start with 'C-' (e.g. C-0001)")
        return v

    @field_validator("scorecard_total")
    @classmethod
    def validate_scorecard_total(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 70):
            raise ValueError("scorecard_total must be between 0 and 70")
        return v


class CreditAccount(BaseModel):
    """A credit account or trade line on a consumer report."""

    creditor_name: str
    account_number: str = Field(..., description="Last 4 digits or masked")
    account_type: str = Field(..., description="e.g. auto loan, credit card, collection")
    bureau: Bureau
    balance: float | None = None
    status: AccountStatus = AccountStatus.OPEN
    date_opened: str | None = None
    date_closed: str | None = None
    remarks: str | None = None


class EvidenceItem(BaseModel):
    """A single document or piece of evidence in a client's file."""

    file_name: str
    file_path: str
    date: str | None = Field(None, description="Document date from letterhead or metadata")
    sender: str | None = None
    account_referenced: str | None = None
    outcome: str | None = Field(None, description="Key quotes, decisions, next steps")
    belongs_in_report: bool = True
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class Finding(BaseModel):
    """A single finding in an audit report, gated by Vicktor's 3 questions."""

    finding_number: int = Field(..., ge=1, le=20)
    category: FindingCategory
    what_is_wrong: str = Field(..., description="Vicktor Q1: What is wrong?")
    evidence_support: str = Field(..., description="Vicktor Q2: What evidence supports it?")
    next_step: str = Field(..., description="Vicktor Q3: What should happen next?")
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class ActionReceipt(BaseModel):
    """An audit-trail entry recording an action taken on a case."""

    receipt_id: str = Field(..., description="Format: R-0001")
    case_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = Field(..., description="Who performed the action (Hermes / Isiah / System)")
    action: str = Field(..., description="e.g. intake_received, document_cataloged, finding_created")
    details: dict = Field(default_factory=dict)
    file_path: str | None = None


class Scorecard(BaseModel):
    """7-category consumer readiness scorecard, each /10, total /70."""

    credit: int = Field(..., ge=0, le=10)
    collection_defense: int = Field(..., ge=0, le=10)
    housing: int = Field(..., ge=0, le=10)
    employment: int = Field(..., ge=0, le=10)
    documentation: int = Field(..., ge=0, le=10)
    evidence: int = Field(..., ge=0, le=10)
    follow_up: int = Field(..., ge=0, le=10)

    @property
    def total(self) -> int:
        return (
            self.credit
            + self.collection_defense
            + self.housing
            + self.employment
            + self.documentation
            + self.evidence
            + self.follow_up
        )

    @property
    def rating(self) -> ScorecardRating:
        total = self.total
        if total >= 60:
            return ScorecardRating.STRONG
        if total >= 40:
            return ScorecardRating.MODERATE
        if total >= 20:
            return ScorecardRating.WEAK
        return ScorecardRating.HIGH_RISK

    def category_scores(self) -> dict[str, int]:
        """Return a dict of category name → score for display."""
        return {
            "credit": self.credit,
            "collection_defense": self.collection_defense,
            "housing": self.housing,
            "employment": self.employment,
            "documentation": self.documentation,
            "evidence": self.evidence,
            "follow_up": self.follow_up,
        }
