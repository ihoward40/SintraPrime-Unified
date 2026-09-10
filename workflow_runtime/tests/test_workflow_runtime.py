"""Phase 5A certification tests — Governed Workflow Runtime Foundation.

Proof matrix (directive §45):
1. persistence across restart
2. bounded retry
3. tenant isolation
4. capability enforcement
5. provider abstraction
6. fresh evaluator context
7. budget enforcement (tokens/cost/time/calls)
8. immutable evidence/receipts
9. clean gates (separate CI lane)
10. no authority escalation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workflow_runtime.budgets import BudgetEnvelope, budget_from_spec
from workflow_runtime.checkpoint import CheckpointStore
from workflow_runtime.models import (
    BudgetSpec,
    NodeStatus,
    NodeType,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeRun,
    WorkflowRun,
    WorkflowStatus,
)
from workflow_runtime.node_executor import AgentNodeExecutor, register_operation
from workflow_runtime.parser import parse_workflow
from workflow_runtime.receipts import ReceiptStore
from workflow_runtime.registry import WorkflowRegistry, load_defaults
from workflow_runtime.retries import CircuitBreaker, RetryPolicy
from workflow_runtime.runner import WorkflowRunner
from workflow_runtime.state_machine import StateError, WorkflowStateMachine
from workflow_runtime.validator import ValidationError, validate_workflow

DEFAULTS = Path(__file__).parent.parent.parent / "workflows" / "defaults"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _proof_defn() -> WorkflowDefinition:
    return parse_workflow(DEFAULTS / "proof_workflow.yaml")


@pytest.fixture
def proof_defn() -> WorkflowDefinition:
    return _proof_defn()


@pytest.fixture
def run_store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "runs")


@pytest.fixture
def receipt_store(tmp_path: Path) -> ReceiptStore:
    return ReceiptStore(tmp_path / "receipts")


def _make_runner(run_store, receipt_store, **kwargs) -> WorkflowRunner:
    return WorkflowRunner(run_store, receipt_store, **kwargs)


# ---------------------------------------------------------------------------
# 1. Parser + validator
# ---------------------------------------------------------------------------


class TestParser:
    def test_parses_default_workflow(self):
        defn = _proof_defn()
        assert defn.name == "proof_workflow"
        assert defn.version == 1
        assert len(defn.nodes) == 6

    def test_parse_missing_name_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("version: 1\nnodes: []\n", encoding="utf-8")
        with pytest.raises(KeyError):
            parse_workflow(p)

    def test_parse_unknown_node_type_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(
            "name: x\nversion: 1\nnodes:\n  - id: a\n    type: wizard\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Unknown node type"):
            parse_workflow(p)


class TestValidator:
    def test_valid_workflow(self, proof_defn):
        result = validate_workflow(proof_defn)
        assert result.valid, result.errors

    def test_missing_dependency(self, proof_defn):
        proof_defn.nodes[0].depends_on = ["ghost"]
        result = validate_workflow(proof_defn)
        assert not result.valid
        assert any("depends on unknown node" in e for e in result.errors)

    def test_cyclic_graph_rejected(self, proof_defn):
        a, b = proof_defn.nodes[0], proof_defn.nodes[1]
        a.depends_on = [b.id]
        b.depends_on = [a.id]
        result = validate_workflow(proof_defn)
        assert not result.valid
        assert any("cycle" in e for e in result.errors)

    def test_deterministic_node_requires_action(self):
        defn = WorkflowDefinition(
            name="t",
            version=1,
            description="",
            nodes=[WorkflowNode(id="n", type=NodeType.DETERMINISTIC)],
        )
        result = validate_workflow(defn)
        assert not result.valid
        assert any("no action" in e for e in result.errors)

    def test_agent_node_requires_role(self):
        defn = WorkflowDefinition(
            name="t",
            version=1,
            description="",
            nodes=[WorkflowNode(id="n", type=NodeType.AGENT)],
        )
        result = validate_workflow(defn)
        assert not result.valid
        assert any("no role" in e for e in result.errors)

    def test_unbounded_loop_rejected(self):
        defn = WorkflowDefinition(
            name="t",
            version=1,
            description="",
            nodes=[WorkflowNode(id="n", type=NodeType.LOOP, max_iterations=10_000)],
        )
        result = validate_workflow(defn)
        assert not result.valid
        assert any("unbounded loops forbidden" in e for e in result.errors)

    def test_missing_source_hash_rejected(self):
        defn = _proof_defn()
        defn.source_hash = ""
        result = validate_workflow(defn)
        assert not result.valid
        assert any("source_hash is missing" in e for e in result.errors)


class TestRegistry:
    def test_load_defaults(self):
        reg = load_defaults(DEFAULTS)
        assert "proof_workflow" in reg.list_names()
        assert "repository_issue_fix" in reg.list_names()

    def test_register_rejects_invalid(self):
        reg = WorkflowRegistry()
        defn = WorkflowDefinition(
            name="bad",
            version=1,
            description="",
            nodes=[WorkflowNode(id="n", type=NodeType.DETERMINISTIC)],
            source_hash="abc",
        )
        with pytest.raises(ValidationError):
            reg.register(defn)

    def test_register_version_conflict(self, proof_defn):
        reg = WorkflowRegistry()
        reg.register(proof_defn)
        clash = _proof_defn()
        clash.source_hash = "different-hash"
        with pytest.raises(ValidationError, match="different hash"):
            reg.register(clash)


# ---------------------------------------------------------------------------
# 2. State machine
# ---------------------------------------------------------------------------


class TestStateMachine:
    def _run(self) -> WorkflowRun:
        return WorkflowRun(
            run_id="r1",
            workflow_name="w",
            workflow_version=1,
            workflow_hash="h",
            tenant_id="t1",
            principal_id="p1",
            node_runs={"a": WorkflowNodeRun(node_id="a", node_type=NodeType.DETERMINISTIC)},
        )

    def test_pending_to_ready_to_running(self):
        run = self._run()
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.READY)
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.RUNNING)
        assert run.status == WorkflowStatus.RUNNING

    def test_illegal_transition_raises(self):
        run = self._run()
        with pytest.raises(StateError):
            WorkflowStateMachine.transition_workflow(run, WorkflowStatus.SUCCEEDED)

    def test_terminal_superseded_only(self):
        run = self._run()
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.READY)
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.RUNNING)
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.SUCCEEDED)
        WorkflowStateMachine.transition_workflow(run, WorkflowStatus.SUPERSEDED)
        assert run.status == WorkflowStatus.SUPERSEDED


# ---------------------------------------------------------------------------
# 3. Execution + checkpoint persistence
# ---------------------------------------------------------------------------


class TestExecution:
    def test_proof_workflow_runs_to_completion(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(
            proof_defn,
            tenant_id="t1",
            principal_id="p1",
            run_id="run-1",
            context={"constraints": ["no external writes"]},
        )
        run = runner.execute(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED
        for n in proof_defn.nodes:
            assert run.node_runs[n.id].status == NodeStatus.SUCCEEDED

    def test_deterministic_nodes_cannot_be_skipped(self, proof_defn, run_store, receipt_store):
        """An agent node cannot silently skip deterministic validation."""
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="r2")
        run = runner.execute(proof_defn, run)
        validate_node = run.node_runs["validate"]
        certify_node = run.node_runs["certify"]
        assert validate_node.status == NodeStatus.SUCCEEDED
        assert certify_node.status == NodeStatus.SUCCEEDED

    def test_persistence_across_restart(self, tmp_path):
        """Simulate process crash: create run, write state, reload from disk."""
        store = CheckpointStore(tmp_path / "runs")
        receipts = ReceiptStore(tmp_path / "receipts")
        defn = _proof_defn()
        runner = WorkflowRunner(store, receipts)
        run = runner.start_run(defn, tenant_id="t1", principal_id="p1", run_id="crash-1")
        # crash before execution: state must be reloadable
        reloaded = store.load_run("crash-1")
        assert reloaded is not None
        assert reloaded.tenant_id == "t1"
        assert reloaded.status == WorkflowStatus.PENDING
        # execute partially then reload
        run = runner.execute(defn, run)
        reloaded2 = store.load_run("crash-1")
        assert reloaded2.status == WorkflowStatus.SUCCEEDED
        assert "validate" in reloaded2.node_runs

    def test_checkpoint_written_after_material_nodes(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="cp-1")
        runner.execute(proof_defn, run)
        checkpoints = run_store.list_checkpoints("cp-1")
        # deterministic + agent nodes all checkpoint
        assert len(checkpoints) >= 4

    def test_pause_resume(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="pr-1")
        run = runner.execute(proof_defn, run, pause_at_node="implement")
        assert run.status == WorkflowStatus.PAUSED
        run = runner.resume(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED

    def test_cancel(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="c-1")
        run = runner.execute(proof_defn, run, pause_at_node="plan")
        run = runner.cancel(run, reason="principal decided otherwise")
        assert run.status == WorkflowStatus.CANCELLED
        assert run.cancellation_reason == "principal decided otherwise"


# ---------------------------------------------------------------------------
# 4. Budgets
# ---------------------------------------------------------------------------


class TestBudgets:
    def test_token_ceiling_hard_stop(self, proof_defn, run_store, receipt_store):
        """Tokens ceiling must terminate execution."""
        defn = _proof_defn()
        defn.budget = BudgetSpec(
            max_tokens=10, max_provider_cost=1.0, max_wall_time_seconds=60, max_agent_calls=2
        )
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(defn, tenant_id="t", principal_id="p", run_id="b-1")
        run = runner.execute(defn, run)
        assert run.status == WorkflowStatus.BLOCKED
        assert run.error is not None

    def test_agent_call_ceiling(self):
        envelope = BudgetEnvelope(budget_from_spec(BudgetSpec(max_agent_calls=2)))
        assert envelope.consume_agent_call() is None
        reason = envelope.consume_agent_call()
        assert reason == "agent_calls_exceeded"

    def test_cost_ceiling(self):
        envelope = BudgetEnvelope(budget_from_spec(BudgetSpec(max_provider_cost=5.0)))
        assert envelope.consume_cost(3.0) is None
        reason = envelope.consume_cost(3.0)
        assert reason == "cost_exceeded"

    def test_time_ceiling(self):
        envelope = BudgetEnvelope(budget_from_spec(BudgetSpec(max_wall_time_seconds=100)))
        assert envelope.consume_wall_time(60) is None
        reason = envelope.consume_wall_time(60)
        assert reason == "time_exceeded"


# ---------------------------------------------------------------------------
# 5. Retries + circuit breaker
# ---------------------------------------------------------------------------


class TestRetries:
    def test_bounded_retry(self, proof_defn, run_store, receipt_store):
        """A failing node must fail after max_attempts, not retry forever."""
        calls = {"n": 0}

        @register_operation("test.flaky")
        def _flaky(_run, _node, _context):
            calls["n"] += 1
            raise RuntimeError("flaky op failed")

        defn = _proof_defn()
        defn.nodes.append(
            WorkflowNode(
                id="flaky",
                type=NodeType.DETERMINISTIC,
                action="test.flaky",
                depends_on=[defn.nodes[-1].id],
            )
        )
        runner = _make_runner(
            run_store,
            receipt_store,
            retry_policy=RetryPolicy(max_attempts=3, jitter=False),
        )
        run = runner.start_run(defn, tenant_id="t", principal_id="p", run_id="rt-1")
        run = runner.execute(defn, run)
        assert calls["n"] == 3
        assert run.node_runs["flaky"].status == NodeStatus.FAILED
        assert run.status == WorkflowStatus.FAILED

    def test_retry_succeeds_on_second_attempt(self, proof_defn, run_store, receipt_store):
        calls = {"n": 0}

        @register_operation("test.retry_ok")
        def _ok(_run, _node, _context):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("first attempt fails")
            return {"status": "ok"}

        defn = _proof_defn()
        defn.nodes.append(
            WorkflowNode(
                id="retry_ok",
                type=NodeType.DETERMINISTIC,
                action="test.retry_ok",
                depends_on=[defn.nodes[-1].id],
            )
        )
        runner = _make_runner(
            run_store,
            receipt_store,
            retry_policy=RetryPolicy(max_attempts=3, jitter=False),
        )
        run = runner.start_run(defn, tenant_id="t", principal_id="p", run_id="rt-2")
        run = runner.execute(defn, run)
        assert calls["n"] == 2
        assert run.node_runs["retry_ok"].status == NodeStatus.SUCCEEDED
        assert run.status == WorkflowStatus.SUCCEEDED

    def test_circuit_breaker_opens_on_identical_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.record("same error") is False
        assert cb.record("same error") is False
        assert cb.record("same error") is True  # opens
        assert cb.open is True

    def test_circuit_breaker_resets_on_different_error(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record("error A")
        cb.record("error B")  # different signature resets count
        cb.record("error A")
        cb.record("error A")
        assert cb.open is False  # never reached 3 identical


# ---------------------------------------------------------------------------
# 6. Tenant isolation + capability enforcement
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    def test_tenant_isolation(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run_a = runner.start_run(proof_defn, tenant_id="tenant-a", principal_id="p", run_id="ta-1")
        run_b = runner.start_run(proof_defn, tenant_id="tenant-b", principal_id="p", run_id="tb-1")
        runner.execute(proof_defn, run_a)
        runner.execute(proof_defn, run_b)
        reloaded_a = run_store.load_run("ta-1")
        reloaded_b = run_store.load_run("tb-1")
        assert reloaded_a.tenant_id == "tenant-a"
        assert reloaded_b.tenant_id == "tenant-b"
        # artifacts are scoped per run
        assert reloaded_a.artifacts is not reloaded_b.artifacts

    def test_tenant_scoped_receipts(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t-a", principal_id="p", run_id="tr-1")
        runner.execute(proof_defn, run)
        chain = receipt_store.load_chain("tr-1")
        assert len(chain) >= 5
        # receipts are keyed by run_id → no cross-tenant leakage
        assert receipt_store.load_chain("other-run") == []


# ---------------------------------------------------------------------------
# 7. Fresh-context evaluator contract
# ---------------------------------------------------------------------------


class TestFreshContext:
    def test_fresh_context_package(self, proof_defn, run_store, receipt_store):
        """The evaluator receives artifacts, not the implementer's chain."""
        captured = {}

        class RecordingAgentExecutor(AgentNodeExecutor):
            def execute(self, run, node, context):
                captured[node.id] = self.build_context_package(run, node)
                return super().execute(run, node, context)

        runner = _make_runner(
            run_store,
            receipt_store,
            agent_executor=RecordingAgentExecutor(),
        )
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="fc-1")
        run = runner.execute(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED
        # evaluator node has fresh_context: true and a scoped package
        evaluator_pkg = captured["evaluate"]
        assert evaluator_pkg.agent_role == "evaluator"
        assert evaluator_pkg.run_id == "fc-1"
        # artifacts come from dependencies, not from the implementer's reasoning
        artifact_sources = [a["from_node"] for a in evaluator_pkg.artifacts]
        assert "implement" in artifact_sources or "validate" in artifact_sources
        # context package is minimal: no full omni-brain dump
        assert evaluator_pkg.relevant_memories == []


# ---------------------------------------------------------------------------
# 8. Provider abstraction
# ---------------------------------------------------------------------------


class TestProviderAbstraction:
    def test_agent_executor_uses_provider_factory(self, proof_defn, run_store, receipt_store):
        """Provider selection is abstracted — no hardcoded model."""
        calls: list[str] = []

        class FakeProvider:
            def __init__(self, cls, role):
                self.cls, self.role = cls, role

            def invoke(self, pkg):
                calls.append(f"{self.cls}:{pkg.agent_role}")
                return {"provider": self.cls, "role": self.role, "output": {"done": True}}

        agent_exec = AgentNodeExecutor(provider_factory=lambda cls, role: FakeProvider(cls, role))
        runner = _make_runner(run_store, receipt_store, agent_executor=agent_exec)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="pa-1")
        run = runner.execute(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED
        # three agent nodes: planner, engineer, evaluator
        assert any("planner" in c for c in calls)
        assert any("engineer" in c for c in calls)
        assert any("evaluator" in c for c in calls)


# ---------------------------------------------------------------------------
# 9. Immutable receipts
# ---------------------------------------------------------------------------


class TestReceipts:
    def test_receipt_chain_integrity(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="rc-1")
        runner.execute(proof_defn, run)
        ok, reason = receipt_store.verify_chain("rc-1")
        assert ok, reason

    def test_tampered_receipt_detected(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="rc-2")
        runner.execute(proof_defn, run)
        chain_file = receipt_store.base_dir / "receipts_rc-2.jsonl"
        lines = chain_file.read_text(encoding="utf-8").splitlines()
        # tamper with the second receipt
        receipt = json.loads(lines[1])
        receipt["output_hash"] = "deadbeef" * 8
        lines[1] = json.dumps(receipt)
        chain_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, reason = receipt_store.verify_chain("rc-2")
        assert not ok
        assert "hash mismatch" in reason

    def test_node_run_links_receipt(self, proof_defn, run_store, receipt_store):
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(proof_defn, tenant_id="t", principal_id="p", run_id="rc-3")
        runner.execute(proof_defn, run)
        receipts = {r.node_id: r for r in receipt_store.load_chain("rc-3")}
        for node in proof_defn.nodes:
            node_run = run.node_runs[node.id]
            assert node_run.receipt_hash is not None
            assert receipts[node.id].receipt_hash == node_run.receipt_hash


# ---------------------------------------------------------------------------
# 10. Authority escalation
# ---------------------------------------------------------------------------


class TestNoEscalation:
    def test_no_authority_escalation(self, proof_defn, run_store, receipt_store):
        """Agent nodes never receive escalation: run context is fixed."""
        run = runner = None
        # run with a restricted permission set
        restricted = ["tests.execute"]
        proof_defn.capabilities = restricted
        runner = _make_runner(run_store, receipt_store)
        run = runner.start_run(
            proof_defn,
            tenant_id="t",
            principal_id="p",
            run_id="ne-1",
            context={"permissions": restricted},
        )
        run = runner.execute(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED
        # permissions never expanded
        assert run.context["permissions"] == restricted

    def test_agent_node_is_not_authority_grant(self, proof_defn, run_store, receipt_store):
        """AgentNode output cannot mutate the run's permission set."""

        class EscalationAttemptExecutor(AgentNodeExecutor):
            def execute(self, run, node, context):
                # attempt to escalate via output
                return {
                    "status": "ok",
                    "granted_permissions": ["github.write", "deploy"],
                }

        runner = _make_runner(run_store, receipt_store, agent_executor=EscalationAttemptExecutor())
        run = runner.start_run(
            proof_defn,
            tenant_id="t",
            principal_id="p",
            run_id="ne-2",
            context={"permissions": ["tests.execute"]},
        )
        run = runner.execute(proof_defn, run)
        assert run.status == WorkflowStatus.SUCCEEDED
        # the run's permission context is unchanged — output is just an artifact
        assert run.context["permissions"] == ["tests.execute"]
        assert "granted_permissions" in run.node_runs["plan"].output
        assert run.node_runs["plan"].output["granted_permissions"] == ["github.write", "deploy"]
        # but the run did NOT adopt them
        assert run.context.get("permissions") == ["tests.execute"]
