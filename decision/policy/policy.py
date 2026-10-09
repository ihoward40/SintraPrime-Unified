"""Policy — SHADOW_ONLY default; mechanics only; fail-closed (R1 policy).

Constitutional rule is structural: under SHADOW_ONLY, no result authorizes
execution. Non-DECISION results short-circuit to FALLBACK_HERMES before any
threshold/margin logic. AUTO_ROUTE_CANDIDATE requires LOW risk + threshold
satisfaction + shadow disabled — unreachable for R1 contracts (which are
ELEVATED+), and itself a provenance event. Probability is recorded fact, never
authority.
"""
from __future__ import annotations

from typing import Optional

from decision.engine.types import DecisionContract, DecisionResult, PolicyDisposition, ResultKind

AMBIGUOUS_MARGIN = 0.02  # margin at/below this is not sufficient to authorize


def compute_margin(distribution: Optional[dict]) -> Optional[float]:
    if not isinstance(distribution, dict) or len(distribution) < 2:
        return None
    vals = sorted(distribution.values(), reverse=True)
    return vals[0] - vals[1]


def apply_policy(result: DecisionResult, shadow_only: bool,
                 contract: Optional[DecisionContract] = None) -> PolicyDisposition:
    # Fail-closed: any non-DECISION result -> FALLBACK_HERMES.
    if result.kind is not ResultKind.DECISION:
        return PolicyDisposition.FALLBACK_HERMES
    # Shadow default: never execute, even on a clean DECISION.
    if shadow_only:
        return PolicyDisposition.FALLBACK_HERMES
    # DECISION with shadow off: ambiguous distributions are still not authorized.
    margin = compute_margin(_first_distribution(result))
    if margin is None or margin <= AMBIGUOUS_MARGIN:
        return PolicyDisposition.HERMES_REVIEW
    # Only LOW-risk contracts could ever reach AUTO_ROUTE; R1 contracts are not LOW.
    if contract is not None and contract.risk.name == "LOW":
        return PolicyDisposition.AUTO_ROUTE_CANDIDATE
    return PolicyDisposition.HERMES_REVIEW


def _first_distribution(result: DecisionResult):
    for a in result.answers:
        if a.distribution:
            return a.distribution
    return None
