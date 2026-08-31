"""Independent verification contracts for orchestration outputs."""

from __future__ import annotations

from typing import Any

from .schemas import VerificationResultSchema


UNSUPPORTED_MARKERS = ("maybe", "assume", "guarantee", "always", "never")


def verify_output(output: dict[str, Any], *, require_evidence: bool = True) -> VerificationResultSchema:
    """Deterministically verify a mock provider output."""
    evidence = output.get("evidence", [])
    assumptions = list(output.get("assumptions", []))
    uncertainty = list(output.get("unresolved_uncertainty", []))
    contradictions = list(output.get("contradictions", []))
    result_text = str(output.get("result", ""))

    findings: list[str] = []
    if require_evidence and not evidence:
        findings.append("missing_evidence")
        uncertainty.append("Required evidence was not supplied.")
    if any(marker in result_text.lower() for marker in UNSUPPORTED_MARKERS) and not evidence:
        findings.append("unsupported_claim_language")
    if contradictions:
        findings.append("contradictions_present")

    confidence = float(output.get("confidence", 0.5))
    if findings:
        confidence = min(confidence, 0.55)
    status = "PASSED" if not findings else "DISPUTED"

    return VerificationResultSchema(
        confidence_score=max(0.0, min(1.0, confidence)),
        evidence_quality=_evidence_quality(evidence),
        unresolved_uncertainty=uncertainty,
        assumptions=assumptions,
        contradictions=contradictions,
        verification_result=status,
    )


def _evidence_quality(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "unsupported"
    qualities = {str(item.get("evidence_quality", "")).lower() for item in evidence}
    if "primary" in qualities:
        return "primary"
    if "test" in qualities:
        return "test"
    if "verified" in qualities:
        return "verified"
    return "secondary"
