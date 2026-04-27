"""Phase 16A — Load Balancer for MoE Router."""
from __future__ import annotations
import threading
from typing import Dict, List, Optional
from phase16.moe_router.models import ExpertCapacity, ExpertType, RoutingRequest
from phase16.moe_router.experts import EXPERT_REGISTRY


class LoadBalancer:
    """Distributes routing requests across expert instances based on capacity."""

    def __init__(self, max_capacity_per_expert: int = 10):
        self._capacities: Dict[ExpertType, ExpertCapacity] = {
            et: ExpertCapacity(expert_type=et, max_capacity=max_capacity_per_expert)
            for et in EXPERT_REGISTRY
        }
        self._lock = threading.Lock()

    def assign(self, request: RoutingRequest, candidates: List[ExpertType]) -> ExpertType:
        """Assign the request to the least-loaded available expert from candidates."""
        with self._lock:
            available = [et for et in candidates if self._capacities[et].available]
            if not available:
                available = candidates  # fallback: assign even if over capacity
            # Pick least loaded
            chosen = min(available, key=lambda et: self._capacities[et].utilization)
            self._capacities[chosen].current_load += 1
            return chosen

    def release(self, expert_type: ExpertType) -> None:
        """Release one slot for the given expert."""
        with self._lock:
            cap = self._capacities.get(expert_type)
            if cap and cap.current_load > 0:
                cap.current_load -= 1

    def get_capacity(self, expert_type: ExpertType) -> ExpertCapacity:
        with self._lock:
            return self._capacities[expert_type]

    def rebalance(self) -> None:
        """Reset all loads to zero (e.g., after a batch completes)."""
        with self._lock:
            for cap in self._capacities.values():
                cap.current_load = 0

    def get_all_capacities(self) -> Dict[ExpertType, ExpertCapacity]:
        with self._lock:
            return dict(self._capacities)
