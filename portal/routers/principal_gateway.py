"""Principal-only gateway for governed IKE runtime integration.

This router is deliberately narrow:
- authenticates the Principal through the existing JWT/RBAC boundary;
- provisions durable, non-secret, mission-scoped service identity descriptors;
- exposes bounded living-file retrieval;
- bridges to the canonical durable orchestration authority;
- commits one acceptance-only side effect after an orchestration approval;
- writes all material actions into the canonical hash-chained audit ledger.

Mission lifecycle state is persisted through the same durable orchestration authority
used by the activated Mission Control START/CANCEL command path. External computer,
email, filing, payment, and publication actions remain disabled.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.correlation import get_current_context
from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..services.audit_service import audit
from ..services.durable_orchestration_authority import (
    DurableOrchestrationStateError,
    approve_durable_run,
    cancel_durable_run,
    get_durable_run,
    start_durable_run,
)
from ..services.governed_identity import (
    DuplicateServiceIdentityConflictError,
    GovernedIdentity,
    identity_service,
)
from ..services.orchestration.budget_policy import BudgetLimits
from ..services.orchestration.schemas import ExecutionMode

router = APIRouter(prefix="/api/v1/principal", tags=["principal-runtime"])

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWED_LIVING_ROOTS = tuple(
    (_REPO_ROOT / relative).resolve()
    for relative in ("docs", "artifacts", "apps/ike-bot")
)


class PrincipalSession(BaseModel):
    authenticated: bool = True
    principal_id: str
    tenant_id: str
    role: str
    permissions: list[str]
    correlation_id: str | None = None
    causation_id: str | None = None
    service_identity_persistence: Literal["postgresql-durable-descriptor"] = (
        "postgresql-durable-descriptor"
    )
    orchestration_state_persistence: Literal["postgresql-durable-orchestration"] = (
        "postgresql-durable-orchestration"
    )


@router.get("/session", response_model=PrincipalSession)
async def principal_session(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
) -> PrincipalSession:
    """Return identity derived only from the already-verified JWT claims."""
    context = get_current_context()
    return PrincipalSession(
        principal_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        role=current_user.role.value,
        permissions=sorted(permission.value for permission in current_user.permissions),
        correlation_id=context.correlation_id if context else None,
        causation_id=context.causation_id if context else None,
    )


class ServiceIdentityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    agent_id: str | None = Field(default=None, max_length=128)
    scopes: list[str] = Field(default_factory=list, max_length=50)
    scoped_folders: list[str] = Field(default_factory=list, max_length=100)
    allowed_capabilities: list[str] = Field(default_factory=list, max_length=50)
    credential_ref: str | None = Field(default=None, max_length=512)
    ttl_minutes: int = Field(default=60, ge=1, le=1440)
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=128)


@router.post(
    "/service-identities",
    response_model=GovernedIdentity,
    status_code=status.HTTP_201_CREATED,
)
async def provision_service_identity(
    body: ServiceIdentityRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> GovernedIdentity:
    try:
        identity = await identity_service.provision_service_identity(
            db,
            tenant_id=current_user.tenant_id,
            created_by=current_user.user_id,
            display_name=body.display_name,
            agent_id=body.agent_id,
            scopes=body.scopes,
            scoped_folders=body.scoped_folders,
            allowed_capabilities=body.allowed_capabilities,
            credential_ref=body.credential_ref,
            ttl_minutes=body.ttl_minutes,
            idempotency_key=body.idempotency_key,
        )
    except DuplicateServiceIdentityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SERVICE_IDENTITY_IDEMPOTENCY_CONFLICT",
                "identity_id": exc.identity_id,
            },
        ) from exc

    await audit(
        db,
        action="service_identity_provisioned",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_service_identity",
        resource_id=identity.identity_id,
        resource_name=identity.display_name,
        details={
            "agent_id": identity.agent_id,
            "scopes": identity.scopes,
            "scoped_folders": identity.scoped_folders,
            "allowed_capabilities": identity.allowed_capabilities,
            "expires_at": identity.expires_at.isoformat() if identity.expires_at else None,
            "credential_ref_present": bool(identity.credential_ref),
            "credential_material_stored": False,
            "idempotency_key_present": bool(body.idempotency_key),
            "persistence": "postgresql-durable-descriptor",
        },
    )
    return identity


@router.get("/service-identities", response_model=list[GovernedIdentity])
async def list_service_identities(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[GovernedIdentity]:
    return await identity_service.list_identities(db, tenant_id=current_user.tenant_id)


class RevokeIdentityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


@router.post("/service-identities/{identity_id}/revoke", response_model=GovernedIdentity)
async def revoke_service_identity(
    identity_id: str,
    body: RevokeIdentityRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> GovernedIdentity:
    identity = await identity_service.revoke_identity(
        db,
        identity_id,
        tenant_id=current_user.tenant_id,
        reason=body.reason,
    )
    if identity is None:
        raise HTTPException(status_code=404, detail="Service identity not found")
    await audit(
        db,
        action="service_identity_revoked",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_service_identity",
        resource_id=identity.identity_id,
        resource_name=identity.display_name,
        details={"reason": body.reason, "persistence": "postgresql-durable-descriptor"},
    )
    return identity


class LivingContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=1000)
    refs: list[str] = Field(min_length=1, max_length=20)
    max_chars_per_ref: int = Field(default=12000, ge=512, le=50000)


class LivingContextItem(BaseModel):
    uri: str
    title: str
    content_hash: str
    source: Literal["git"] = "git"
    classification: Literal["internal"] = "internal"
    excerpt: str
    matched_terms: list[str]


def _resolve_living_ref(ref: str) -> Path:
    candidate = (_REPO_ROOT / ref).resolve()
    if candidate.suffix.lower() != ".md":
        raise HTTPException(status_code=422, detail=f"Living ref must be Markdown: {ref}")
    if not any(candidate.is_relative_to(root) for root in _ALLOWED_LIVING_ROOTS):
        raise HTTPException(status_code=403, detail=f"Living ref is outside allowed roots: {ref}")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"Living ref not found: {ref}")
    return candidate


@router.post("/living-context", response_model=list[LivingContextItem])
async def retrieve_living_context(
    body: LivingContextRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
) -> list[LivingContextItem]:
    terms = sorted({term.lower() for term in body.query.split() if len(term) >= 3})
    items: list[LivingContextItem] = []
    for ref in body.refs:
        path = _resolve_living_ref(ref)
        raw = path.read_text(encoding="utf-8", errors="replace")
        lowered = raw.lower()
        matched = [term for term in terms if term in lowered]
        if terms and not matched:
            continue
        excerpt = raw[: body.max_chars_per_ref]
        items.append(
            LivingContextItem(
                uri=ref,
                title=path.stem,
                content_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                excerpt=excerpt,
                matched_terms=matched,
            )
        )
    return items


class PrincipalMissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=10000)
    constraints: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.THINK_WORK_CHECK
    budget_limits: BudgetLimits | None = None


class PrincipalMissionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    reason: str | None = Field(default=None, max_length=2000)


class PrincipalMissionCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


@router.post("/missions")
async def execute_principal_mission(
    body: PrincipalMissionRequest,
    current_user: CurrentUser = Depends(require_permissions(
        Permission.MISSION_COMMAND_ADMIN,
        Permission.ORCHESTRATION_CREATE,
    )),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a bounded run, then persist it as the authoritative lifecycle state."""
    run = await start_durable_run(
        db,
        objective=body.objective,
        constraints=body.constraints,
        execution_mode=body.execution_mode,
        budget_limits=body.budget_limits,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
    )
    await audit(
        db,
        action="ike_runtime_mission_coordinated",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="ike_runtime_mission",
        resource_id=str(run["run_id"]),
        resource_name="principal_mission",
        details={
            "status": run["status"],
            "routing_decisions": len(run.get("routing_decisions", [])),
            "approval_requests": len(run.get("approvals", [])),
            "orchestration_state_persistence": "postgresql-durable-orchestration",
            "external_action_performed": False,
        },
    )
    return run


