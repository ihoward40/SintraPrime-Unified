"""JARVIS-001-A2 read-only bridge into the certified S1 swarm surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

from swarm_runtime.hermes_adapter import DelegateTask, HermesSwarmAdapter, SwarmResult

from .jarvis_principal_mission import (
    EXTERNAL_SIDE_EFFECTS,
    JARVIS_AUTHORITY,
    JARVIS_WORKFLOW_TYPE,
    DecisionContext,
    PrincipalMissionRequest,
)


@dataclass(frozen=True, slots=True)
class AuthoritativeMission:
    mission_id: UUID
    request_id: UUID
    tenant_id: str
    created_by: str
    workflow_type: str = JARVIS_WORKFLOW_TYPE
    authority: str = JARVIS_AUTHORITY


@dataclass(frozen=True, slots=True)
class JarvisMissionResult:
    mission: AuthoritativeMission
    request_id: UUID
    request_hash: str
    status: str
    evidence: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    error: str
    task_provenance: dict[str, Any]
    swarm_id: str
    routed_to_swarm: bool
    legacy_delegate_used: bool
    external_side_effects: int = EXTERNAL_SIDE_EFFECTS


class ReadOnlySwarmSurface(Protocol):
    def delegate(self, tasks: list[DelegateTask]) -> SwarmResult: ...


class JarvisReadOnlyWorkflow:
    """Server-owned A2 handler; the only execution surface is HermesSwarmAdapter."""

    capability = "jarvis.read_only"
    workflow_type = JARVIS_WORKFLOW_TYPE
    authority = JARVIS_AUTHORITY
    external_side_effects = EXTERNAL_SIDE_EFFECTS

    def __init__(self, *, repo_path: str, run_dir: str | None = None) -> None:
        self._repo_path = repo_path
        self._run_dir = run_dir

    def execute(
        self,
        request: PrincipalMissionRequest,
        *,
        adapter: ReadOnlySwarmSurface | None = None,
        mission_id: UUID | None = None,
    ) -> JarvisMissionResult:
        self._validate_request(request)
        mission = AuthoritativeMission(
            mission_id=mission_id or uuid4(),
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            created_by=request.requested_by,
        )
        context: DecisionContext = request.decision_context
        task = DelegateTask(
            task_id=f"jarvis-{request.request_id}",
            description=context.objective,
            role="breaker",
            worker_class="ModelReasoningWorker",
            base_sha="",
            timeout_seconds=30,
            tenant=request.tenant_id,
            mission=str(mission.mission_id),
            run_context={
                "swarm_id": f"jarvis-{mission.mission_id}",
                "mission_id": str(mission.mission_id),
                "request_id": str(request.request_id),
            },
            task_params={
                "prompt": context.objective,
                # `capability`/`task_type` must be a governed_inference router
                # processor name (not a custom JARVIS capability marker) or the
                # router denies with `unsupported_capability`. The read-only
                # JARVIS capability/authority is bound on the workflow and the
                # mission result, not on the inner provider capability slot.
                "task_type": "summarization",
                "capability": "summarization",
                "provider_fixtures": [{"name": "fallback", "fail_times": 0}],
            },
            artifact_filename="artifacts/result.json",
        )
        surface = adapter or HermesSwarmAdapter(
            repo_path=self._repo_path, run_dir=self._run_dir, max_concurrent=1
        )
        if adapter is not None and not isinstance(adapter, HermesSwarmAdapter):
            raise PermissionError("CANONICAL_HERMES_SWARM_ADAPTER_REQUIRED")
        result = surface.delegate([task])
        return JarvisMissionResult(
            mission=mission,
            request_id=request.request_id,
            request_hash=request.request_hash,
            status=result.status,
            evidence=tuple(result.artifacts),
            summary=dict(result.summary),
            error=result.error,
            task_provenance={
                "task_id": task.task_id,
                "request_id": str(request.request_id),
                "mission_id": str(mission.mission_id),
                "tenant_id": request.tenant_id,
                "capability": self.capability,
                "worker_class": task.worker_class,
            },
            swarm_id=result.swarm_id,
            routed_to_swarm=result.routed_to_swarm,
            legacy_delegate_used=result.legacy_delegate_used,
        )

    @staticmethod
    def _validate_request(request: PrincipalMissionRequest) -> None:
        if request.workflow_type != JARVIS_WORKFLOW_TYPE:
            raise PermissionError("JARVIS_WORKFLOW_TYPE_REQUIRED")
        if request.authority != JARVIS_AUTHORITY:
            raise PermissionError("JARVIS_AUTHORITY_REQUIRED")
        if EXTERNAL_SIDE_EFFECTS != 0:
            raise PermissionError("JARVIS_EXTERNAL_SIDE_EFFECTS_FORBIDDEN")
        if request.decision_context is None:
            raise ValueError("DECISION_CONTEXT_REQUIRED")
