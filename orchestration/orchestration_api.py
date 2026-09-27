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

# ruff: noqa: B008, B904

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .a2a_protocol import A2AProtocol, Message, MessageType, Priority
from .agent_commons import (
    AgentCommonsStore,
    AuthorizationError,
    CommonsError,
    IdempotencyConflictError,
    LoopDetectedError,
    MockAgentAdapter,
    Principal,
    SupervisorAgent,
)
from .durable_execution import (
    DurableWorkflowEngine,
    WorkflowStatus,
)
from .langgraph_engine import (
    InMemoryCheckpointer,
    create_legal_graph,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Shared singletons (in production these would be injected via DI)
# ---------------------------------------------------------------------------

_engine: DurableWorkflowEngine | None = None
_a2a: A2AProtocol | None = None
_checkpointer: InMemoryCheckpointer | None = None
_commons_store: AgentCommonsStore | None = None
_supervisor: SupervisorAgent | None = None


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


def get_checkpointer() -> InMemoryCheckpointer:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = InMemoryCheckpointer()
    return _checkpointer


def get_commons_store() -> AgentCommonsStore:
    global _commons_store
    if _commons_store is None:
        db_path = os.getenv("AGENT_COMMONS_DB_PATH", "agent_commons.db")
        ledger_dir = os.getenv("AGENT_COMMONS_LEDGER_DIR", ".mesh/ledger")
        _commons_store = AgentCommonsStore(db_path=db_path, ledger_dir=ledger_dir)
    return _commons_store


def get_supervisor(
    store: AgentCommonsStore = Depends(get_commons_store),
    a2a: A2AProtocol = Depends(get_a2a),
) -> SupervisorAgent:
    global _supervisor
    if _supervisor is None or _supervisor.store is not store or _supervisor.protocol is not a2a:
        _supervisor = SupervisorAgent(store, protocol=a2a)
        _supervisor.register_adapter(MockAgentAdapter("builder-agent", "Builder Agent", "worker", ["build"]))
        _supervisor.register_adapter(MockAgentAdapter("reviewer-agent", "Reviewer Agent", "reviewer", ["review"]))
        _supervisor.register_adapter(MockAgentAdapter("tasklet-agent", "Tasklet Agent", "worker", ["tasklet"]))
    return _supervisor


def get_commons_principal(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_principal_id: str = Header(..., alias="X-Principal-Id"),
    x_role: str = Header(..., alias="X-Role"),
) -> Principal:
    role = x_role.strip().lower()
    if role not in {"owner", "supervisor", "worker", "reviewer", "observer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unsupported commons role")
    return Principal(tenant_id=x_tenant_id, principal_id=x_principal_id, role=role)


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class StartWorkflowRequest(BaseModel):
    workflow_type: str = Field(..., description="Registered workflow type name")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    workflow_id: str | None = Field(None, description="Optional explicit workflow ID")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")


class StartWorkflowResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    started_at: float


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    status: str
    state: dict[str, Any]
    created_at: float
    updated_at: float
    completed_at: float | None
    error: str | None
    activity_count: int
    history_event_count: int


class ResumeWorkflowRequest(BaseModel):
    signal: dict[str, Any] = Field(default_factory=dict, description="Signal payload to merge into state")


class ResumeWorkflowResponse(BaseModel):
    workflow_id: str
    resumed: bool
    message: str


class HistoryEventResponse(BaseModel):
    event_id: str
    event_type: str
    timestamp: float
    activity_name: str | None
    payload: dict[str, Any]
    attempt: int
    error: str | None


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    capabilities: list[str]
    status: str
    endpoint: str | None
    last_seen: float


class AgentRegistryResponse(BaseModel):
    agents: list[AgentInfo]
    total: int


class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str = Field("REQUEST", description="One of: REQUEST, RESPONSE, BROADCAST, DELEGATION, RESULT, ERROR")
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = Field("NORMAL", description="One of: LOW, NORMAL, HIGH, CRITICAL")
    ttl: float | None = Field(None, description="Time to live in seconds")


class SendMessageResponse(BaseModel):
    message_id: str
    correlation_id: str
    delivered: bool


class LangGraphRunRequest(BaseModel):
    case_id: str | None = None
    practice_area: str = Field("general", description="e.g. trust, estate, probate, general")
    initial_state: dict[str, Any] = Field(default_factory=dict)


class LangGraphRunResponse(BaseModel):
    run_id: str
    graph_id: str
    status: str
    visited_nodes: list[str]
    final_state: dict[str, Any]
    duration_seconds: float
    checkpoints_saved: int


class CreateWorkspaceRequest(BaseModel):
    name: str
    community_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateChannelRequest(BaseModel):
    workspace_id: str
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateThreadRequest(BaseModel):
    workspace_id: str
    channel_id: str
    title: str
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateThreadMessageRequest(BaseModel):
    workspace_id: str
    channel_id: str
    task_id: str
    recipients: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    lifecycle_status: str = "IN_PROGRESS"
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)


class SupervisorObjectiveRequest(BaseModel):
    workspace_id: str
    channel_id: str
    objective: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    builder_capability: str = "build"
    reviewer_capability: str = "review"
    idempotency_key: str | None = None
    thread_title: str | None = None


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None
    idempotency_key: str | None = None


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


