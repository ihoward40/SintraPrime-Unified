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
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["observatory"])

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
    db: AsyncSession = Depends(get_db),
):
    """Ingest a new observatory event (hash-chained)."""
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

    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "event_hash": event.event_hash,
        "previous_hash": event.previous_hash,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }


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
    db: AsyncSession = Depends(get_db),
):
    """Create a new observatory mission."""
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
    db: AsyncSession = Depends(get_db),
):
    """Request an approval."""
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

    return {
        "id": str(approval.id),
        "mission_id": str(approval.mission_id),
        "gate": approval.gate,
        "requester": approval.requester,
        "status": approval.status,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
    }


@router.post("/approvals/{approval_id}/decide", response_model=dict)
async def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve or deny a pending approval."""
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

    return {
        "id": str(approval.id),
        "mission_id": str(approval.mission_id),
        "gate": approval.gate,
        "status": approval.status,
        "reviewer": approval.reviewer,
        "notes": approval.notes,
    }


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
    db: AsyncSession = Depends(get_db),
):
    """Submit evidence for a mission."""
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

    return {
        "id": str(evidence.id),
        "mission_id": str(evidence.mission_id),
        "source": evidence.source,
        "content_type": evidence.content_type,
        "content_hash": evidence.content_hash,
        "verified": evidence.verified,
        "created_at": evidence.created_at.isoformat() if evidence.created_at else None,
    }


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
    db: AsyncSession = Depends(get_db),
):
    """Activate the emergency kill switch. Idempotent — re-activation returns existing state.
    Persists to database. Cancels all active missions. Fails closed."""
    count, affected_ids, state = await KillSwitchService.activate(
        db,
        reason=request.reason,
        activated_by=request.activated_by,
        scope=request.scope,
    )
    await db.commit()

    return KillSwitchResponse(
        activated=True,
        reason=state.reason,
        activated_by=state.activated_by,
        scope=state.scope,
        timestamp=state.activated_at,
        events_affected=count,
    )


@router.delete("/emergency/kill-switch", response_model=KillSwitchStatusResponse)
async def clear_kill_switch(
    request: KillSwitchClearRequest,
    db: AsyncSession = Depends(get_db),
):
    """Clear (deactivate) the kill switch. Requires authorized principal.
    Generates a KILL_SWITCH_CLEARED audit event. Returns None if no active switch exists."""
    state = await KillSwitchService.clear(
        db,
        cleared_by=request.cleared_by,
        reason=request.reason,
    )
    await db.commit()

    if state is None:
        return KillSwitchStatusResponse(is_active=False)

    return KillSwitchStatusResponse(
        is_active=False,
        reason=state.reason,
        activated_by=state.activated_by,
        activated_at=state.activated_at,
        cleared_by=state.cleared_by,
        cleared_at=state.cleared_at,
        scope=state.scope,
    )