@router.get("/missions/{run_id}")
async def get_principal_mission(
    run_id: str,
    current_user: CurrentUser = Depends(require_permissions(
        Permission.MISSION_COMMAND_ADMIN,
        Permission.ORCHESTRATION_READ,
    )),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    run = await get_durable_run(db, run_id=run_id, tenant_id=current_user.tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return run


@router.post("/missions/{run_id}/approve")
async def approve_principal_mission(
    run_id: str,
    body: PrincipalMissionDecision,
    current_user: CurrentUser = Depends(require_permissions(
        Permission.MISSION_COMMAND_ADMIN,
        Permission.ORCHESTRATION_APPROVE,
    )),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        run = await approve_durable_run(
            db,
            run_id=run_id,
            tenant_id=current_user.tenant_id,
            principal_id=current_user.user_id,
            approved=body.approved,
            reason=body.reason,
        )
    except DurableOrchestrationStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    await audit(
        db,
        action="ike_runtime_mission_approval_decided",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="ike_runtime_mission",
        resource_id=run_id,
        resource_name="principal_approval",
        details={
            "approved": body.approved,
            "reason": body.reason,
            "principal_id": current_user.user_id,
            "persistence": "postgresql-durable-orchestration",
        },
    )
    return run


@router.post("/missions/{run_id}/cancel")
async def cancel_principal_mission(
    run_id: str,
    body: PrincipalMissionCancel,
    current_user: CurrentUser = Depends(require_permissions(
        Permission.MISSION_COMMAND_ADMIN,
        Permission.ORCHESTRATION_CANCEL,
    )),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        run = await cancel_durable_run(
            db,
            run_id=run_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.user_id,
            reason=body.reason,
        )
    except DurableOrchestrationStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    await audit(
        db,
        action="ike_runtime_mission_cancelled",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="ike_runtime_mission",
        resource_id=run_id,
        resource_name="principal_cancel",
        details={"reason": body.reason, "persistence": "postgresql-durable-orchestration"},
    )
    return run


class AcceptanceSideEffectRequest(BaseModel):
    """One deliberately bounded side effect used to certify the approval path."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=128)
    draft_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    service_identity_id: str = Field(min_length=1, max_length=128)
    side_effect_type: Literal["ACCEPTANCE_MARKER"] = "ACCEPTANCE_MARKER"
    principal_brief: dict[str, Any] = Field(default_factory=dict)


class AcceptanceSideEffectReceipt(BaseModel):
    committed: bool
    side_effect_type: str
    run_id: str
    draft_hash: str
    service_identity_id: str
    audit_log_id: str
    evidence_hash: str
    previous_evidence_hash: str | None = None


@router.post(
    "/acceptance-side-effects",
    response_model=AcceptanceSideEffectReceipt,
    status_code=status.HTTP_201_CREATED,
)
async def commit_acceptance_side_effect(
    body: AcceptanceSideEffectRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AcceptanceSideEffectReceipt:
    """Commit one internal, bounded acceptance marker after exact-draft approval."""
    identity = await identity_service.get_identity(
        db,
        body.service_identity_id,
        tenant_id=current_user.tenant_id,
    )
    has_access = identity is not None and await identity_service.validate_access(
        db,
        body.service_identity_id,
        "runtime-acceptance",
        required_scope="runtime:side-effect",
        required_capability="computer_control",
        tenant_id=current_user.tenant_id,
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Service identity lacks side-effect authority")

    run = await get_durable_run(
        db,
        run_id=body.run_id,
        tenant_id=current_user.tenant_id,
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Orchestration run not found")

    approved = any(
        approval.get("status") == "APPROVED"
        and approval.get("principal_id") == current_user.user_id
        for approval in run.get("approvals", [])
    )
    if not approved:
        raise HTTPException(status_code=409, detail="Principal approval has not been recorded")

    expected_draft_hash = str(run.get("constraints", {}).get("draft_hash", ""))
    if expected_draft_hash != body.draft_hash:
        raise HTTPException(
            status_code=409,
            detail="Approved draft hash does not match; approval is stale",
        )

    entry = await audit(
        db,
        action="ike_runtime_acceptance_side_effect_committed",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="ike_runtime_acceptance",
        resource_id=body.run_id,
        resource_name=body.side_effect_type,
        status="success",
        details={
            "run_id": body.run_id,
            "draft_hash": body.draft_hash,
            "service_identity_id": body.service_identity_id,
            "side_effect_type": body.side_effect_type,
            "principal_brief": body.principal_brief,
            "approval_bound_to_exact_draft": True,
            "external_action_performed": False,
        },
    )
    return AcceptanceSideEffectReceipt(
        committed=True,
        side_effect_type=body.side_effect_type,
        run_id=body.run_id,
        draft_hash=body.draft_hash,
        service_identity_id=body.service_identity_id,
        audit_log_id=str(entry.id),
        evidence_hash=entry.entry_hash,
        previous_evidence_hash=entry.previous_hash,
    )
