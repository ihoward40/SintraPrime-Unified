"""Workflow state machine — governed transitions.

Defines the legal state transitions for workflows and nodes.
Every transition is deterministic and auditable.
"""

from __future__ import annotations

from .models import NodeStatus, WorkflowRun, WorkflowStatus

# Legal workflow-level transitions: (from, to) pairs.
_WORKFLOW_TRANSITIONS: set[tuple[str, str]] = {
    # Lifecycle
    (WorkflowStatus.PENDING, WorkflowStatus.READY),
    (WorkflowStatus.PENDING, WorkflowStatus.RUNNING),
    (WorkflowStatus.READY, WorkflowStatus.RUNNING),
    (WorkflowStatus.RUNNING, WorkflowStatus.SUCCEEDED),
    (WorkflowStatus.RUNNING, WorkflowStatus.FAILED),
    (WorkflowStatus.RUNNING, WorkflowStatus.BLOCKED),
    (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED),
    (WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED),
    # From paused
    (WorkflowStatus.PAUSED, WorkflowStatus.RUNNING),
    (WorkflowStatus.PAUSED, WorkflowStatus.CANCELLED),
    # Approval
    (WorkflowStatus.RUNNING, WorkflowStatus.WAITING_APPROVAL),
    (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.RUNNING),
    (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.CANCELLED),
    # Human input
    (WorkflowStatus.RUNNING, WorkflowStatus.WAITING_INPUT),
    (WorkflowStatus.WAITING_INPUT, WorkflowStatus.RUNNING),
    (WorkflowStatus.WAITING_INPUT, WorkflowStatus.CANCELLED),
    # Blocked
    (WorkflowStatus.BLOCKED, WorkflowStatus.RUNNING),
    (WorkflowStatus.BLOCKED, WorkflowStatus.CANCELLED),
    # Terminal → superseded only
    (WorkflowStatus.SUCCEEDED, WorkflowStatus.SUPERSEDED),
    (WorkflowStatus.FAILED, WorkflowStatus.SUPERSEDED),
}

# Legal node-level transitions.
_NODE_TRANSITIONS: set[tuple[str, str]] = {
    (NodeStatus.PENDING, NodeStatus.READY),
    (NodeStatus.PENDING, NodeStatus.RUNNING),
    (NodeStatus.READY, NodeStatus.RUNNING),
    (NodeStatus.RUNNING, NodeStatus.SUCCEEDED),
    (NodeStatus.RUNNING, NodeStatus.FAILED),
    (NodeStatus.RUNNING, NodeStatus.WAITING_APPROVAL),
    (NodeStatus.RUNNING, NodeStatus.WAITING_INPUT),
    (NodeStatus.RUNNING, NodeStatus.BLOCKED),
    (NodeStatus.RUNNING, NodeStatus.CANCELLED),
    (NodeStatus.WAITING_APPROVAL, NodeStatus.RUNNING),
    (NodeStatus.WAITING_APPROVAL, NodeStatus.CANCELLED),
    (NodeStatus.WAITING_INPUT, NodeStatus.RUNNING),
    (NodeStatus.WAITING_INPUT, NodeStatus.CANCELLED),
    (NodeStatus.BLOCKED, NodeStatus.RUNNING),
    (NodeStatus.BLOCKED, NodeStatus.CANCELLED),
    (NodeStatus.PENDING, NodeStatus.CANCELLED),  # skip
    (NodeStatus.READY, NodeStatus.CANCELLED),  # skip
}


class StateError(Exception):
    """Raised when an illegal state transition is attempted."""


class WorkflowStateMachine:
    """Enforces governed state transitions for a WorkflowRun."""

    @staticmethod
    def transition_workflow(run: WorkflowRun, new_status: WorkflowStatus) -> WorkflowStatus:
        current = run.status
        if (current, new_status) not in _WORKFLOW_TRANSITIONS:
            raise StateError(f"Illegal workflow transition: {current} → {new_status}")
        run.status = new_status
        return new_status

    @staticmethod
    def transition_node(run: WorkflowRun, node_id: str, new_status: NodeStatus) -> NodeStatus:
        node_run = run.node_runs.get(node_id)
        if node_run is None:
            raise StateError(f"Node run {node_id!r} not found in workflow run")
        current = node_run.status
        if (current, new_status) not in _NODE_TRANSITIONS:
            raise StateError(f"Illegal node transition {node_id}: {current} → {new_status}")
        node_run.status = new_status
        return new_status

    @staticmethod
    def is_terminal(workflow_status: WorkflowStatus) -> bool:
        return workflow_status in {
            WorkflowStatus.SUCCEEDED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.SUPERSEDED,
        }

    @staticmethod
    def is_node_terminal(node_status: NodeStatus) -> bool:
        return node_status in {
            NodeStatus.SUCCEEDED,
            NodeStatus.FAILED,
            NodeStatus.CANCELLED,
            NodeStatus.BLOCKED,
        }
