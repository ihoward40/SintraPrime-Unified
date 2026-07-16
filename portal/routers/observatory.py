"""
Observatory router for the SintraPrime Portal.

Exposes all observatory endpoints including events, missions, agents,
approvals, governance gates, evidence, artifacts, incidents, SSE streaming,
WebSocket broadcast, and kill switch.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from portal.database import get_db
from portal.models.observatory import (
    Agent,
    Approval,
    Artifact,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
)
from portal.schemas.observatory import (
    AgentRegisterRequest,
    AgentResponse,
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalResponse,
    ApprovalStatus,
    ArtifactCreateRequest,
    ArtifactResponse,
    EventCreateRequest,
    EvidenceCreateRequest,
    EvidenceResponse,
    EventType,
    GovernanceGate,
    GovernanceGateCheckRequest,
    GovernanceGateCheckResponse,
    IncidentCreateRequest,
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
    IncidentUpdateRequest,
    KillSwitchClearRequest,
    KillSwitchRequest,
    KillSwitchResponse,
    KillSwitchStatusResponse,
    MissionCreateRequest,
    MissionResponse,
    MissionStatus,
    MissionUpdateRequest,
    PaginatedResponse,
    ReplayRequest,
    ReplayResponse,
)
from portal.services.observatory_service import (
    AgentService,
    ApprovalService,
    ArtifactService,
    DataMaskingService,
    EventService,
    EvidenceService,
    GovernanceService,
    IncidentService,
    KillSwitchService,
    MissionService,
    ReplayService,
)
from portal.auth.rbac import (
    assert_role_allowed,
    CurrentUser,
    get_current_user,
    Role,
)
from portal.services.execution_guard import (
    ExecutionAction,
    ExecutionGuard,
    ExecutionGuardError,
    PrincipalContext,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["observatory"])


# ── G4.8 C1 boundary-security helpers ──────────────────────────────────────────
#
# The portal is the sole authority that authenticates, authorizes, guards,
# records, and refuses observatory mutations. The MCP bridge (C2) must route
# through these SAME dependencies — it may never call the service layer
# directly without them.
#
# Audit boundary (precise): Observatory boundary events begin AFTER successful
# identity authentication but BEFORE role, permission, approval, guard, or
# execution authorization. Authentication-transport rejections (missing /
# malformed / expired / invalid JWT) are handled by get_current_user and are
# out of scope here — no principal is fabricated merely to write an event.
#
# Lifecycle emitted by require_audited_role + route body:
#   insufficient role : BOUNDARY_REQUESTED -> BOUNDARY_REFUSED (no mutation)
#   guard refusal     : BOUNDARY_REQUESTED -> BOUNDARY_AUTHORIZED -> BOUNDARY_REFUSED
#   success           : BOUNDARY_REQUESTED -> BOUNDARY_AUTHORIZED -> BOUNDARY_EXECUTED
#   service failure   : BOUNDARY_REQUESTED -> BOUNDARY_AUTHORIZED -> BOUNDARY_FAILED
# One correlation_id is used throughout (extracted from the body or generated).


def _build_principal(user: CurrentUser) -> PrincipalContext:
    """G-B1: derive a REAL authenticated PrincipalContext from the verified JWT.

    Identity, roles, and permissions come exclusively from the JWT payload.
    Caller-supplied actor names in request bodies are NEVER trusted.

    Role vocabulary bridge: the ExecutionGuard policy vocabulary
    ("system_admin", "incident_commander") is distinct from the portal RBAC
    vocabulary ("SUPER_ADMIN", "FIRM_ADMIN"). The portal's highest authority
    (SUPER_ADMIN) is equivalent to both guard roles; FIRM_ADMIN maps to
    "system_admin". This keeps the guard's role requirements satisfiable by
    real authenticated principals without forging new authorities.
    """
    rbac_role = user.role.value
    _RBAC_TO_GUARD = {
        Role.SUPER_ADMIN.value: ["system_admin", "incident_commander"],
        Role.FIRM_ADMIN.value: ["system_admin"],
    }
    combined_roles = [rbac_role, *_RBAC_TO_GUARD.get(rbac_role, [])]
    return PrincipalContext(
        subject_id=user.user_id,
        authentication_method="jwt",
        roles=combined_roles,
        permissions=[p.value for p in user.permissions],
        is_authenticated=True,
    )


# Boundary audit lifecycle event types (G-B4). Distinct from the domain event
# types emitted by the services themselves.
_BOUNDARY_EVENT_TYPES = {
    "requested": "BOUNDARY_REQUESTED",
    "authorized": "BOUNDARY_AUTHORIZED",
    "refused": "BOUNDARY_REFUSED",
    "executed": "BOUNDARY_EXECUTED",
    "failed": "BOUNDARY_FAILED",
}


async def _write_boundary_event(
    db: AsyncSession,
    lifecycle: str,
    action_value: str,
    principal: PrincipalContext,
    *,
    mission_id: str | None = None,
    detail: str | None = None,
    correlation_id: str | None = None,
    fail_closed: bool = False,
) -> None:
    """Persist one boundary audit event and commit it independently.

    Boundary events live on their own transaction so that REFUSED / FAILED
    records survive even when the protected route is refused or the domain
    mutation never commits. EventService.create only flushes (never commits),
    so we commit here.

    fail_closed=True (used for REQUESTED / REFUSED): if the audit write cannot
    be persisted, raise so the protected operation is refused — audit failure
    must never grant access. fail_closed=False (EXECUTED / FAILED): log only,
    so a transient audit problem never masks a real result or rolls back a
    legitimate mutation.
    """
    payload: dict[str, Any] = {
        "lifecycle": lifecycle,
        "action": action_value,
        "subject": principal.subject_id,
        "authenticated": principal.is_authenticated,
        "roles": list(principal.roles),
    }
    if mission_id is not None:
        payload["mission_id"] = mission_id
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    if detail is not None:
        payload["detail"] = detail
    try:
        await EventService.create(
            db,
            event_type=_BOUNDARY_EVENT_TYPES[lifecycle],
            mission_id=UUID(mission_id) if mission_id else None,
            agent_id=principal.subject_id,
            payload=payload,
            run_id="boundary",
        )
        await db.commit()
    except Exception as exc:
        logger.error(
            "boundary_audit_event_failed lifecycle=%s action=%s correlation=%s error=%s",
            lifecycle, action_value, correlation_id, exc,
        )
        if fail_closed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization audit could not be recorded; request refused.",
            ) from exc


async def _resolve_correlation_id(request: Request, action_value: str) -> str:
    """Extract the request correlation id from the body, or generate one.

    The body is read via the cached request stream (Starlette caches it, so
    the route's own Pydantic body parsing is unaffected). A generated id is
    stored on request.state so the route body reuses the exact same value.
    """
    correlation_id = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            meta = body.get("metadata")
            if isinstance(meta, dict):
                correlation_id = meta.get("correlation_id")
            if not correlation_id:
                correlation_id = body.get("correlation_id")
    except Exception:
        correlation_id = None
    if not correlation_id:
        correlation_id = uuid4().hex
    request.state.boundary_correlation_id = correlation_id
    return correlation_id


def require_audited_role(required_role: Role, action: ExecutionAction):
    """Composite dependency: role authorization + boundary audit.

    Resolves the real CurrentUser (so authentication-transport rejections are
    handled by get_current_user before we run), the DB session, and the request
    correlation id; emits BOUNDARY_REQUESTED; applies the canonical role policy
    via assert_role_allowed; on denial emits BOUNDARY_REFUSED (reason
    "insufficient_role") and raises the same structured 403 used by require_role;
    on success emits BOUNDARY_AUTHORIZED and returns the real PrincipalContext.

    The route body then owns guard evaluation, protected service execution,
    BOUNDARY_EXECUTED, and BOUNDARY_FAILED — all tagged with the same
    correlation id.

    This is applied ONLY to privileged Observatory mutation routes in C1; it is
    not introduced globally.
    """
    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        user: CurrentUser = Depends(get_current_user),
    ) -> PrincipalContext:
        principal = _build_principal(user)
        correlation_id = await _resolve_correlation_id(request, action.value)
        # REQUESTED must persist before any authorization decision (fail-closed).
        await _write_boundary_event(
            db, "requested", action.value, principal,
            correlation_id=correlation_id, fail_closed=True,
        )
        try:
            assert_role_allowed(user, required_role)
        except HTTPException:
            # Refusal must persist independently (fail-closed) and then deny.
            await _write_boundary_event(
                db, "refused", action.value, principal,
                detail="insufficient_role", correlation_id=correlation_id, fail_closed=True,
            )
            raise
        await _write_boundary_event(
            db, "authorized", action.value, principal,
            correlation_id=correlation_id, fail_closed=True,
        )
        return principal
    return dependency


async def _record_boundary_event(
    db: AsyncSession,
    lifecycle: str,
    action_value: str,
    principal: PrincipalContext,
    *,
    mission_id: str | None = None,
    detail: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Route-body boundary audit for EXECUTED / FAILED (best-effort, non-masking).

    Recursion guard: never emit EXECUTED / FAILED while appending the underlying
    observatory event — that path handles its own chaining. The payload
    deliberately omits secrets, bearer tokens, and raw credentials.
    """
    if action_value == ExecutionAction.EVENT_APPEND.value and lifecycle in ("executed", "failed"):
        return
    await _write_boundary_event(
        db, lifecycle, action_value, principal,
        mission_id=mission_id, detail=detail, correlation_id=correlation_id,
        fail_closed=False,
    )


# ── WebSocket connection manager ──────────────────────────────────────────────


class ConnectionManager:
    """Simple WebSocket connection manager for real-time event broadcast."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, data: dict[str, Any]) -> None:
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


_manager = ConnectionManager()


# ── Helper ─────────────────────────────────────────────────────────────────────


def _to_str(uuid_val: UUID | str | None) -> str | None:
    return str(uuid_val) if uuid_val else None


# ── WebSocket ──────────────────────────────────────────────────────────────────


@router.websocket("/ws/observatory")
async def observatory_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time observatory event broadcast."""
    await _manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(websocket)


# ── Events ─────────────────────────────────────────────────────────────────────


@router.post("/events", response_model=dict, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    request: EventCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.FIRM_ADMIN, action=ExecutionAction.EVENT_APPEND)
    ),
):
    """Ingest a new observatory event (hash-chained).

    G-B1/B-B2/B-B3: requires an authenticated FIRM_ADMIN-or-higher principal
    (enforced + audited by require_audited_role); passes through the
    ExecutionGuard (EVENT_APPEND is BLOCKED by an active kill switch).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.EVENT_APPEND,
            mission_id=request.mission_id, principal_context=principal,
        )
        mission_uuid = UUID(request.mission_id) if request.mission_id else None
        event = await EventService.create(
            db,
            event_type=request.event_type,
            mission_id=mission_uuid,
            agent_id=request.agent_id,
            payload=DataMaskingService.mask_payload(request.payload),
            metadata=request.metadata_,
            timestamp=request.timestamp,
        )
        await db.commit()

        # Broadcast to WebSocket clients
        event_data = {
            "id": str(event.id),
            "event_type": event.event_type,
            "mission_id": _to_str(event.mission_id),
            "agent_id": event.agent_id,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }
        await _manager.broadcast(event_data)
        # G-B4: success event only after the side effect commits.
        await _record_boundary_event(
            db, "executed", ExecutionAction.EVENT_APPEND.value, principal,
            mission_id=request.mission_id, correlation_id=correlation_id,
        )

        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "event_hash": event.event_hash,
            "previous_hash": event.previous_hash,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.EVENT_APPEND.value, principal,
            mission_id=request.mission_id, detail=exc.decision.reason_code.value,
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Observatory mutation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.EVENT_APPEND.value, principal,
            mission_id=request.mission_id, detail=type(exc).__name__,
            correlation_id=correlation_id,
        )
        raise


@router.get("/events", response_model=dict)
async def list_events(
    mission_id: str | None = None,
    agent_id: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List observatory events with optional filters."""
    mission_uuid = UUID(mission_id) if mission_id else None
    events, total = await EventService.list_events(
        db,
        mission_id=mission_uuid,
        agent_id=agent_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "mission_id": _to_str(e.mission_id),
                "agent_id": e.agent_id,
                "payload": e.payload,
                "event_hash": e.event_hash,
                "previous_hash": e.previous_hash,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/events/{event_id}", response_model=dict)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single event by ID."""
    event = await EventService.get_by_id(db, UUID(event_id))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "mission_id": _to_str(event.mission_id),
        "agent_id": event.agent_id,
        "payload": event.payload,
        "metadata_": event.metadata_,
        "event_hash": event.event_hash,
        "previous_hash": event.previous_hash,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/events/chain/verify", response_model=dict)
async def verify_chain(db: AsyncSession = Depends(get_db)):
    """Verify the integrity of the event hash chain."""
    result = await EventService.verify_chain(db)
    return {"valid": result.valid, "reason": result.reason if not result.valid else None}


# ── SSE stream ─────────────────────────────────────────────────────────────────


@router.get("/runs/{run_id}/stream")
async def stream_run_events(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for streaming events for a given run/mission."""
    mission_uuid = UUID(run_id)

    async def event_generator():
        last_count = 0
        while True:
            events, _ = await EventService.list_events(
                db, mission_id=mission_uuid, limit=100, offset=last_count
            )
            for event in events:
                yield {
                    "event": "event",
                    "data": json.dumps({
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "mission_id": _to_str(event.mission_id),
                        "agent_id": event.agent_id,
                        "payload": event.payload,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    }),
                }
            last_count += len(events)
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


# ── Missions ───────────────────────────────────────────────────────────────────


@router.post("/missions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_mission(
    request: MissionCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.FIRM_ADMIN, action=ExecutionAction.MISSION_CREATE)
    ),
):
    """Create a new observatory mission.

    G-B1/B-B2/B-B3: requires an authenticated FIRM_ADMIN-or-higher principal
    (enforced + audited by require_audited_role); passes through the
    ExecutionGuard (MISSION_CREATE is BLOCKED by an active kill switch).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.MISSION_CREATE,
            principal_context=principal,
        )
        gates_required = [g.value if isinstance(g, GovernanceGate) else g for g in request.governance_gates_required]
        mission = await MissionService.create(
            db,
            title=request.title,
            description=request.description,
            objective=request.objective,
            agent_ids=request.agent_ids,
            governance_gates_required=gates_required,
            metadata=request.metadata_,
        )
        await db.commit()

        # Emit event
        await EventService.create(
            db,
            event_type=EventType.MISSION_CREATED,
            mission_id=mission.id,
            payload={"title": mission.title, "status": mission.status},
        )
        await db.commit()
        await _record_boundary_event(
            db, "executed", ExecutionAction.MISSION_CREATE.value, principal,
            mission_id=str(mission.id), correlation_id=correlation_id,
        )

        return {
            "id": str(mission.id),
            "title": mission.title,
            "description": mission.description,
            "objective": mission.objective,
            "status": mission.status,
            "governance_gates_required": mission.governance_gates_required,
            "governance_gates_passed": mission.governance_gates_passed,
            "created_at": mission.created_at.isoformat() if mission.created_at else None,
        }
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.MISSION_CREATE.value, principal,
            detail=exc.decision.reason_code.value, correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Observatory mutation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.MISSION_CREATE.value, principal,
            detail=type(exc).__name__, correlation_id=correlation_id,
        )
        raise


