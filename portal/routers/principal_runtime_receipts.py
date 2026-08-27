"""Principal-only runtime evidence receipt endpoint.

IKE-Bot uses this endpoint instead of maintaining a parallel evidence ledger.
Each receipt is appended to the existing tenant-scoped SHA-256 audit chain.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..services.audit_service import audit

router = APIRouter(prefix="/api/v1/principal", tags=["principal-runtime"])


class RuntimeReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(min_length=1, max_length=128)
    mission_id: str = Field(min_length=1, max_length=128)
    causation_id: str = Field(min_length=1, max_length=128)
    capability: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=512)
    actor_agent_id: str = Field(min_length=1, max_length=128)
    timestamp: str = Field(min_length=1, max_length=128)
    input_hash: str | None = Field(default=None, max_length=128)
    output_hash: str | None = Field(default=None, max_length=128)
    approval_id: str | None = Field(default=None, max_length=128)
    side_effect_reference: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeReceiptResponse(BaseModel):
    receipt_id: str
    audit_log_id: str
    evidence_hash: str
    previous_evidence_hash: str | None = None


@router.post(
    "/runtime-receipts",
    response_model=RuntimeReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def write_runtime_receipt(
    body: RuntimeReceiptRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RuntimeReceiptResponse:
    entry = await audit(
        db,
        action="ike_runtime_receipt",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="ike_runtime_mission",
        resource_id=body.mission_id,
        resource_name=body.action,
        status="success",
        details={
            "receipt_id": body.receipt_id,
            "mission_id": body.mission_id,
            "causation_id": body.causation_id,
            "capability": body.capability,
            "actor_agent_id": body.actor_agent_id,
            "timestamp": body.timestamp,
            "input_hash": body.input_hash,
            "output_hash": body.output_hash,
            "approval_id": body.approval_id,
            "side_effect_reference": body.side_effect_reference,
            "metadata": body.metadata,
        },
    )
    return RuntimeReceiptResponse(
        receipt_id=body.receipt_id,
        audit_log_id=str(entry.id),
        evidence_hash=entry.entry_hash,
        previous_evidence_hash=entry.previous_hash,
    )
