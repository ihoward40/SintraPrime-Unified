"""
Convenience orchestrator that wires the five BRA engines together.
"""
from __future__ import annotations

from typing import Any

from blackstone.engines.authority_engine import AuthorityEngine
from blackstone.engines.evidence_engine import EvidenceEngine
from blackstone.engines.provenance_engine import ProvenanceEngine
from blackstone.engines.reasoning_engine import ReasoningEngine
from blackstone.engines.risk_engine import RiskEngine
from blackstone.models import Claim, EvidenceItem, Jurisdiction, Risk


class BlackstoneOrchestrator:
    """
    Single entry point for evaluating a claim through all BRA engines.
    """

    def __init__(self, agents: list[str] | None = None) -> None:
        self.evidence = EvidenceEngine()
        self.authority = AuthorityEngine()
        self.provenance = ProvenanceEngine()
        self.risk = RiskEngine()
        self.reasoning = ReasoningEngine(self.evidence, self.authority, agents=agents)

    def register_jurisdiction(self, jurisdiction: Jurisdiction) -> None:
        self.authority.register_jurisdiction(jurisdiction)

    def register_source(self, source: Any) -> None:
        self.authority.register_source(source)
        self.provenance.record(
            object_id=source.id,
            object_type="source",
            action="registered",
            actor="blackstone_orchestrator",
            payload=source.to_dict(),
        )

    def add_evidence(self, evidence: EvidenceItem, actor: str = "system") -> str:
        evidence_id = self.evidence.add_evidence(evidence)
        self.provenance.record(
            object_id=evidence_id,
            object_type="evidence",
            action="added",
            actor=actor,
            payload=evidence.to_dict(),
        )
        return evidence_id

    def add_claim(self, claim: Claim) -> str:
        return self.evidence.add_claim(claim)

    def add_risk(self, risk: Risk) -> str:
        return self.risk.add_risk(risk)

    def evaluate(self, claim_id: str, question: str | None = None, actor: str = "system") -> dict[str, object]:
        claim = self.evidence.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} not found")

        self.evidence.evaluate_claim(claim)
        self.provenance.record(
            object_id=claim_id,
            object_type="claim",
            action="evaluated",
            actor=actor,
            payload=claim.to_dict(),
        )

        authority_summary = self.authority.authority_summary(claim)
        risks = self.risk.risks_for_claim(claim)
        recommendation = self.reasoning.recommend(
            question=question or f"Should we adopt claim {claim_id}?",
            claim=claim,
        )

        return {
            "claim": claim.to_dict(),
            "authority": authority_summary,
            "provenance": {
                "chain_length": len(self.provenance.chain(claim_id)),
                "verified": self.provenance.verify(claim_id)["valid"],
            },
            "risks": [
                {**risk.to_dict(), "score": self.risk.score(risk)} for risk in risks
            ],
            "recommendation": recommendation.to_dict(),
        }
