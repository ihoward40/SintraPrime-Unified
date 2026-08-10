"""Domain models for evidence-first economic governance.

The models are deliberately conservative: recorded documents and public filings are
tracked as evidence, while legal effects remain explicit assertions that require their
own support and review.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ClaimStatus(StrEnum):
    """Maturity of an asserted fact or right."""

    CLAIMED = "claimed"
    DOCUMENTED = "documented"
    VERIFIED = "verified"
    ADJUDICATED = "adjudicated"


class LegalEffectStatus(StrEnum):
    """Status of a distinct legal conclusion.

    A filing or document never promotes these fields automatically.
    """

    NOT_ASSESSED = "not_assessed"
    ASSERTED = "asserted"
    VERIFIED = "verified"
    ADJUDICATED = "adjudicated"


class EvidenceType(StrEnum):
    PUBLIC_FILING = "public_filing"
    CONTRACT = "contract"
    ASSIGNMENT = "assignment"
    TRUST_INSTRUMENT = "trust_instrument"
    ACCOUNTING_RECORD = "accounting_record"
    POSSESSION_OR_CONTROL = "possession_or_control"
    GOVERNMENT_ACKNOWLEDGMENT = "government_acknowledgment"
    COURT_ORDER = "court_order"
    SOURCE_FILE = "source_file"
    GIT_HISTORY = "git_history"
    COMMERCIAL_RECORD = "commercial_record"
    OTHER = "other"


class EvidenceReference(BaseModel):
    evidence_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    reference: str = Field(min_length=1)
    description: str = Field(min_length=1)
    verified: bool = False
    supports: set[str] = Field(default_factory=set)


class AssetProvenanceRecord(BaseModel):
    """Trace an asset from origin through claimed ownership and legal classification."""

    asset_id: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    asset_name: str = Field(min_length=1)
    origin: str | None = None
    creator_or_source: str | None = None
    creation_or_acquisition_date: date | None = None

    claimed_owner: str | None = None
    claim_status: ClaimStatus = ClaimStatus.CLAIMED
    transfer_document: str | None = None
    consideration: str | None = None
    trust_acceptance_record: str | None = None
    schedule_a_reference: str | None = None
    accounting_record: str | None = None
    control_or_possession: str | None = None
    legal_classification: str | None = None
    public_filing_reference: str | None = None

    ownership_status: LegalEffectStatus = LegalEffectStatus.NOT_ASSESSED
    attachment_status: LegalEffectStatus = LegalEffectStatus.NOT_ASSESSED
    perfection_status: LegalEffectStatus = LegalEffectStatus.NOT_ASSESSED
    priority_status: LegalEffectStatus = LegalEffectStatus.NOT_ASSESSED
    enforceability_status: LegalEffectStatus = LegalEffectStatus.NOT_ASSESSED

    evidence: list[EvidenceReference] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ValueAccrualRecord(BaseModel):
    """Describe where economic value is intended to accrue and how that is evidenced."""

    value_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    activity: str = Field(min_length=1)
    revenue_source: str = Field(min_length=1)
    intended_value_recipient: str = Field(min_length=1)
    governing_instrument: str | None = None
    measurement_method: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)
    claim_status: ClaimStatus = ClaimStatus.CLAIMED


class ScenarioConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScenarioRecord(BaseModel):
    """A thesis is stored as a scenario, never silently promoted to fact."""

    scenario_id: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    confidence: ScenarioConfidence
    failure_conditions: list[str] = Field(min_length=1)
    time_horizon: str = Field(min_length=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    decision_use: str | None = None

    @model_validator(mode="after")
    def require_meaningful_scenario(self) -> ScenarioRecord:
        if any(not item.strip() for item in self.assumptions):
            raise ValueError("scenario assumptions must be non-empty")
        if any(not item.strip() for item in self.failure_conditions):
            raise ValueError("scenario failure conditions must be non-empty")
        return self


class CapitalReserveLayer(BaseModel):
    layer: int = Field(ge=1, le=6)
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    target_amount: Decimal | None = Field(default=None, ge=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    deployable: bool = False


class CapitalReservePolicy(BaseModel):
    """Six-layer reserve structure; targets remain explicit policy choices."""

    layers: list[CapitalReserveLayer] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_layers(self) -> CapitalReservePolicy:
        identifiers = [item.layer for item in self.layers]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("capital reserve layer numbers must be unique")
        return self

    @classmethod
    def default_stack(cls) -> CapitalReservePolicy:
        names = (
            (1, "Daily liquidity", "Ordinary near-term operating needs"),
            (2, "30-day operating reserve", "Short-duration operating resilience"),
            (3, "Business revolving credit", "Pre-arranged working-capital capacity"),
            (4, "Revenue-producing digital assets", "Assets intended to produce recurring revenue"),
            (5, "Strategic investment capital", "Selective long-duration opportunity capital"),
            (6, "Long-duration family/trust capital", "Capital reserved for long-horizon stewardship"),
        )
        return cls(
            layers=[
                CapitalReserveLayer(layer=layer, name=name, purpose=purpose)
                for layer, name, purpose in names
            ]
        )


class SpendCategory(StrEnum):
    RESEARCH = "research"
    PUBLIC_RECORDS = "public_records"
    API_CREDITS = "api_credits"
    SOFTWARE = "software"
    TRANSFER_TO_HUMAN = "transfer_to_human"
    BORROWING = "borrowing"
    OPEN_ACCOUNT = "open_account"
    SECURITIES = "securities"
    TRUST_ASSET_MOVEMENT = "trust_asset_movement"
    OTHER = "other"


class SpendRequest(BaseModel):
    request_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    category: SpendCategory
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    purpose: str = Field(min_length=1)
