"""Deterministic condition evaluation for workflow branching.

Conditions are evaluated as simple Python expressions over the run
context and node outputs. No LLM involvement — pure determinism.
"""

from __future__ import annotations

from typing import Any

import operator

from .models import WorkflowRun

# Safe comparison operators for condition expressions.
_OPS: dict[str, Any] = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


def evaluate_condition(condition: str, run: WorkflowRun) -> bool:
    """Evaluate a structured condition string against run state.

    Supported formats:
        - "field op value"  (e.g. "last_output.status == success")
        - "field"           (truthy check)
        - ""                (always True — default branch)

    For Phase 5A we support simple key-path lookups into run.context
    and the previous node's output. No arbitrary Python eval.
    """
    if not condition or not condition.strip():
        return True
    parts = condition.strip().split(None, 2)
    if len(parts) == 1:
        # truthy check
        val = _resolve(parts[0], run)
        return bool(val)
    if len(parts) == 3:
        left_key, op_str, right_val = parts
        if op_str not in _OPS:
            raise ValueError(f"Unknown operator: {op_str!r}")
        left = _resolve(left_key, run)
        right = _coerce(right_val)
        return _OPS[op_str](left, right)
    raise ValueError(f"Invalid condition: {condition!r}")


def _resolve(key_path: str, run: WorkflowRun) -> Any:
    """Resolve a dot-separated key path against run context/artifacts."""
    parts = key_path.split(".")
    # Search order: run.context → run.artifacts → node_run outputs
    source: dict[str, Any] = {**run.context, **run.artifacts}
    current = source
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _coerce(value: str) -> Any:
    """Coerce a string value to its natural type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
        return value[1:-1]
    return value
