"""SwarmInferenceAdapter — thin adapter from swarm workers to GovernedInferenceRouter.

This is NOT a competing provider router. It translates:
  WorkerSpec → InferenceRequest
  InferenceResult → WorkerResult

Provider selection, policy, classification, and failover remain governed by
GovernedInferenceRouter (the canonical authority on main).

The adapter adds worker-specific concerns:
  - timeout observation
  - worker_id/task_id metadata
  - attempt tracking
  - health translation for the swarm supervisor
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.inference_adapter")


@dataclass
class WorkerInferenceRequest:
    """Worker-level inference request (translated to InferenceRequest)."""
    worker_id: str
    task_id: str
    task_type: str
    capability: str
    messages: list[dict[str, Any]]
    tenant_id: str = ""
    principal_id: str = ""
    mission_id: str = ""
    max_input_tokens: int = 12000
    max_output_tokens: int = 2000
    temperature: float = 0.2
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerInferenceResult:
    """Worker-level inference result (translated from InferenceResult)."""
    worker_id: str
    task_id: str
    provider: str
    model: str
    content: str | dict[str, Any]
    latency_ms: int
    attempts: int
    finish_reason: str
    provider_used: str
    started_at: float
    completed_at: float
    failover_observed: bool = False
    error: str | None = None


class SwarmInferenceAdapter:
    """Thin adapter: swarm worker → GovernedInferenceRouter.

    Does NOT select providers independently.
    Does NOT maintain a competing policy engine.
    Defers all routing to GovernedInferenceRouter.
    """

    def __init__(self, router: Any) -> None:
        """Initialize with a GovernedInferenceRouter instance.

        Args:
            router: GovernedInferenceRouter (canonical inference authority)
        """
        self._router = router
        self._attempt_log: list[dict] = []

    def invoke(self, request: WorkerInferenceRequest) -> WorkerInferenceResult:
        """Translate worker request → governed inference → worker result.

        Provider selection, failover, and policy are handled by
        GovernedInferenceRouter. This adapter only adds worker metadata.
        """
        from governed_inference.contracts import InferenceRequest

        started = time.time()

        # Translate to InferenceRequest
        inference_req = InferenceRequest.new(
            task_type=request.task_type,
            capability=request.capability,
            messages=request.messages,
            max_input_tokens=request.max_input_tokens,
            max_output_tokens=request.max_output_tokens,
            temperature=request.temperature,
            metadata={
                "worker_id": request.worker_id,
                "task_id": request.task_id,
                "tenant_id": request.tenant_id,
                "principal_id": request.principal_id,
                "mission_id": request.mission_id,
                **request.metadata,
            },
        )

        # Delegate to canonical router
        try:
            result = self._router.invoke(inference_req)
            completed = time.time()

            # Record attempt
            self._attempt_log.append({
                "worker_id": request.worker_id,
                "task_id": request.task_id,
                "provider": result.provider,
                "model": result.model,
                "attempts": result.attempts,
                "latency_ms": result.latency_ms,
                "finish_reason": result.finish_reason,
                "started_at": started,
                "completed_at": completed,
                "failover_observed": result.attempts > 1,
            })

            return WorkerInferenceResult(
                worker_id=request.worker_id,
                task_id=request.task_id,
                provider=result.provider,
                model=result.model,
                content=result.content,
                latency_ms=result.latency_ms,
                attempts=result.attempts,
                finish_reason=result.finish_reason,
                provider_used=result.provider,
                started_at=started,
                completed_at=completed,
                failover_observed=result.attempts > 1,
            )
        except Exception as e:
            completed = time.time()
            logger.error("GovernedInferenceRouter failed for worker %s: %s",
                        request.worker_id, e)
            return WorkerInferenceResult(
                worker_id=request.worker_id,
                task_id=request.task_id,
                provider="none",
                model="none",
                content="",
                latency_ms=int((completed - started) * 1000),
                attempts=0,
                finish_reason="error",
                provider_used="none",
                started_at=started,
                completed_at=completed,
                error=str(e),
            )

    def get_attempt_log(self) -> list[dict]:
        """Return all inference attempts for audit/receipt purposes."""
        return list(self._attempt_log)

    def get_provider_health_snapshot(self) -> dict[str, Any]:
        """Translate GovernedInferenceRouter provider health for swarm supervisor.

        This does NOT create a competing health registry — it reads the
        canonical router's health state and translates it for swarm consumption.
        """
        providers = {}
        if hasattr(self._router, 'providers'):
            for provider in self._router.providers:
                try:
                    h = provider.health()
                    providers[provider.__class__.__name__] = {
                        "state": "healthy" if h.healthy else "degraded",
                        "last_check": getattr(h, 'last_check', None),
                    }
                except Exception:
                    providers[provider.__class__.__name__] = {"state": "unknown"}
        return providers
