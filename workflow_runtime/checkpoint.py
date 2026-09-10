"""Checkpoint store — disk-persisted workflow state.

A workflow resumes only from a valid checkpoint. The checkpoint store
writes a JSON snapshot after every material node transition.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import (
    NodeStatus,
    WorkflowCheckpoint,
    WorkflowNodeRun,
    WorkflowRun,
    WorkflowStatus,
    sha256_json,
    utcnow_iso,
)


class CheckpointStore:
    """Disk-backed checkpoint store for workflow runs."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        d = self.base_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_run(self, run: WorkflowRun) -> Path:
        """Persist the full run state. Returns the state file path."""
        path = self._run_dir(run.run_id) / "execution_state.json"
        path.write_text(
            json.dumps(self._serialize_run(run), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_run(self, run_id: str) -> WorkflowRun | None:
        path = self.base_dir / run_id / "execution_state.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._deserialize_run(data)

    def write_checkpoint(
        self,
        run: WorkflowRun,
        node_id: str,
        budget_used: dict[str, Any],
    ) -> WorkflowCheckpoint:
        """Write an immutable checkpoint after a node completes."""
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            run_id=run.run_id,
            node_id=node_id,
            status=run.status,
            node_statuses={nid: n.status for nid, n in run.node_runs.items()},
            budget_used=budget_used,
            artifacts=run.artifacts,
            snapshot_hash=sha256_json(self._serialize_run(run)),
            created_at=utcnow_iso(),
        )
        path = self._run_dir(run.run_id) / f"checkpoint_{node_id}.json"
        path.write_text(
            json.dumps(asdict(checkpoint), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return checkpoint

    def list_checkpoints(self, run_id: str) -> list[Path]:
        return sorted(self._run_dir(run_id).glob("checkpoint_*.json"))

    def verify_checkpoint(self, run_id: str, node_id: str) -> tuple[bool, str]:
        """Verify a checkpoint's snapshot hash against current state."""
        path = self.base_dir / run_id / f"checkpoint_{node_id}.json"
        if not path.exists():
            return False, "checkpoint not found"
        cp = json.loads(path.read_text(encoding="utf-8"))
        current_state = self.load_run(run_id)
        if current_state is None:
            return False, "no current execution state"
        expected = sha256_json(self._serialize_run(current_state))
        if cp["snapshot_hash"] == expected:
            return True, "checkpoint valid"
        return False, "snapshot hash mismatch"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_run(self, run: WorkflowRun) -> dict[str, Any]:
        return {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "workflow_version": run.workflow_version,
            "workflow_hash": run.workflow_hash,
            "tenant_id": run.tenant_id,
            "principal_id": run.principal_id,
            "status": str(run.status),
            "current_node_id": run.current_node_id,
            "node_runs": {
                nid: {
                    "node_id": n.node_id,
                    "node_type": str(n.node_type),
                    "status": str(n.status),
                    "attempt": n.attempt,
                    "output": n.output,
                    "error": n.error,
                    "started_at": n.started_at,
                    "completed_at": n.completed_at,
                    "receipt_hash": n.receipt_hash,
                }
                for nid, n in run.node_runs.items()
            },
            "budget": {
                "tokens_used": run.budget.tokens_used if run.budget else 0,
                "provider_cost_used": run.budget.provider_cost_used if run.budget else 0.0,
                "wall_time_used_seconds": run.budget.wall_time_used_seconds if run.budget else 0.0,
                "agent_calls_used": run.budget.agent_calls_used if run.budget else 0,
                "max_tokens": run.budget.max_tokens if run.budget else 500_000,
                "max_provider_cost": run.budget.max_provider_cost if run.budget else 10.0,
                "max_wall_time_seconds": run.budget.max_wall_time_seconds if run.budget else 3600,
                "max_agent_calls": run.budget.max_agent_calls if run.budget else 20,
            },
            "context": run.context,
            "artifacts": run.artifacts,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "completed_at": run.completed_at,
            "error": run.error,
            "cancellation_reason": run.cancellation_reason,
        }

    def _deserialize_run(self, data: dict[str, Any]) -> WorkflowRun:
        node_runs = {
            nid: WorkflowNodeRun(
                node_id=n["node_id"],
                node_type=n["node_type"],
                status=NodeStatus(n["status"]),
                attempt=n["attempt"],
                output=n["output"],
                error=n["error"],
                started_at=n["started_at"],
                completed_at=n["completed_at"],
                receipt_hash=n["receipt_hash"],
            )
            for nid, n in data.get("node_runs", {}).items()
        }
        budget = data.get("budget", {})
        from .models import WorkflowBudget

        wb = WorkflowBudget(
            max_tokens=budget.get("max_tokens", 500_000),
            max_provider_cost=budget.get("max_provider_cost", 10.0),
            max_wall_time_seconds=budget.get("max_wall_time_seconds", 3600),
            max_agent_calls=budget.get("max_agent_calls", 20),
            tokens_used=budget.get("tokens_used", 0),
            provider_cost_used=budget.get("provider_cost_used", 0.0),
            wall_time_used_seconds=budget.get("wall_time_used_seconds", 0.0),
            agent_calls_used=budget.get("agent_calls_used", 0),
        )
        return WorkflowRun(
            run_id=data["run_id"],
            workflow_name=data["workflow_name"],
            workflow_version=data["workflow_version"],
            workflow_hash=data["workflow_hash"],
            tenant_id=data["tenant_id"],
            principal_id=data["principal_id"],
            status=WorkflowStatus(data["status"]),
            current_node_id=data.get("current_node_id"),
            node_runs=node_runs,
            budget=wb,
            context=data.get("context", {}),
            artifacts=data.get("artifacts", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
            cancellation_reason=data.get("cancellation_reason"),
        )
