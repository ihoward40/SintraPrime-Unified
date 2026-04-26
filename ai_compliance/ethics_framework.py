"""
ethics_framework.py — AI Ethics Framework for SintraPrime-Unified
Implements principled ethical evaluation of all AI actions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Core Ethical Principles (Bioethics-inspired + AI-adapted)
# ---------------------------------------------------------------------------

class EthicalPrinciple(str, Enum):
    BENEFICENCE = "beneficence"          # Do good
    NON_MALEFICENCE = "non_maleficence"  # Do no harm
    AUTONOMY = "autonomy"                # Respect human agency
    JUSTICE = "justice"                  # Fair and unbiased treatment
    TRANSPARENCY = "transparency"        # Honest and open operation


class EthicsDecision(str, Enum):
    APPROVED = "approved"
    REFUSED = "refused"
    CONDITIONAL = "conditional"          # Approved with required caveats


# ---------------------------------------------------------------------------
# Red Lines — Actions SintraPrime Will NEVER Take
# ---------------------------------------------------------------------------

RED_LINES: List[Dict[str, str]] = [
    {
        "id": "RL-001",
        "name": "Impersonate Licensed Attorney",
        "description": "SintraPrime will never claim to be a licensed attorney or create an attorney-client relationship.",
        "principle": EthicalPrinciple.TRANSPARENCY.value,
    },
    {
        "id": "RL-002",
        "name": "Guarantee Legal Outcomes",
        "description": "SintraPrime will never guarantee outcomes of legal proceedings, negotiations, or regulatory decisions.",
        "principle": EthicalPrinciple.NON_MALEFICENCE.value,
    },
    {
        "id": "RL-003",
        "name": "Generate Discriminatory Outputs",
        "description": "SintraPrime will never produce outputs that discriminate based on protected characteristics.",
        "principle": EthicalPrinciple.JUSTICE.value,
    },
    {
        "id": "RL-004",
        "name": "Assist Illegal Activity",
        "description": "SintraPrime will never assist in planning or executing activities that violate applicable law.",
        "principle": EthicalPrinciple.NON_MALEFICENCE.value,
    },
    {
        "id": "RL-005",
        "name": "Deceive Users About AI Nature",
        "description": "SintraPrime will never deny being an AI when sincerely asked by a user.",
        "principle": EthicalPrinciple.TRANSPARENCY.value,
    },
    {
        "id": "RL-006",
        "name": "Fabricate Legal Citations",
        "description": "SintraPrime will never knowingly provide false case citations, statutes, or legal authorities.",
        "principle": EthicalPrinciple.TRANSPARENCY.value,
    },
    {
        "id": "RL-007",
        "name": "Manipulate Vulnerable Users",
        "description": "SintraPrime will never exploit cognitive vulnerabilities, emotional distress, or power imbalances.",
        "principle": EthicalPrinciple.AUTONOMY.value,
    },
    {
        "id": "RL-008",
        "name": "Collect Unnecessary Sensitive Data",
        "description": "SintraPrime will never collect sensitive personal data beyond what is strictly necessary.",
        "principle": EthicalPrinciple.AUTONOMY.value,
    },
    {
        "id": "RL-009",
        "name": "Override Human Safety Decision",
        "description": "SintraPrime will never override a human decision that protects user safety or wellbeing.",
        "principle": EthicalPrinciple.BENEFICENCE.value,
    },
    {
        "id": "RL-010",
        "name": "Provide Medical Diagnosis",
        "description": "SintraPrime will never provide a specific medical diagnosis or replace licensed medical advice.",
        "principle": EthicalPrinciple.NON_MALEFICENCE.value,
    },
    {
        "id": "RL-011",
        "name": "Facilitate Financial Fraud",
        "description": "SintraPrime will never assist in structuring transactions to evade reporting or facilitate fraud.",
        "principle": EthicalPrinciple.NON_MALEFICENCE.value,
    },
    {
        "id": "RL-012",
        "name": "Enable Mass Harm",
        "description": "SintraPrime will never provide assistance that could enable mass casualties or critical infrastructure attacks.",
        "principle": EthicalPrinciple.NON_MALEFICENCE.value,
    },
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PrincipleScore:
    """Score of an action against a single ethical principle."""
    principle: EthicalPrinciple
    score: float                     # 0.0 (worst) to 1.0 (best)
    rationale: str
    concerns: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class RedLineViolation:
    """Describes a red line that would be violated by an action."""
    red_line_id: str
    red_line_name: str
    description: str
    principle: str
    triggered_by: str               # What aspect of the action triggers this


@dataclass
class EthicsReview:
    """Complete ethical review of a proposed AI action."""
    action_id: str
    action_description: str
    decision: EthicsDecision
    overall_score: float             # Weighted average 0.0–1.0
    principle_scores: List[PrincipleScore]
    red_line_violations: List[RedLineViolation]
    conditions: List[str]            # Required if decision is CONDITIONAL
    refusal_reason: Optional[str]
    recommendations: List[str]
    reviewed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def passes(self) -> bool:
        return self.decision in (EthicsDecision.APPROVED, EthicsDecision.CONDITIONAL)

    @property
    def has_red_line_violations(self) -> bool:
        return len(self.red_line_violations) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "decision": self.decision.value,
            "overall_score": round(self.overall_score, 3),
            "passes": self.passes,
            "red_line_violations": [
                {
                    "id": v.red_line_id,
                    "name": v.red_line_name,
                    "triggered_by": v.triggered_by,
                }
                for v in self.red_line_violations
            ],
            "principle_scores": {
                ps.principle.value: round(ps.score, 3)
                for ps in self.principle_scores
            },
            "conditions": self.conditions,
            "refusal_reason": self.refusal_reason,
            "recommendations": self.recommendations,
            "reviewed_at": self.reviewed_at.isoformat(),
        }


@dataclass
class AIAction:
    """
    Represents a proposed AI action to be ethically reviewed.
    """
    action_id: str
    action_type: str                 # e.g., "generate_legal_document", "provide_advice"
    description: str
    requester_context: str = ""      # Who is requesting and why
    output_preview: Optional[str] = None    # Preview of planned output
    affects_third_parties: bool = False
    involves_sensitive_data: bool = False
    is_irreversible: bool = False
    involves_vulnerable_person: bool = False
    could_cause_financial_harm: bool = False
    could_cause_physical_harm: bool = False
    is_discriminatory: Optional[bool] = None
    is_transparent: bool = True
    respects_autonomy: bool = True
    benefits_user: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Principle Evaluators
# ---------------------------------------------------------------------------

PRINCIPLE_WEIGHTS: Dict[EthicalPrinciple, float] = {
    EthicalPrinciple.NON_MALEFICENCE: 0.30,
    EthicalPrinciple.BENEFICENCE: 0.25,
    EthicalPrinciple.TRANSPARENCY: 0.20,
    EthicalPrinciple.AUTONOMY: 0.15,
    EthicalPrinciple.JUSTICE: 0.10,
}

APPROVAL_THRESHOLD = 0.55        # Overall score needed to approve
CONDITIONAL_THRESHOLD = 0.40     # Score needed for conditional approval


def evaluate_beneficence(action: AIAction) -> PrincipleScore:
    """Does this action provide genuine benefit to the user?"""
    score = 0.7
    concerns: List[str] = []
    strengths: List[str] = []

    if action.benefits_user:
        score += 0.2
        strengths.append("Action directly benefits the requesting user.")
    else:
        score -= 0.3
        concerns.append("Action does not appear to benefit the requesting user.")

    if action.could_cause_physical_harm:
        score -= 0.4
        concerns.append("Action could result in physical harm to individuals.")

    if action.could_cause_financial_harm:
        score -= 0.2
        concerns.append("Action could result in financial harm to individuals.")

    if action.involves_vulnerable_person:
        if action.benefits_user:
            score += 0.05
            strengths.append("Provides benefit to a vulnerable person.")
        else:
            score -= 0.25
            concerns.append("Could harm a vulnerable person who may have limited recourse.")

    score = max(0.0, min(1.0, score))
    return PrincipleScore(
        principle=EthicalPrinciple.BENEFICENCE,
        score=score,
        rationale=f"Action scored {score:.2f} on beneficence. Benefit to user: {action.benefits_user}.",
        concerns=concerns,
        strengths=strengths,
    )


def evaluate_non_maleficence(action: AIAction) -> PrincipleScore:
    """Does this action avoid causing harm?"""
    score = 0.75
    concerns: List[str] = []
    strengths: List[str] = []

    if action.could_cause_physical_harm:
        score -= 0.5
        concerns.append("HIGH: Action could cause physical harm.")

    if action.could_cause_financial_harm:
        score -= 0.3
        concerns.append("Action could cause financial harm.")

    if action.is_irreversible:
        score -= 0.15
        concerns.append("Action is irreversible; harm cannot be undone if error occurs.")
    else:
        strengths.append("Action is reversible if errors are found.")

    if action.affects_third_parties:
        score -= 0.1
        concerns.append("Action affects third parties who have not consented.")

    if action.is_discriminatory is True:
        score -= 0.4
        concerns.append("Action produces discriminatory outcomes.")
    elif action.is_discriminatory is False:
        strengths.append("Action verified as non-discriminatory.")

    score = max(0.0, min(1.0, score))
    return PrincipleScore(
        principle=EthicalPrinciple.NON_MALEFICENCE,
        score=score,
        rationale=f"Harm potential score: {score:.2f}. Physical harm risk: {action.could_cause_physical_harm}.",
        concerns=concerns,
        strengths=strengths,
    )


def evaluate_autonomy(action: AIAction) -> PrincipleScore:
    """Does this action respect human agency and self-determination?"""
    score = 0.75
    concerns: List[str] = []
    strengths: List[str] = []

    if action.respects_autonomy:
        score += 0.15
        strengths.append("Action preserves user autonomy and decision-making capacity.")
    else:
        score -= 0.35
        concerns.append("Action undermines user autonomy or overrides user preferences.")

    if action.involves_vulnerable_person:
        concerns.append("Extra care required: vulnerable person may have reduced autonomy capacity.")
        score -= 0.1

    if action.involves_sensitive_data:
        if action.metadata.get("consent_obtained"):
            strengths.append("Sensitive data processing with user consent — autonomy respected.")
        else:
            concerns.append("Sensitive data processing without confirmed consent.")
            score -= 0.2

    score = max(0.0, min(1.0, score))
    return PrincipleScore(
        principle=EthicalPrinciple.AUTONOMY,
        score=score,
        rationale=f"Autonomy score: {score:.2f}. Respects autonomy: {action.respects_autonomy}.",
        concerns=concerns,
        strengths=strengths,
    )


def evaluate_justice(action: AIAction) -> PrincipleScore:
    """Is this action fair and equitable?"""
    score = 0.75
    concerns: List[str] = []
    strengths: List[str] = []

    if action.is_discriminatory is True:
        score -= 0.5
        concerns.append("CRITICAL: Action produces discriminatory or biased outputs.")
    elif action.is_discriminatory is False:
        score += 0.15
        strengths.append("Action has been verified to be non-discriminatory.")

    if action.affects_third_parties and not action.benefits_user:
        score -= 0.2
        concerns.append("Action negatively affects third parties without benefit to primary user.")

    if action.involves_vulnerable_person and not action.benefits_user:
        score -= 0.2
        concerns.append("Action may be unjust to a vulnerable person.")

    if action.metadata.get("bias_tested"):
        strengths.append("Output has been bias-tested against protected categories.")
        score += 0.1

    score = max(0.0, min(1.0, score))
    return PrincipleScore(
        principle=EthicalPrinciple.JUSTICE,
        score=score,
        rationale=f"Justice score: {score:.2f}. Discriminatory: {action.is_discriminatory}.",
        concerns=concerns,
        strengths=strengths,
    )


def evaluate_transparency(action: AIAction) -> PrincipleScore:
    """Is this action honest and transparent?"""
    score = 0.75
    concerns: List[str] = []
    strengths: List[str] = []

    if action.is_transparent:
        score += 0.15
        strengths.append("Action operates transparently with clear disclosure of AI nature.")
    else:
        score -= 0.4
        concerns.append("CRITICAL: Action lacks transparency about AI involvement.")

    if action.metadata.get("ai_disclosed"):
        strengths.append("AI identity explicitly disclosed to user.")
        score += 0.1
    elif not action.is_transparent:
        concerns.append("AI identity not disclosed to user.")
        score -= 0.2

    if action.output_preview and action.metadata.get("contains_citations"):
        if action.metadata.get("citations_verified"):
            strengths.append("Legal citations verified for accuracy.")
        else:
            concerns.append("Legal citations in output have not been verified.")
            score -= 0.15

    score = max(0.0, min(1.0, score))
    return PrincipleScore(
        principle=EthicalPrinciple.TRANSPARENCY,
        score=score,
        rationale=f"Transparency score: {score:.2f}. Transparent operation: {action.is_transparent}.",
        concerns=concerns,
        strengths=strengths,
    )


# ---------------------------------------------------------------------------
# Red Line Checker
# ---------------------------------------------------------------------------

def check_red_lines(action: AIAction) -> List[RedLineViolation]:
    """Check if the action would violate any red lines."""
    violations: List[RedLineViolation] = []
    output = (action.output_preview or "").lower()
    desc = action.description.lower()

    def add_violation(rl_id: str, triggered_by: str) -> None:
        rl = next((r for r in RED_LINES if r["id"] == rl_id), None)
        if rl:
            violations.append(RedLineViolation(
                red_line_id=rl["id"],
                red_line_name=rl["name"],
                description=rl["description"],
                principle=rl["principle"],
                triggered_by=triggered_by,
            ))

    # RL-001: Impersonating attorney
    if any(phrase in output or phrase in desc for phrase in [
        "as your attorney", "as your lawyer", "i am your counsel",
        "i represent you", "attorney-client"
    ]):
        add_violation("RL-001", "Output contains attorney impersonation language.")

    # RL-002: Guarantee outcomes
    if any(phrase in output or phrase in desc for phrase in [
        "guarantee", "guaranteed outcome", "certain to win", "will definitely"
    ]):
        add_violation("RL-002", "Output contains guarantee of legal outcome.")

    # RL-003: Discriminatory outputs
    if action.is_discriminatory is True:
        add_violation("RL-003", "Action flagged as producing discriminatory outputs.")

    # RL-004: Illegal activity
    if any(phrase in desc for phrase in [
        "fraud", "money laundering", "tax evasion", "bribery", "perjury",
        "obstruct justice", "illegal"
    ]) and action.metadata.get("user_requesting_illegal_assistance"):
        add_violation("RL-004", "User appears to request assistance with illegal activity.")

    # RL-005: Deny AI nature
    if not action.is_transparent and action.metadata.get("user_asked_if_ai"):
        add_violation("RL-005", "Action would deny AI nature when user asked.")

    # RL-006: Fabricated citations
    if action.metadata.get("contains_citations") and not action.metadata.get("citations_verified"):
        if action.metadata.get("citations_may_be_hallucinated"):
            add_violation("RL-006", "Output may contain unverified AI-hallucinated citations.")

    # RL-007: Manipulate vulnerable users
    if action.involves_vulnerable_person and not action.respects_autonomy:
        add_violation("RL-007", "Action may manipulate a vulnerable user.")

    # RL-008: Unnecessary sensitive data
    if action.involves_sensitive_data and action.metadata.get("data_not_minimized"):
        add_violation("RL-008", "Collecting unnecessary sensitive personal data.")

    # RL-010: Medical diagnosis
    if any(phrase in output for phrase in ["you have", "your diagnosis is", "you are suffering from"]):
        if action.metadata.get("is_medical_diagnosis"):
            add_violation("RL-010", "Output appears to provide specific medical diagnosis.")

    # RL-012: Enable mass harm
    if action.could_cause_physical_harm and action.metadata.get("mass_scale"):
        add_violation("RL-012", "Action could enable harm at mass scale.")

    return violations


# ---------------------------------------------------------------------------
# Ethics Reviewer
# ---------------------------------------------------------------------------

class EthicsReviewer:
    """
    Reviews AI actions against ethical principles and red lines.
    Refuses actions that violate red lines or score below threshold.
    """

    def __init__(
        self,
        approval_threshold: float = APPROVAL_THRESHOLD,
        conditional_threshold: float = CONDITIONAL_THRESHOLD,
    ):
        self.approval_threshold = approval_threshold
        self.conditional_threshold = conditional_threshold
        self._evaluators: Dict[EthicalPrinciple, Callable[[AIAction], PrincipleScore]] = {
            EthicalPrinciple.BENEFICENCE: evaluate_beneficence,
            EthicalPrinciple.NON_MALEFICENCE: evaluate_non_maleficence,
            EthicalPrinciple.AUTONOMY: evaluate_autonomy,
            EthicalPrinciple.JUSTICE: evaluate_justice,
            EthicalPrinciple.TRANSPARENCY: evaluate_transparency,
        }

    def review(self, action: AIAction) -> EthicsReview:
        """Perform a full ethical review of a proposed action."""

        # 1. Check red lines first
        red_line_violations = check_red_lines(action)

        # 2. Score against all principles
        principle_scores: List[PrincipleScore] = []
        for principle, evaluator in self._evaluators.items():
            ps = evaluator(action)
            principle_scores.append(ps)

        # 3. Compute weighted overall score
        overall_score = sum(
            ps.score * PRINCIPLE_WEIGHTS[ps.principle]
            for ps in principle_scores
        )

        # 4. Determine decision
        conditions: List[str] = []
        recommendations: List[str] = []
        refusal_reason: Optional[str] = None

        if red_line_violations:
            decision = EthicsDecision.REFUSED
            refusal_reason = (
                f"Action violates {len(red_line_violations)} red line(s): "
                + "; ".join(v.red_line_name for v in red_line_violations)
                + ". These are absolute constraints that cannot be overridden."
            )
        elif overall_score < self.conditional_threshold:
            decision = EthicsDecision.REFUSED
            refusal_reason = (
                f"Action scored {overall_score:.3f} overall, below minimum threshold "
                f"of {self.conditional_threshold}. Ethical concerns are too significant to proceed."
            )
        elif overall_score < self.approval_threshold:
            decision = EthicsDecision.CONDITIONAL
            conditions = self._generate_conditions(principle_scores, action)
        else:
            decision = EthicsDecision.APPROVED

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(principle_scores, action)

        return EthicsReview(
            action_id=action.action_id,
            action_description=action.description,
            decision=decision,
            overall_score=overall_score,
            principle_scores=principle_scores,
            red_line_violations=red_line_violations,
            conditions=conditions,
            refusal_reason=refusal_reason,
            recommendations=recommendations,
        )

    @staticmethod
    def _generate_conditions(
        scores: List[PrincipleScore],
        action: AIAction,
    ) -> List[str]:
        conditions: List[str] = []
        for ps in scores:
            if ps.score < 0.5:
                if ps.principle == EthicalPrinciple.TRANSPARENCY:
                    conditions.append("Add explicit AI disclosure statement before responding.")
                elif ps.principle == EthicalPrinciple.NON_MALEFICENCE:
                    conditions.append(
                        "Include clear risk warnings and recommend professional consultation."
                    )
                elif ps.principle == EthicalPrinciple.AUTONOMY:
                    conditions.append(
                        "Obtain explicit user consent before proceeding with sensitive aspects."
                    )
                elif ps.principle == EthicalPrinciple.JUSTICE:
                    conditions.append(
                        "Run bias screening on output before delivery."
                    )
                elif ps.principle == EthicalPrinciple.BENEFICENCE:
                    conditions.append(
                        "Reframe response to ensure clear user benefit and avoid potential harm."
                    )
        return conditions

    @staticmethod
    def _generate_recommendations(
        scores: List[PrincipleScore],
        action: AIAction,
    ) -> List[str]:
        recommendations: List[str] = []
        for ps in scores:
            if ps.concerns:
                for concern in ps.concerns[:2]:
                    recommendations.append(f"[{ps.principle.value}] Address: {concern}")
        if action.is_irreversible:
            recommendations.append(
                "Consider whether a reversible alternative exists before taking irreversible action."
            )
        if action.affects_third_parties:
            recommendations.append(
                "Consider impact on affected third parties and document mitigation steps."
            )
        return recommendations

    def get_red_lines(self) -> List[Dict[str, str]]:
        """Return all red lines for documentation purposes."""
        return list(RED_LINES)

    def is_red_line_violation(self, action: AIAction) -> bool:
        """Quick check: does this action violate any red line?"""
        return len(check_red_lines(action)) > 0


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

_default_reviewer = EthicsReviewer()


def ethics_review(
    action_type: str,
    description: str,
    requester_context: str = "",
    output_preview: Optional[str] = None,
    **kwargs: Any,
) -> EthicsReview:
    """
    Convenience function for quick ethics review.
    """
    import uuid
    action = AIAction(
        action_id=str(uuid.uuid4())[:8],
        action_type=action_type,
        description=description,
        requester_context=requester_context,
        output_preview=output_preview,
        affects_third_parties=kwargs.get("affects_third_parties", False),
        involves_sensitive_data=kwargs.get("involves_sensitive_data", False),
        is_irreversible=kwargs.get("is_irreversible", False),
        involves_vulnerable_person=kwargs.get("involves_vulnerable_person", False),
        could_cause_financial_harm=kwargs.get("could_cause_financial_harm", False),
        could_cause_physical_harm=kwargs.get("could_cause_physical_harm", False),
        is_discriminatory=kwargs.get("is_discriminatory", None),
        is_transparent=kwargs.get("is_transparent", True),
        respects_autonomy=kwargs.get("respects_autonomy", True),
        benefits_user=kwargs.get("benefits_user", True),
        metadata=kwargs.get("metadata", {}),
    )
    return _default_reviewer.review(action)


if __name__ == "__main__":
    review = ethics_review(
        action_type="legal_advice",
        description="Provide legal information about contract terms",
        requester_context="Business owner reviewing vendor contract",
        is_transparent=True,
        benefits_user=True,
        metadata={"ai_disclosed": True},
    )
    print(f"Decision: {review.decision.value}")
    print(f"Overall Score: {review.overall_score:.3f}")
    print(f"Red Line Violations: {len(review.red_line_violations)}")
    for ps in review.principle_scores:
        print(f"  {ps.principle.value}: {ps.score:.3f}")