@router.get("/missions", response_model=dict)
async def list_missions(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List missions with optional status filter."""
    missions, total = await MissionService.list_missions(db, status=status, limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": str(m.id),
                "title": m.title,
                "status": m.status,
                "governance_gates_required": m.governance_gates_required,
                "governance_gates_passed": m.governance_gates_passed,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in missions
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/missions/{mission_id}", response_model=dict)
async def get_mission(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a mission by ID."""
    mission = await MissionService.get_by_id(db, UUID(mission_id))
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    agent_ids = await MissionService.get_agent_ids(db, mission.id)
    return {
        "id": str(mission.id),
        "title": mission.title,
        "description": mission.description,
        "objective": mission.objective,
        "status": mission.status,
        "agent_ids": agent_ids,
        "governance_gates_required": mission.governance_gates_required,
        "governance_gates_passed": mission.governance_gates_passed,
        "metadata_": mission.metadata_,
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
        "updated_at": mission.updated_at.isoformat() if mission.updated_at else None,
    }


@router.patch("/missions/{mission_id}", response_model=dict)
async def update_mission(
    mission_id: str,
    request: MissionUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a mission."""
    uuid_id = UUID(mission_id)
    mission = await MissionService.get_by_id(db, uuid_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    if request.title is not None:
        mission.title = request.title
    if request.description is not None:
        mission.description = request.description
    if request.objective is not None:
        mission.objective = request.objective
    if request.status is not None:
        old_status = mission.status
        mission.status = request.status.value if isinstance(request.status, MissionStatus) else request.status
        await EventService.create(
            db,
            event_type=EventType.MISSION_STATUS_CHANGED,
            mission_id=uuid_id,
            payload={"old_status": old_status, "new_status": mission.status},
        )
    if request.metadata_ is not None:
        mission.metadata_ = request.metadata_

    await db.flush()
    await db.commit()

    return {
        "id": str(mission.id),
        "title": mission.title,
        "status": mission.status,
        "updated_at": mission.updated_at.isoformat() if mission.updated_at else None,
    }


@router.post("/missions/{mission_id}/agents/{agent_id}", response_model=dict)
async def assign_agent_to_mission(
    mission_id: str,
    agent_id: str,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Assign an agent to a mission."""
    uuid_id = UUID(mission_id)
    mission = await MissionService.get_by_id(db, uuid_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    ma = await MissionService.add_agent(db, uuid_id, agent_id, role=role)
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.AGENT_ASSIGNED,
        mission_id=uuid_id,
        agent_id=agent_id,
        payload={"role": role},
    )
    await db.commit()

    return {"id": str(ma.id), "mission_id": mission_id, "agent_id": agent_id, "role": role}


@router.delete("/missions/{mission_id}/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_agent_from_mission(
    mission_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove an agent from a mission."""
    uuid_id = UUID(mission_id)
    removed = await MissionService.remove_agent(db, uuid_id, agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent assignment not found")
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.AGENT_UNASSIGNED,
        mission_id=uuid_id,
        agent_id=agent_id,
    )
    await db.commit()


# ── Agents ─────────────────────────────────────────────────────────────────────


@router.post("/agents", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_agent(
    request: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent."""
    agent = await AgentService.register(
        db,
        agent_id=request.agent_id,
        name=request.name,
        agent_type=request.agent_type,
        capabilities=request.capabilities,
        metadata=request.metadata_,
    )
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.AGENT_REGISTERED,
        agent_id=request.agent_id,
        payload={"name": request.name, "agent_type": request.agent_type},
    )
    await db.commit()

    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.get("/agents", response_model=dict)
async def list_agents(
    agent_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List registered agents."""
    agents, total = await AgentService.list_agents(db, status=agent_status, limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": str(a.id),
                "agent_id": a.agent_id,
                "name": a.name,
                "agent_type": a.agent_type,
                "status": a.status,
                "capabilities": a.capabilities,
                "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
            }
            for a in agents
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/agents/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get an agent by agent_id."""
    agent = await AgentService.get_by_agent_id(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "metadata_": agent.metadata_,
        "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.post("/agents/{agent_id}/heartbeat", response_model=dict)
async def agent_heartbeat(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Record agent heartbeat."""
    agent = await AgentService.heartbeat(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.commit()
    return {"agent_id": agent.agent_id, "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None}


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Deregister an agent."""
    success = await AgentService.deregister(db, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.AGENT_DEREGISTERED,
        agent_id=agent_id,
    )
    await db.commit()


# ── Approvals ──────────────────────────────────────────────────────────────────


@router.post("/approvals", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_approval(
    request: ApprovalCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.FIRM_ADMIN, action=ExecutionAction.APPROVAL_REQUEST)
    ),
):
    """Request an approval.

    G-B1/B-B2/B-B3: requires an authenticated FIRM_ADMIN-or-higher principal
    (enforced + audited by require_audited_role); passes through the
    ExecutionGuard (APPROVAL_REQUEST is BLOCKED by an active kill switch).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.APPROVAL_REQUEST,
            mission_id=request.mission_id, principal_context=principal,
        )
        mission_uuid = UUID(request.mission_id)
        gate_str = request.gate.value if isinstance(request.gate, GovernanceGate) else request.gate
        approval = await ApprovalService.create(
            db,
            mission_id=mission_uuid,
            requester=request.requester,
            gate=gate_str,
            reason=request.reason,
            metadata=request.metadata_,
        )
        await db.commit()

        await EventService.create(
            db,
            event_type=EventType.APPROVAL_REQUESTED,
            mission_id=mission_uuid,
            payload={"approval_id": str(approval.id), "gate": gate_str, "requester": request.requester},
        )
        await db.commit()
        await _record_boundary_event(
            db, "executed", ExecutionAction.APPROVAL_REQUEST.value, principal,
            mission_id=request.mission_id, correlation_id=correlation_id,
        )

        return {
            "id": str(approval.id),
            "mission_id": str(approval.mission_id),
            "gate": approval.gate,
            "requester": approval.requester,
            "status": approval.status,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
        }
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.APPROVAL_REQUEST.value, principal,
            mission_id=request.mission_id, detail=exc.decision.reason_code.value,
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Observatory mutation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.APPROVAL_REQUEST.value, principal,
            mission_id=request.mission_id, detail=type(exc).__name__,
            correlation_id=correlation_id,
        )
        raise


@router.post("/approvals/{approval_id}/decide", response_model=dict)
async def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.FIRM_ADMIN, action=ExecutionAction.APPROVAL_DECISION)
    ),
):
    """Approve or deny a pending approval.

    G-B1/B-B2: requires an authenticated principal with FIRM_ADMIN or higher
    (enforced + audited by require_audited_role). G-B3: passes through the
    ExecutionGuard (APPROVAL_DECISION is BLOCKED by an active kill switch).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.APPROVAL_DECISION,
            principal_context=principal,
        )
        approval = await ApprovalService.decide(
            db,
            approval_id=UUID(approval_id),
            decision=request.decision,
            reviewer=request.reviewer,
            notes=request.notes,
        )
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        await db.commit()

        event_type = EventType.APPROVAL_GRANTED if approval.status == ApprovalStatus.APPROVED.value else EventType.APPROVAL_DENIED
        await EventService.create(
            db,
            event_type=event_type,
            mission_id=approval.mission_id,
            payload={"approval_id": str(approval.id), "gate": approval.gate, "reviewer": request.reviewer},
        )
        await db.commit()
        await _record_boundary_event(
            db, "executed", ExecutionAction.APPROVAL_DECISION.value, principal,
            mission_id=str(approval.mission_id), detail=f"approval={approval_id}",
            correlation_id=correlation_id,
        )

        return {
            "id": str(approval.id),
            "mission_id": str(approval.mission_id),
            "gate": approval.gate,
            "status": approval.status,
            "reviewer": approval.reviewer,
            "notes": approval.notes,
        }
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.APPROVAL_DECISION.value, principal,
            detail=exc.decision.reason_code.value, correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Observatory mutation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.APPROVAL_DECISION.value, principal,
            detail=type(exc).__name__, correlation_id=correlation_id,
        )
        raise


@router.get("/approvals/pending", response_model=dict)
async def list_pending_approvals(
    mission_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List pending approvals."""
    mission_uuid = UUID(mission_id) if mission_id else None
    approvals = await ApprovalService.get_pending(db, mission_id=mission_uuid)
    return {
        "items": [
            {
                "id": str(a.id),
                "mission_id": str(a.mission_id),
                "gate": a.gate,
                "requester": a.requester,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in approvals
        ],
        "total": len(approvals),
    }


# ── Governance gates ──────────────────────────────────────────────────────────


@router.post("/governance/check", response_model=GovernanceGateCheckResponse)
async def check_governance_gate(
    request: GovernanceGateCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check whether a mission passes a governance gate."""
    mission_uuid = UUID(request.mission_id)
    evidence_uuids = [UUID(eid) for eid in request.evidence_ids] if request.evidence_ids else None

    passed, reason = await GovernanceService.check_gate(
        db, mission_id=mission_uuid, gate=request.gate, evidence_ids=evidence_uuids
    )

    # Record result
    await GovernanceService.record_gate_result(
        db, mission_id=mission_uuid, gate=request.gate, passed=passed, reason=reason
    )
    await db.commit()

    event_type = EventType.GOVERNANCE_GATE_PASSED if passed else EventType.GOVERNANCE_GATE_FAILED
    await EventService.create(
        db,
        event_type=event_type,
        mission_id=mission_uuid,
        payload={"gate": request.gate.value, "passed": passed, "reason": reason},
    )
    await db.commit()

    return GovernanceGateCheckResponse(
        mission_id=request.mission_id,
        gate=request.gate.value,
        passed=passed,
        reason=reason,
        checked_at=datetime.now(UTC),
    )


# ── Evidence ──────────────────────────────────────────────────────────────────


@router.post("/evidence", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    request: EvidenceCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.FIRM_ADMIN, action=ExecutionAction.EVIDENCE_SUBMIT)
    ),
):
    """Submit evidence for a mission.

    G-B1/B-B2/B-B3: requires an authenticated FIRM_ADMIN-or-higher principal
    (enforced + audited by require_audited_role); passes through the
    ExecutionGuard (EVIDENCE_SUBMIT is BLOCKED by an active kill switch).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.EVIDENCE_SUBMIT,
            mission_id=request.mission_id, principal_context=principal,
        )
        mission_uuid = UUID(request.mission_id)
        evidence = await EvidenceService.create(
            db,
            mission_id=mission_uuid,
            source=request.source,
            content_hash=request.content_hash,
            content_type=request.content_type,
            description=request.description,
            metadata=request.metadata_,
        )
        await db.commit()

        await EventService.create(
            db,
            event_type=EventType.EVIDENCE_CAPTURED,
            mission_id=mission_uuid,
            payload={"evidence_id": str(evidence.id), "source": request.source},
        )
        await db.commit()
        await _record_boundary_event(
            db, "executed", ExecutionAction.EVIDENCE_SUBMIT.value, principal,
            mission_id=request.mission_id, correlation_id=correlation_id,
        )

        return {
            "id": str(evidence.id),
            "mission_id": str(evidence.mission_id),
            "source": evidence.source,
            "content_type": evidence.content_type,
            "content_hash": evidence.content_hash,
            "verified": evidence.verified,
            "created_at": evidence.created_at.isoformat() if evidence.created_at else None,
        }
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.EVIDENCE_SUBMIT.value, principal,
            mission_id=request.mission_id, detail=exc.decision.reason_code.value,
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Observatory mutation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.EVIDENCE_SUBMIT.value, principal,
            mission_id=request.mission_id, detail=type(exc).__name__,
            correlation_id=correlation_id,
        )
        raise


@router.get("/evidence/{evidence_id}/verify", response_model=dict)
async def verify_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark evidence as verified."""
    evidence = await EvidenceService.verify(db, UUID(evidence_id))
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.EVIDENCE_VERIFIED,
        mission_id=evidence.mission_id,
        payload={"evidence_id": str(evidence.id)},
    )
    await db.commit()

    return {"id": str(evidence.id), "verified": True}


