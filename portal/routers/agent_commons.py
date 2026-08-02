from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_commons.adapters import MockAgentAdapter
from agent_commons.events import AgentCommonsEventBus
from agent_commons.models import RunStatus
from agent_commons.store import AgentCommonsStore
from agent_commons.supervisor import GovernedSupervisor
from portal.auth.rbac import (
    CurrentUser,
    Permission,
    Role,
    require_permissions,
    require_role,
)

router = APIRouter(prefix="/api/v1/agent-commons", tags=["agent-commons"])
ADAPTER_MODE_DISABLED = "disabled"
ADAPTER_MODE_MOCK = "mock"
SUPPORTED_ADAPTER_MODES = {ADAPTER_MODE_DISABLED, ADAPTER_MODE_MOCK}
STORAGE_MODE_SQLITE = "sqlite"
STORAGE_MODE_POSTGRES = "postgres"
EVENT_BACKEND_IN_PROCESS = "in_process"
EVENT_BACKEND_REDIS = "redis"
SSE_RETRY_MILLISECONDS = 3_000


class ObjectiveRequest(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=120)
    channel_id: str = Field(min_length=1, max_length=120)
    thread_id: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=3, max_length=20_000)
    builder_agent: str = Field(min_length=1, max_length=120)
    reviewer_agent: str = Field(min_length=1, max_length=120)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=50)
    requested_actions: list[str] = Field(default_factory=list, max_length=25)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ApprovalRequest(BaseModel):
    note: str = Field(default="", max_length=4_000)


def get_adapter_mode() -> str:
    mode = os.getenv("AGENT_COMMONS_ADAPTER_MODE", ADAPTER_MODE_DISABLED).strip().lower()
    if mode not in SUPPORTED_ADAPTER_MODES:
        raise RuntimeError(
            "AGENT_COMMONS_ADAPTER_MODE must be one of: "
            f"{', '.join(sorted(SUPPORTED_ADAPTER_MODES))}"
        )
    return mode


def _is_production() -> bool:
    value = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))
    return value.strip().lower() in {"prod", "production"}


def _worker_count() -> int:
    raw = os.getenv("WEB_CONCURRENCY", os.getenv("GUNICORN_WORKERS", "1"))
    try:
        return max(1, int(raw))
    except ValueError as exc:
        raise RuntimeError("worker count must be an integer") from exc


def get_storage_mode() -> str:
    return os.getenv("AGENT_COMMONS_STORAGE_MODE", STORAGE_MODE_SQLITE).strip().lower()


def get_event_backend() -> str:
    return os.getenv("AGENT_COMMONS_EVENT_BACKEND", EVENT_BACKEND_IN_PROCESS).strip().lower()


def validate_runtime_backends() -> None:
    storage_mode = get_storage_mode()
    event_backend = get_event_backend()
    if storage_mode not in {STORAGE_MODE_SQLITE, STORAGE_MODE_POSTGRES}:
        raise RuntimeError("unsupported Agent Commons storage mode")
    if event_backend not in {EVENT_BACKEND_IN_PROCESS, EVENT_BACKEND_REDIS}:
        raise RuntimeError("unsupported Agent Commons event backend")
    if _is_production() and storage_mode != STORAGE_MODE_POSTGRES:
        raise RuntimeError(
            "Agent Commons is disabled in production until shared PostgreSQL persistence is configured"
        )
    if (_is_production() or _worker_count() > 1) and event_backend != EVENT_BACKEND_REDIS:
        raise RuntimeError(
            "Agent Commons is disabled for production or multi-worker use until a shared event broker is configured"
        )
    if storage_mode == STORAGE_MODE_POSTGRES:
        raise RuntimeError(
            "Agent Commons PostgreSQL persistence is not implemented in Increment 1; feature remains fail-closed"
        )
    if event_backend == EVENT_BACKEND_REDIS:
        raise RuntimeError(
            "Agent Commons Redis event delivery is not implemented in Increment 1; feature remains fail-closed"
        )


@lru_cache(maxsize=1)
def get_store() -> AgentCommonsStore:
    validate_runtime_backends()
    database_path = os.getenv("AGENT_COMMONS_DB_PATH", "data/agent_commons.sqlite3")
    return AgentCommonsStore(database_path)


@lru_cache(maxsize=1)
def get_event_bus() -> AgentCommonsEventBus:
    validate_runtime_backends()
    return AgentCommonsEventBus()


@lru_cache(maxsize=1)
def get_supervisor() -> GovernedSupervisor:
    mode = get_adapter_mode()
    adapters = {}
    if mode == ADAPTER_MODE_MOCK:
        adapters = {
            "hermes": MockAgentAdapter(
                "hermes", ["orchestrate", "evidence"],
                {"summary": "Hermes mock adapter", "decision": "hold"},
            ),
            "codex": MockAgentAdapter(
                "codex", ["code", "test"],
                {"summary": "Codex mock adapter", "decision": "hold"},
            ),
            "claude-code": MockAgentAdapter(
                "claude-code", ["review", "architecture"],
                {
                    "summary": "Claude mock adapter",
                    "approved": False,
                    "material_disagreement": True,
                },
            ),
            "manus": MockAgentAdapter(
                "manus", ["research", "implement"],
                {"summary": "Manus mock adapter", "decision": "hold"},
            ),
        }
    return GovernedSupervisor(get_store(), adapters)


