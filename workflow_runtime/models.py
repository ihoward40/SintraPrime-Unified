"""Phase 5A Workflow Runtime — core data models.

All models are plain dataclasses for Phase 5A (no ORM dependency yet).
The checkpoint store serializes them to JSON. When the PostgreSQL
migration lands (Phase B+), these become SQLAlchemy-mapped.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------


class WorkflowStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_INPUT = "WAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class NodeStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_INPUT = "WAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class NodeType(StrEnum):
    DETERMINISTIC = "deterministic"
    AGENT = "agent"
    APPROVAL = "approval"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    HUMAN_INPUT = "human_input"


# ---------------------------------------------------------------------------
# Workflow definition (parsed from YAML)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodePolicy:
    authority: str = "default"
    approval_mode: str = "inherited"
    isolation: str = "worktree"
    max_parallel_nodes: int = 4


@dataclass(frozen=True)
class NodeDefaults:
    provider_class: str = "balanced"
    execution_profile: str = "standard"


@dataclass(frozen=True)
class BudgetSpec:
    max_tokens: int = 500_000
    max_provider_cost: float = 10.0
    max_wall_time_seconds: int = 3600
    max_agent_calls: int = 20


@dataclass
class ModelStrategy:
    initial: str = "economy"
    escalate_after_failures: int = 2
    escalation: list[str] = field(default_factory=lambda: ["balanced", "reasoning", "frontier"])


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    # For deterministic nodes: the registered operation key.
    action: str | None = None
    # For agent nodes: role, provider_class, fresh_context, etc.
    role: str | None = None
    provider_class: str | None = None
    model_class: str | None = None
    fresh_context: bool = False
    context_keys: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    # For conditional/loop nodes.
    branches: dict[str, str] = field(default_factory=dict)
    condition: str | None = None
    max_iterations: int | None = None
    exit_condition: str | None = None
    # For approval nodes.
    required_when: str | None = None
    # Dependencies (topological ordering).
    depends_on: list[str] = field(default_factory=list)
    # Budget override per node.
    budget: BudgetSpec | None = None
    # Metadata.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    name: str
    version: int
    description: str
    nodes: list[WorkflowNode]
    policy: NodePolicy = field(default_factory=NodePolicy)
    defaults: NodeDefaults = field(default_factory=NodeDefaults)
    budget: BudgetSpec = field(default_factory=BudgetSpec)
    model_strategy: ModelStrategy = field(default_factory=ModelStrategy)
    # Capabilities this workflow requires (for capability intersection).
    capabilities: list[str] = field(default_factory=list)
    # Source file for auditability.
    source_path: str = ""
    # SHA-256 of the YAML source for version pinning.
    source_hash: str = ""

    def node_by_id(self, node_id: str) -> WorkflowNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None


# ---------------------------------------------------------------------------
# Run-time models (persisted via checkpoint store)
# ---------------------------------------------------------------------------


@dataclass
class WorkflowRun:
    run_id: str
    workflow_name: str
    workflow_version: int
    workflow_hash: str
    tenant_id: str
    principal_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node_id: str | None = None
    node_runs: dict[str, WorkflowNodeRun] = field(default_factory=dict)
    budget: WorkflowBudget | None = None
    context: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None
    error: str | None = None
    cancellation_reason: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class WorkflowNodeRun:
    node_id: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.PENDING
    attempt: int = 0
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    receipt_hash: str | None = None


@dataclass
class WorkflowCheckpoint:
    """Immutable checkpoint snapshot — written to disk after every material node."""

    checkpoint_id: str
    run_id: str
    node_id: str
    status: WorkflowStatus
    node_statuses: dict[str, NodeStatus]
    budget_used: dict[str, Any]
    artifacts: dict[str, Any]
    snapshot_hash: str
    created_at: str


@dataclass
class WorkflowReceipt:
    """Immutable evidence receipt for a completed node."""

    receipt_id: str
    run_id: str
    node_id: str
    node_type: NodeType
    status: NodeStatus
    output_hash: str
    provider: str | None = None
    model: str | None = None
    tokens_used: int = 0
    cost: float = 0.0
    previous_hash: str | None = None
    receipt_hash: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowBudget:
    max_tokens: int = 500_000
    max_provider_cost: float = 10.0
    max_wall_time_seconds: int = 3600
    max_agent_calls: int = 20
    tokens_used: int = 0
    provider_cost_used: float = 0.0
    wall_time_used_seconds: float = 0.0
    agent_calls_used: int = 0

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.max_tokens - self.tokens_used)

    @property
    def cost_remaining(self) -> float:
        return max(0.0, self.max_provider_cost - self.provider_cost_used)

    def is_exceeded(self) -> str | None:
        if self.tokens_used >= self.max_tokens:
            return "tokens_exceeded"
        if self.provider_cost_used >= self.max_provider_cost:
            return "cost_exceeded"
        if self.wall_time_used_seconds >= self.max_wall_time_seconds:
            return "time_exceeded"
        if self.agent_calls_used >= self.max_agent_calls:
            return "agent_calls_exceeded"
        return None


# ---------------------------------------------------------------------------
# Context / contracts for agent nodes
# ---------------------------------------------------------------------------


@dataclass
class ContextPackage:
    """Scoped context delivered to an AgentNode — never the full OmniBrain."""

    run_id: str
    agent_role: str
    task: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    relevant_memories: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)


@dataclass
class AcceptanceRequirement:
    id: str
    requirement: str
    verification: str
    minimum_score: float = 7.0
    mandatory: bool = True


@dataclass
class AcceptanceContract:
    run_id: str
    workflow_name: str
    requirements: list[AcceptanceRequirement] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_json(data: dict[str, Any]) -> str:
    """Deterministic SHA-256 of a JSON-serialised dict."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_receipt_hash(receipt: WorkflowReceipt) -> str:
    """Hash a receipt including its previous_hash for chain integrity."""
    d = asdict(receipt)
    d.pop("receipt_hash", None)
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
