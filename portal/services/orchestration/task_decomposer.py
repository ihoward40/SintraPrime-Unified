"""Bounded work-unit decomposition for orchestration plans."""

from __future__ import annotations

from .instruction_compiler import compile_instruction
from .role_assignment import assign_roles
from .schemas import ClassificationResult, ExecutionMode, ExecutionNode, NodeStatus, Role


def decompose_task(
    *,
    objective: str,
    classification: ClassificationResult,
    execution_mode: ExecutionMode,
) -> list[ExecutionNode]:
    """Create a deterministic DAG from classification and execution mode."""
    roles = assign_roles(execution_mode, classification.required_roles)
    nodes: list[ExecutionNode] = []
    prior_node_ids: list[str] = []
    sequence_by_role: dict[Role, int] = {}

    for role in roles:
        sequence_by_role[role] = sequence_by_role.get(role, 0) + 1
        node_id = f"{role.value.lower()}-{sequence_by_role[role]}"
        dependencies = _dependencies_for(role, prior_node_ids, execution_mode)
        nodes.append(
            ExecutionNode(
                node_id=node_id,
                role=role,
                objective=objective,
                instructions=compile_instruction(
                    role=role,
                    objective=objective,
                    classification=classification,
                    dependencies=dependencies,
                ),
                dependencies=dependencies,
                status=NodeStatus.WAITING if dependencies else NodeStatus.READY,
            )
        )
        if role != Role.PRINCIPAL:
            prior_node_ids.append(node_id)
    return nodes


def _dependencies_for(role: Role, prior_node_ids: list[str], execution_mode: ExecutionMode) -> list[str]:
    if role in {Role.PLANNER, Role.THINKER, Role.RESEARCHER}:
        return []
    if execution_mode == ExecutionMode.PARALLEL_COMPARE and role in {Role.WORKER, Role.CHECKER}:
        return []
    if role == Role.RECONCILER:
        return list(prior_node_ids)
    if role == Role.PRINCIPAL:
        return list(prior_node_ids[-2:])
    return prior_node_ids[-1:] if prior_node_ids else []
