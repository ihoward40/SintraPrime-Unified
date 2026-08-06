"""Deterministic mock orchestration coordinator."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .audit_recorder import append_event
from .budget_policy import BudgetLimits, consume_budget, initial_budget_usage
from .execution_graph import topological_node_ids, validate_dag
from .model_router import route_provider
from .provider_registry import mock_provider_registry
from .result_reconciler import reconcile_outputs
from .schemas import ExecutionMode, NodeStatus, Role, RunStatus
from .security import denied_actions, detect_prompt_injection, redact_text, sanitize_payload
from .task_classifier import classify_task
from .task_decomposer import decompose_task
from .verifier import verify_output


RUNS: dict[str, dict[str, Any]] = {}


def plan_run(
    *,
    objective: str,
    constraints: dict[str, Any] | None = None,
    execution_mode: ExecutionMode = ExecutionMode.THINK_WORK_CHECK,
    budget_limits: BudgetLimits | None = None,
) -> dict[str, Any]:
    classification = classify_task(redact_text(objective), sanitize_payload(constraints or {}))
    budget = initial_budget_usage(budget_limits)
    nodes = decompose_task(objective=objective, classification=classification, execution_mode=execution_mode)
    validate_dag(nodes)
    run_id = str(uuid.uuid4())
    run = {
        "run_id": run_id,
        "objective": redact_text(objective),
        "constraints": sanitize_payload(constraints or {}),
        "classification": classification.model_dump(mode="json"),
        "execution_mode": execution_mode.value,
        "status": RunStatus.PLANNED.value,
        "nodes": [node.model_dump(mode="json") for node in nodes],
        "routing_decisions": [],
        "budget": budget.model_dump(mode="json"),
        "verification": [],
        "reconciliation": None,
        "approvals": [],
        "events": [],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    append_event(run["events"], "RUN_PLANNED", {"node_count": len(nodes), "prompt_injection": detect_prompt_injection(objective), "denied_actions": denied_actions(objective)}, Role.PLANNER.value)
    RUNS[run_id] = run
    return deepcopy(run)


def execute_run(
    *,
    objective: str,
    constraints: dict[str, Any] | None = None,
    execution_mode: ExecutionMode = ExecutionMode.THINK_WORK_CHECK,
    budget_limits: BudgetLimits | None = None,
) -> dict[str, Any]:
    run = plan_run(
        objective=objective,
        constraints=constraints,
        execution_mode=execution_mode,
        budget_limits=budget_limits,
    )
    run_id = run["run_id"]
    stored = RUNS[run_id]
    _execute_existing(stored)
    return deepcopy(stored)


def get_run(run_id: str) -> dict[str, Any] | None:
    run = RUNS.get(run_id)
    return deepcopy(run) if run else None


def get_events(run_id: str) -> list[dict[str, Any]] | None:
    run = RUNS.get(run_id)
    return deepcopy(run["events"]) if run else None


def cancel_run(run_id: str, reason: str) -> dict[str, Any] | None:
    run = RUNS.get(run_id)
    if not run:
        return None
    run["status"] = RunStatus.CANCELLED.value
    run["cancellation_reason"] = reason
    for node in run["nodes"]:
        if node["status"] not in {NodeStatus.COMPLETED.value, NodeStatus.FAILED.value}:
            node["status"] = NodeStatus.CANCELLED.value
    append_event(run["events"], "RUN_CANCELLED", {"reason": reason}, Role.PRINCIPAL.value)
    return deepcopy(run)


def approve_run(run_id: str, principal_id: str, approved: bool, reason: str | None = None) -> dict[str, Any] | None:
    run = RUNS.get(run_id)
    if not run:
        return None
    status = "APPROVED" if approved else "DENIED"
    for approval in run["approvals"]:
        approval["status"] = status
        approval["principal_id"] = principal_id
        approval["decision_reason"] = reason
        approval["decided_at"] = datetime.now(UTC).isoformat()
    append_event(run["events"], "APPROVAL_DECIDED", {"status": status, "reason": reason}, Role.PRINCIPAL.value)
    if approved and run["status"] == RunStatus.APPROVAL_REQUIRED.value:
        run["status"] = RunStatus.COMPLETED.value
    return deepcopy(run)


def _execute_existing(run: dict[str, Any]) -> None:
    run["status"] = RunStatus.RUNNING.value
    append_event(run["events"], "RUN_STARTED", {}, Role.PLANNER.value)
    classification = classify_task(run["objective"], run["constraints"])
    providers = mock_provider_registry()
    budget = initial_budget_usage(BudgetLimits(**run["budget"]["limits"]))
    outputs: list[dict[str, Any]] = []
    verifications = []
    selected_worker_provider: str | None = None
    nodes_by_id = {node["node_id"]: node for node in run["nodes"]}

    for node_id in topological_node_ids(_nodes_from_run(run)):
        node = nodes_by_id[node_id]
        role = Role(node["role"])
        if run["status"] == RunStatus.CANCELLED.value:
            node["status"] = NodeStatus.CANCELLED.value
            continue
        budget = consume_budget(budget, nodes=1)
        run["budget"] = budget.model_dump(mode="json")
        if budget.hard_limit_reached:
            node["status"] = NodeStatus.BLOCKED.value
            run["status"] = RunStatus.PARTIAL.value if outputs else RunStatus.BLOCKED.value
            append_event(run["events"], "BUDGET_BLOCKED", {"reason": budget.limit_reason}, role.value)
            break
        if role == Role.PRINCIPAL:
            _request_principal_approval(run, node)
            continue
        exclude = {selected_worker_provider} if role == Role.CHECKER and selected_worker_provider else set()
        decision = route_provider(
            role=role,
            classification=classification,
            budget=budget,
            providers=providers,
            exclude_provider_ids=exclude,
        )
        run["routing_decisions"].append(decision.model_dump(mode="json"))
        if not decision.selected_provider:
            node["status"] = NodeStatus.BLOCKED.value
            run["status"] = RunStatus.BLOCKED.value
            append_event(run["events"], "ROUTING_BLOCKED", {"node_id": node_id}, role.value)
            break
        node["assigned_provider"] = decision.selected_provider
        node["status"] = NodeStatus.RUNNING.value
        append_event(run["events"], "NODE_STARTED", {"node_id": node_id, "provider": decision.selected_provider}, role.value)
        if run["constraints"].get("scenario") == "provider_failure" and role == Role.WORKER and node["retry_count"] == 0:
            node["retry_count"] = 1
            budget = consume_budget(budget, retries=1)
            run["budget"] = budget.model_dump(mode="json")
            append_event(run["events"], "PROVIDER_FAILED", {"node_id": node_id, "provider": decision.selected_provider, "retry_count": 1}, role.value)
        output = _mock_output(role, run["objective"], decision.selected_provider)
        output = sanitize_payload(output)
        node["output_artifacts"] = [output]
        node["confidence"] = output["confidence"]
        node["evidence"] = output["evidence"]
        node["status"] = NodeStatus.COMPLETED.value
        outputs.append(output)
        if role == Role.WORKER:
            selected_worker_provider = decision.selected_provider
        if role == Role.CHECKER:
            verification = verify_output(output, require_evidence=True)
            verifications.append(verification)
            run["verification"].append(verification.model_dump(mode="json"))
        append_event(run["events"], "NODE_COMPLETED", {"node_id": node_id, "confidence": output["confidence"]}, role.value)

    if run["status"] in {RunStatus.BLOCKED.value, RunStatus.PARTIAL.value, RunStatus.APPROVAL_REQUIRED.value}:
        return
    if not verifications:
        verifications = [verify_output(output, require_evidence=False) for output in outputs]
        run["verification"] = [item.model_dump(mode="json") for item in verifications]
    reconciliation = reconcile_outputs(outputs, verifications, approval_required=classification.approval_requirement)
    run["reconciliation"] = reconciliation.model_dump(mode="json")
    if reconciliation.principal_decision_required:
        run["status"] = RunStatus.APPROVAL_REQUIRED.value
        _request_principal_approval(run, {"node_id": "principal-approval", "role": Role.PRINCIPAL.value})
    else:
        run["status"] = RunStatus.COMPLETED.value
    append_event(run["events"], "RUN_RECONCILED", {"final_confidence": reconciliation.final_confidence}, Role.RECONCILER.value)
    run["updated_at"] = datetime.now(UTC).isoformat()


def _nodes_from_run(run: dict[str, Any]):
    from .schemas import ExecutionNode

    return [ExecutionNode(**node) for node in run["nodes"]]


def _mock_output(role: Role, objective: str, provider_id: str) -> dict[str, Any]:
    if role == Role.CHECKER:
        return {
            "result": "Checker found an unresolved implementation assumption.",
            "claims": ["Implementation requires Principal approval before external action"],
            "confidence": 0.72,
            "evidence": [{"source_type": "mock", "evidence_quality": "test", "verified": True}],
            "assumptions": [],
            "contradictions": ["Worker output did not prove external action remained disabled."],
            "unresolved_uncertainty": ["External action boundary must be confirmed."],
        }
    return {
        "result": f"{role.value} mock output for: {objective}",
        "claims": [f"{role.value} completed bounded task"],
        "confidence": 0.8 if provider_id != "reasoning_model" else 0.76,
        "evidence": [{"source_type": "mock", "evidence_quality": "verified", "verified": True}],
        "assumptions": ["Milestone One mock execution only."],
        "contradictions": [],
        "unresolved_uncertainty": [],
    }


def _request_principal_approval(run: dict[str, Any], node: dict[str, Any]) -> None:
    approval = {
        "approval_id": str(uuid.uuid4()),
        "node_id": node.get("node_id"),
        "requested_action": "Approve governed orchestration result",
        "reason": "Approval required by policy, sensitivity, or unresolved disagreement.",
        "risk_level": "controlled",
        "status": "REQUESTED",
        "requested_by_role": node.get("role", Role.GOVERNANCE_REVIEWER.value),
        "principal_id": None,
    }
    if not run["approvals"]:
        run["approvals"].append(approval)
    run["status"] = RunStatus.APPROVAL_REQUIRED.value
    append_event(run["events"], "APPROVAL_REQUESTED", approval, Role.GOVERNANCE_REVIEWER.value)
