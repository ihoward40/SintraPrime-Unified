"""Governed Mission Control adapter over the existing durable workflow engine."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestration.durable_execution import DurableWorkflowEngine

from ..models.mission_control_execution import Mission, Run
from .mission_control_capability_policy import CapabilityDecision
from .orchestration_runtime import get_canonical_durable_engine


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _compute_input_hash(input_data: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(input_data).encode("utf-8")).hexdigest()


class DurableDispatchError(RuntimeError):
    """Dispatch failed after a governed Run identity was persisted."""

    def __init__(self, run_id: str, cause: Exception) -> None:
        super().__init__(str(cause))
        self.run_id = run_id


class MissingPrincipalApprovalArtifactError(RuntimeError):
    """approve_and_start cannot be invoked without a verified Principal approval artifact."""

    def __init__(self) -> None:
        super().__init__("PRINCIPAL_APPROVAL_ARTIFACT_REQUIRED")


class DurableOrchestrationAuthority:
    """Owns Mission/Run governance; delegates execution to DurableWorkflowEngine."""

    def __init__(self, engine: DurableWorkflowEngine | None = None) -> None:
        self.engine = engine or get_canonical_durable_engine()

    async def create_mission(self, db: AsyncSession, *, tenant_id: str, created_by: str) -> Mission:
        mission = Mission(tenant_id=tenant_id, created_by=created_by)
        db.add(mission)
        await db.flush()
        return mission

    async def get_mission(self, db: AsyncSession, *, mission_id: str, tenant_id: str) -> Mission | None:
        return await self._mission(db, mission_id, tenant_id)

    async def get_run(self, db: AsyncSession, *, run_id: str, tenant_id: str) -> Run | None:
        return await self._run(db, run_id, tenant_id)

    async def start_run(
        self,
        db: AsyncSession,
        *,
        mission_id: str,
        tenant_id: str,
        created_by: str,
        workflow_type: str,
        input_data: dict[str, Any],
        policy_decision: CapabilityDecision,
        preallocated_workflow_id: str | None = None,
    ) -> Run:
        mission = await self._mission(db, mission_id, tenant_id)
        if mission is None:
            raise ValueError("MISSION_NOT_FOUND")
        if mission.status != "ACTIVE":
            raise ValueError("MISSION_INVALID_STATE")

        canonical_input = dict(input_data) if isinstance(input_data, dict) else {}
        run = Run(
            mission_id=mission.mission_id,
            tenant_id=tenant_id,
            created_by=created_by,
            workflow_type=workflow_type,
            input_data=canonical_input,
            input_data_hash=_compute_input_hash(canonical_input),
            status="APPROVAL_REQUIRED" if policy_decision == CapabilityDecision.APPROVAL_REQUIRED else "PENDING",
        )
        # Store preallocated workflow ID in execution_ref if provided so
        # activation can reuse the same durable engine workflow identity.
        if preallocated_workflow_id:
            run.execution_ref = preallocated_workflow_id
        db.add(run)
        await db.flush()
        if policy_decision == CapabilityDecision.APPROVAL_REQUIRED:
            return run

        return await self._dispatch_run(db, run, canonical_input)

    async def _dispatch_run(self, db: AsyncSession, run: Run, input_data: dict[str, Any]) -> Run:
        # If execution_ref already holds a preallocated workflow_id, reuse it
        # so the durable engine's request-replay semantics prevent duplicates.
        preallocated_wid = run.execution_ref
        try:
            workflow_id = await self.engine.start_workflow(
                run.workflow_type,
                input_data,
                metadata={"mission_id": run.mission_id, "run_id": run.run_id},
                workflow_id=preallocated_wid,
            )
        except ValueError as exc:
            run.status = "FAILED"
            run.failure_reason = str(exc)
            await db.flush()
            if str(exc).startswith("Unknown workflow type:"):
                raise
            raise DurableDispatchError(run.run_id, exc) from exc
        except Exception as exc:
            run.status = "FAILED"
            run.failure_reason = str(exc)
            await db.flush()
            raise DurableDispatchError(run.run_id, exc) from exc

        run.execution_ref = workflow_id
        run.status = "ACTIVE"
        await db.flush()
        return run

    async def approve_and_start(
        self,
        db: AsyncSession,
        *,
        run_id: str,
        tenant_id: str,
        input_data: dict[str, Any],
        principal_approval_artifact: dict[str, Any] | None = None,
    ) -> Run:
        """Fail closed unless a verified Principal approval artifact is supplied.

        There is currently no existing Principal approval authority that can produce
        a run-bound artifact, so the default production path is blocked.
        """
        if not principal_approval_artifact:
            raise MissingPrincipalApprovalArtifactError()
        run = await self._run(db, run_id, tenant_id)
        if run is None:
            raise ValueError("RUN_NOT_FOUND")
        if run.status != "APPROVAL_REQUIRED":
            raise ValueError("RUN_NOT_APPROVAL_REQUIRED")
        canonical_input = dict(input_data) if isinstance(input_data, dict) else {}
        if _compute_input_hash(canonical_input) != run.input_data_hash:
            raise ValueError("INPUT_HASH_MISMATCH")
        return await self._dispatch_run(db, run, canonical_input)

    async def activate_run(
        self,
        db: AsyncSession,
        *,
        run_id: str,
        tenant_id: str,
    ) -> Run:
        """Consume an approved Principal artifact and dispatch the SAME Run.

        Pre-conditions checked by the caller (approval service):
          - approval artifact exists and is APPROVED + PENDING
          - actor is verified TenantPrincipal
          - Run is APPROVAL_REQUIRED
          - input_data_hash matches

        This method performs the atomic activation:
          1. Mark Run as ACTIVATING (no execution_ref yet → truthful)
          2. Dispatch to durable engine using preallocated workflow_id
          3. On success: store execution_ref, mark Run ACTIVE
          4. On failure: mark Run FAILED

        The caller is responsible for consuming the approval artifact
        (PENDING → CONSUMED) after this method succeeds.
        """
        run = await self._run(db, run_id, tenant_id)
        if run is None:
            raise ValueError("RUN_NOT_FOUND")
        if run.status != "APPROVAL_REQUIRED":
            raise ValueError("RUN_NOT_APPROVAL_REQUIRED")

        # Transition to ACTIVATING — truthful: not yet dispatched
        run.status = "ACTIVATING"
        await db.flush()

        canonical_input = dict(run.input_data) if isinstance(run.input_data, dict) else {}
        return await self._dispatch_run(db, run, canonical_input)

    async def reject_run(
        self,
        db: AsyncSession,
        *,
        run_id: str,
        tenant_id: str,
    ) -> Run:
        """Cancel a Run that has been rejected by the Principal.

        Sets Run.status = CANCELLED with failure_reason = PRINCIPAL_REJECTED.
        No durable engine dispatch occurs.
        """
        run = await self._run(db, run_id, tenant_id)
        if run is None:
            raise ValueError("RUN_NOT_FOUND")
        if run.status != "APPROVAL_REQUIRED":
            raise ValueError("RUN_NOT_APPROVAL_REQUIRED")
        run.status = "CANCELLED"
        run.failure_reason = "PRINCIPAL_REJECTED"
        await db.flush()
        return run

    async def cancel_run(self, db: AsyncSession, *, run_id: str, tenant_id: str) -> bool:
        run = await self._run(db, run_id, tenant_id)
        if run is None:
            raise ValueError("RUN_NOT_FOUND")
        if not run.execution_ref:
            if run.status in {"PENDING", "APPROVAL_REQUIRED"}:
                run.status = "CANCELLED"
                await db.flush()
                return True
            run.status = "FAILED"
            run.failure_reason = "EXECUTION_REF_REQUIRED"
            await db.flush()
            return False
        cancelled = await self.engine.cancel_workflow(run.execution_ref)
        if not cancelled:
            run.status = "FAILED"
            run.failure_reason = "DURABLE_WORKFLOW_NOT_FOUND"
            await db.flush()
            return False
        run.status = "CANCELLED"
        await db.flush()
        return True

    @staticmethod
    async def _mission(db: AsyncSession, mission_id: str, tenant_id: str) -> Mission | None:
        result = await db.execute(select(Mission).where(Mission.mission_id == mission_id, Mission.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def _run(db: AsyncSession, run_id: str, tenant_id: str) -> Run | None:
        result = await db.execute(select(Run).where(Run.run_id == run_id, Run.tenant_id == tenant_id))
        return result.scalar_one_or_none()
