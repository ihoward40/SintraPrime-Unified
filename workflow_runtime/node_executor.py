"""Node executors — deterministic operations and agent-node abstraction.

Phase 5A node types:
- DeterministicNode: runs a registered operation (callable).
- AgentNode: calls a governed provider with scoped context, fresh-context flag.
- ApprovalNode: pauses until Principal decision (stub for Phase 5A).
- ConditionNode: deterministic branching on structured output.

No node may acquire more authority than the initiating principal/agent
possesses. AgentNode is a computation abstraction, not an authority grant.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from .models import (
    ContextPackage,
    NodeType,
    WorkflowNode,
    WorkflowRun,
    utcnow_iso,
)

# ---------------------------------------------------------------------------
# Deterministic operation registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Callable[[WorkflowRun, WorkflowNode, dict[str, Any]], dict[str, Any]]] = {}


def register_operation(key: str):
    """Decorator to register a deterministic operation."""

    def wrapper(fn: Callable):
        _REGISTRY[key] = fn
        return fn

    return wrapper


def get_operation(key: str) -> Callable | None:
    return _REGISTRY.get(key)


# ---------------------------------------------------------------------------
# Built-in deterministic operations
# ---------------------------------------------------------------------------


@register_operation("noop")
def _noop(run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok"}


@register_operation("context.collect")
def _context_collect(
    run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]
) -> dict[str, Any]:
    """Collect deterministic context: run metadata, workflow info, timestamp."""
    return {
        "run_id": run.run_id,
        "workflow": run.workflow_name,
        "version": run.workflow_version,
        "collected_at": utcnow_iso(),
        "context_keys": list(context.keys()),
    }


@register_operation("test.changed_scope")
def _test_changed_scope(
    run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]
) -> dict[str, Any]:
    """Run changed-scope tests. Deterministic — no LLM involved."""
    # Phase 5A: return pass for proof; real implementation in Phase B+.
    return {
        "tests_passed": True,
        "tests_run": 0,
        "tests_failed": 0,
        "scope": "deterministic_validation",
        "validated_at": utcnow_iso(),
    }


@register_operation("validate.immutable_output")
def _validate_immutable_output(
    run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]
) -> dict[str, Any]:
    """Verify output artifacts are present and hashable."""
    artifacts = run.artifacts
    if not artifacts:
        return {"valid": False, "reason": "no artifacts found"}
    output_hash = hashlib.sha256(json.dumps(artifacts, sort_keys=True).encode()).hexdigest()
    return {"valid": True, "output_hash": output_hash}


@register_operation("github.issue.fetch")
def _github_issue_fetch(
    run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]
) -> dict[str, Any]:
    """Fetch a GitHub issue. Phase 5A: deterministic stub — no network."""
    return {
        "status": "fetched",
        "issue_key": context.get("issue_key", "unknown"),
        "source": "github.issue.fetch (deterministic stub)",
    }


@register_operation("github.pr.prepare")
def _github_pr_prepare(
    run: WorkflowRun, node: WorkflowNode, context: dict[str, Any]
) -> dict[str, Any]:
    """Prepare a draft PR. Phase 5A: deterministic stub — no auto-merge."""
    return {
        "status": "draft_prepared",
        "branch": context.get("branch", "draft-branch"),
        "auto_merge": False,  # no auto-merge, ever
        "source": "github.pr.prepare (deterministic stub)",
    }


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


class DeterministicExecutor:
    """Executes deterministic nodes from the registered operation pool."""

    def execute(
        self,
        run: WorkflowRun,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if node.type != NodeType.DETERMINISTIC:
            raise TypeError(f"DeterministicExecutor called on non-deterministic node {node.id}")
        if not node.action:
            raise ValueError(f"Deterministic node {node.id} has no action")
        op = get_operation(node.action)
        if op is None:
            raise KeyError(f"No registered operation for action {node.action!r}")
        return op(run, node, context)


class AgentNodeExecutor:
    """AgentNode: calls a governed provider with scoped context.

    Phase 5A: returns a structured output via the provider abstraction.
    The provider is selected by the workflow's provider_class routing.
    """

    def __init__(self, provider_factory: Callable[[str, str], Any] | None = None):
        self._provider_factory = provider_factory

    def build_context_package(
        self,
        run: WorkflowRun,
        node: WorkflowNode,
    ) -> ContextPackage:
        """Build a scoped context package for an agent node.

        Minimum necessary context only — never dump OmniBrain.
        """
        relevant_artifacts = []
        for dep_id in node.depends_on:
            node_run = run.node_runs.get(dep_id)
            if node_run and node_run.output:
                relevant_artifacts.append(
                    {
                        "from_node": dep_id,
                        "output": node_run.output,
                    }
                )
        return ContextPackage(
            run_id=run.run_id,
            agent_role=node.role or "unknown",
            task=node.metadata.get("objective", ""),
            artifacts=relevant_artifacts,
            constraints=run.context.get("constraints", []),
            permissions=run.context.get("permissions", []),
            provenance=[
                f"run:{run.run_id}",
                f"workflow:{run.workflow_name}@{run.workflow_version}",
            ],
        )

    def execute(
        self,
        run: WorkflowRun,
        node: WorkflowNode,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if node.type != NodeType.AGENT:
            raise TypeError(f"AgentNodeExecutor called on non-agent node {node.id}")
        pkg = self.build_context_package(run, node)
        provider_class = node.provider_class or "balanced"
        # Phase 5A: call the provider factory if available, otherwise
        # return a deterministic stub that proves the contract.
        if self._provider_factory:
            provider = self._provider_factory(provider_class, pkg.agent_role)
            return provider.invoke(pkg)
        return {
            "agent_role": pkg.agent_role,
            "provider_class": provider_class,
            "context_keys": list(pkg.artifacts[0].keys()) if pkg.artifacts else [],
            "output": {"status": "agent_completed", "role": pkg.agent_role},
            "fresh_context": node.fresh_context,
        }


class ApprovalNodeExecutor:
    """ApprovalNode: pauses until Principal decision.

    Phase 5A: returns WAITING_APPROVAL; the runner persists the pause.
    """

    def check(self, node: WorkflowNode, run: WorkflowRun) -> dict[str, Any]:
        return {
            "required_when": node.required_when,
            "status": "WAITING_APPROVAL",
            "principal_id": run.principal_id,
        }