@router.get("/missions/{mission_id}/evidence", response_model=dict)
async def list_mission_evidence(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List evidence for a mission."""
    mission_uuid = UUID(mission_id)
    evidence_list = await EvidenceService.get_by_mission(db, mission_uuid)
    return {
        "items": [
            {
                "id": str(e.id),
                "mission_id": str(e.mission_id),
                "source": e.source,
                "content_type": e.content_type,
                "content_hash": e.content_hash,
                "verified": e.verified,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence_list
        ],
        "total": len(evidence_list),
    }


# ── Artifacts ──────────────────────────────────────────────────────────────────


@router.post("/artifacts", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: ArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create an artifact for a mission."""
    mission_uuid = UUID(request.mission_id)
    artifact = await ArtifactService.create(
        db,
        mission_id=mission_uuid,
        name=request.name,
        artifact_type=request.artifact_type,
        uri=request.uri,
        content_hash=request.content_hash,
        metadata=request.metadata_,
    )
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.ARTIFACT_CREATED,
        mission_id=mission_uuid,
        payload={"artifact_id": str(artifact.id), "name": request.name},
    )
    await db.commit()

    return {
        "id": str(artifact.id),
        "mission_id": str(artifact.mission_id),
        "name": artifact.name,
        "artifact_type": artifact.artifact_type,
        "uri": artifact.uri,
        "content_hash": artifact.content_hash,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
    }


