"""Policy evaluation for economic governance.

No function in this module performs a payment, transfers an asset, opens an account,
borrows money, trades a security, or makes a legal determination. It only evaluates
structured requests and evidence.
"""

from __future__ import annotations

from decimal import Decimal

from .models import (
    AssetProvenanceRecord,
    EvidenceType,
    SpendCategory,
    SpendRequest,
)
from pydantic import BaseModel, Field


PROVENANCE_CHAIN_FIELDS: tuple[tuple[str, str], ...] = (
    ("origin", "origin"),
    ("claimed_owner", "claimed owner"),
    ("transfer_document", "transfer document"),
    ("consideration", "consideration"),
    ("trust_acceptance_record", "trust acceptance record"),
    ("schedule_a_reference", "Schedule A reference"),
    ("accounting_record", "accounting record"),
    ("control_or_possession", "control or possession evidence"),
    ("legal_classification", "legal classification"),
)


class ProvenanceAssessment(BaseModel):
    asset_id: str
    complete: bool
    missing_elements: list[str]
    verified_evidence_count: int = Field(ge=0)
    public_filing_present: bool
    warnings: list[str] = Field(default_factory=list)


def assess_provenance(record: AssetProvenanceRecord) -> ProvenanceAssessment:
    """Assess documentary completeness without manufacturing legal effects.

    In particular, a public UCC or government filing is evidence that a record exists.
    It does not, by itself, establish ownership, attachment, perfection, priority, or
    enforceability. Those conclusions remain explicit status fields on the record.
    """

    missing = [label for field, label in PROVENANCE_CHAIN_FIELDS if not getattr(record, field)]
    missing.extend(item for item in record.missing_elements if item not in missing)

    public_filing_present = bool(record.public_filing_reference) or any(
        item.evidence_type
        in {EvidenceType.PUBLIC_FILING, EvidenceType.GOVERNMENT_ACKNOWLEDGMENT}
        for item in record.evidence
    )
    verified_evidence_count = sum(item.verified for item in record.evidence)

    warnings: list[str] = []
    if public_filing_present:
        warnings.append(
            "Public filing evidence records notice/filing activity only; it does not auto-establish "
            "ownership, attachment, perfection, priority, or enforceability."
        )

    return ProvenanceAssessment(
        asset_id=record.asset_id,
        complete=not missing,
        missing_elements=missing,
        verified_evidence_count=verified_evidence_count,
        public_filing_present=public_filing_present,
        warnings=warnings,
    )


class SpendPolicy(BaseModel):
    """Mission-scoped default-deny spending policy."""

    mission_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    per_transaction_limit: Decimal = Field(gt=0)
    mission_budget: Decimal = Field(gt=0)
    spent_to_date: Decimal = Field(default=Decimal("0"), ge=0)
    allowed_categories: set[SpendCategory] = Field(
        default_factory=lambda: {
            SpendCategory.RESEARCH,
            SpendCategory.PUBLIC_RECORDS,
            SpendCategory.API_CREDITS,
        }
    )
    principal_approval_categories: set[SpendCategory] = Field(
        default_factory=lambda: {SpendCategory.SOFTWARE}
    )


class SpendDecision(BaseModel):
    allowed: bool
    requires_principal_approval: bool = False
    reason: str
    remaining_budget: Decimal = Field(ge=0)


HARD_DENY_CATEGORIES = frozenset(
    {
        SpendCategory.TRANSFER_TO_HUMAN,
        SpendCategory.BORROWING,
        SpendCategory.OPEN_ACCOUNT,
        SpendCategory.SECURITIES,
        SpendCategory.TRUST_ASSET_MOVEMENT,
    }
)


def evaluate_spend(request: SpendRequest, policy: SpendPolicy) -> SpendDecision:
    """Evaluate a proposed agent spend. This function never executes the spend."""

    remaining = max(policy.mission_budget - policy.spent_to_date, Decimal("0"))

    if request.mission_id != policy.mission_id:
        return SpendDecision(
            allowed=False,
            reason="mission mismatch",
            remaining_budget=remaining,
        )
    if request.agent_id != policy.agent_id:
        return SpendDecision(
            allowed=False,
            reason="agent mismatch",
            remaining_budget=remaining,
        )
    if request.category in HARD_DENY_CATEGORIES:
        return SpendDecision(
            allowed=False,
            reason=f"category {request.category.value} is hard-denied for autonomous execution",
            remaining_budget=remaining,
        )
    if request.amount > policy.per_transaction_limit:
        return SpendDecision(
            allowed=False,
            reason="request exceeds per-transaction limit",
            remaining_budget=remaining,
        )
    if request.amount > remaining:
        return SpendDecision(
            allowed=False,
            reason="request exceeds remaining mission budget",
            remaining_budget=remaining,
        )
    if request.category in policy.principal_approval_categories:
        return SpendDecision(
            allowed=False,
            requires_principal_approval=True,
            reason=f"category {request.category.value} requires principal approval",
            remaining_budget=remaining,
        )
    if request.category not in policy.allowed_categories:
        return SpendDecision(
            allowed=False,
            reason=f"category {request.category.value} is not allowlisted",
            remaining_budget=remaining,
        )

    return SpendDecision(
        allowed=True,
        reason="request is within mission scope, category allowlist, and budget",
        remaining_budget=remaining - request.amount,
    )
