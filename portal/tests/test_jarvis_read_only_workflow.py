from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

import pytest

from portal.services.jarvis_principal_mission import (
    DecisionContext,
    InMemoryPrincipalMissionRequestStore,
    PrincipalMissionRequestInput,
    persist_principal_mission_request,
)
from portal.services.jarvis_read_only_workflow import JarvisReadOnlyWorkflow
from swarm_runtime.hermes_adapter import HermesSwarmAdapter, SwarmResult

REPO_ROOT = Path(__file__).resolve().parents[2]


class ArbitraryAdapter:
    def delegate(self, tasks):
        raise AssertionError("arbitrary adapter must never be invoked")




class SpyAdapter(HermesSwarmAdapter):
    def __init__(self) -> None:
        self.tasks = []

    def delegate(self, tasks):
        self.tasks.extend(tasks)
        return SwarmResult(
            task_id=tasks[0].task_id,
            swarm_id="swarm-a2",
            status="SUCCESS",
            workers_requested=1,
            workers_started=1,
            workers_completed=1,
            artifacts=[{"worker_id": "w1", "artifact": {"state": "completed"}}],
            routed_to_swarm=True,
            legacy_delegate_used=False,
            summary={"evidence_count": 1},
            error="",
        )


async def _request():
    store = InMemoryPrincipalMissionRequestStore()
    return await persist_principal_mission_request(
        store,
        tenant_id="tenant-1",
        requested_by="principal-1",
        input_data=PrincipalMissionRequestInput(
            objective="Review the repository and identify attention items.",
            decision_context=DecisionContext(
                objective="Review the repository and identify attention items.",
                constraints=("read_only",),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_a2_preserves_mission_request_and_invokes_server_swarm_surface():
    request = await _request()
    spy = SpyAdapter()
    result = JarvisReadOnlyWorkflow(repo_path=str(Path.cwd())).execute(request, adapter=spy)
    assert isinstance(result.mission.mission_id, UUID)
    assert result.mission.request_id == request.request_id
    assert result.mission.tenant_id == request.tenant_id
    assert result.routed_to_swarm is True
    assert result.legacy_delegate_used is False
    assert result.external_side_effects == 0
    assert len(spy.tasks) == 1
    assert spy.tasks[0].worker_class == "ModelReasoningWorker"
    # JARVIS read-only capability/authority are bound at the workflow/result
    # layer, NOT as an inner provider capability (which must be a
    # governed_inference router processor name to route at all).
    assert result.mission.authority == "JARVIS_READ_ONLY"
    assert result.mission.workflow_type == "jarvis.principal_mission"
    assert spy.tasks[0].task_params["capability"] == "summarization"
    assert result.evidence[0]["artifact"]["state"] == "completed"


@pytest.mark.asyncio
async def test_a2_rejects_unapproved_workflow_and_authority():
    request = await _request()
    object.__setattr__(request, "workflow_type", "legacy.provider.workflow")
    with pytest.raises(PermissionError, match="WORKFLOW_TYPE"):
        JarvisReadOnlyWorkflow(repo_path=str(Path.cwd())).execute(request, adapter=SpyAdapter())


@pytest.mark.asyncio
async def test_a2_rejects_noncanonical_adapter_before_invocation():
    request = await _request()
    with pytest.raises(PermissionError, match="CANONICAL_HERMES_SWARM_ADAPTER"):
        JarvisReadOnlyWorkflow(repo_path=str(Path.cwd())).execute(
            request, adapter=ArbitraryAdapter()
        )


@pytest.mark.asyncio
async def test_a2_preserves_summary_error_and_provenance():
    request = await _request()
    result = JarvisReadOnlyWorkflow(repo_path=str(Path.cwd())).execute(
        request, adapter=SpyAdapter()
    )
    assert result.request_hash == request.request_hash
    assert result.summary == {"evidence_count": 1}
    assert result.error == ""
    assert result.task_provenance["tenant_id"] == request.tenant_id
    assert result.task_provenance["request_id"] == str(request.request_id)


@pytest.mark.integration
async def test_a2_real_bridge_reaches_swarm_controller_and_governed_inference() -> None:
    """Proof #2/#5/#6 of the directive's 8-point requirement set.

    Runs the A2 workflow with NO injected adapter so the production path is
    exercised end-to-end: JarvisReadOnlyWorkflow -> HermesSwarmAdapter ->
    SwarmController -> ModelReasoningWorker -> SwarmInferenceAdapter ->
    GovernedInferenceRouter -> typed evidence-backed result. The worker runs in
    a subprocess with only deterministic MockProviders, so no external provider
    or network is contacted and EXTERNAL_SIDE_EFFECTS stays 0.
    """
    request = await _request()
    with tempfile.TemporaryDirectory(prefix="a2-real-bridge-") as run_dir:
        result = JarvisReadOnlyWorkflow(repo_path=str(REPO_ROOT), run_dir=run_dir).execute(
            request
        )

    # #3/#4: mission execution reached the swarm controller and completed.
    assert result.status == "SUCCESS"
    assert result.routed_to_swarm is True
    # #6: the legacy provider-bound path was not used.
    assert result.legacy_delegate_used is False
    # invariant: no external side effect escaped.
    assert result.external_side_effects == 0
    # #7: a typed, evidence-backed artifact returned to the mission boundary.
    assert isinstance(result.evidence, tuple)
    assert len(result.evidence) == 1
    artifact = result.evidence[0]["artifact"]
    assert artifact["state"] == "completed"
    # #5: semantic worker inference reached GovernedInferenceRouter and the
    # provider that produced the answer is recorded.
    assert artifact["findings"]["provider"] == "fallback"
    assert artifact["findings"]["provider_attempts"]
    # mission provenance is intact.
    assert result.mission.request_id == request.request_id
    assert result.mission.tenant_id == request.tenant_id
    assert result.request_hash == request.request_hash
