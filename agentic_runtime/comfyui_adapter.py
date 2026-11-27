"""Governed ComfyUI HTTP adapter.

The transport is injected so this module can be tested without network access
and cannot bypass MediaWorkflowPolicy.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .media_workflows import MediaJob, MediaWorkflowPolicy


class GovernedComfyUIAdapter:
    def __init__(self, policy: MediaWorkflowPolicy, submit: Callable[[dict[str, Any]], dict[str, Any]]):
        self.policy = policy
        self.submit = submit

    def run(self, job: MediaJob) -> dict[str, Any]:
        admitted, reason = self.policy.admit(job)
        if not admitted:
            raise PermissionError(reason)
        payload = {
            "workflow_id": job.workflow_id,
            "kind": job.kind.value,
            "inputs": dict(job.inputs),
            "output_paths": list(job.output_paths),
        }
        return self.submit(payload)
