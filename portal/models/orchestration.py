"""Governed adaptive orchestration domain models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class OrchestrationTaskType(StrEnum):
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


class OrchestrationSensitivity(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    PRIVILEGED = "PRIVILEGED"


class OrchestrationRole(StrEnum):
    PLANNER = "PLANNER"
    THINKER = "THINKER"
    RESEARCHER = "RESEARCHER"
    WORKER = "WORKER"
    CHECKER = "CHECKER"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    GOVERNANCE_REVIEWER = "GOVERNANCE_REVIEWER"
    RECONCILER = "RECONCILER"
    PRINCIPAL = "PRINCIPAL"


class OrchestrationExecutionMode(StrEnum):
    SINGLE = "SINGLE"
    PLAN_AND_EXECUTE = "PLAN_AND_EXECUTE"
    THINK_WORK_CHECK = "THINK_WORK_CHECK"
    PARALLEL_COMPARE = "PARALLEL_COMPARE"
    RESEARCH_SYNTHESIS = "RESEARCH_SYNTHESIS"
    CODE_REVIEW_LOOP = "CODE_REVIEW_LOOP"
    HIGH_ASSURANCE = "HIGH_ASSURANCE"


class OrchestrationRunStatus(StrEnum):
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


class OrchestrationNodeStatus(StrEnum):
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


class ApprovalStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class OrchestrationRun(Base):
    """Tenant-scoped orchestration run with governed status and budgets."""

    __tablename__ = "orchestration_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=OrchestrationRunStatus.PLANNED)
    classification: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    policy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    nodes: Mapped[list[OrchestrationNode]] = relationship(
        "OrchestrationNode",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrchestrationNode.sequence",
    )
    events: Mapped[list[OrchestrationEvent]] = relationship(
        "OrchestrationEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrchestrationEvent.sequence",
    )
    budget_usage: Mapped[BudgetUsage | None] = relationship(
        "BudgetUsage",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_orchestration_runs_tenant_status", "tenant_id", "status"),
        Index("ix_orchestration_runs_tenant_created", "tenant_id", "created_at"),
        Index("ix_orchestration_runs_task_type", "tenant_id", "task_type"),
    )


class OrchestrationNode(Base):
    """DAG node for a bounded role assignment."""

    __tablename__ = "orchestration_nodes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dependencies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    assigned_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=OrchestrationNodeStatus.PLANNED)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_artifacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    output_artifacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    run: Mapped[OrchestrationRun] = relationship("OrchestrationRun", back_populates="nodes")
    routing_decisions: Mapped[list[RoutingDecision]] = relationship(
        "RoutingDecision",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("run_id", "node_id", name="uq_orchestration_nodes_run_node"),
        Index("ix_orchestration_nodes_run_status", "run_id", "status"),
        Index("ix_orchestration_nodes_provider", "assigned_provider_id", "assigned_model_id"),
    )


class OrchestrationEvent(Base):
    """Append-only orchestration audit event."""

    __tablename__ = "orchestration_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[OrchestrationRun] = relationship("OrchestrationRun", back_populates="events")

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_orchestration_events_run_seq"),
        Index("ix_orchestration_events_run", "run_id"),
        Index("ix_orchestration_events_type", "run_id", "event_type"),
    )


class ProviderDefinition(Base):
    """Declared provider capabilities; no provider is assumed mandatory."""

    __tablename__ = "orchestration_provider_definitions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(80), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    supported_task_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    structured_output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tool_support: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    coding_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasoning_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_class: Mapped[str] = mapped_column(String(40), nullable=False)
    input_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    output_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    availability: Mapped[str] = mapped_column(String(40), nullable=False)
    data_policy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    allowed_sensitivity: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_history: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider_id", "model_id", name="uq_orchestration_provider_model"),
        Index("ix_orchestration_provider_enabled", "enabled", "availability"),
    )


class RoutingDecision(Base):
    """Auditable routing decision for a node."""

    __tablename__ = "orchestration_routing_decisions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_pk: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_nodes.id", ondelete="CASCADE"), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    candidate_providers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rejected_providers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_applied: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    node: Mapped[OrchestrationNode | None] = relationship("OrchestrationNode", back_populates="routing_decisions")

    __table_args__ = (
        Index("ix_orchestration_routing_run_node", "run_id", "node_id"),
        Index("ix_orchestration_routing_selected", "selected_provider_id", "selected_model_id"),
    )


class VerificationResult(Base):
    """Independent checker result for a node output."""

    __tablename__ = "orchestration_verification_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(80), nullable=False)
    checker_node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_quality: Mapped[str] = mapped_column(String(40), nullable=False)
    unresolved_uncertainty: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    contradictions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_orchestration_verification_run_node", "run_id", "node_id"),)


class ReconciliationResult(Base):
    """Final reconciled result preserving disagreement and Principal gates."""

    __tablename__ = "orchestration_reconciliation_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    reconciler_node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verified_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supported_inference: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    unresolved_issues: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    disputed_claims: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    principal_decision_required: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_orchestration_reconciliation_run", "run_id"),)


class ApprovalRequest(Base):
    """Principal approval gate for high-risk orchestration actions."""

    __tablename__ = "orchestration_approval_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    requested_action: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=ApprovalStatus.REQUESTED)
    requested_by_role: Mapped[str] = mapped_column(String(40), nullable=False)
    principal_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_orchestration_approval_run_status", "run_id", "status"),
        Index("ix_orchestration_approval_principal", "principal_id", "status"),
    )


class OrchestrationLinkage(Base):
    """Remediation: Dedicated immutable linkage between events and nodes."""

    __tablename__ = "orchestration_linkages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_events.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_nodes.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_orchestration_linkage_event", "event_id"),
        Index("ix_orchestration_linkage_node", "node_id"),
        UniqueConstraint("event_id", "node_id", name="uq_orchestration_linkage_event_node"),
    )


class PrincipalAuthority(Base):
    """Remediation: Tenant-scoped human principal authority registration."""

    __tablename__ = "orchestration_principal_authorities"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="GLOBAL")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "scope", name="uq_orchestration_principal_auth"),
        Index("ix_orchestration_principal_tenant", "tenant_id", "is_active"),
    )


class BudgetUsage(Base):
    """Per-run budget ceilings and usage."""

    __tablename__ = "orchestration_budget_usage"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_provider_cost: Mapped[float] = mapped_column(Float, nullable=False)
    max_nodes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    max_execution_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_cost_used: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    nodes_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retries_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hard_limit_reached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    limit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_providers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_task_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    run: Mapped[OrchestrationRun] = relationship("OrchestrationRun", back_populates="budget_usage")


class EvidenceReference(Base):
    """Redacted evidence reference used by researchers, checkers, and reconcilers."""

    __tablename__ = "orchestration_evidence_references"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt_redacted: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_quality: Mapped[str] = mapped_column(String(40), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_orchestration_evidence_run_node", "run_id", "node_id"),
        Index("ix_orchestration_evidence_quality", "run_id", "evidence_quality"),
    )


class MemoryEntry(Base):
    """Remediation: Durable OmniBrain memory entry for Phase 10 flow."""

    __tablename__ = "memory_vault"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_memory_vault_tenant_type", "tenant_id", "type"),
    )
