"""Phase 16A — MoE Legal Specialist Router."""
from __future__ import annotations
import time
import threading
from typing import Dict, List, Optional
import numpy as np

from phase16.moe_router.models import (
    ExpertType, RoutingRequest, RoutingResult, ConfidenceScore,
)
from phase16.moe_router.experts import EXPERT_REGISTRY
from phase16.moe_router.confidence_scorer import ConfidenceScorer
from phase16.moe_router.load_balancer import LoadBalancer
from phase16.moe_router.dispatcher import Dispatcher


class MoERouter:
    """Mixture-of-Experts router for legal domain specialisation.

    Routes incoming legal queries to the most appropriate domain expert(s)
    using confidence scoring, load balancing, and a learned routing matrix.
    """

    def __init__(self, top_k: int = 2, max_workers: int = 8):
        self._top_k = top_k
        self._scorer = ConfidenceScorer()
        self._balancer = LoadBalancer()
        self._dispatcher = Dispatcher(max_workers=max_workers)
        self._lock = threading.Lock()
        expert_types = list(EXPERT_REGISTRY.keys())
        n = len(expert_types)
        self._expert_list = expert_types
        # Routing matrix: n×n (expert × domain) — starts as identity
        self._routing_matrix = np.eye(n)

    def route(self, request: RoutingRequest) -> RoutingResult:
        """Route a request to the best expert(s)."""
        start = time.time()
        scores = self._scorer.score_experts(request)
        weights = self._scorer.aggregate_scores(scores)
        top_scores = scores[:self._top_k]
        primary = top_scores[0].expert_type if top_scores else ExpertType.CORPORATE
        secondary = [s.expert_type for s in top_scores[1:]]

        # Dispatch to primary expert
        analysis = self._dispatcher.dispatch(request, [primary])

        latency = (time.time() - start) * 1000
        return RoutingResult(
            request_id=request.request_id,
            primary_expert=primary,
            secondary_experts=secondary,
            confidence_scores=scores,
            analysis=analysis,
            routing_weights=weights,
            latency_ms=latency,
        )

    def _compute_routing_weights(self, request: RoutingRequest) -> Dict[str, float]:
        """Compute softmax routing weights for all experts."""
        scores = self._scorer.score_experts(request)
        raw = np.array([s.score for s in scores])
        exp_raw = np.exp(raw - raw.max())
        softmax = exp_raw / exp_raw.sum()
        return {s.expert_type.value: float(w) for s, w in zip(scores, softmax)}

    def _select_experts(self, weights: Dict[str, float]) -> List[ExpertType]:
        """Select top-k experts by weight."""
        sorted_experts = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        return [ExpertType(name) for name, _ in sorted_experts[:self._top_k]]

    def update_routing_matrix(self, feedback: Dict[str, float]) -> None:
        """Update routing matrix based on expert performance feedback."""
        with self._lock:
            for i, et in enumerate(self._expert_list):
                if et.value in feedback:
                    self._routing_matrix[i, i] = max(0.1, min(2.0,
                        self._routing_matrix[i, i] + 0.01 * feedback[et.value]))

    def get_routing_stats(self) -> Dict:
        return self._dispatcher.get_stats()
