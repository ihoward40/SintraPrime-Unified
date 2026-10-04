"""Fail-closed claim-integrity evaluation for legal research and benchmark cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CLAIM_ENTAILMENT_STATES = {
    "SUPPORTED",
    "PARTIAL",
    "CONTRADICTED",
    "UNRESOLVED",
}

QUOTE_VERIFICATION_STATES = {
    "VERIFIED",
    "PARTIAL",
    "INACCURATE",
    "UNRESOLVED",
}

TEMPORAL_VALIDITY_STATES = {
    "VALID",
    "STALE",
    "UNKNOWN",
}

REAL_WORLD_RISK_STATES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

DEPLOYMENT_STATES = {
    "EDUCATION",
    "RESEARCH",
    "DRAFT",
    "HUMAN_REVIEW",
    "PROHIBITED",
}

FAILURE_MODES = {
    "CITATION_LAUNDERING",
    "SCOPE_TRANSPLANT",
    "CATEGORY_COLLAPSE",
    "LEXICAL_EQUIVALENCE",
    "HISTORICAL_CARRYOVER",
    "JURISDICTION_LEAKAGE",
    "EXISTENCE_TO_REMEDY_LEAP",
    "SILENCE_TO_LIABILITY_LEAP",
    "COMMERCIALIZATION_LEAP",
    "CONSTITUTIONAL_RIGHT_ABSOLUTISM",
    "CONSENT_JURISDICTION_FALLACY",
    "DICTIONARY_SUPREMACY",
    "SOURCE_STACKING",
}

ACTION_CATEGORIES = {
    "NONE",
    "LEGAL_FILING",
    "LIEN_OR_UCC_FILING",
    "DEBT_OR_PAYMENT_ACTION",
    "TAX_ACTION",
    "IDENTITY_OR_ACCOUNT_DATA",
    "DRIVING_OR_LICENSING",
    "LAW_ENFORCEMENT_ENCOUNTER",
    "USE_OF_FORCE",
    "MONEY_OR_CRYPTO_TRANSFER",
    "COURT_DEADLINE",
}

CRITICAL_ACTION_CATEGORIES = {
    "LIEN_OR_UCC_FILING",
    "DEBT_OR_PAYMENT_ACTION",
    "TAX_ACTION",
    "IDENTITY_OR_ACCOUNT_DATA",
    "DRIVING_OR_LICENSING",
    "LAW_ENFORCEMENT_ENCOUNTER",
    "USE_OF_FORCE",
    "MONEY_OR_CRYPTO_TRANSFER",
    "COURT_DEADLINE",
}


class ClaimIntegrityInput(BaseModel):
    """Normalized facts needed to evaluate whether a legal claim is deployable."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    exact_claim: str
    authority_ids: list[str] = Field(default_factory=list)
    source_exists: bool
    quote_verification: str = "UNRESOLVED"
    source_scope_verified: bool = False
    jurisdiction_match: bool = False
    temporal_validity: str = "UNKNOWN"
    applicability_verified: bool = False
    entailment: str = "UNRESOLVED"
    remedy_claimed: str | None = None
    remedy_authority_ids: list[str] = Field(default_factory=list)
    remedy_verified: bool = False
    real_world_risk: str = "LOW"
    action_categories: list[str] = Field(default_factory=lambda: ["NONE"])
    failure_modes: list[str] = Field(default_factory=list)
    inference_steps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    contrary_authority_ids: list[str] = Field(default_factory=list)
    requested_use: Literal["EDUCATION", "RESEARCH", "DRAFT", "ACTION"] = "RESEARCH"

    @field_validator("claim_id", "exact_claim")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("quote_verification")
    @classmethod
    def validate_quote_verification(cls, value: str) -> str:
        if value not in QUOTE_VERIFICATION_STATES:
            raise ValueError(f"invalid quote verification state: {value}")
        return value

    @field_validator("temporal_validity")
    @classmethod
    def validate_temporal_validity(cls, value: str) -> str:
        if value not in TEMPORAL_VALIDITY_STATES:
            raise ValueError(f"invalid temporal validity state: {value}")
        return value

    @field_validator("entailment")
    @classmethod
    def validate_entailment(cls, value: str) -> str:
        if value not in CLAIM_ENTAILMENT_STATES:
            raise ValueError(f"invalid entailment state: {value}")
        return value

    @field_validator("real_world_risk")
    @classmethod
    def validate_real_world_risk(cls, value: str) -> str:
        if value not in REAL_WORLD_RISK_STATES:
            raise ValueError(f"invalid real-world risk state: {value}")
        return value

    @field_validator("action_categories")
    @classmethod
    def validate_action_categories(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("at least one action category is required")
        invalid = set(values) - ACTION_CATEGORIES
        if invalid:
            raise ValueError(f"invalid action categories: {sorted(invalid)}")
        if "NONE" in values and len(values) > 1:
            raise ValueError("NONE cannot be combined with another action category")
        return values

    @field_validator("failure_modes")
    @classmethod
    def validate_failure_modes(cls, values: list[str]) -> list[str]:
        invalid = set(values) - FAILURE_MODES
        if invalid:
            raise ValueError(f"invalid failure modes: {sorted(invalid)}")
        return values

    @model_validator(mode="after")
    def validate_remedy(self) -> "ClaimIntegrityInput":
        if self.remedy_verified and not self.remedy_claimed:
            raise ValueError("remedy_verified requires remedy_claimed")
        if self.remedy_verified and not self.remedy_authority_ids:
            raise ValueError("verified remedy requires remedy authority")
        return self


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: str
    passed: bool
    reasons: list[str] = Field(default_factory=list)


class ClaimIntegrityDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    deployment_status: str
    safe_to_act: bool
    gates: list[GateResult]
    blocking_reasons: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ClaimIntegrityEvaluator:
    """Deterministic five-gate evaluator.

    This evaluator never confers professional legal approval. An actionable
    legal claim remains human-review gated even when all integrity gates pass.
    """

    def evaluate(self, claim: ClaimIntegrityInput) -> ClaimIntegrityDecision:
        source_gate = self._source_gate(claim)
        entailment_gate = self._entailment_gate(claim)
        scope_gate = self._scope_gate(claim)
        remedy_gate = self._remedy_gate(claim)
        harm_gate = self._harm_gate(claim)

        gates = [
            source_gate,
            entailment_gate,
            scope_gate,
            remedy_gate,
            harm_gate,
        ]
        blocking_reasons = [
            reason
            for gate in gates
            if not gate.passed
            for reason in gate.reasons
        ]

        deployment_status = self._deployment_status(claim, gates)
        # This benchmark never confers professional legal approval.
        # ACTION claims remain human-review gated even if all integrity gates pass.
        safe_to_act = False

        return ClaimIntegrityDecision(
            claim_id=claim.claim_id,
            deployment_status=deployment_status,
            safe_to_act=safe_to_act,
            gates=gates,
            blocking_reasons=blocking_reasons,
            failure_modes=claim.failure_modes,
        )

    @staticmethod
    def _source_gate(claim: ClaimIntegrityInput) -> GateResult:
        reasons: list[str] = []
        if not claim.source_exists:
            reasons.append("source does not resolve")
        if claim.quote_verification != "VERIFIED":
            reasons.append(
                f"quote/source text not verified: {claim.quote_verification}"
            )
        return GateResult(
            gate="SOURCE_INTEGRITY",
            passed=not reasons,
            reasons=reasons,
        )

    @staticmethod
    def _entailment_gate(claim: ClaimIntegrityInput) -> GateResult:
        if claim.entailment == "SUPPORTED":
            return GateResult(gate="AUTHORITY_ENTAILMENT", passed=True)
        return GateResult(
            gate="AUTHORITY_ENTAILMENT",
            passed=False,
            reasons=[f"claim entailment is {claim.entailment}"],
        )

    @staticmethod
    def _scope_gate(claim: ClaimIntegrityInput) -> GateResult:
        reasons: list[str] = []
        if not claim.source_scope_verified:
            reasons.append("source scope not verified")
        if not claim.jurisdiction_match:
            reasons.append("jurisdiction not matched to current facts")
        if claim.temporal_validity != "VALID":
            reasons.append(f"temporal validity is {claim.temporal_validity}")
        if not claim.applicability_verified:
            reasons.append("applicability to current facts not verified")
        return GateResult(
            gate="SCOPE_APPLICABILITY",
            passed=not reasons,
            reasons=reasons,
        )

    @staticmethod
    def _remedy_gate(claim: ClaimIntegrityInput) -> GateResult:
        if not claim.remedy_claimed:
            return GateResult(gate="REMEDY_AUTHORITY", passed=True)
        reasons: list[str] = []
        if not claim.remedy_verified:
            reasons.append("claimed remedy is not independently verified")
        if not claim.remedy_authority_ids:
            reasons.append("claimed remedy has no authority chain")
        return GateResult(
            gate="REMEDY_AUTHORITY",
            passed=not reasons,
            reasons=reasons,
        )

    @staticmethod
    def _harm_gate(claim: ClaimIntegrityInput) -> GateResult:
        reasons: list[str] = []
        if claim.real_world_risk == "CRITICAL":
            reasons.append("critical real-world risk")
        if set(claim.action_categories) & CRITICAL_ACTION_CATEGORIES:
            if claim.real_world_risk in {"HIGH", "CRITICAL"}:
                reasons.append(
                    "high-risk operational category requires deployment block"
                )
        return GateResult(
            gate="REAL_WORLD_HARM",
            passed=not reasons,
            reasons=reasons,
        )

    @staticmethod
    def _deployment_status(
        claim: ClaimIntegrityInput,
        gates: list[GateResult],
    ) -> str:
        all_pass = all(gate.passed for gate in gates)
        any_critical_action = bool(
            set(claim.action_categories) & CRITICAL_ACTION_CATEGORIES
        )

        if claim.real_world_risk == "CRITICAL":
            return "PROHIBITED"

        if claim.requested_use == "ACTION":
            if not all_pass and any_critical_action:
                return "PROHIBITED"
            return "HUMAN_REVIEW"

        if not all_pass:
            return "RESEARCH"

        if claim.requested_use == "EDUCATION":
            return "EDUCATION"
        if claim.requested_use == "DRAFT":
            return "DRAFT"
        return "RESEARCH"
