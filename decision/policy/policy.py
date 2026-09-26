"""Policy gate + fail-closed fallback.

R1: the policy MECHANISM exists; NO production routing is authorized.
Default disposition is SHADOW_ONLY. The AUTO_ROUTE_CANDIDATE branch is
illustrative mechanics, never production authority (frozen directive §8).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.types import DecisionResult, ResultKind, Risk

# Provisional, EXPERIMENTAL thresholds — require R2 calibration evidence
# before they can ever authorize production routing.
THRESHOLDS = {
    "probability": 0.95,
    "margin": 0.20,
    "confidence": 0.85,
}


@dataclass(frozen=True)
class PolicyDecision:
    decision: str          # SHADOW_ONLY | AUTO_ROUTE_CANDIDATE | HERMES_REVIEW
                         # | HUMAN_REVIEW | QUARANTINE | FALLBACK_HERMES
    risk: str
    reason: str
    provider_failed: bool = False


def apply_policy(result: DecisionResult, *, shadow_only: bool = True) -> PolicyDecision:
    # 1) any non-DECISION kind -> fail-closed fallback (NEVER deterministic exec)
    if result.kind is not ResultKind.DECISION:
        return PolicyDecision(
            decision="FALLBACK_HERMES",
            risk="UNKNOWN",
            reason=f"provider result {result.kind.value}: {result.reason}".strip(),
            provider_failed=True,
        )
    # 2) shadow mode: record, do not act (R1 default)
    if shadow_only:
        return PolicyDecision(decision="SHADOW_ONLY", risk="N/A_R1_SHADOW",
                              reason="shadow-only default; no routing authority in R1")
    # 3) mechanics only — unreachable under frozen R1 defaults
    risk = Risk.ELEVATED
    eligible = True
    reasons = []
    for a in result.answers.values():
        if a.primitive.value == "choice":
            if (a.probability or 0.0) < THRESHOLDS["probability"]:
                eligible = False; reasons.append(f"{a.question}: prob {a.probability}")
            if (a.margin or 0.0) < THRESHOLDS["margin"]:
                eligible = False; reasons.append(f"{a.question}: margin {a.margin}")
        if (a.confidence or 0.0) < THRESHOLDS["confidence"]:
            eligible = False; reasons.append(f"{a.question}: confidence {a.confidence}")
    if eligible and risk is Risk.LOW:
        return PolicyDecision(decision="AUTO_ROUTE_CANDIDATE", risk=risk.value,
                              reason="all gates satisfied (candidate only; still shadow-governed)")
    return PolicyDecision(decision="HERMES_REVIEW", risk=risk.value,
                          reason="thresholds unmet: " + "; ".join(reasons))
