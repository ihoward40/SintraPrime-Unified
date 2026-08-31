"""Confidence and evidence-quality helpers."""

from __future__ import annotations

from .schemas import VerificationResultSchema


EVIDENCE_QUALITY_WEIGHTS = {
    "primary": 1.0,
    "verified": 0.9,
    "test": 0.85,
    "secondary": 0.7,
    "inference": 0.5,
    "unsupported": 0.2,
}


def evidence_quality_score(label: str) -> float:
    return EVIDENCE_QUALITY_WEIGHTS.get(label.lower(), 0.4)


def aggregate_confidence(results: list[VerificationResultSchema]) -> float:
    if not results:
        return 0.0
    weighted = [
        result.confidence_score * evidence_quality_score(result.evidence_quality)
        for result in results
    ]
    return round(sum(weighted) / len(weighted), 3)


def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    if score >= 0.35:
        return "low"
    return "blocked"
