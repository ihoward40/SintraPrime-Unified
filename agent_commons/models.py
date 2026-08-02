from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentRole(StrEnum):
    OWNER = "owner"
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"


class LifecycleStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    ACK = "ACK"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    RESULT = "RESULT"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MessageRecord:
    tenant_id: str
    workspace_id: str
    channel_id: str
    thread_id: str
    task_id: str
    from_agent: str
    to_agents: list[str]
    status: LifecycleStatus
    payload: dict[str, Any]
    evidence: list[str] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    owner_decision_required: bool = False
    timestamp: float = field(default_factory=time.time)
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupervisorRun:
    tenant_id: str
    workspace_id: str
    channel_id: str
    thread_id: str
    objective: str
    owner_agent: str
    builder_agent: str
    reviewer_agent: str
    acceptance_criteria: list[str]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = field(
        default_factory=lambda: f"SPU-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    )
    status: RunStatus = RunStatus.PENDING
    builder_result: dict[str, Any] | None = None
    review_result: dict[str, Any] | None = None
    reconciliation: dict[str, Any] | None = None
    approval_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
