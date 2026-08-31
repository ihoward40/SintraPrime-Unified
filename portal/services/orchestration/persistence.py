"""Durable persistence for governed mock orchestration runs."""

from __future__ import annotations

import uuid
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from portal.models.orchestration import (
    ApprovalRequest,
    BudgetUsage,
    EvidenceReference,
    OrchestrationEvent,
    OrchestrationNode,
    OrchestrationRun,
    ReconciliationResult,
    RoutingDecision,
    VerificationResult,
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


async def save_run(db: AsyncSession, run: dict[str, Any]) -> dict[str, Any]:
    """
    Remediation: Upsert the durable projection for an orchestration run.
    Ensures append-only audit integrity by avoiding deletion of existing records.
    """
    from ..remediation_service import remediation
    
    run_id = run["run_id"]
    tenant_id = run["tenant_id"]
    
    # 1. REMEDIATION: Redact all boundaries before persistence
    run = remediation.redact_boundaries(run)
    
    classification = run.get("classification", {})
    now = datetime.now(UTC)
    
    # Check for existing run
    logger.info(f"[PERSISTENCE] Checking for existing run {run_id} for tenant {tenant_id}")
    existing_run = await db.get(OrchestrationRun, run_id)
    if existing_run:
        logger.info(f"[PERSISTENCE] Found existing run {run_id}")
        existing_run.status = run.get("status", existing_run.status)
        existing_run.final_result = run.get("reconciliation", existing_run.final_result)
        existing_run.cancellation_reason = run.get("cancellation_reason", existing_run.cancellation_reason)
        existing_run.started_at = _parse_dt(run.get("started_at")) or existing_run.started_at
        existing_run.completed_at = _parse_dt(run.get("completed_at")) or existing_run.completed_at
        existing_run.updated_at = now
    else:
        db.add(
            OrchestrationRun(
                id=run_id,
                tenant_id=tenant_id,
                created_by=run.get("created_by"),
                objective=run["objective"],
                constraints=run.get("constraints", {}),
                task_type=classification.get("task_type", "mixed"),
                sensitivity=classification.get("sensitivity", "INTERNAL"),
                execution_mode=run.get("execution_mode", "THINK_WORK_CHECK"),
                status=run.get("status", "PLANNED"),
                classification=classification,
                policy={"mock_only": True, "external_providers_enabled": False},
                final_result=run.get("reconciliation"),
                approval_required=bool(run.get("approvals")),
                cancellation_reason=run.get("cancellation_reason"),
                started_at=_parse_dt(run.get("started_at")),
                completed_at=_parse_dt(run.get("completed_at")),
                created_at=_parse_dt(run.get("created_at")) or now,
                updated_at=now,
            )
        )

    # 2. REMEDIATION: Upsert nodes and evidence
    for sequence, node in enumerate(run.get("nodes", []), start=1):
        node_id = node["node_id"]
        # Finding existing node by run_id and node_id (logical ID)
        stmt = select(OrchestrationNode).where(
            OrchestrationNode.run_id == run_id, 
            OrchestrationNode.node_id == node_id
        )
        res = await db.execute(stmt)
        existing_node = res.scalar_one_or_none()
        
        if existing_node:
            existing_node.status = node.get("status", existing_node.status)
            existing_node.output_artifacts = node.get("output_artifacts", existing_node.output_artifacts)
            existing_node.confidence = node.get("confidence", existing_node.confidence)
            existing_node.error = node.get("error", existing_node.error)
            existing_node.started_at = _parse_dt(node.get("started_at")) or existing_node.started_at
            existing_node.completed_at = _parse_dt(node.get("completed_at")) or existing_node.completed_at
            existing_node.updated_at = now
            node_pk = existing_node.id
        else:
            node_pk = str(uuid.uuid4())
            db.add(
                OrchestrationNode(
                    id=node_pk,
                    run_id=run_id,
                    node_id=node_id,
                    sequence=sequence,
                    role=node["role"],
                    objective=node["objective"],
                    instructions=node.get("instructions", {}),
                    dependencies=node.get("dependencies", []),
                    assigned_provider_id=node.get("assigned_provider"),
                    status=node.get("status", "PLANNED"),
                    retry_count=node.get("retry_count", 0),
                    input_artifacts=node.get("input_artifacts", []),
                    output_artifacts=node.get("output_artifacts", []),
                    confidence=node.get("confidence"),
                    evidence=node.get("evidence", []),
                    started_at=_parse_dt(node.get("started_at")),
                    completed_at=_parse_dt(node.get("completed_at")),
                    error=node.get("error"),
                    created_at=now,
                    updated_at=now,
                )
            )
        
        # Evidence is typically append-only in this context
        for evidence in node.get("evidence", []):
            # Simple check to avoid duplicates if re-saving
            # (In production, would use a hash or unique source_uri)
            db.add(_evidence_reference_from_dict(run_id, node_id, evidence))

    # 3. REMEDIATION: Append-only events and dedicated linkage
    from ...models.orchestration import OrchestrationEvent, OrchestrationLinkage
    for idx, event in enumerate(run.get("events", []), start=1):
        event_id = event.get("id") or str(uuid.uuid4())
        
        # Check if event already exists to maintain append-only idempotency
        stmt = select(OrchestrationEvent).where(OrchestrationEvent.id == event_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            continue

        db.add(
            OrchestrationEvent(
                id=event_id,
                run_id=run_id,
                node_id=event.get("node_id"),
                sequence=event.get("sequence") or idx,
                event_type=event["event_type"],
                actor_role=event.get("actor_role"),
                payload=event.get("payload", {}),
                previous_event_hash=event.get("previous_event_hash"),
                event_hash=event["event_hash"],
                created_at=_parse_dt(event.get("created_at")) or now,
            )
        )
        
        # 4. REMEDIATION: Dedicated immutable event-to-node linkage
        if event.get("node_id"):
            # Find the node PK
            stmt = select(OrchestrationNode.id).where(
                OrchestrationNode.run_id == run_id, 
                OrchestrationNode.node_id == event["node_id"]
            )
            res = await db.execute(stmt)
            node_pk = res.scalar_one_or_none()
            
            if node_pk:
                db.add(
                    OrchestrationLinkage(
                        id=str(uuid.uuid4()),
                        event_id=event_id,
                        node_id=node_pk,
                        tenant_id=tenant_id,
                        linked_at=now
                    )
                )

    budget = run.get("budget", {})
    limits = budget.get("limits", {})
    
    stmt = select(BudgetUsage).where(BudgetUsage.run_id == run_id)
    res = await db.execute(stmt)
    existing_budget = res.scalar_one_or_none()
    
    if existing_budget:
        existing_budget.input_tokens_used = budget.get("input_tokens_used", existing_budget.input_tokens_used)
        existing_budget.output_tokens_used = budget.get("output_tokens_used", existing_budget.output_tokens_used)
        existing_budget.provider_cost_used = budget.get("provider_cost_used", existing_budget.provider_cost_used)
        existing_budget.nodes_used = budget.get("nodes_used", existing_budget.nodes_used)
        existing_budget.retries_used = budget.get("retries_used", existing_budget.retries_used)
        existing_budget.hard_limit_reached = budget.get("hard_limit_reached", existing_budget.hard_limit_reached)
        existing_budget.limit_reason = budget.get("limit_reason", existing_budget.limit_reason)
        existing_budget.updated_at = now
    else:
        db.add(
            BudgetUsage(
                id=str(uuid.uuid4()),
                run_id=run_id,
                max_input_tokens=limits.get("maximum_input_tokens", 8000),
                max_output_tokens=limits.get("maximum_output_tokens", 4000),
                max_provider_cost=limits.get("maximum_provider_cost", 0.0),
                max_nodes=limits.get("maximum_nodes", 12),
                max_retries=limits.get("maximum_retries", 2),
                max_execution_seconds=limits.get("maximum_execution_time", 300),
                input_tokens_used=budget.get("input_tokens_used", 0),
                output_tokens_used=budget.get("output_tokens_used", 0),
                provider_cost_used=budget.get("provider_cost_used", 0.0),
                nodes_used=budget.get("nodes_used", 0),
                retries_used=budget.get("retries_used", 0),
                hard_limit_reached=budget.get("hard_limit_reached", False),
                limit_reason=budget.get("limit_reason"),
                approved_providers=limits.get("approved_providers", []),
                approved_task_types=limits.get("approved_task_types", []),
                created_at=now,
                updated_at=now,
            )
        )

    for decision in run.get("routing_decisions", []):
        node_id = decision.get("node_id")
        stmt = select(RoutingDecision).where(RoutingDecision.run_id == run_id, RoutingDecision.node_id == node_id)
        res = await db.execute(stmt)
        existing_decision = res.scalar_one_or_none()
        
        if existing_decision:
            existing_decision.actual_cost = decision.get("actual_cost", existing_decision.actual_cost)
        else:
            selected = decision.get("selected_provider")
            db.add(
                RoutingDecision(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    node_pk=None,
                    node_id=node_id,
                    selected_provider_id=selected,
                    selected_model_id=None,
                    candidate_providers=decision.get("candidate_providers", []),
                    rejected_providers=decision.get("rejected_providers", []),
                    selection_reason=decision.get("selection_reason", "No selection reason recorded"),
                    policy_applied=decision.get("policy_applied", {}),
                    estimated_cost=decision.get("estimated_cost", 0.0),
                    actual_cost=decision.get("actual_cost"),
                    created_at=now
                )
            )

    for verification in run.get("verification", []):
        node_id = verification.get("node_id", "checker")
        stmt = select(VerificationResult).where(VerificationResult.run_id == run_id, VerificationResult.node_id == node_id)
        res = await db.execute(stmt)
        existing_verification = res.scalar_one_or_none()
        
        if existing_verification:
            existing_verification.verification_status = verification.get("verification_result", existing_verification.verification_status)
            existing_verification.confidence_score = verification.get("confidence_score", existing_verification.confidence_score)
        else:
            db.add(
                VerificationResult(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    node_id=node_id,
                    checker_node_id=verification.get("checker_node_id"),
                    verification_status=verification.get("verification_result", "unknown"),
                    confidence_score=verification.get("confidence_score", 0.0),
                    evidence_quality=verification.get("evidence_quality", "unknown"),
                    unresolved_uncertainty=verification.get("unresolved_uncertainty", []),
                    assumptions=verification.get("assumptions", []),
                    contradictions=verification.get("contradictions", []),
                    findings=verification.get("findings", []),
                    created_at=now
                )
            )

    reconciliation = run.get("reconciliation")
    if reconciliation:
        stmt = select(ReconciliationResult).where(ReconciliationResult.run_id == run_id)
        res = await db.execute(stmt)
        existing_reconciliation = res.scalar_one_or_none()
        
        if existing_reconciliation:
            existing_reconciliation.verified_result = reconciliation.get("verified_result", existing_reconciliation.verified_result)
            existing_reconciliation.final_confidence = reconciliation.get("final_confidence", existing_reconciliation.final_confidence)
        else:
            db.add(
                ReconciliationResult(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    reconciler_node_id=reconciliation.get("reconciler_node_id"),
                    verified_result=reconciliation.get("verified_result", {}),
                    supported_inference=reconciliation.get("supported_inference", []),
                    unresolved_issues=reconciliation.get("unresolved_issue", []),
                    disputed_claims=reconciliation.get("disputed_claims", []),
                    principal_decision_required=reconciliation.get("principal_decision_required", []),
                    final_confidence=reconciliation.get("final_confidence", 0.0),
                    created_at=now
                )
            )

    for approval in run.get("approvals", []):
        approval_id = approval.get("approval_id") or str(uuid.uuid4())
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            continue
            
        db.add(
            ApprovalRequest(
                id=approval_id,
                run_id=run_id,
                node_id=approval.get("node_id"),
                requested_action=approval.get("requested_action", "Approve governed orchestration result"),
                reason=approval.get("reason", "Approval required by policy"),
                risk_level=approval.get("risk_level", "controlled"),
                status=approval.get("status", "REQUESTED"),
                requested_by_role=approval.get("requested_by_role", "GOVERNANCE_REVIEWER"),
                principal_id=approval.get("principal_id"),
                decided_at=_parse_dt(approval.get("decided_at")),
                decision_reason=approval.get("decision_reason"),
                created_at=now,
                updated_at=now
            )
        )

    await db.flush()
    return run


async def get_run(db: AsyncSession, run_id: str, tenant_id: str) -> dict[str, Any] | None:
    result = await db.execute(
        select(OrchestrationRun)
        .options(selectinload(OrchestrationRun.nodes), selectinload(OrchestrationRun.events), selectinload(OrchestrationRun.budget_usage))
        .where(OrchestrationRun.id == run_id, OrchestrationRun.tenant_id == tenant_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return await _run_to_dict(db, row)


async def get_events(db: AsyncSession, run_id: str, tenant_id: str) -> list[dict[str, Any]] | None:
    run = await get_run(db, run_id, tenant_id)
    return None if run is None else run["events"]


async def _delete_existing_projection(db: AsyncSession, run_id: str) -> None:
    for model in (
        EvidenceReference,
        BudgetUsage,
        ApprovalRequest,
        ReconciliationResult,
        VerificationResult,
        RoutingDecision,
        OrchestrationEvent,
        OrchestrationNode,
        OrchestrationRun,
    ):
        await db.execute(delete(model).where(model.run_id == run_id) if model is not OrchestrationRun else delete(model).where(model.id == run_id))


async def _run_to_dict(db: AsyncSession, row: OrchestrationRun) -> dict[str, Any]:
    run_id = row.id
    routing = (await db.execute(select(RoutingDecision).where(RoutingDecision.run_id == run_id))).scalars().all()
    verification = (await db.execute(select(VerificationResult).where(VerificationResult.run_id == run_id))).scalars().all()
    reconciliation = (await db.execute(select(ReconciliationResult).where(ReconciliationResult.run_id == run_id))).scalars().first()
    approvals = (await db.execute(select(ApprovalRequest).where(ApprovalRequest.run_id == run_id))).scalars().all()

    return {
        "run_id": row.id,
        "tenant_id": row.tenant_id,
        "created_by": row.created_by,
        "objective": row.objective,
        "constraints": row.constraints or {},
        "classification": row.classification or {},
        "execution_mode": row.execution_mode,
        "status": row.status,
        "nodes": [_node_to_dict(node) for node in row.nodes],
        "routing_decisions": [_routing_to_dict(item) for item in routing],
        "budget": _budget_to_dict(row.budget_usage),
        "verification": [_verification_to_dict(item) for item in verification],
        "reconciliation": _reconciliation_to_dict(reconciliation) if reconciliation else None,
        "approvals": [_approval_to_dict(item) for item in approvals],
        "events": [_event_to_dict(event) for event in row.events],
        "cancellation_reason": row.cancellation_reason,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _node_to_dict(node: OrchestrationNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "role": node.role,
        "objective": node.objective,
        "instructions": node.instructions or {},
        "dependencies": node.dependencies or [],
        "assigned_provider": node.assigned_provider_id,
        "status": node.status,
        "retry_count": node.retry_count,
        "input_artifacts": node.input_artifacts or [],
        "output_artifacts": node.output_artifacts or [],
        "confidence": node.confidence,
        "evidence": node.evidence or [],
        "started_at": _iso(node.started_at),
        "completed_at": _iso(node.completed_at),
        "error": node.error,
    }


def _event_to_dict(event: OrchestrationEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "event_type": event.event_type,
        "actor_role": event.actor_role,
        "payload": event.payload or {},
        "previous_event_hash": event.previous_event_hash,
        "event_hash": event.event_hash,
        "created_at": _iso(event.created_at),
    }


def _budget_to_dict(budget: BudgetUsage | None) -> dict[str, Any]:
    if budget is None:
        return {"limits": {}}
    return {
        "limits": {
            "maximum_input_tokens": budget.max_input_tokens,
            "maximum_output_tokens": budget.max_output_tokens,
            "maximum_provider_cost": budget.max_provider_cost,
            "maximum_nodes": budget.max_nodes,
            "maximum_retries": budget.max_retries,
            "maximum_execution_time": budget.max_execution_seconds,
            "approved_providers": budget.approved_providers or [],
            "approved_task_types": budget.approved_task_types or [],
        },
        "input_tokens_used": budget.input_tokens_used,
        "output_tokens_used": budget.output_tokens_used,
        "provider_cost_used": budget.provider_cost_used,
        "nodes_used": budget.nodes_used,
        "retries_used": budget.retries_used,
        "hard_limit_reached": budget.hard_limit_reached,
        "limit_reason": budget.limit_reason,
    }


def _routing_to_dict(item: RoutingDecision) -> dict[str, Any]:
    return {
        "node_id": item.node_id,
        "candidate_providers": item.candidate_providers or [],
        "rejected_providers": item.rejected_providers or [],
        "selected_provider": item.selected_provider_id,
        "selection_reason": item.selection_reason,
        "policy_applied": item.policy_applied or {},
        "estimated_cost": item.estimated_cost,
        "actual_cost": item.actual_cost,
    }


def _verification_to_dict(item: VerificationResult) -> dict[str, Any]:
    return {
        "node_id": item.node_id,
        "checker_node_id": item.checker_node_id,
        "confidence_score": item.confidence_score,
        "evidence_quality": item.evidence_quality,
        "unresolved_uncertainty": item.unresolved_uncertainty or [],
        "assumptions": item.assumptions or [],
        "contradictions": item.contradictions or [],
        "findings": item.findings or [],
        "verification_result": item.verification_status,
    }


def _reconciliation_to_dict(item: ReconciliationResult) -> dict[str, Any]:
    return {
        "verified_result": item.verified_result or {},
        "supported_inference": item.supported_inference or [],
        "unresolved_issue": item.unresolved_issues or [],
        "disputed_claims": item.disputed_claims or [],
        "principal_decision_required": item.principal_decision_required or [],
        "final_confidence": item.final_confidence,
    }


def _approval_to_dict(item: ApprovalRequest) -> dict[str, Any]:
    return {
        "approval_id": item.id,
        "node_id": item.node_id,
        "requested_action": item.requested_action,
        "reason": item.reason,
        "risk_level": item.risk_level,
        "status": item.status,
        "requested_by_role": item.requested_by_role,
        "principal_id": item.principal_id,
        "decided_at": _iso(item.decided_at),
        "decision_reason": item.decision_reason,
    }


def _evidence_reference_from_dict(run_id: str, node_id: str, evidence: dict[str, Any]) -> EvidenceReference:
    return EvidenceReference(
        id=str(uuid.uuid4()),
        run_id=run_id,
        node_id=node_id,
        source_type=evidence.get("source_type", "mock"),
        source_uri=evidence.get("source_uri"),
        title=evidence.get("title"),
        excerpt_redacted=evidence.get("excerpt_redacted"),
        citation=evidence.get("citation"),
        evidence_quality=evidence.get("evidence_quality", "unknown"),
        verified=evidence.get("verified", False),
        protected=evidence.get("protected", False),
        metadata_json=evidence.get("metadata", {}),
    )
