"""Run-bound Principal approval and activation routes.

POST /api/v1/mission-control/runs/{run_id}/approval  — Principal decision
POST /api/v1/mission-control/runs/{run_id}/activate   — consume approval, activate
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, get_current_user
from ..database import get_db
from ..services.durable_orchestration_authority import DurableOrchestrationAuthority
from ..services.mission_control_approval_service import (
    ApprovalError,
    ApprovalNotConsumableError,
    CapabilityNotEligibleError,
    DuplicateApprovalError,
    InputHashMismatchError,
    NotPrincipalError,
    RunNotFoundError,
    RunNotApprovalRequiredError,
    consume_approval_and_activate,
    create_approval,
)
from ..services.orchestration_runtime import get_canonical_durable_engine

router = APIRouter(prefix="/api/v1/mission-control", tags=["mission-control"])


class ApprovalRequest(BaseModel):
    """Client supplies only the Principal's decision and optional rationale."""
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reason_code: str | None = Field(default=None, max_length=80)


class ApprovalResponse(BaseModel):
    approval_id: str
    tenant_id: str
    principal_user_id: str
    run_id: str
    decision: str
    status: str
    input_data_hash: str
    mission_id: str | None
    reason_code: str | None
    created_at: datetime
    consumed_at: datetime | None
    execution_ref: str | None


class ActivationResponse(BaseModel):
    run_id: str
    mission_id: str
    status: str
    execution_ref: str | None
    workflow_type: str
    input_data_hash: str | None


@router.post(
    "/runs/{run_id}/approval",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_approval(
    run_id: str,
    body: ApprovalRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Create a run-bound Principal approval artifact.

    The client supplies only the decision (APPROVED or REJECTED) and optional
    rationale.  All authoritative facts (tenant_id, principal_user_id, mission_id,
    input_data_hash) are reloaded server-side.
    """
    authority = DurableOrchestrationAuthority(
        engine=get_canonical_durable_engine()
    )
    try:
        approval = await create_approval(
            db,
            run_id=run_id,
            tenant_id=str(current_user.tenant_id),
            actor=current_user,
            decision=body.decision,
            reason_code=body.reason_code,
            authority=authority,
        )
    except NotPrincipalError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason_code": "NOT_TENANT_PRINCIPAL"},
        )
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason_code": "RUN_NOT_FOUND"},
        )
    except RunNotApprovalRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason_code": str(exc)},
        )
    except DuplicateApprovalError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason_code": "APPROVAL_ALREADY_EXISTS"},
        )
    except CapabilityNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason_code": str(exc)},
        )
    except ApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"reason_code": str(exc)},
        )

    return ApprovalResponse(
        approval_id=approval.approval_id,
        tenant_id=approval.tenant_id,
        principal_user_id=approval.principal_user_id,
        run_id=approval.run_id,
        decision=approval.decision,
        status=approval.status,
        input_data_hash=approval.input_data_hash,
        mission_id=approval.mission_id,
        reason_code=approval.reason_code,
        created_at=approval.created_at,
        consumed_at=approval.consumed_at,
        execution_ref=approval.execution_ref,
    )


@router.post(
    "/runs/{run_id}/activate",
    response_model=ActivationResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActivationResponse:
    """Consume an approved Principal artifact and activate the SAME Run.

    This is a mechanical activation route — it does not constitute a second
    Principal approval.  It consumes the existing durable approval artifact.
    """
    authority = DurableOrchestrationAuthority(
        engine=get_canonical_durable_engine()
    )
    try:
        run = await consume_approval_and_activate(
            db,
            run_id=run_id,
            tenant_id=str(current_user.tenant_id),
            actor=current_user,
            authority=authority,
        )
    except NotPrincipalError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason_code": "NOT_TENANT_PRINCIPAL"},
        )
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason_code": "RUN_NOT_FOUND"},
        )
    except RunNotApprovalRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason_code": str(exc)},
        )
    except ApprovalNotConsumableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason_code": str(exc)},
        )
    except InputHashMismatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason_code": "INPUT_HASH_MISMATCH"},
        )
    except CapabilityNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason_code": str(exc)},
        )
    except ApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"reason_code": str(exc)},
        )

    return ActivationResponse(
        run_id=run.run_id,
        mission_id=run.mission_id,
        status=run.status,
        execution_ref=run.execution_ref,
        workflow_type=run.workflow_type,
        input_data_hash=run.input_data_hash,
    )