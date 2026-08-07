"""Failure, retry, partial, blocked, and cancellation policy."""

from __future__ import annotations

from .schemas import NodeStatus, RunStatus


def node_status_after_failure(retry_count: int, max_retries: int) -> NodeStatus:
    return NodeStatus.READY if retry_count < max_retries else NodeStatus.FAILED


def run_status_for_limit(hard_limit_reached: bool, completed_nodes: int) -> RunStatus:
    if not hard_limit_reached:
        return RunStatus.RUNNING
    return RunStatus.PARTIAL if completed_nodes else RunStatus.BLOCKED


def cancellation_status(cancel_requested: bool) -> RunStatus | None:
    return RunStatus.CANCELLED if cancel_requested else None
