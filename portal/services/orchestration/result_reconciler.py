"""Reconcile independent outputs without fabricating consensus."""

from __future__ import annotations

from typing import Any

from .confidence import aggregate_confidence
from .schemas import ReconciliationResultSchema, VerificationResultSchema


def reconcile_outputs(
    outputs: list[dict[str, Any]],
    verifications: list[VerificationResultSchema],
    *,
    approval_required: bool,
) -> ReconciliationResultSchema:
    """Compare claims, preserve disputes, and produce a governed final result."""
    claims_by_value: dict[str, list[str]] = {}
    for index, output in enumerate(outputs):
        claims = output.get("claims") or [output.get("result", "")]
        for claim in claims:
            claims_by_value.setdefault(str(claim), []).append(f"output-{index + 1}")

    disputed_claims = _disputed_claims(claims_by_value, outputs)
    unresolved = _collect_unresolved(verifications)
    verified_claims = [
        claim
        for claim, sources in claims_by_value.items()
        if len(sources) > 1 and claim and claim not in {item["claim"] for item in disputed_claims}
    ]
    if not verified_claims and outputs and not disputed_claims and verifications:
        verified_claims = [str(outputs[0].get("result", ""))]

    principal_decisions = []
    if approval_required:
        principal_decisions.append("Principal approval required before gated action.")
    if disputed_claims:
        principal_decisions.append("Principal review recommended for unresolved disagreement.")

    return ReconciliationResultSchema(
        verified_result={"claims": verified_claims},
        supported_inference=_supported_inference(outputs, verifications),
        unresolved_issue=unresolved,
        principal_decision_required=principal_decisions,
        disputed_claims=disputed_claims,
        final_confidence=aggregate_confidence(verifications),
    )


def _disputed_claims(claims_by_value: dict[str, list[str]], outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explicit = []
    for output in outputs:
        explicit.extend(output.get("contradictions", []))
    if explicit:
        return [{"claim": str(item), "sources": ["explicit_contradiction"], "resolution": "unresolved"} for item in explicit]
    if len(claims_by_value) <= 1:
        return []
    return [
        {"claim": claim, "sources": sources, "resolution": "unresolved"}
        for claim, sources in claims_by_value.items()
        if claim
    ]


def _collect_unresolved(verifications: list[VerificationResultSchema]) -> list[str]:
    unresolved: list[str] = []
    for verification in verifications:
        unresolved.extend(verification.unresolved_uncertainty)
        unresolved.extend(verification.contradictions)
        if verification.verification_result != "PASSED":
            unresolved.append(f"Verification status: {verification.verification_result}")
    return list(dict.fromkeys(unresolved))


def _supported_inference(outputs: list[dict[str, Any]], verifications: list[VerificationResultSchema]) -> list[str]:
    supported: list[str] = []
    for output, verification in zip(outputs, verifications, strict=False):
        if verification.verification_result == "PASSED":
            supported.extend(str(item) for item in output.get("inferences", []))
    return list(dict.fromkeys(supported))
