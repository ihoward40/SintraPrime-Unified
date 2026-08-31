"""Run-bound Principal approval service.

Connects constitutional Principal authority (TenantPrincipal) to one
already-created immutable Run.  This service owns:
  - approval artifact creation (Principal decision)
  - approval artifact consumption (activation)
  - rejection (Run cancellation)

Constitutional rules enforced:
  - APPROVAL_BOUND_TO = RUN (not action hash)
  - Principal authority via TenantPrincipal only, never RBAC inference
  - Explicit Principal decision required
  - Exactly-once consumption via atomic status transition
  - Run immutability (input_data_hash re-validated)
  - No second Run created on activation
  - ACTIVATING before ACTIVE; execution_ref required for ACTIVE
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser
from ..models.mission_control_execution import Mission, Run
from ..models.mission_control_run_approval import RunApproval
from .audit_service import audit
from .durable_orchestration_authority import DurableOrchestrationAuthority
from .mission_control_capability_policy import CapabilityDecision, resolve_capability_policy
from .mission_control_execution_binding import resolve_mission_capability
from .tenant_principal_service import is_tenant_principal


class ApprovalError(Exception):
    """Base approval service error."""


class NotPrincipalError(ApprovalError):
    """Actor is not the constitutional Principal for this tenant."""


class RunNotApprovalRequiredError(ApprovalError):
    """Run is not in APPROVAL_REQUIRED state."""


class RunNotFoundError(ApprovalError):
    """Run does not exist in this tenant."""


class DuplicateApprovalError(ApprovalError):
    """An approval artifact already exists for this Run."""


class InputHashMismatchError(ApprovalError):
    """Run input_data_hash does not match the approval artifact."""


class ApprovalNotConsumableError(ApprovalError):
    """Approval artifact is not in PENDING/APPROVED state for consumption."""


class CapabilityNotEligibleError(ApprovalError):
    """Server capability is not eligible for activation."""


async def create_approval(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    actor: CurrentUser,
    decision: str,
    reason_code: str | None = None,
    authority: DurableOrchestrationAuthority | None = None,
) -> RunApproval:
    """Create a run-bound Principal approval artifact.

    Pre-conditions (all checked fail-closed):
      1. Actor is verified TenantPrincipal for this tenant
      2. Run exists and is tenant-scoped
      3. Run.status == APPROVAL_REQUIRED
      4. Run.execution_ref is NULL (not yet dispatched)
      5. Server capability still exists and remains approval-required

    The client supplies only the decision and optional rationale.
    Server reloads all authoritative facts (tenant_id, principal_user_id,
    mission_id, input_data_hash).
    """
    # 1. Verify constitutional Principal authority
    is_principal = await is_tenant_principal(
        db, authenticated_user_id=str(actor.user_id), tenant_id=tenant_id
    )
    if not is_principal:
        raise NotPrincipalError("NOT_TENANT_PRINCIPAL")

    # 2. Load tenant-scoped Run
    authority = authority or DurableOrchestrationAuthority()
    run = await authority.get_run(db, run_id=run_id, tenant_id=tenant_id)
    if run is None:
        raise RunNotFoundError("RUN_NOT_FOUND")

    # 3. Run must be APPROVAL_REQUIRED
    if run.status != "APPROVAL_REQUIRED":
        raise RunNotApprovalRequiredError("RUN_NOT_APPROVAL_REQUIRED")

    # 4. execution_ref must be NULL (not yet dispatched)
    if run.execution_ref is not None:
        raise RunNotApprovalRequiredError("RUN_ALREADY_DISPATCHED")

    # 5. Server capability still exists and remains approval-required
    capability = await resolve_mission_capability(
        db, mission_id=run.mission_id, tenant_id=tenant_id
    )
    policy = resolve_capability_policy(authority.engine, capability=capability)
    if policy != CapabilityDecision.APPROVAL_REQUIRED:
        raise CapabilityNotEligibleError("CAPABILITY_NOT_APPROVAL_REQUIRED")

    # Validate decision vocabulary
    if decision not in ("APPROVED", "REJECTED"):
        raise ApprovalError("INVALID_DECISION")

    # Check for existing approval before attempting insert
    existing_result = await db.execute(
        select(RunApproval).where(
            RunApproval.tenant_id == tenant_id,
            RunApproval.run_id == run_id,
        )
    )
    prior = existing_result.scalar_one_or_none()
    if prior is not None:
        raise DuplicateApprovalError("APPROVAL_ALREADY_EXISTS")

    # Create approval artifact — server supplies all authoritative fields
    approval = RunApproval(
        approval_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        principal_user_id=str(actor.user_id),
        run_id=run_id,
        decision=decision,
        status="PENDING" if decision == "APPROVED" else "REJECTED",
        input_data_hash=run.input_data_hash,
        mission_id=run.mission_id,
        reason_code=reason_code,
    )

    db.add(approval)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        # Race: another request inserted between our check and insert
        existing_after = await db.execute(
            select(RunApproval).where(
                RunApproval.tenant_id == tenant_id,
                RunApproval.run_id == run_id,
            )
        )
        prior_after = existing_after.scalar_one_or_none()
        if prior_after is not None:
            raise DuplicateApprovalError("APPROVAL_ALREADY_EXISTS") from exc
        raise

    # Audit evidence
    await audit(
        db,
        action="mission_control_approval_created",
        user_id=actor.user_id,
        tenant_id=tenant_id,
        resource_type="run_approval",
        resource_id=approval.approval_id,
        resource_name=decision,
        status="approved" if decision == "APPROVED" else "rejected",
        details={
            "approval_id": approval.approval_id,
            "run_id": run_id,
            "mission_id": run.mission_id,
            "decision": decision,
            "input_data_hash": run.input_data_hash,
            "principal_user_id": str(actor.user_id),
        },
    )

    # If rejected, cancel the Run immediately
    if decision == "REJECTED":
        await authority.reject_run(db, run_id=run_id, tenant_id=tenant_id)
        approval.status = "REJECTED"
        await db.flush()

    return approval


async def consume_approval_and_activate(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    actor: CurrentUser,
    authority: DurableOrchestrationAuthority | None = None,
) -> Run:
    """Consume an approved Principal artifact and activate the SAME Run.

    Steps:
      1. Load PENDING + APPROVED approval artifact
      2. Re-validate Run is still APPROVAL_REQUIRED
      3. Re-validate input_data_hash
      4. Re-validate capability eligibility
      5. Atomically transition approval PENDING → CONSUMED
      6. Dispatch via authority.activate_run (ACTIVATING → ACTIVE)
      7. Record execution_ref on approval artifact

    Concurrent activation requests are serialized by the UNIQUE(tenant_id, run_id)
    constraint and the atomic PENDING → CONSUMED transition.
    """
    authority = authority or DurableOrchestrationAuthority()

    # 1. Load approval artifact
    result = await db.execute(
        select(RunApproval).where(
            RunApproval.tenant_id == tenant_id,
            RunApproval.run_id == run_id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise ApprovalError("APPROVAL_NOT_FOUND")
    if approval.status != "PENDING":
        raise ApprovalNotConsumableError(f"APPROVAL_ALREADY_{approval.status}")
    if approval.decision != "APPROVED":
        raise ApprovalNotConsumableError("APPROVAL_NOT_APPROVED")

    # 2. Load Run and re-validate
    run = await authority.get_run(db, run_id=run_id, tenant_id=tenant_id)
    if run is None:
        raise RunNotFoundError("RUN_NOT_FOUND")
    if run.status != "APPROVAL_REQUIRED":
        raise RunNotApprovalRequiredError(f"RUN_STATUS_{run.status}")

    # 3. Re-validate input_data_hash
    if run.input_data_hash != approval.input_data_hash:
        raise InputHashMismatchError("INPUT_HASH_MISMATCH")

    # 4. Re-validate capability eligibility
    capability = await resolve_mission_capability(
        db, mission_id=run.mission_id, tenant_id=tenant_id
    )
    policy = resolve_capability_policy(authority.engine, capability=capability)
    if policy != CapabilityDecision.APPROVAL_REQUIRED:
        raise CapabilityNotEligibleError("CAPABILITY_NOT_APPROVAL_REQUIRED")

    # Verify Run's workflow_type matches the server-bound capability
    if run.workflow_type != capability:
        raise CapabilityNotEligibleError("RUN_WORKFLOW_TYPE_MISMATCH")

    # 5. Atomically transition approval PENDING → CONSUMED
    approval.status = "CONSUMED"
    approval.consumed_at = datetime.now(UTC)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ApprovalNotConsumableError("APPROVAL_CONSUMPTION_RACE_LOST") from exc

    # 6. Dispatch the SAME Run (no new Run)
    run = await authority.activate_run(db, run_id=run_id, tenant_id=tenant_id)

    # 7. Record execution_ref on approval artifact
    approval.execution_ref = run.execution_ref
    await db.flush()

    # Audit evidence
    await audit(
        db,
        action="mission_control_run_activated",
        user_id=actor.user_id,
        tenant_id=tenant_id,
        resource_type="run",
        resource_id=run_id,
        resource_name="activate",
        status="active",
        details={
            "approval_id": approval.approval_id,
            "run_id": run_id,
            "mission_id": run.mission_id,
            "execution_ref": run.execution_ref,
            "input_data_hash": run.input_data_hash,
        },
    )

    return run