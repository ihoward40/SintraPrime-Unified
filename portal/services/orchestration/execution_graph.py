"""Execution graph helpers for orchestration DAGs."""

from __future__ import annotations

from collections import defaultdict, deque

from .schemas import ExecutionNode


def validate_dag(nodes: list[ExecutionNode]) -> None:
    """Raise ValueError when node dependencies are missing or cyclic."""
    node_ids = {node.node_id for node in nodes}
    for node in nodes:
        missing = [dep for dep in node.dependencies if dep not in node_ids]
        if missing:
            raise ValueError(f"Node {node.node_id} has missing dependencies: {missing}")

    indegree = {node.node_id: 0 for node in nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        for dep in node.dependencies:
            outgoing[dep].append(node.node_id)
            indegree[node.node_id] += 1

    queue = deque(node_id for node_id, count in indegree.items() if count == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for child in outgoing[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if visited != len(nodes):
        raise ValueError("Execution graph contains a cycle")


def topological_node_ids(nodes: list[ExecutionNode]) -> list[str]:
    validate_dag(nodes)
    remaining = {node.node_id: set(node.dependencies) for node in nodes}
    ordered: list[str] = []
    while remaining:
        ready = sorted(node_id for node_id, deps in remaining.items() if not deps)
        if not ready:
            raise ValueError("Execution graph contains a cycle")
        for node_id in ready:
            ordered.append(node_id)
            remaining.pop(node_id)
            for deps in remaining.values():
                deps.discard(node_id)
    return ordered
