"""Phase 16A — Confidence Scorer for MoE Router."""
from __future__ import annotations
from typing import Dict, List
from phase16.moe_router.models import ConfidenceScore, ExpertType, RoutingRequest
from phase16.moe_router.experts import EXPERT_REGISTRY


class ConfidenceScorer:
    """Scores and calibrates expert confidence for routing decisions."""

    def __init__(self):
        self._calibration_offsets: Dict[ExpertType, float] = {et: 0.0 for et in ExpertType}

    def score_experts(self, request: RoutingRequest) -> List[ConfidenceScore]:
        """Score all registered experts for the given request."""
        scores = []
        for expert_type, expert in EXPERT_REGISTRY.items():
            raw = expert.get_confidence(request)
            calibrated = max(0.0, min(1.0, raw + self._calibration_offsets[expert_type]))
            scores.append(ConfidenceScore(
                expert_type=expert_type,
                score=calibrated,
                reasoning=f"keyword match score for {expert_type.value}",
                calibrated=True,
            ))
        return sorted(scores, key=lambda s: s.score, reverse=True)

    def aggregate_scores(self, scores: List[ConfidenceScore]) -> Dict[str, float]:
        """Aggregate scores into a normalised weight dict."""
        total = sum(s.score for s in scores)
        if total == 0:
            n = len(scores)
            return {s.expert_type.value: 1.0 / n for s in scores} if n else {}
        return {s.expert_type.value: s.score / total for s in scores}

    def calibrate(self, expert_type: ExpertType, feedback_score: float,
                  predicted_score: float) -> None:
        """Update calibration offset based on prediction error."""
        error = feedback_score - predicted_score
        self._calibration_offsets[expert_type] += 0.1 * error

    def get_top_k(self, request: RoutingRequest, k: int = 3) -> List[ConfidenceScore]:
        return self.score_experts(request)[:k]
