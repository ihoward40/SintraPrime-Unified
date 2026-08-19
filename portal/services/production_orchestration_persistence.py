"""PostgreSQL-authoritative persistence for the activated durable orchestration path."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.production_authority import (
    ProductionApprovalRequest as ApprovalRequest,
    ProductionBudgetUsage as BudgetUsage,
    ProductionOrchestrationEvent as OrchestrationEvent,
    ProductionOrchestrationNode as OrchestrationNode,
    ProductionOrchestrationRun as OrchestrationRun,
    ProductionReconciliationResult as ReconciliationResult,
    ProductionRoutingDecision as RoutingDecision,
    ProductionVerificationResult as VerificationResult,
)
from .remediation_service import remediation


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


async def save_production_run(db: AsyncSession, run: dict[str, Any]) -> dict[str, Any]:
    """Persist one newly-created deterministic run into the raw production schema."""
    run = remediation.redact_boundaries(run)
    run_id = str(run["run_id"])
    classification = run.get("classification", {})
    now = datetime.now(UTC)

    db.add(
        OrchestrationRun(
            id=run_id,
            tenant_id=str(run["tenant_id"]),
            created_by=str(run["created_by"]) if run.get("created_by") else None,
            objective=run["objective"],
            constraints=run.get("constraints", {}),
            task_type=classification.get("task_type", "mixed"),
            sensitivity=classification.get("sensitivity", "INTERNAL"),
            execution_mode=run.get("execution_mode", "THINK_WORK_CHECK"),
            status=run.get("status", "PLANNED"),
            classification=classification,
            policy={
                "durable_authority": "postgresql-raw-schema",
                "external_providers_enabled": False,
            },
            final_result=run.get("reconciliation"),
            approval_required=bool(run.get("approvals")),
            cancellation_reason=run.get("cancellation_reason"),
            started_at=_parse_dt(run.get("started_at")),
            completed_at=_parse_dt(run.get("completed_at")),
            created_at=_parse_dt(run.get("created_at")) or now,
            updated_at=now,
        )
    )

    for sequence, node in enumerate(run.get("nodes", []), start=1):
        db.add(
            OrchestrationNode(
                id=str(uuid.uuid4()),
                run_id=run_id,
                node_id=node["node_id"],
                sequence=sequence,
                role=node["role"],
                objective=node["objective"],
                instructions=node.get("instructions", {}),
                dependencies=node.get("dependencies", []),
                assigned_provider_id=node.get("assigned_provider"),
                assigned_model_id=node.get("assigned_model"),
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

    for index, event in enumerate(run.get("events", []), start=1):
        db.add(
            OrchestrationEvent(
                id=str(uuid.uuid4()),
                run_id=run_id,
                node_id=event.get("node_id"),
                sequence=event.get("sequence") or index,
                event_type=event["event_type"],
                actor_role=event.get("actor_role"),
                payload=event.get("payload", {}),
                previous_event_hash=event.get("previous_event_hash"),
                event_hash=event["event_hash"],
                created_at=_parse_dt(event.get("created_at")) or now,
            )
        )

    budget = run.get("budget", {})
    limits = budget.get("limits", {})
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
        db.add(
            RoutingDecision(
                id=str(uuid.uuid4()),
                run_id=run_id,
                node_pk=None,
                node_id=decision.get("node_id"),
                selected_provider_id=decision.get("selected_provider"),
                selected_model_id=decision.get("selected_model"),
                candidate_providers=decision.get("candidate_providers", []),
                rejected_providers=decision.get("rejected_providers", []),
                selection_reason=decision.get("selection_reason", "No selection reason recorded"),
                policy_applied=decision.get("policy_applied", {}),
                estimated_cost=decision.get("estimated_cost", 0.0),
                actual_cost=decision.get("actual_cost"),
                created_at=now,
            )
        )

    for verification in run.get("verification", []):
        db.add(
            VerificationResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                node_id=verification.get("node_id", "checker"),
                checker_node_id=verification.get("checker_node_id"),
                verification_status=verification.get("verification_result", "unknown"),
                confidence_score=verification.get("confidence_score", 0.0),
                evidence_quality=verification.get("evidence_quality", "unknown"),
                unresolved_uncertainty=verification.get("unresolved_uncertainty", []),
                assumptions=verification.get("assumptions", []),
                contradictions=verification.get("contradictions", []),
                findings=verification.get("findings", []),
                created_at=now,
            )
        )

    reconciliation = run.get("reconciliation")
    if reconciliation:
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
                created_at=now,
            )
        )

    for approval in run.get("approvals", []):
        db.add(
            ApprovalRequest(
                id=approval.get("approval_id") or str(uuid.uuid4()),
                run_id=run_id,
                node_id=approval.get("node_id"),
                requested_action=approval.get(
                    "requested_action", "Approve governed orchestration result"
                ),
                reason=approval.get("reason", "Approval required by policy"),
                risk_level=approval.get("risk_level", "controlled"),
                status=approval.get("status", "REQUESTED"),
                requested_by_role=approval.get("requested_by_role", "GOVERNANCE_REVIEWER"),
                principal_id=approval.get("principal_id"),
                decided_at=_parse_dt(approval.get("decided_at")),
                decision_reason=approval.get("decision_reason"),
                created_at=now,
            )
        )

    await db.flush()
    persisted = await get_production_run(db, run_id=run_id, tenant_id=str(run["tenant_id"]))
    if persisted is None:
        raise RuntimeError("Production orchestration projection was not persisted")
    return persisted


async def get_production_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    run = (
        await db.execute(
            select(OrchestrationRun).where(
                OrchestrationRun.id == run_id,
                OrchestrationRun.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        return None

    nodes = list(
        (
            await db.execute(
                select(OrchestrationNode)
                .where(OrchestrationNode.run_id == run_id)
                .order_by(OrchestrationNode.sequence)
            )
        ).scalars()
    )
    events = list(
        (
            await db.execute(
                select(OrchestrationEvent)
                .where(OrchestrationEvent.run_id == run_id)
                .order_by(OrchestrationEvent.sequence)
            )
        ).scalars()
    )
    routing = list(
        (
            await db.execute(
                select(RoutingDecision)
                .where(RoutingDecision.run_id == run_id)
                .order_by(RoutingDecision.created_at, RoutingDecision.id)
            )
        ).scalars()
    )
    verification = list(
        (await db.execute(select(VerificationResult).where(VerificationResult.run_id == run_id))).scalars()
    )
    reconciliation = (
        await db.execute(select(ReconciliationResult).where(ReconciliationResult.run_id == run_id))
    ).scalars().first()
    approvals = list(
        (await db.execute(select(ApprovalRequest).where(ApprovalRequest.run_id == run_id))).scalars()
    )
    budget = (
        await db.execute(select(BudgetUsage).where(BudgetUsage.run_id == run_id))
    ).scalar_one_or_none()

    return {
        "run_id": str(run.id),
        "tenant_id": str(run.tenant_id),
        "created_by": str(run.created_by) if run.created_by else None,
        "objective": run.objective,
        "constraints": run.constraints or {},
        "classification": run.classification or {},
        "execution_mode": run.execution_mode,
        "status": run.status,
        "nodes": [_node_to_dict(node) for node in nodes],
        "routing_decisions": [_routing_to_dict(item) for item in routing],
        "budget": _budget_to_dict(budget),
        "verification": [_verification_to_dict(item) for item in verification],
        "reconciliation": _reconciliation_to_dict(reconciliation) if reconciliation else None,
        "approvals": [_approval_to_dict(item) for item in approvals],
        "events": [_event_to_dict(event) for event in events],
        "cancellation_reason": run.cancellation_reason,
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
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
        "approval_id": str(item.id),
        "node_id": item.node_id,
        "requested_action": item.requested_action,
        "reason": item.reason,
        "risk_level": item.risk_level,
        "status": item.status,
        "requested_by_role": item.requested_by_role,
        "principal_id": str(item.principal_id) if item.principal_id else None,
        "decided_at": _iso(item.decided_at),
        "decision_reason": item.decision_reason,
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
