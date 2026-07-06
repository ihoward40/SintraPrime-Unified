"""
Reasoning Engine — build traceable recommendations from evidence and authority.
"""
from __future__ import annotations

from blackstone.engines.authority_engine import AuthorityEngine
from blackstone.engines.evidence_engine import EvidenceEngine
from blackstone.models import Claim, Recommendation


class ReasoningEngine:
    """
    Produce recommendations with full decision traceability.
    """

    def __init__(
        self,
        evidence_engine: EvidenceEngine,
        authority_engine: AuthorityEngine,
        agents: list[str] | None = None,
    ) -> None:
        self.evidence_engine = evidence_engine
        self.authority_engine = authority_engine
        self.agents = agents or []

    def recommend(
        self,
        question: str,
        claim: Claim,
        alternatives: list[str] | None = None,
        conditions_for_change: list[str] | None = None,
    ) -> Recommendation:
        """
        Build a recommendation for a question given a claim and its evidence.
        """
        evaluated = self.evidence_engine.evaluate_claim(claim)
        authority_summary = self.authority_engine.authority_summary(evaluated)

        evidence_ids = [e.id for e in evaluated.evidence]
        counter_ids = [e.id for e in evaluated.counter_evidence]
        authority_ids = []
        if authority_summary.get("controlling_authority"):
            authority_ids.append(authority_summary["controlling_authority"]["id"])
        authority_ids.extend(authority_summary.get("persuasive_authorities", []))

        rationale = self._build_rationale(evaluated, authority_summary)

        selected_recommendation = self._select_recommendation(evaluated)

        return Recommendation(
            id=f"REC-{claim.id}",
            question=question,
            recommendation=selected_recommendation,
            rationale=rationale,
            evidence_considered=evidence_ids + counter_ids,
            authorities_consulted=authority_ids,
            assumptions=evaluated.assumptions or [],
            alternatives=alternatives or [],
            conditions_for_change=conditions_for_change or [],
            confidence=evaluated.confidence,
            agents=self.agents,
        )

    def _build_rationale(self, claim: Claim, authority_summary: dict[str, object]) -> str:
        parts: list[str] = []
        status = claim.status.value
        confidence = claim.confidence.value
        parts.append(f"Claim status: {status}; confidence: {confidence}.")

        controlling = authority_summary.get("controlling_authority")
        if controlling:
            parts.append(f"Controlling authority: {controlling['citation']} ({controlling.get('jurisdiction')}).")

        persuasive = authority_summary.get("persuasive_authorities", [])
        if persuasive:
            parts.append(f"Persuasive authorities consulted: {', '.join(persuasive)}.")

        conflicts = authority_summary.get("conflicts", [])
        if conflicts:
            parts.append(f"Detected {len(conflicts)} conflicting authority record(s).")

        if claim.counter_evidence:
            parts.append(
                f"Counter-evidence considered: {len(claim.counter_evidence)} item(s); "
                "competing interpretations preserved."
            )

        if claim.missing_evidence:
            parts.append(f"Evidence gaps noted: {', '.join(claim.missing_evidence)}.")

        return " ".join(parts)

    def _select_recommendation(self, claim: Claim) -> str:
        if claim.status.value == "controlling":
            return "Adopt the claim as controlling authority permits."
        if claim.status.value == "persuasive":
            return "Adopt the claim as persuasive, subject to controlling authority review."
        if claim.status.value == "disputed":
            return "Do not adopt without further review; document conflict and seek specialist input."
        if claim.status.value == "emerging":
            return "Track as emerging position; gather additional corroboration before adoption."
        if claim.status.value == "educational":
            return "Use for educational or explanatory purposes only; not a legal recommendation."
        return "Insufficient evidence to support adoption at this time."
