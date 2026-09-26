"""
orchestration_api.py
====================
FastAPI router for the SintraPrime-Unified orchestration layer.

Endpoints:
  POST   /workflows/start
  GET    /workflows/{id}/status
  POST   /workflows/{id}/resume
  GET    /workflows/{id}/history
  GET    /agents/registry
  POST   /agents/message
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .a2a_protocol import A2AProtocol, MessageType, Priority, Message
from .a2a_governance import (
    ApprovalReceipt,
    ClaimStatus,
    DispatchAudit,
    EvidenceClaim,
    content_hash,
    validate_dispatch,
)
from .a2a_audit import A2AAuditStore
from .agent_policy import AgentPolicy
from .redis_a2a import RedisA2ATransport
from .durable_execution import (
    DurableWorkflowEngine,
    WorkflowStatus,
    HistoryEvent,
    WorkflowRecord,
    ActivityRecord,
)
from .langgraph_engine import (
    StateGraph,
    GraphState,
    InMemoryCheckpointer,
    create_legal_graph,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared singletons (in production these would be injected via DI)
# ---------------------------------------------------------------------------

_engine: Optional[DurableWorkflowEngine] = None
_a2a: Optional[A2AProtocol] = None
_redis_a2a: Optional[RedisA2ATransport] = None
_a2a_audit: Optional[A2AAuditStore] = None
_agent_policy: Optional[AgentPolicy] = None
_checkpointer: Optional[InMemoryCheckpointer] = None


def get_engine() -> DurableWorkflowEngine:
    """Return the portal-owned canonical durable engine when available."""
    try:
        from portal.services.orchestration_runtime import get_canonical_durable_engine
    except ImportError:
        # Standalone orchestration deployments retain a local persistent owner.
        global _engine
        if _engine is None:
            db_path = os.getenv("DURABLE_WORKFLOW_STORE_PATH", "orchestration_durable.db")
            _engine = DurableWorkflowEngine(db_path=db_path)
        return _engine
    return get_canonical_durable_engine()


def get_a2a() -> A2AProtocol:
    global _a2a
    if _a2a is None:
        _a2a = A2AProtocol()
    return _a2a


def get_redis_a2a() -> RedisA2ATransport:
    global _redis_a2a
    if _redis_a2a is None:
        _redis_a2a = RedisA2ATransport()
    return _redis_a2a


def get_a2a_audit() -> A2AAuditStore:
    global _a2a_audit
    if _a2a_audit is None:
        _a2a_audit = A2AAuditStore()
    return _a2a_audit


def get_agent_policy() -> AgentPolicy:
    global _agent_policy
    if _agent_policy is None:
        _agent_policy = AgentPolicy()
    return _agent_policy


def get_checkpointer() -> InMemoryCheckpointer:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = InMemoryCheckpointer()
    return _checkpointer


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class StartWorkflowRequest(BaseModel):
    workflow_type: str = Field(..., description="Registered workflow type name")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    workflow_id: Optional[str] = Field(None, description="Optional explicit workflow ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class StartWorkflowResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    started_at: float


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    state: Dict[str, Any]
    created_at: float
    updated_at: float
    completed_at: Optional[float]
    error: Optional[str]
    activity_count: int
    history_event_count: int


class ResumeWorkflowRequest(BaseModel):
    signal: Dict[str, Any] = Field(default_factory=dict, description="Signal payload to merge into state")


class ResumeWorkflowResponse(BaseModel):
    workflow_id: str
    resumed: bool
    message: str


class HistoryEventResponse(BaseModel):
    event_id: str
    event_type: str
    timestamp: float
    activity_name: Optional[str]
    payload: Dict[str, Any]
    attempt: int
    error: Optional[str]


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    capabilities: List[str]
    status: str
    endpoint: Optional[str]
    last_seen: float


class AgentRegistryResponse(BaseModel):
    agents: List[AgentInfo]
    total: int


class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str = Field("REQUEST", description="One of: REQUEST, RESPONSE, BROADCAST, DELEGATION, RESULT, ERROR")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field("NORMAL", description="One of: LOW, NORMAL, HIGH, CRITICAL")
    ttl: Optional[float] = Field(None, description="Time to live in seconds")
    correlation_id: Optional[str] = None
    headers: Dict[str, Any] = Field(default_factory=dict)
    external_action: bool = Field(False, description="True when this message requests an external side effect")
    approval: Optional[Dict[str, Any]] = Field(None, description="Approval receipt for an external action")
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    attachment_hashes: List[str] = Field(default_factory=list)


class SendMessageResponse(BaseModel):
    message_id: str
    correlation_id: str
    delivered: bool


class ReceiveMessageResponse(BaseModel):
    message: Optional[Dict[str, Any]]
    received: bool


class LangGraphRunRequest(BaseModel):
    case_id: Optional[str] = None
    practice_area: str = Field("general", description="e.g. trust, estate, probate, general")
    initial_state: Dict[str, Any] = Field(default_factory=dict)


class LangGraphRunResponse(BaseModel):
    run_id: str
    graph_id: str
    status: str
    visited_nodes: List[str]
    final_state: Dict[str, Any]
    duration_seconds: float
    checkpoints_saved: int


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


@router.post("/workflows/start", response_model=StartWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    req: StartWorkflowRequest,
    engine: DurableWorkflowEngine = Depends(get_engine),
) -> StartWorkflowResponse:
    """Start a new durable workflow."""
    try:
        wf_id = await engine.start_workflow(
            workflow_type=req.workflow_type,
            input_data=req.input_data,
            workflow_id=req.workflow_id,
            metadata=req.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to start workflow: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error starting workflow")

    return StartWorkflowResponse(
        workflow_id=wf_id,
        workflow_type=req.workflow_type,
        status=WorkflowStatus.RUNNING.value,
        started_at=time.time(),
    )


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    engine: DurableWorkflowEngine = Depends(get_engine),
) -> WorkflowStatusResponse:
    """Get the status and state of a workflow."""
    wf = engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    activities = engine.get_activities(workflow_id)
    history = engine.get_history(workflow_id)

    return WorkflowStatusResponse(
        workflow_id=wf.workflow_id,
        workflow_type=wf.workflow_type,
        status=wf.status.value,
        state=wf.state,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        completed_at=wf.completed_at,
        error=wf.error,
        activity_count=len(activities),
        history_event_count=len(history),
    )


@router.post("/workflows/{workflow_id}/resume", response_model=ResumeWorkflowResponse)
async def resume_workflow(
    workflow_id: str,
    req: ResumeWorkflowRequest,
    engine: DurableWorkflowEngine = Depends(get_engine),
) -> ResumeWorkflowResponse:
    """Resume a paused or waiting workflow with a signal."""
    wf = engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    resumed = await engine.resume_workflow(workflow_id, req.signal)
    return ResumeWorkflowResponse(
        workflow_id=workflow_id,
        resumed=resumed,
        message="Workflow resumed successfully" if resumed else "Workflow could not be resumed",
    )


@router.get("/workflows/{workflow_id}/history", response_model=List[HistoryEventResponse])
async def get_workflow_history(
    workflow_id: str,
    engine: DurableWorkflowEngine = Depends(get_engine),
) -> List[HistoryEventResponse]:
    """Get the full audit history of a workflow."""
    wf = engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    events = engine.get_history(workflow_id)
    return [
        HistoryEventResponse(
            event_id=e.event_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp,
            activity_name=e.activity_name,
            payload=e.payload,
            attempt=e.attempt,
            error=e.error,
        )
        for e in events
    ]


@router.get("/agents/registry", response_model=AgentRegistryResponse)
async def get_agent_registry(
    a2a: A2AProtocol = Depends(get_a2a),
) -> AgentRegistryResponse:
    """List all registered agents and their capabilities."""
    agents = a2a.get_all_agents()
    return AgentRegistryResponse(
        agents=[
            AgentInfo(
                agent_id=a.agent_id,
                name=a.name,
                capabilities=a.capabilities,
                status=a.status.value,
                endpoint=a.endpoint,
                last_seen=a.last_seen,
            )
            for a in agents
        ],
        total=len(agents),
    )


@router.post("/agents/message", response_model=SendMessageResponse)
async def send_agent_message(
    req: SendMessageRequest,
    a2a: A2AProtocol = Depends(get_a2a),
    redis_a2a: RedisA2ATransport = Depends(get_redis_a2a),
    audit_store: A2AAuditStore = Depends(get_a2a_audit),
    agent_policy: AgentPolicy = Depends(get_agent_policy),
) -> SendMessageResponse:
    """Send an A2A message between agents.

    ``A2A_BACKEND=redis`` makes delivery cross-process. The default remains
    the in-memory bus for embedded deployments and unit tests.
    """
    try:
        msg_type = MessageType(req.message_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid message_type: {req.message_type}")

    try:
        priority = Priority.from_str(req.priority)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {req.priority}")

    msg = Message(
        from_agent=req.from_agent,
        to_agent=req.to_agent,
        message_type=msg_type,
        payload=req.payload,
        priority=priority,
        ttl=req.ttl,
        correlation_id=req.correlation_id or uuid.uuid4().hex,
        headers=req.headers,
    )
    claims: list[EvidenceClaim] = []
    approval = None
    final_hash = content_hash(req.payload)
    try:
        agent_policy.authorize_sender(req.from_agent)
    except PermissionError as exc:
        audit_store.append(DispatchAudit(
            mission_id=msg.correlation_id,
            objective=msg.message_type.value,
            agents_used=(req.from_agent, req.to_agent),
            sources_used=(),
            claims_verified=(),
            risks_flagged=(),
            user_approval="no",
            external_action_taken=req.external_action,
            final_output_hash=final_hash,
            payload_hash=final_hash,
            status="blocked",
            reason_code="sender_policy_blocked",
            reason_detail=str(exc),
        ))
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        if req.approval:
            approval_data = dict(req.approval)
            approval_data["attachment_hashes"] = tuple(approval_data.get("attachment_hashes", []))
            approval = ApprovalReceipt(**approval_data)
        claims = [
            EvidenceClaim(
                claim=str(claim.get("claim", "")),
                status=ClaimStatus(claim.get("status", "UNVERIFIED")),
                source_refs=tuple(claim.get("source_refs", [])),
            )
            for claim in req.claims
        ]
        if req.external_action:
            audit_store.append(DispatchAudit(
                mission_id=msg.correlation_id,
                objective=msg.message_type.value,
                agents_used=(req.from_agent, req.to_agent),
                sources_used=tuple(source for claim in claims for source in claim.source_refs),
                claims_verified=tuple(claim.claim for claim in claims if claim.status == ClaimStatus.PROVEN),
                risks_flagged=tuple(claim.claim for claim in claims if claim.status in {ClaimStatus.RISKY, ClaimStatus.UNSUPPORTED}),
                user_approval="no",
                external_action_taken=True,
                final_output_hash=final_hash,
                payload_hash=final_hash,
                status="blocked",
                reason_code="external_actions_disabled",
                reason_detail="External actions remain disabled pending Patch B/C verification.",
            ))
            raise HTTPException(status_code=403, detail="Dispatch blocked: external actions are disabled")
        final_hash = validate_dispatch(
            payload=req.payload,
            recipient=req.to_agent,
            external_action=req.external_action,
            sender_agent_id=req.from_agent,
            approval=approval,
            claims=claims,
            attachment_hashes=req.attachment_hashes,
        )
        msg.headers["final_content_hash"] = final_hash
    except (PermissionError, ValueError) as exc:
        audit_store.append(DispatchAudit(
            mission_id=msg.correlation_id,
            objective=msg.message_type.value,
            agents_used=(req.from_agent, req.to_agent),
            sources_used=tuple(source for claim in claims for source in claim.source_refs),
            claims_verified=tuple(claim.claim for claim in claims if claim.status == ClaimStatus.PROVEN),
            risks_flagged=tuple(claim.claim for claim in claims if claim.status in {ClaimStatus.RISKY, ClaimStatus.UNSUPPORTED}),
            user_approval="yes" if approval else "no",
            external_action_taken=req.external_action,
            final_output_hash=final_hash,
            payload_hash=final_hash,
            status="blocked",
            reason_code="governance_blocked",
            reason_detail=str(exc),
        ))
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    audit_store.append(DispatchAudit(
        mission_id=msg.correlation_id,
        objective=msg.message_type.value,
        agents_used=(req.from_agent, req.to_agent),
        sources_used=tuple(source for claim in claims for source in claim.source_refs),
        claims_verified=tuple(claim.claim for claim in claims if claim.status == ClaimStatus.PROVEN),
        risks_flagged=tuple(claim.claim for claim in claims if claim.status in {ClaimStatus.RISKY, ClaimStatus.UNSUPPORTED}),
        user_approval="not required",
        external_action_taken=False,
        final_output_hash=final_hash,
        payload_hash=final_hash,
        status="accepted",
    ))
    if os.getenv("A2A_BACKEND", "memory").lower() == "redis":
        try:
            await redis_a2a.send(msg)
        except Exception as exc:
            audit_store.append(DispatchAudit(
                mission_id=msg.correlation_id,
                objective=msg.message_type.value,
                agents_used=(req.from_agent, req.to_agent),
                sources_used=tuple(source for claim in claims for source in claim.source_refs),
                claims_verified=tuple(claim.claim for claim in claims if claim.status == ClaimStatus.PROVEN),
                risks_flagged=(),
                user_approval="not required",
                external_action_taken=False,
                final_output_hash=final_hash,
                payload_hash=final_hash,
                status="delivery_failed",
                reason_code="redis_delivery_failed",
                reason_detail=str(exc),
            ))
            logger.exception("Redis A2A delivery failed")
            raise HTTPException(status_code=503, detail="Agent messaging backend unavailable") from exc
    else:
        await a2a.bus.publish(msg)

    audit_store.append(DispatchAudit(
        mission_id=msg.correlation_id,
        objective=msg.message_type.value,
        agents_used=(req.from_agent, req.to_agent),
        sources_used=tuple(source for claim in claims for source in claim.source_refs),
        claims_verified=tuple(claim.claim for claim in claims if claim.status == ClaimStatus.PROVEN),
        risks_flagged=(),
        user_approval="not required",
        external_action_taken=False,
        final_output_hash=final_hash,
        payload_hash=final_hash,
        status="delivered",
    ))

    return SendMessageResponse(
        message_id=msg.message_id,
        correlation_id=msg.correlation_id,
        delivered=True,
    )


@router.get("/agents/{agent_id}/messages/receive", response_model=ReceiveMessageResponse)
async def receive_agent_message(
    agent_id: str,
    timeout: int = 5,
    redis_a2a: RedisA2ATransport = Depends(get_redis_a2a),
) -> ReceiveMessageResponse:
    """Receive one cross-process message for an agent (Redis backend only)."""
    if os.getenv("A2A_BACKEND", "memory").lower() != "redis":
        raise HTTPException(status_code=409, detail="Set A2A_BACKEND=redis to use HTTP receive")
    if timeout < 0 or timeout > 30:
        raise HTTPException(status_code=400, detail="timeout must be between 0 and 30 seconds")
    try:
        message = await redis_a2a.receive(agent_id, timeout=timeout)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Redis A2A receive failed")
        raise HTTPException(status_code=503, detail="Agent messaging backend unavailable") from exc
    return ReceiveMessageResponse(
        message=message.to_dict() if message else None,
        received=message is not None,
    )


@router.post("/workflows/langgraph/run", response_model=LangGraphRunResponse)
async def run_langgraph_workflow(
    req: LangGraphRunRequest,
    checkpointer: InMemoryCheckpointer = Depends(get_checkpointer),
) -> LangGraphRunResponse:
    """Run the built-in SintraPrime legal LangGraph workflow."""
    compiled = create_legal_graph(checkpointer=checkpointer)
    initial = {
        "case_id": req.case_id or uuid.uuid4().hex[:8],
        "practice_area": req.practice_area,
        **req.initial_state,
    }
    run_id = uuid.uuid4().hex
    result = await compiled._graph.run(initial, run_id=run_id)

    return LangGraphRunResponse(
        run_id=result.run_id,
        graph_id=result.graph_id,
        status=result.status.value,
        visited_nodes=result.visited_nodes,
        final_state=result.final_state,
        duration_seconds=result.duration_seconds,
        checkpoints_saved=result.checkpoints_saved,
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "service": "SintraPrime-Unified Orchestration",
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> "FastAPI":
    """Create and configure the FastAPI application."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        raise RuntimeError("FastAPI is required. Install with: pip install fastapi")

    app = FastAPI(
        title="SintraPrime-Unified Orchestration API",
        description="Multi-agent orchestration with LangGraph + A2A + Durable Execution",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
