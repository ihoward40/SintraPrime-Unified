"""Legal authority and jurisdiction rule framework for fifty-state intelligence."""

from legal_authority.claim_integrity import (
    ClaimIntegrityDecision,
    ClaimIntegrityEvaluator,
    ClaimIntegrityInput,
    GateResult,
)
from legal_authority.engine import RuleEvaluationEngine
from legal_authority.models import (
    ConflictRecord,
    JurisdictionRule,
    LegalAuthority,
    ProfessionalReview,
)
from legal_authority.repository import LegalAuthorityRepository

__all__ = [
    "ClaimIntegrityDecision",
    "ClaimIntegrityEvaluator",
    "ClaimIntegrityInput",
    "ConflictRecord",
    "GateResult",
    "JurisdictionRule",
    "LegalAuthority",
    "LegalAuthorityRepository",
    "ProfessionalReview",
    "RuleEvaluationEngine",
]
