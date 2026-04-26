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
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .a2a_protocol import A2AProtocol, MessageType, Priority, Message
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
_checkpointer: Optional[InMemoryCheckpointer] = None


def get_engine() -> DurableWorkflowEngine:
    global _engine
    if _engine is None:
        _engine = DurableWorkflowEngine()
    return _engine


def get_a2a() -> A2AProtocol:
    global _a2a
    if _a2a is None:
        _a2a = A2AProtocol()
    return _a2a


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


class SendMessageResponse(BaseModel):
    message_id: str
    correlation_id: str
    delivered: bool


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
) -> SendMessageResponse:
    """Send an A2A message between agents."""
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
    )
    await a2a.bus.publish(msg)

    return SendMessageResponse(
        message_id=msg.message_id,
        correlation_id=msg.correlation_id,
        delivered=True,
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
