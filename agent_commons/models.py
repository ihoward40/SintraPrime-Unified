from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    OWNER = "owner"
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"


class LifecycleStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    ACK = "ACK"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    RESULT = "RESULT"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class RunStatus(str, Enum):
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
    to_agents: List[str]
    status: LifecycleStatus
    payload: Dict[str, Any]
    evidence: List[str] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    owner_decision_required: bool = False
    timestamp: float = field(default_factory=time.time)
    trace: Dict[str, Any] = field(default_factory=dict)


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
    acceptance_criteria: List[str]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = field(default_factory=lambda: f"SPU-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    status: RunStatus = RunStatus.PENDING
    builder_result: Optional[Dict[str, Any]] = None
    review_result: Optional[Dict[str, Any]] = None
    reconciliation: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
