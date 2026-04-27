"""Phase 16A — Dispatcher for MoE Router."""
from __future__ import annotations
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from phase16.moe_router.models import ExpertType, RoutingRequest, RoutingResult
from phase16.moe_router.experts import EXPERT_REGISTRY
from phase16.moe_router.load_balancer import LoadBalancer


class Dispatcher:
    """Dispatches routing requests to experts and collects results."""

    def __init__(self, max_workers: int = 8):
        self._max_workers = max_workers
        self._balancer = LoadBalancer()
        self._lock = threading.Lock()
        self._stats: Dict[str, Any] = {
            "total_dispatched": 0,
            "total_errors": 0,
            "avg_latency_ms": 0.0,
        }

    def dispatch(self, request: RoutingRequest,
                 expert_types: List[ExpertType] = None) -> Dict[str, Any]:
        """Dispatch a single request to the specified (or all) experts."""
        targets = expert_types or list(EXPERT_REGISTRY.keys())
        start = time.time()
        results = {}
        for et in targets:
            expert = EXPERT_REGISTRY.get(et)
            if expert:
                try:
                    results[et.value] = expert.analyze(request)
                except Exception as e:
                    results[et.value] = {"error": str(e)}
                    with self._lock:
                        self._stats["total_errors"] += 1
        latency = (time.time() - start) * 1000
        with self._lock:
            self._stats["total_dispatched"] += 1
            n = self._stats["total_dispatched"]
            self._stats["avg_latency_ms"] = (
                (self._stats["avg_latency_ms"] * (n - 1) + latency) / n
            )
        return results

    def execute_parallel(self, requests: List[RoutingRequest]) -> List[Dict[str, Any]]:
        """Execute multiple routing requests in parallel."""
        results = [None] * len(requests)
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            future_map = {pool.submit(self.dispatch, req): i for i, req in enumerate(requests)}
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {"error": str(e)}
        return results

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)