@router.get("/workflows/{workflow_id}/history", response_model=list[HistoryEventResponse])
async def get_workflow_history(
    workflow_id: str,
    engine: DurableWorkflowEngine = Depends(get_engine),
) -> list[HistoryEventResponse]:
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


@router.post("/commons/workspaces", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    req: CreateWorkspaceRequest,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("workspace:create")
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return store.create_workspace(principal.tenant_id, req.name, req.metadata, req.community_id)


@router.post("/commons/channels", status_code=status.HTTP_201_CREATED)
async def create_channel(
    req: CreateChannelRequest,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("channel:create")
        return store.create_channel(principal.tenant_id, req.workspace_id, req.name, req.metadata)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CommonsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/commons/threads", status_code=status.HTTP_201_CREATED)
async def create_thread(
    req: CreateThreadRequest,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("thread:create")
        thread = store.create_thread(
            principal.tenant_id,
            req.workspace_id,
            req.channel_id,
            req.title,
            task_id=req.task_id,
            metadata=req.metadata,
        )
        store.add_participant(
            principal.tenant_id,
            req.workspace_id,
            req.channel_id,
            thread["thread_id"],
            principal.principal_id,
            "human",
            principal.role,
            principal.principal_id,
        )
        return store.get_thread(thread["thread_id"], principal.tenant_id) or thread
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CommonsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/commons/threads/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
async def post_thread_message(
    thread_id: str,
    req: CreateThreadMessageRequest,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("message:create")
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    thread = store.get_thread(thread_id, principal.tenant_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if (
        req.workspace_id != thread["workspace_id"]
        or req.channel_id != thread["channel_id"]
        or req.task_id != thread["task_id"]
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Routing metadata does not match the thread")
    message = store.add_message(
        tenant_id=principal.tenant_id,
        workspace_id=req.workspace_id,
        channel_id=req.channel_id,
        thread_id=thread_id,
        task_id=req.task_id,
        sender=principal.principal_id,
        recipients=req.recipients,
        correlation_id=req.correlation_id or uuid.uuid4().hex,
        lifecycle_status=req.lifecycle_status,
        payload=req.payload,
        evidence=req.evidence,
        trace=req.trace,
    )
    store.add_task_event(
        tenant_id=principal.tenant_id,
        workspace_id=req.workspace_id,
        channel_id=req.channel_id,
        thread_id=thread_id,
        task_id=req.task_id,
        status=req.lifecycle_status,
        actor=principal.principal_id,
        details={"objective": thread["title"], "notes": "Manual thread message recorded."},
        evidence=req.evidence,
        run_id=req.trace.get("run_id"),
    )
    return message


@router.get("/commons/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("thread:read")
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    thread = store.get_thread(thread_id, principal.tenant_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.post("/supervisor/objectives", status_code=status.HTTP_201_CREATED)
async def submit_supervisor_objective(
    req: SupervisorObjectiveRequest,
    principal: Principal = Depends(get_commons_principal),
    supervisor: SupervisorAgent = Depends(get_supervisor),
) -> dict[str, Any]:
    try:
        return await supervisor.submit_objective(
            principal=principal,
            workspace_id=req.workspace_id,
            channel_id=req.channel_id,
            objective=req.objective,
            acceptance_criteria=req.acceptance_criteria,
            builder_capability=req.builder_capability,
            reviewer_capability=req.reviewer_capability,
            idempotency_key=req.idempotency_key,
            thread_title=req.thread_title,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LoopDetectedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommonsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/supervisor/runs/{run_id}/approve")
async def approve_supervisor_run(
    run_id: str,
    req: ApprovalDecisionRequest,
    principal: Principal = Depends(get_commons_principal),
    supervisor: SupervisorAgent = Depends(get_supervisor),
) -> dict[str, Any]:
    try:
        return supervisor.decide_run(
            principal=principal,
            run_id=run_id,
            decision="approve",
            reason=req.reason,
            idempotency_key=req.idempotency_key,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommonsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/supervisor/runs/{run_id}/reject")
async def reject_supervisor_run(
    run_id: str,
    req: ApprovalDecisionRequest,
    principal: Principal = Depends(get_commons_principal),
    supervisor: SupervisorAgent = Depends(get_supervisor),
) -> dict[str, Any]:
    try:
        return supervisor.decide_run(
            principal=principal,
            run_id=run_id,
            decision="reject",
            reason=req.reason,
            idempotency_key=req.idempotency_key,
        )
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommonsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/supervisor/runs/{run_id}/trace")
async def get_supervisor_run_trace(
    run_id: str,
    principal: Principal = Depends(get_commons_principal),
    store: AgentCommonsStore = Depends(get_commons_store),
) -> dict[str, Any]:
    try:
        principal.ensure("trace:read")
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    trace = store.get_run_trace(run_id, principal.tenant_id)
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run trace not found")
    return trace


@router.get("/commons/agents/{agent_id}/health")
async def get_agent_health(
    agent_id: str,
    principal: Principal = Depends(get_commons_principal),
    supervisor: SupervisorAgent = Depends(get_supervisor),
) -> dict[str, Any]:
    try:
        principal.ensure("agent:health")
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    health = supervisor.agent_health(agent_id)
    if not health:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return health


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
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "service": "SintraPrime-Unified Orchestration",
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:
        raise RuntimeError("FastAPI is required. Install with: pip install fastapi") from exc

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
