"""
Risk Engine — identify, score, and track operational and legal risks.
"""
from __future__ import annotations

from blackstone.models import Claim, Confidence, Risk


class RiskEngine:
    """
    Score risks based on likelihood and impact, and map risks to claims.
    """

    def __init__(self) -> None:
        self._risks: dict[str, Risk] = {}

    def add_risk(self, risk: Risk) -> str:
        self._risks[risk.id] = risk
        return risk.id

    def get_risk(self, risk_id: str) -> Risk:
        return self._risks[risk_id]

    def list_risks(self, category: str = "") -> list[Risk]:
        if not category:
            return list(self._risks.values())
        return [r for r in self._risks.values() if r.category == category]

    def score(self, risk: Risk) -> float:
        """
        Compute a numeric risk score from likelihood and impact.
        """
        likelihood = self._confidence_value(risk.likelihood)
        impact = self._confidence_value(risk.impact)
        return likelihood * impact

    @staticmethod
    def _confidence_value(confidence: Confidence) -> float:
        values = {
            Confidence.HIGH: 1.0,
            Confidence.MODERATE: 0.7,
            Confidence.LIMITED: 0.4,
            Confidence.PRELIMINARY: 0.2,
            Confidence.INSUFFICIENT: 0.0,
        }
        return values.get(confidence, 0.0)

    def risks_for_claim(self, claim: Claim) -> list[Risk]:
        """
        Return risks whose category or description relates to the claim subject or tags.
        """
        related = []
        subject_terms = [claim.subject.lower()]
        subject_terms.extend(tag.lower() for tag in claim.tags)
        for risk in self._risks.values():
            risk_text = f"{risk.category} {risk.description}".lower()
            if any(term in risk_text for term in subject_terms):
                related.append(risk)
        return related

    def summary(self) -> dict[str, object]:
        scored = [(risk.id, self.score(risk)) for risk in self._risks.values()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return {
            "total_risks": len(self._risks),
            "highest_risk": scored[0] if scored else None,
            "by_category": self._by_category(),
        }

    def _by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for risk in self._risks.values():
            counts[risk.category] = counts.get(risk.category, 0) + 1
        return counts
