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

    def invoke(self, request: WorkerInferenceRequest, cancel_event: Any | None = None) -> WorkerInferenceResult:
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

        # Cancellation is terminal and checked before entering the provider path.
        if cancel_event is not None and cancel_event.is_set():
            from governed_inference.contracts import ProviderErrorKind
            return WorkerInferenceResult(worker_id=request.worker_id, task_id=request.task_id, provider="none", model="none", content="", latency_ms=0, attempts=0, finish_reason=ProviderErrorKind.CANCELLED.value, provider_used="none", started_at=started, completed_at=time.time(), error=ProviderErrorKind.CANCELLED.value)

        # Delegate to canonical router
        try:
            result = self._router.invoke(inference_req)
            completed = time.time()
            attempt_log = self._attempt_entries(inference_req.request_id)
            invocation_attempts = self._finalize_attempt_entries(
                attempt_log,
                worker_id=request.worker_id,
                task_id=request.task_id,
                started_at=started,
                completed_at=completed,
                final_provider=result.provider,
                final_model=result.model,
                final_finish_reason=result.finish_reason,
                final_latency_ms=result.latency_ms,
            )

            self._attempt_log.extend(invocation_attempts)

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
                failover_observed=len({entry["provider"] for entry in invocation_attempts}) > 1,
            )
        except Exception as e:
            completed = time.time()
            failure_class = getattr(getattr(e, "kind", None), "value", "unknown")
            attempt_log = self._attempt_entries(inference_req.request_id)
            if attempt_log:
                self._attempt_log.extend(
                    self._finalize_attempt_entries(
                        attempt_log,
                        worker_id=request.worker_id,
                        task_id=request.task_id,
                        started_at=started,
                        completed_at=completed,
                        final_provider=None,
                        final_model=None,
                        final_finish_reason="error",
                        final_latency_ms=int((completed - started) * 1000),
                    )
                )
            else:
                self._attempt_log.append({
                    "worker_id": request.worker_id,
                    "task_id": request.task_id,
                    "provider": "unknown",
                    "model": "unknown",
                    "attempts": 0,
                    "latency_ms": int((completed - started) * 1000),
                    "finish_reason": "error",
                    "started_at": started,
                    "completed_at": completed,
                    "failover_observed": False,
                    "outcome": "failure",
                    "failure_class": failure_class,
                    "retry_same_provider": False,
                    "failover_from_provider": None,
                    "failover_to_provider": None,
                })
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

    def _attempt_entries(self, request_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        failures_by_attempt: dict[tuple[str, int], str] = {}
        ledger = getattr(self._router, "ledger", None)
        if ledger is None:
            return entries
        for event in ledger.events:
            if event.get("request_id") != request_id:
                continue
            if event["event"] == "inference.attempt_failed":
                failures_by_attempt[(str(event["provider"]), int(event.get("attempt", 1)))] = str(
                    event["error_kind"]
                )
            if event["event"] != "inference.attempt_started":
                continue
            entries.append(
                {
                    "provider": str(event["provider"]),
                    "model": str(event.get("model", "unknown")),
                    "attempts": int(event.get("attempt", 1)),
                    "failure_class": None,
                    "outcome": "started",
                }
            )
        for entry in entries:
            key = (entry["provider"], entry["attempts"])
            if key in failures_by_attempt:
                entry["failure_class"] = failures_by_attempt[key]
                entry["outcome"] = "failure"
        return entries

    def _finalize_attempt_entries(
        self,
        entries: list[dict[str, Any]],
        *,
        worker_id: str,
        task_id: str,
        started_at: float,
        completed_at: float,
        final_provider: str | None,
        final_model: str | None,
        final_finish_reason: str,
        final_latency_ms: int,
    ) -> list[dict[str, Any]]:
        providers = [entry["provider"] for entry in entries]
        finalized: list[dict[str, Any]] = []
        for index, entry in enumerate(entries):
            provider = str(entry["provider"])
            finalized.append(
                {
                    "worker_id": worker_id,
                    "task_id": task_id,
                    "provider": provider,
                    "model": str(entry.get("model") or final_model or "unknown"),
                    "attempts": int(entry["attempts"]),
                    "latency_ms": final_latency_ms if provider == final_provider else 0,
                    "finish_reason": final_finish_reason if provider == final_provider else "error",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "failover_observed": len(set(providers)) > 1,
                    "outcome": "success" if provider == final_provider else "failure",
                    "failure_class": entry["failure_class"],
                    "retry_same_provider": providers.count(provider) > 1,
                    "failover_from_provider": provider if index < len(entries) - 1 else None,
                    "failover_to_provider": providers[index + 1] if index < len(entries) - 1 else None,
                }
            )
        return finalized

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
