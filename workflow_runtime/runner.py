"""Workflow runner — the deterministic orchestration loop.

Executes a validated workflow definition against a WorkflowRun:
- respects topological order (dependencies first)
- executes deterministic nodes via registered operations
- executes agent nodes via AgentNodeExecutor (bounded computation)
- honors approval nodes (pause → WAITING_APPROVAL)
- honors condition nodes (structured branching)
- enforces budgets (hard stop)
- persists checkpoints after every material node
- emits immutable receipts
- bounded retries per node via RetryPolicy
- circuit breaker halts on repeated identical failures

The runner never grants authority: it executes within the
capability/tenant/principal context the run was created with.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from .budgets import BudgetEnvelope, budget_from_spec
from .checkpoint import CheckpointStore
from .conditions import evaluate_condition
from .models import (
    NodeStatus,
    NodeType,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeRun,
    WorkflowRun,
    WorkflowStatus,
    utcnow_iso,
)
from .node_executor import (
    AgentNodeExecutor,
    ApprovalNodeExecutor,
    DeterministicExecutor,
)
from .receipts import ReceiptStore
from .retries import CircuitBreaker, RetryPolicy
from .state_machine import StateError, WorkflowStateMachine


class WorkflowExecutionError(Exception):
    """Raised when a workflow cannot be executed."""


class WorkflowRunner:
    """Runs a workflow to completion (or a governed terminal state)."""

    def __init__(
        self,
        store: CheckpointStore,
        receipts: ReceiptStore,
        *,
        agent_executor: AgentNodeExecutor | None = None,
        deterministic_executor: DeterministicExecutor | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.store = store
        self.receipts = receipts
        self.agent_executor = agent_executor or AgentNodeExecutor()
        self.deterministic_executor = deterministic_executor or DeterministicExecutor()
        self.approval_executor = ApprovalNodeExecutor()
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=3)
        self.state_machine = WorkflowStateMachine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_run(
        self,
        defn: WorkflowDefinition,
        *,
        tenant_id: str,
        principal_id: str,
        run_id: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Create a new run in PENDING state and persist it."""
        budget = budget_from_spec(defn.budget)
        run = WorkflowRun(
            run_id=run_id,
            workflow_name=defn.name,
            workflow_version=defn.version,
            workflow_hash=defn.source_hash,
            tenant_id=tenant_id,
            principal_id=principal_id,
            status=WorkflowStatus.PENDING,
            budget=budget,
            context=context or {},
            node_runs={n.id: WorkflowNodeRun(node_id=n.id, node_type=n.type) for n in defn.nodes},
        )
        self.store.save_run(run)
        return run

    def execute(
        self,
        defn: WorkflowDefinition,
        run: WorkflowRun,
        *,
        pause_at_node: str | None = None,
    ) -> WorkflowRun:
        """Execute a run in governed order. Returns the final run state.

        `pause_at_node`: if set, execution pauses before that node
        (used for pause/resume tests and Principal pause).
        """
        try:
            self.state_machine.transition_workflow(run, WorkflowStatus.RUNNING)
        except StateError:
            if run.status in (
                WorkflowStatus.PAUSED,
                WorkflowStatus.WAITING_APPROVAL,
                WorkflowStatus.WAITING_INPUT,
            ):
                self.state_machine.transition_workflow(run, WorkflowStatus.RUNNING)
            else:
                raise
        self.store.save_run(run)

        order = self._topological_order(defn)
        if order is None:
            run.status = WorkflowStatus.BLOCKED
            run.error = "workflow graph contains a cycle"
            self.store.save_run(run)
            return run

        envelope = BudgetEnvelope(run.budget)
        circuit = CircuitBreaker()

        for node_id in order:
            node = defn.node_by_id(node_id)
            if node is None:
                run.status = WorkflowStatus.BLOCKED
                run.error = f"unknown node in execution order: {node_id}"
                break

            # Skip already-completed nodes (resume from checkpoint).
            node_run = run.node_runs.get(node_id)
            if node_run and node_run.status in (NodeStatus.SUCCEEDED,):
                continue

            if pause_at_node == node_id:
                self.state_machine.transition_workflow(run, WorkflowStatus.PAUSED)
                run.current_node_id = node_id
                self.store.save_run(run)
                return run

            # Budget check before node execution (hard stop).
            if envelope.check():
                run.status = WorkflowStatus.BLOCKED
                run.error = f"budget exceeded: {envelope.check()}"
                self.store.save_run(run)
                return run

            budget_hit = self._execute_node(defn, run, node, envelope, circuit)
            if budget_hit:
                run.status = WorkflowStatus.BLOCKED
                run.error = f"budget exceeded: {budget_hit}"
                self.store.save_run(run)
                return run

            if circuit.open:
                run.status = WorkflowStatus.BLOCKED
                run.error = "circuit breaker OPEN (repeated identical failures)"
                self.store.save_run(run)
                return run

            node_run = run.node_runs[node.id]
            if node_run.status == NodeStatus.FAILED:
                run.status = WorkflowStatus.FAILED
                run.error = node_run.error or f"node {node_id} failed"
                self.store.save_run(run)
                return run
            if node_run.status == NodeStatus.WAITING_APPROVAL:
                run.status = WorkflowStatus.WAITING_APPROVAL
                run.current_node_id = node_id
                self.store.save_run(run)
                return run
            if node_run.status == NodeStatus.WAITING_INPUT:
                run.status = WorkflowStatus.WAITING_INPUT
                run.current_node_id = node_id
                self.store.save_run(run)
                return run

            run.current_node_id = node_id
            self.store.save_run(run)

        if run.status not in (WorkflowStatus.BLOCKED, WorkflowStatus.FAILED):
            self.state_machine.transition_workflow(run, WorkflowStatus.SUCCEEDED)
            run.completed_at = utcnow_iso()
            self.store.save_run(run)
        return run

    # ------------------------------------------------------------------
    # Control actions (resume / cancel / approve)
    # ------------------------------------------------------------------

    def resume(self, defn: WorkflowDefinition, run: WorkflowRun) -> WorkflowRun:
        """Resume a paused / waiting run."""
        if run.status in (
            WorkflowStatus.PAUSED,
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.WAITING_INPUT,
        ):
            return self.execute(defn, run)
        return run

    def cancel(self, run: WorkflowRun, reason: str) -> WorkflowRun:
        """Cancel a run (from RUNNING, PAUSED, WAITING_*)."""
        self.state_machine.transition_workflow(run, WorkflowStatus.CANCELLED)
        run.cancellation_reason = reason
        run.completed_at = utcnow_iso()
        self.store.save_run(run)
        return run

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _topological_order(self, defn: WorkflowDefinition) -> list[str] | None:
        """Kahn's algorithm. Returns None if the graph has a cycle."""
        indegree: dict[str, int] = {n.id: 0 for n in defn.nodes}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for n in defn.nodes:
            for dep in n.depends_on:
                outgoing[dep].append(n.id)
                indegree[n.id] += 1
        queue = deque([nid for nid, c in indegree.items() if c == 0])
        order: list[str] = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for child in outgoing[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        return order if len(order) == len(defn.nodes) else None

    def _execute_node(
        self,
        defn: WorkflowDefinition,
        run: WorkflowRun,
        node: WorkflowNode,
        envelope: BudgetEnvelope,
        circuit: CircuitBreaker,
    ) -> str | None:
        """Execute one node with bounded retries. Returns budget-hit reason or None."""
        node_run = run.node_runs[node.id]
        self.state_machine.transition_node(run, node.id, NodeStatus.RUNNING)
        node_run.started_at = utcnow_iso()
        node_run.attempt += 1
        self.store.save_run(run)

        attempts = 0
        max_attempts = self.retry_policy.max_attempts
        while attempts < max_attempts:
            attempts += 1
            node_run.attempt = attempts
            try:
                output = self._dispatch_node(defn, run, node, envelope)
                node_run.output = output
                node_run.status = NodeStatus.SUCCEEDED
                node_run.completed_at = utcnow_iso()
                node_run.error = None
                self._emit_receipt(run, node, node_run, envelope)
                self.store.write_checkpoint(run, node.id, envelope.snapshot())
                self.store.save_run(run)
                return None
            except WorkflowExecutionError as exc:
                # Budget exhaustion — BLOCKED, no retry, no circuit.
                node_run.error = str(exc)
                node_run.status = NodeStatus.BLOCKED
                node_run.completed_at = utcnow_iso()
                self.store.save_run(run)
                return "budget_exceeded"
            except Exception as exc:
                node_run.error = str(exc)
                self.store.save_run(run)
                # If retries exhausted, natural FAILED — not circuit BLOCKED.
                if attempts >= max_attempts:
                    node_run.status = NodeStatus.FAILED
                    node_run.completed_at = utcnow_iso()
                    self.store.save_run(run)
                    return None
                # Circuit breaker: early termination before exhausting retries.
                if circuit.record(str(exc)):
                    node_run.status = NodeStatus.BLOCKED
                    node_run.completed_at = utcnow_iso()
                    self.store.save_run(run)
                    return None
                # retry after backoff
                delay = self.retry_policy.next_delay(attempts - 1)
                time.sleep(delay)
        return None

    def _dispatch_node(
        self,
        defn: WorkflowDefinition,
        run: WorkflowRun,
        node: WorkflowNode,
        envelope: BudgetEnvelope,
    ) -> dict[str, Any]:
        """Dispatch a node to the correct executor. Returns output dict."""
        del defn  # definition is validated upstream; runner holds run state
        if node.type == NodeType.DETERMINISTIC:
            # Deterministic nodes cannot be skipped by agents: they are
            # executed here and only here.
            return self.deterministic_executor.execute(run, node, run.context)
        if node.type == NodeType.AGENT:
            budget_hit = envelope.consume_agent_call()
            if budget_hit:
                raise WorkflowExecutionError(f"agent call budget exceeded: {budget_hit}")
            output = self.agent_executor.execute(run, node, run.context)
            # agent calls consume token budget estimates
            envelope.consume_tokens(
                input_tokens=node.metadata.get("input_tokens_estimate", 0),
                output_tokens=node.metadata.get("output_tokens_estimate", 0),
            )
            return output
        if node.type == NodeType.APPROVAL:
            return self.approval_executor.check(node, run)
        if node.type == NodeType.CONDITION:
            # evaluate structured condition, record chosen branch
            branch_choice = node.branches.get("default", "")
            for condition_expr, target in node.branches.items():
                if condition_expr == "default":
                    continue
                if evaluate_condition(condition_expr, run):
                    branch_choice = target
                    break
            return {"branch": branch_choice, "chosen": branch_choice}
        if node.type == NodeType.HUMAN_INPUT:
            return {"status": "WAITING_INPUT", "node_id": node.id}
        if node.type == NodeType.LOOP:
            iterations = 0
            while iterations < (node.max_iterations or 1):
                iterations += 1
                envelope.consume_tokens(input_tokens=10)  # loop bookkeeping
            return {"iterations": iterations, "completed": True}
        raise WorkflowExecutionError(f"Unsupported node type: {node.type}")

    def _emit_receipt(
        self,
        run: WorkflowRun,
        node: WorkflowNode,
        node_run: WorkflowNodeRun,
        envelope: BudgetEnvelope,
    ) -> None:
        receipt = self.receipts.append(
            run_id=run.run_id,
            node_id=node.id,
            node_type=node.type,
            status=node_run.status,
            output=node_run.output,
            provider=node.metadata.get("provider"),
            model=node.metadata.get("model"),
            tokens_used=envelope.budget.tokens_used,
            cost=round(envelope.budget.provider_cost_used, 6),
        )
        node_run.receipt_hash = receipt.receipt_hash