def _run_payload(run: Any) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "task_id": run.task_id,
        "tenant_id": run.tenant_id,
        "workspace_id": run.workspace_id,
        "channel_id": run.channel_id,
        "thread_id": run.thread_id,
        "objective": run.objective,
        "status": run.status.value,
        "builder_agent": run.builder_agent,
        "reviewer_agent": run.reviewer_agent,
        "builder_result": run.builder_result,
        "review_result": run.review_result,
        "reconciliation": run.reconciliation,
        "approval_id": run.approval_id,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


def _encode_sse(event: dict[str, Any], event_id: int) -> str:
    return (
        f"id: {event_id}\n"
        f"event: {event.get('type', 'message')}\n"
        f"retry: {SSE_RETRY_MILLISECONDS}\n"
        f"data: {json.dumps(event, default=str)}\n\n"
    )


@router.get("/agents")
async def list_agents(
    user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    supervisor: GovernedSupervisor = Depends(get_supervisor),
) -> dict[str, Any]:
    mode = get_adapter_mode()
    agents = []
    for agent_id, adapter in supervisor.adapters.items():
        health, capabilities = await asyncio.gather(adapter.health(), adapter.capabilities())
        agents.append(
            {
                "agent_id": agent_id,
                "health": {**health, "adapter_mode": mode},
                "capabilities": capabilities,
            }
        )
    return {
        "tenant_id": user.tenant_id,
        "adapter_mode": mode,
        "storage_mode": get_storage_mode(),
        "event_backend": get_event_backend(),
        "operational": bool(agents) and mode != ADAPTER_MODE_DISABLED,
        "agents": agents,
    }


@router.post("/objectives", status_code=status.HTTP_202_ACCEPTED)
async def create_objective(
    request: ObjectiveRequest,
    user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_CREATE)),
    supervisor: GovernedSupervisor = Depends(get_supervisor),
    events: AgentCommonsEventBus = Depends(get_event_bus),
) -> dict[str, Any]:
    if get_adapter_mode() == ADAPTER_MODE_DISABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent Commons adapters are disabled; configure an explicit adapter mode.",
        )
    try:
        run = await supervisor.run_objective(
            tenant_id=user.tenant_id,
            workspace_id=request.workspace_id,
            channel_id=request.channel_id,
            thread_id=request.thread_id,
            owner_agent=user.user_id,
            objective=request.objective,
            builder_agent=request.builder_agent,
            reviewer_agent=request.reviewer_agent,
            acceptance_criteria=request.acceptance_criteria,
            idempotency_key=request.idempotency_key,
            requested_actions=request.requested_actions,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = _run_payload(run)
    await events.publish(user.tenant_id, {"type": "supervisor.run.updated", "data": payload})
    return payload


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    store: AgentCommonsStore = Depends(get_store),
) -> dict[str, Any]:
    try:
        return _run_payload(store.get_run(user.tenant_id, run_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc


@router.get("/threads/{workspace_id}/{channel_id}/{thread_id}")
async def get_thread(
    workspace_id: str,
    channel_id: str,
    thread_id: str,
    user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    store: AgentCommonsStore = Depends(get_store),
) -> dict[str, Any]:
    return {
        "tenant_id": user.tenant_id,
        "workspace_id": workspace_id,
        "channel_id": channel_id,
        "thread_id": thread_id,
        "messages": store.get_thread(
            user.tenant_id, workspace_id, channel_id, thread_id
        ),
    }


@router.post("/runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    request: ApprovalRequest,
    user: CurrentUser = Depends(require_role(Role.FIRM_ADMIN)),
    supervisor: GovernedSupervisor = Depends(get_supervisor),
    events: AgentCommonsEventBus = Depends(get_event_bus),
) -> dict[str, Any]:
    run = supervisor.store.get_run(user.tenant_id, run_id)
    if run.status is not RunStatus.WAITING_APPROVAL or not run.approval_id:
        raise HTTPException(status_code=409, detail="run is not waiting for approval")
    updated = supervisor.approve(user.tenant_id, run_id, run.approval_id, request.note)
    payload = _run_payload(updated)
    await events.publish(
        user.tenant_id,
        {"type": "supervisor.run.approved", "actor_id": user.user_id, "data": payload},
    )
    return payload


@router.post("/runs/{run_id}/reject")
async def reject_run(
    run_id: str,
    request: ApprovalRequest,
    user: CurrentUser = Depends(require_role(Role.FIRM_ADMIN)),
    supervisor: GovernedSupervisor = Depends(get_supervisor),
    events: AgentCommonsEventBus = Depends(get_event_bus),
) -> dict[str, Any]:
    run = supervisor.store.get_run(user.tenant_id, run_id)
    if run.status is not RunStatus.WAITING_APPROVAL or not run.approval_id:
        raise HTTPException(status_code=409, detail="run is not waiting for approval")
    updated = supervisor.reject(user.tenant_id, run_id, run.approval_id, request.note)
    payload = _run_payload(updated)
    await events.publish(
        user.tenant_id,
        {"type": "supervisor.run.rejected", "actor_id": user.user_id, "data": payload},
    )
    return payload


@router.get("/events")
async def stream_events(
    heartbeat_seconds: float = Query(default=15.0, ge=5.0, le=60.0),
    user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    events: AgentCommonsEventBus = Depends(get_event_bus),
) -> StreamingResponse:
    async def event_stream():
        subscription = await events.open_subscription(user.tenant_id)
        event_id = 0
        try:
            while True:
                event = await events.next_event(subscription, heartbeat_seconds)
                if event is None:
                    yield f": heartbeat\nretry: {SSE_RETRY_MILLISECONDS}\n\n"
                    continue
                event_id += 1
                yield _encode_sse(event, event_id)
        finally:
            await events.close_subscription(subscription)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
