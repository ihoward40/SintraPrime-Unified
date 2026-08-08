"""Workflow validator — semantic checks, DAG validation, version pinning.

Phase 5A validation rules:
1. Every dependency reference exists.
2. The graph has no cycles (reuse execution_graph.validate_dag pattern).
3. Every node has a valid type.
4. Deterministic nodes have an ``action`` field.
5. Agent nodes have a ``role`` field.
6. Conditional nodes have ``branches``.
7. Loop nodes have ``max_iterations``.
8. All IDs are unique.
9. Workflow version and source hash are pinned.
"""

from __future__ import annotations

from collections import defaultdict, deque

from .models import NodeType, WorkflowDefinition


class ValidationError(Exception):
    """Raised when a workflow definition fails validation."""


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.valid = True

    def add(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def __bool__(self) -> bool:
        return self.valid

    def __repr__(self) -> str:
        return f"ValidationResult(valid={self.valid}, errors={len(self.errors)})"


def validate_workflow(defn: WorkflowDefinition) -> ValidationResult:
    """Validate a workflow definition. Returns a ValidationResult."""
    result = ValidationResult()

    # --- uniqueness ---
    node_ids: set[str] = set()
    for node in defn.nodes:
        if node.id in node_ids:
            result.add(f"Duplicate node id: {node.id}")
        node_ids.add(node.id)

    if not node_ids:
        result.add("Workflow has no nodes")

    # --- dependency existence ---
    for node in defn.nodes:
        for dep in node.depends_on:
            if dep not in node_ids:
                result.add(f"Node {node.id} depends on unknown node: {dep}")

    # --- cycle detection (Kahn's algorithm) ---
    indegree: dict[str, int] = {n.id: 0 for n in defn.nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for node in defn.nodes:
        for dep in node.depends_on:
            if dep in node_ids:
                outgoing[dep].append(node.id)
                indegree[node.id] += 1
    queue = deque(nid for nid, count in indegree.items() if count == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for child in outgoing[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(defn.nodes):
        result.add("Workflow graph contains a cycle")

    # --- node-type-specific checks ---
    for node in defn.nodes:
        if node.type == NodeType.DETERMINISTIC and not node.action:
            result.add(f"Deterministic node {node.id} has no action")
        if node.type == NodeType.AGENT and not node.role:
            result.add(f"Agent node {node.id} has no role")
        if node.type == NodeType.CONDITION and not node.branches:
            result.add(f"Condition node {node.id} has no branches")
        if node.type == NodeType.LOOP and not node.max_iterations:
            result.add(f"Loop node {node.id} has no max_iterations")
        if node.type == NodeType.LOOP and node.max_iterations and node.max_iterations > 100:
            result.add(
                f"Loop node {node.id} max_iterations {node.max_iterations} exceeds 100 (unbounded loops forbidden)"
            )

    # --- version pinning ---
    if defn.version < 1:
        result.add("Workflow version must be >= 1")
    if not defn.source_hash:
        result.add("Workflow source_hash is missing (version pinning required)")

    # --- approval mode ---
    if defn.policy.approval_mode not in ("inherited", "always", "consequential_only"):
        result.add(f"Unknown approval_mode: {defn.policy.approval_mode!r}")

    return result
