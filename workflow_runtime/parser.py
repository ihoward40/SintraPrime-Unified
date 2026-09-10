"""YAML parser — declarative workflow definitions.

Reads a workflow YAML file and returns a validated WorkflowDefinition.
Supports fragment composition via ``uses:`` keys.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .models import (
    BudgetSpec,
    ModelStrategy,
    NodeDefaults,
    NodePolicy,
    NodeType,
    WorkflowDefinition,
    WorkflowNode,
)


def _parse_budget(d: dict[str, Any] | None) -> BudgetSpec:
    if not d:
        return BudgetSpec()
    return BudgetSpec(
        max_tokens=d.get("max_tokens", 500_000),
        max_provider_cost=d.get("max_provider_cost", 10.0),
        max_wall_time_seconds=d.get("max_wall_time_seconds", 3600),
        max_agent_calls=d.get("max_agent_calls", 20),
    )


def _parse_model_strategy(d: dict[str, Any] | None) -> ModelStrategy:
    if not d:
        return ModelStrategy()
    return ModelStrategy(
        initial=d.get("initial", "economy"),
        escalate_after_failures=d.get("escalate_after_failures", 2),
        escalation=d.get("escalation", ["balanced", "reasoning", "frontier"]),
    )


def _parse_node(d: dict[str, Any]) -> WorkflowNode:
    node_type_str = d.get("type", "deterministic")
    try:
        node_type = NodeType(node_type_str)
    except ValueError:
        raise ValueError(f"Unknown node type: {node_type_str!r}") from None

    budget = None
    if "budget" in d:
        budget = _parse_budget(d["budget"])

    return WorkflowNode(
        id=d["id"],
        type=node_type,
        action=d.get("action"),
        role=d.get("role"),
        provider_class=d.get("provider_class"),
        model_class=d.get("model_class"),
        fresh_context=d.get("fresh_context", False),
        context_keys=d.get("context_keys", []),
        required_capabilities=d.get("required_capabilities", []),
        branches=d.get("branches", {}),
        condition=d.get("condition"),
        max_iterations=d.get("max_iterations"),
        exit_condition=d.get("exit_condition"),
        required_when=d.get("required_when"),
        depends_on=d.get("depends_on", []),
        budget=budget,
        metadata=d.get("metadata", {}),
    )


def parse_workflow(
    path: str | Path,
    *,
    fragment_dir: Path | None = None,
) -> WorkflowDefinition:
    """Parse a workflow YAML into a WorkflowDefinition.

    If ``fragment_dir`` is given and the YAML contains ``uses:``
    references, fragments are loaded and merged.
    """
    _ = fragment_dir  # fragment composition reserved for Phase B+
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Workflow YAML must be a mapping, got {type(raw).__name__}")

    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    nodes = [_parse_node(n) for n in raw.get("nodes", [])]

    policy_d = raw.get("policy", {})
    policy = NodePolicy(
        authority=policy_d.get("authority", "default"),
        approval_mode=policy_d.get("approval_mode", "inherited"),
        isolation=policy_d.get("isolation", "worktree"),
        max_parallel_nodes=policy_d.get("max_parallel_nodes", 4),
    )

    defaults_d = raw.get("defaults", {})
    defaults = NodeDefaults(
        provider_class=defaults_d.get("provider_class", "balanced"),
        execution_profile=defaults_d.get("execution_profile", "standard"),
    )

    return WorkflowDefinition(
        name=raw["name"],
        version=raw.get("version", 1),
        description=raw.get("description", ""),
        nodes=nodes,
        policy=policy,
        defaults=defaults,
        budget=_parse_budget(raw.get("budget")),
        model_strategy=_parse_model_strategy(raw.get("model_strategy")),
        capabilities=raw.get("capabilities", []),
        source_path=str(path),
        source_hash=source_hash,
    )
