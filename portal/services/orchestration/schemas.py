"""Typed contracts for the governed adaptive orchestration layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskType(StrEnum):
    CODING = "coding"
    RESEARCH = "research"
    LEGAL_INFORMATION = "legal-information"
    FINANCIAL_ANALYSIS = "financial-analysis"
    DOCUMENT_GENERATION = "document-generation"
    OPERATIONS = "operations"
    CUSTOMER_SUPPORT = "customer-support"
    MARKETING = "marketing"
    SECURITY = "security"
    MIXED = "mixed"


class Sensitivity(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    PRIVILEGED = "PRIVILEGED"


class Role(StrEnum):
    PLANNER = "PLANNER"
    THINKER = "THINKER"
    RESEARCHER = "RESEARCHER"
    WORKER = "WORKER"
    CHECKER = "CHECKER"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    GOVERNANCE_REVIEWER = "GOVERNANCE_REVIEWER"
    RECONCILER = "RECONCILER"
    PRINCIPAL = "PRINCIPAL"


class ExecutionMode(StrEnum):
    SINGLE = "SINGLE"
    PLAN_AND_EXECUTE = "PLAN_AND_EXECUTE"
    THINK_WORK_CHECK = "THINK_WORK_CHECK"
    PARALLEL_COMPARE = "PARALLEL_COMPARE"
    RESEARCH_SYNTHESIS = "RESEARCH_SYNTHESIS"
    CODE_REVIEW_LOOP = "CODE_REVIEW_LOOP"
    HIGH_ASSURANCE = "HIGH_ASSURANCE"


class NodeStatus(StrEnum):
    PLANNED = "PLANNED"
    WAITING = "WAITING"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class RunStatus(StrEnum):
    PLANNED = "PLANNED"
    WAITING = "WAITING"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    model_id: str
    supported_task_types: list[TaskType]
    context_window: int = Field(ge=1)
    structured_output: bool
    tool_support: list[str] = Field(default_factory=list)
    coding_strength: float = Field(ge=0.0, le=1.0)
    reasoning_strength: float = Field(ge=0.0, le=1.0)
    research_strength: float = Field(ge=0.0, le=1.0)
    verification_strength: float = Field(ge=0.0, le=1.0)
    latency_class: str
    input_cost: float = Field(ge=0.0)
    output_cost: float = Field(ge=0.0)
    availability: str
    data_policy: dict[str, Any] = Field(default_factory=dict)
    allowed_sensitivity: list[Sensitivity]
    enabled: bool = True
    confidence_history: dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    sensitivity: Sensitivity
    required_roles: list[Role]
    recommended_providers: list[str]
    expected_cost: float = Field(ge=0.0)
    expected_latency: str
    approval_requirement: bool
    evidence_requirement: str
    prohibited_actions: list[str]


class BudgetLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maximum_input_tokens: int = Field(default=8000, ge=1)
    maximum_output_tokens: int = Field(default=4000, ge=1)
    maximum_provider_cost: float = Field(default=0.0, ge=0.0)
    maximum_nodes: int = Field(default=12, ge=1)
    maximum_retries: int = Field(default=2, ge=0)
    maximum_execution_time: int = Field(default=300, ge=1)
    approved_providers: list[str] = Field(default_factory=list)
    approved_task_types: list[TaskType] = Field(default_factory=list)


class BudgetUsageSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limits: BudgetLimits
    input_tokens_used: int = Field(default=0, ge=0)
    output_tokens_used: int = Field(default=0, ge=0)
    provider_cost_used: float = Field(default=0.0, ge=0.0)
    nodes_used: int = Field(default=0, ge=0)
    retries_used: int = Field(default=0, ge=0)
    hard_limit_reached: bool = False
    limit_reason: str | None = None


class EvidenceReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    source_uri: str | None = None
    title: str | None = None
    excerpt_redacted: str | None = None
    citation: str | None = None
    evidence_quality: str
    verified: bool = False
    protected: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class FocusedInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exact_objective: str
    permitted_inputs: list[str]
    required_output_schema: dict[str, Any]
    constraints: list[str]
    prohibited_actions: list[str]
    evidence_requirements: list[str]
    completion_criteria: list[str]
    escalation_conditions: list[str]


class ExecutionNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    role: Role
    objective: str
    instructions: FocusedInstruction
    dependencies: list[str] = Field(default_factory=list)
    assigned_provider: str | None = None
    status: NodeStatus = NodeStatus.PLANNED
    retry_count: int = Field(default=0, ge=0)
    input_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    output_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[EvidenceReferenceSchema] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class RoutingDecisionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_providers: list[str]
    rejected_providers: list[dict[str, str]]
    selected_provider: str | None
    selection_reason: str
    policy_applied: dict[str, Any]
    estimated_cost: float = Field(ge=0.0)
    actual_cost: float | None = Field(default=None, ge=0.0)


class VerificationResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_quality: str
    unresolved_uncertainty: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    verification_result: str


class ReconciliationResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_result: dict[str, Any]
    supported_inference: list[str] = Field(default_factory=list)
    unresolved_issue: list[str] = Field(default_factory=list)
    principal_decision_required: list[str] = Field(default_factory=list)
    disputed_claims: list[dict[str, Any]] = Field(default_factory=list)
    final_confidence: float = Field(ge=0.0, le=1.0)


class ApprovalRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_action: str
    reason: str
    risk_level: str
    status: str = "REQUESTED"
    principal_id: str | None = None


class OrchestrationRunSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    objective: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    classification: ClassificationResult
    execution_mode: ExecutionMode
    status: RunStatus
    nodes: list[ExecutionNode] = Field(default_factory=list)
    routing_decisions: list[RoutingDecisionSchema] = Field(default_factory=list)
    budget: BudgetUsageSnapshot
    verification: list[VerificationResultSchema] = Field(default_factory=list)
    reconciliation: ReconciliationResultSchema | None = None
    approvals: list[ApprovalRequestSchema] = Field(default_factory=list)