@router.get("/missions/{mission_id}/artifacts", response_model=dict)
async def list_mission_artifacts(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List artifacts for a mission."""
    mission_uuid = UUID(mission_id)
    artifacts = await ArtifactService.get_by_mission(db, mission_uuid)
    return {
        "items": [
            {
                "id": str(a.id),
                "mission_id": str(a.mission_id),
                "name": a.name,
                "artifact_type": a.artifact_type,
                "uri": a.uri,
                "content_hash": a.content_hash,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


# ── Incidents ─────────────────────────────────────────────────────────────────


@router.post("/incidents", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_incident(
    request: IncidentCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Report an incident."""
    mission_uuid = UUID(request.mission_id) if request.mission_id else None
    incident = await IncidentService.create(
        db,
        title=request.title,
        severity=request.severity,
        mission_id=mission_uuid,
        agent_id=request.agent_id,
        description=request.description,
        metadata=request.metadata_,
    )
    await db.commit()

    await EventService.create(
        db,
        event_type=EventType.INCIDENT_CREATED,
        mission_id=mission_uuid,
        agent_id=request.agent_id,
        payload={"incident_id": str(incident.id), "severity": incident.severity, "title": request.title},
    )
    await db.commit()

    return {
        "id": str(incident.id),
        "mission_id": _to_str(incident.mission_id),
        "agent_id": incident.agent_id,
        "severity": incident.severity,
        "status": incident.status,
        "title": incident.title,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


@router.patch("/incidents/{incident_id}", response_model=dict)
async def update_incident(
    incident_id: str,
    request: IncidentUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an incident (resolve or escalate)."""
    uuid_id = UUID(incident_id)

    if request.status == IncidentStatus.RESOLVED and request.resolution:
        incident = await IncidentService.resolve(db, uuid_id, request.resolution)
    elif request.status == IncidentStatus.ESCALATED:
        incident = await IncidentService.escalate(db, uuid_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid update parameters")

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    await db.commit()

    event_type = EventType.INCIDENT_RESOLVED if incident.status == IncidentStatus.RESOLVED.value else EventType.INCIDENT_ESCALATED
    await EventService.create(
        db,
        event_type=event_type,
        mission_id=incident.mission_id,
        agent_id=incident.agent_id,
        payload={"incident_id": str(incident.id), "status": incident.status},
    )
    await db.commit()

    return {
        "id": str(incident.id),
        "severity": incident.severity,
        "status": incident.status,
        "resolution": incident.resolution,
    }


@router.get("/incidents", response_model=dict)
async def list_incidents(
    mission_id: str | None = None,
    incident_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List incidents with optional filters."""
    mission_uuid = UUID(mission_id) if mission_id else None
    incidents, total = await IncidentService.list_incidents(
        db, mission_id=mission_uuid, status=incident_status, limit=limit, offset=offset
    )
    return {
        "items": [
            {
                "id": str(i.id),
                "mission_id": _to_str(i.mission_id),
                "agent_id": i.agent_id,
                "severity": i.severity,
                "status": i.status,
                "title": i.title,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in incidents
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# ── Replay ────────────────────────────────────────────────────────────────────


@router.post("/replay", response_model=dict)
async def replay_events(
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
):
    """Replay events from a given point in the hash chain."""
    mission_uuid = UUID(request.mission_id) if request.mission_id else None
    events, total, truncated = await ReplayService.replay(
        db,
        from_hash=request.from_hash,
        from_timestamp=request.from_timestamp,
        mission_id=mission_uuid,
        limit=request.limit,
    )
    return {
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "mission_id": _to_str(e.mission_id),
                "agent_id": e.agent_id,
                "payload": e.payload,
                "event_hash": e.event_hash,
                "previous_hash": e.previous_hash,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ],
        "total": total,
        "truncated": truncated,
    }


# ── Kill Switch ────────────────────────────────────────────────────────────────


@router.get("/emergency/kill-switch", response_model=KillSwitchStatusResponse)
async def get_kill_switch_status(
    db: AsyncSession = Depends(get_db),
):
    """Get current kill switch status. Loads from persistent storage."""
    is_active = await KillSwitchService.is_active(db)
    if is_active:
        state = await KillSwitchService.get_active_state(db)
        if state:
            return KillSwitchStatusResponse(
                is_active=True,
                reason=state.reason,
                activated_by=state.activated_by,
                activated_at=state.activated_at,
                scope=state.scope,
            )
        # Fails closed: is_active=True but couldn't load state
        return KillSwitchStatusResponse(is_active=True)
    return KillSwitchStatusResponse(is_active=False)


@router.post("/emergency/kill-switch", response_model=KillSwitchResponse)
async def activate_kill_switch(
    request: KillSwitchRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.SUPER_ADMIN, action=ExecutionAction.KILL_SWITCH_ACTIVATE)
    ),
):
    """Activate the emergency kill switch. Idempotent — re-activation returns existing state.
    Persists to database. Cancels all active missions. Fails closed.

    G-B1/B-B2/B-B3: requires an authenticated principal with SUPER_ADMIN or
    higher (enforced by `require_role`). The activating identity is derived
    from the authenticated principal — caller-supplied `activated_by` in the
    request body is NOT trusted. Passes through the ExecutionGuard
    (KILL_SWITCH_ACTIVATE requires an authenticated system_admin /
    incident_commander principal).
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.KILL_SWITCH_ACTIVATE,
            principal_context=principal,
        )
        count, affected_ids, state = await KillSwitchService.activate(
            db,
            reason=request.reason,
            # G-B1: identity comes from the authenticated principal, never the body.
            activated_by=principal.subject_id,
            scope=request.scope,
        )
        await db.commit()
        await _record_boundary_event(
            db, "executed", ExecutionAction.KILL_SWITCH_ACTIVATE.value, principal,
            correlation_id=correlation_id,
        )

        return KillSwitchResponse(
            activated=True,
            reason=state.reason,
            activated_by=state.activated_by,
            scope=state.scope,
            timestamp=state.activated_at,
            events_affected=count,
        )
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.KILL_SWITCH_ACTIVATE.value, principal,
            detail=exc.decision.reason_code.value, correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Kill switch activation refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.KILL_SWITCH_ACTIVATE.value, principal,
            detail=type(exc).__name__, correlation_id=correlation_id,
        )
        raise


@router.delete("/emergency/kill-switch", response_model=KillSwitchStatusResponse)
async def clear_kill_switch(
    request: KillSwitchClearRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(
        require_audited_role(required_role=Role.SUPER_ADMIN, action=ExecutionAction.KILL_SWITCH_CLEAR)
    ),
):
    """Clear (deactivate) the kill switch. Requires authorized principal.

    G-B1/B-B2/B-B3: requires an authenticated principal with SUPER_ADMIN or
    higher (enforced by `require_role`). The clearing identity is derived from
    the authenticated principal — caller-supplied `cleared_by` in the request
    body is NOT trusted. Passes through the ExecutionGuard (KILL_SWITCH_CLEAR
    requires an authenticated system_admin / incident_commander principal).
    Generates a KILL_SWITCH_CLEARED audit event. Returns None if no active
    switch exists.
    """
    correlation_id = http_request.state.boundary_correlation_id
    try:
        await ExecutionGuard.require_allowed(
            session=db, action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        state = await KillSwitchService.clear(
            db,
            # G-B1: identity comes from the authenticated principal, never the body.
            cleared_by=principal.subject_id,
            reason=request.reason,
            principal_context=principal,
        )
        await db.commit()

        if state is None:
            await _record_boundary_event(
                db, "executed", ExecutionAction.KILL_SWITCH_CLEAR.value, principal,
                detail="no_active_switch", correlation_id=correlation_id,
            )
            return KillSwitchStatusResponse(is_active=False)

        await _record_boundary_event(
            db, "executed", ExecutionAction.KILL_SWITCH_CLEAR.value, principal,
            correlation_id=correlation_id,
        )
        return KillSwitchStatusResponse(
            is_active=False,
            reason=state.reason,
            activated_by=state.activated_by,
            activated_at=state.activated_at,
            cleared_by=state.cleared_by,
            cleared_at=state.cleared_at,
            scope=state.scope,
        )
    except ExecutionGuardError as exc:
        await _record_boundary_event(
            db, "refused", ExecutionAction.KILL_SWITCH_CLEAR.value, principal,
            detail=exc.decision.reason_code.value, correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Kill switch clear refused: {exc.decision.reason_code.value}",
        ) from exc
    except Exception as exc:
        await db.rollback()
        await _record_boundary_event(
            db, "failed", ExecutionAction.KILL_SWITCH_CLEAR.value, principal,
            detail=type(exc).__name__, correlation_id=correlation_id,
        )
        raise