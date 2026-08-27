"""PostgreSQL-authoritative mappings for production control-plane persistence.

These mappings intentionally use a separate SQLAlchemy registry from the legacy
portal ``Base``. The raw SQL migration sequence is authoritative in production
and uses native PostgreSQL UUID columns, while the legacy ORM metadata still
models many identity keys as ``String(36)`` for historical create-all/test paths.
Keeping this registry separate lets the governed production authority path match
the deployed PostgreSQL schema without mutating the legacy metadata contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ProductionAuthorityBase(DeclarativeBase):
    """Independent registry matching the authoritative raw PostgreSQL schema."""


class ProductionMissionControlCommand(ProductionAuthorityBase):
    __tablename__ = "mission_control_commands"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    requested_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    command_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    audit_log_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductionMissionControlCommandEvent(ProductionAuthorityBase):
    __tablename__ = "mission_control_command_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionMissionControlCommandReceipt(ProductionAuthorityBase):
    __tablename__ = "mission_control_command_receipts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    receipt_type: Mapped[str] = mapped_column(String(40), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_log_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionAuditLog(ProductionAuthorityBase):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    actor_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    http_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionOrchestrationRun(ProductionAuthorityBase):
    __tablename__ = "orchestration_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    classification: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    final_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionOrchestrationNode(ProductionAuthorityBase):
    __tablename__ = "orchestration_nodes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    node_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    dependencies: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    assigned_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_artifacts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    output_artifacts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionOrchestrationEvent(ProductionAuthorityBase):
    __tablename__ = "orchestration_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionRoutingDecision(ProductionAuthorityBase):
    __tablename__ = "orchestration_routing_decisions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    node_pk: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    candidate_providers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    rejected_providers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_applied: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionVerificationResult(ProductionAuthorityBase):
    __tablename__ = "orchestration_verification_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    node_id: Mapped[str] = mapped_column(String(80), nullable=False)
    checker_node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_quality: Mapped[str] = mapped_column(String(40), nullable=False)
    unresolved_uncertainty: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    assumptions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    contradictions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    findings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionReconciliationResult(ProductionAuthorityBase):
    __tablename__ = "orchestration_reconciliation_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    reconciler_node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verified_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    supported_inference: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    unresolved_issues: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    disputed_claims: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    principal_decision_required: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionApprovalRequest(ProductionAuthorityBase):
    __tablename__ = "orchestration_approval_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    requested_action: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_by_role: Mapped[str] = mapped_column(String(40), nullable=False)
    principal_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionBudgetUsage(ProductionAuthorityBase):
    __tablename__ = "orchestration_budget_usage"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
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
    approved_providers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    approved_task_types: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
