"""
Evidence Engine — ingest, evaluate, and score evidence items.
"""
from __future__ import annotations

from blackstone.models import (
    Claim,
    ClaimStatus,
    Confidence,
    EvidenceItem,
    SourceClassification,
)


class EvidenceEngine:
    """
    Ingest evidence items, score source reliability, and classify claims.
    """

    def __init__(self) -> None:
        self._items: dict[str, EvidenceItem] = {}
        self._claims: dict[str, Claim] = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def add_evidence(self, item: EvidenceItem) -> str:
        self._items[item.id] = item
        return item.id

    def add_claim(self, claim: Claim) -> str:
        self._claims[claim.id] = claim
        return claim.id

    def get_evidence(self, evidence_id: str) -> EvidenceItem | None:
        return self._items.get(evidence_id)

    def get_claim(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    def list_evidence(self) -> list[EvidenceItem]:
        return list(self._items.values())

    def list_claims(self) -> list[Claim]:
        return list(self._claims.values())

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_claim(self, claim: Claim) -> Claim:
        """
        Score a claim based on its attached evidence and counter-evidence.
        """
        if not claim.evidence and not claim.counter_evidence:
            claim.status = ClaimStatus.UNVERIFIED
            claim.confidence = Confidence.INSUFFICIENT
            return claim

        support_score = sum(self._score_evidence(e) for e in claim.evidence)
        challenge_score = sum(self._score_evidence(e) for e in claim.counter_evidence)

        net_score = support_score - challenge_score

        if self._has_controlling_evidence(claim.evidence):
            claim.status = ClaimStatus.CONTROLLING
        elif support_score > challenge_score * 2 and self._has_primary_evidence(claim.evidence):
            claim.status = ClaimStatus.PERSUASIVE
        elif support_score > 0 and challenge_score == 0:
            claim.status = ClaimStatus.EMERGING
        elif challenge_score > 0:
            claim.status = ClaimStatus.DISPUTED
        else:
            claim.status = ClaimStatus.UNVERIFIED

        claim.confidence = self._net_score_to_confidence(net_score)
        return claim

    def _score_evidence(self, item: EvidenceItem) -> float:
        base = self._source_reliability_score(item.source.classification)
        confidence_multiplier = self._confidence_multiplier(item.confidence)
        return base * confidence_multiplier

    @staticmethod
    def _source_reliability_score(classification: SourceClassification) -> float:
        scores = {
            SourceClassification.PRIMARY_LEGAL: 1.0,
            SourceClassification.SECONDARY_LEGAL: 0.8,
            SourceClassification.SCHOLARLY: 0.7,
            SourceClassification.HISTORICAL: 0.5,
            SourceClassification.ARCHIVAL: 0.6,
            SourceClassification.COMMERCIAL: 0.3,
            SourceClassification.PRIVATE_PUBLISHED: 0.4,
            SourceClassification.AI_GENERATED: 0.1,
            SourceClassification.UNKNOWN: 0.0,
        }
        return scores.get(classification, 0.0)

    @staticmethod
    def _confidence_multiplier(confidence: Confidence) -> float:
        multipliers = {
            Confidence.HIGH: 1.0,
            Confidence.MODERATE: 0.7,
            Confidence.LIMITED: 0.4,
            Confidence.PRELIMINARY: 0.2,
            Confidence.INSUFFICIENT: 0.0,
        }
        return multipliers.get(confidence, 0.0)

    @staticmethod
    def _has_controlling_evidence(evidence: list[EvidenceItem]) -> bool:
        return any(
            e.source.classification == SourceClassification.PRIMARY_LEGAL
            and e.confidence in (Confidence.HIGH, Confidence.MODERATE)
            for e in evidence
        )

    @staticmethod
    def _has_primary_evidence(evidence: list[EvidenceItem]) -> bool:
        return any(
            e.source.classification in (SourceClassification.PRIMARY_LEGAL, SourceClassification.SECONDARY_LEGAL)
            for e in evidence
        )

    @staticmethod
    def _net_score_to_confidence(score: float) -> Confidence:
        if score >= 1.5:
            return Confidence.HIGH
        if score >= 0.8:
            return Confidence.MODERATE
        if score >= 0.3:
            return Confidence.LIMITED
        if score > 0:
            return Confidence.PRELIMINARY
        return Confidence.INSUFFICIENT

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def evaluate_all(self) -> list[Claim]:
        for claim in self._claims.values():
            self.evaluate_claim(claim)
        return self.list_claims()
