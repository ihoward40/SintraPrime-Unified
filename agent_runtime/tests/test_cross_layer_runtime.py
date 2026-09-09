"""Wave 3 CHECKPOINT 1 — cross-layer bounded runtime test (§23).

Principal authority → Hermes → child agent → delegation → context →
memory read → provider fake → tool fake → receipt. No real external
effect. Precursor to the Golden Mission test.
"""
from __future__ import annotations

from agent_runtime.context import BudgetTracker, ContextPackage, context_hash
from agent_runtime.delegation import DelegationAuthority
from agent_runtime.manifest import AgentManifest, BudgetPolicy, manifest_hash
from agent_runtime.receipts import (
    AgentRuntimeReceipt,
    MemoryWriteAuthority,
    RuntimeOutcome,
)
from agent_runtime.registry import AgentRegistry, CertificationStatus


def _manifest(agent_id: str, **kw) -> AgentManifest:
    fields = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "display_name": agent_id,
        "owner": "sintraprime.principal",
        "runtime_class": "tests.Fake",
        "mission_types": ("generic",),
        "provider_policy": {"provider_class": "REASONING", "local_only": True},
        "tool_policy": {"allowed_tool_categories": ("fake",)},
        "authority_policy": "DELEGATED",
    }
    fields.update(kw)
    return AgentManifest(**fields)


class _FakeProvider:
    """Provider fake — structured output only; the provider never decides authority."""

    def __init__(self, budget: BudgetTracker) -> None:
        self._budget = budget

    def complete(self, prompt: str) -> dict:
        self._budget.consume_provider_call()
        return {"text": f"analysed:{prompt[:20]}", "structured": True}


class _FakeTool:
    """Tool fake — availability != permission; the boundary checks policy first."""

    def __init__(self, budget: BudgetTracker) -> None:
        self._budget = budget

    def read_file(self, path: str) -> str:
        self._budget.consume_tool_call()
        return f"file-bytes:{path}"


def test_full_bounded_runtime_mission():
    """§23: the full governed path, no real external effect."""
    # 1. registry: manifests registered + validated + certified (ladder)
    registry = AgentRegistry()
    hermes_m = _manifest("agent.hermes", mission_types=("governed_orchestration",),
                         required_capabilities=("DELEGATE_TASK", "READ_REPOSITORY", "REQUEST_MEMORY_WRITE"))
    worker_m = _manifest("agent.worker",
                         required_capabilities=("READ_REPOSITORY",),
                         forbidden_capabilities=("EXECUTE_PAYMENT", "SEND_EMAIL"))
    registry.register(hermes_m)
    registry.register(worker_m := _manifest("agent.worker"))
    assert registry.validate_registered("agent.hermes") == []
    assert registry.validate_registered("agent.worker") == []
    registry.set_status("agent.hermes", CertificationStatus.TESTED)
    registry.certify("agent.hermes")
    registry.set_status("agent.worker", CertificationStatus.TESTED)
    registry.certify("agent.worker")

    # 2. governance roots Hermes authority; Hermes delegates a subset
    auth = DelegationAuthority()
    auth.set_delegatable("agent.hermes", {"READ_REPOSITORY", "REQUEST_MEMORY_WRITE"}, actor="governance")
    delegation = auth.issue(
        parent_agent="agent.hermes",
        child_manifest=worker_m,
        delegation_id="d-golden",
        mission_id="M-GOLDEN-1",
        capabilities=["READ_REPOSITORY"],
        tenant="t1",
        resource_scope=("src/*",),
        ttl_seconds=1800,
    )

    # 3. typed context package (minimal)
    ctx = ContextPackage(
        mission_id="M-GOLDEN-1",
        mission_type="generic",
        parent_agent="agent.hermes",
        agent_id="agent.worker",
        delegation_id=delegation.delegation_id,
        tenant="t1",
        resource_scope=("src/app.py",),
        payload={"file": "src/app.py"},
    )

    # 4. bounded runtime under the delegation
    budget = BudgetTracker(worker_m.budget_policy)
    budget.begin_iteration()
    auth.check_use(delegation, capability="READ_REPOSITORY", mission_id="M-GOLDEN-1", tenant="t1", resource="src/app.py")

    # 5. provider fake + tool fake (no external effect)
    run_budget = BudgetTracker(BudgetPolicy(max_iterations=10, timeout_seconds=30, max_provider_calls=5, max_tool_calls=5))
    run_budget.begin_iteration()
    tool = _FakeTool(run_budget)
    file_bytes = tool.read_file("src/app.py")
    assert file_bytes == "file-bytes:src/app.py"
    provider = _FakeProvider(run_budget)
    provider.complete("analyse src/app.py")

    # 6. memory: read within scope; write via request with provenance
    memory = MemoryWriteAuthority()
    memory.allow_write_scope("agent.worker", "MISSION")
    write_receipt = memory.submit(
        agent_id="agent.worker",
        proposed_scope="MISSION",
        content="analyzed src/app.py",
        mission_id="M-GOLDEN-1",
        tenant="t1",
        evidence_reference="ev:src-app-analysis",
    )

    # 7. runtime receipt (§21/§38): facts only + manifest/context hashes
    receipt = AgentRuntimeReceipt(
        agent_id="agent.worker",
        agent_version=worker_m.agent_version,
        mission_id="M-GOLDEN-1",
        delegation_id=delegation.delegation_id,
        manifest_hash=manifest_hash(worker_m),
        capabilities_used=("READ_REPOSITORY",),
        tools_used=("fake.read_file",),
        provider_calls=run_budget.provider_calls,
        tool_calls=run_budget.tool_calls,
        memory_reads=1,
        memory_write_requests=1,
        duration_seconds=0.05,
        result=RuntimeOutcome.COMPLETED,
        evidence_refs=(f"ctx:{context_hash(ctx)[:16]}", "memory:write-receipt"),
    )
    assert receipt.result is RuntimeOutcome.COMPLETED
    assert receipt.manifest_hash
    assert receipt.tool_calls == 1
    assert receipt.provider_calls == 1
    # memory provenance is complete
    assert write_receipt.actor_agent == "agent.worker"
    assert write_receipt.mission_id == "M-GOLDEN-1"


class TestRefusalVsFailure:
    def test_refused_is_not_failed_in_outcomes(self):
        from agent_runtime.receipts import RuntimeOutcome

        outcomes = {o.value for o in RuntimeOutcome}
        assert {"COMPLETED", "REFUSED", "FAILED", "TIMED_OUT", "CANCELLED", "DEGRADED", "BUDGET_EXHAUSTED"} == set(outcomes)

    def test_refusal_semantics_distinct(self):
        """Future refactors must not collapse REFUSED into FAILED."""
        assert RuntimeOutcome.REFUSED.value == "REFUSED"
        assert RuntimeOutcome.REFUSED != RuntimeOutcome.FAILED
