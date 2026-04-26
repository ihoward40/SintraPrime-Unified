"""
governance_api.py — FastAPI router for the governance system.

Exposes REST endpoints for:
- Pending approval management
- Audit trail queries
- Compliance reports
- Agent intervention controls
- Governance dashboard
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Stub classes for environments without FastAPI
    class BaseModel:  # type: ignore
        pass
    APIRouter = None  # type: ignore

from governance.governance_engine import GovernanceEngine
from governance.risk_types import ApprovalStatus, RiskLevel

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    approver_id: str
    notes: str = ""


class RejectRequest(BaseModel):
    approver_id: str
    reason: str


class AuditQueryParams(BaseModel):
    actor: Optional[str] = None
    action: Optional[str] = None
    risk_level: Optional[str] = None
    outcome: Optional[str] = None
    limit: int = 100


class GuardrailRequest(BaseModel):
    rule: str


class PauseAgentRequest(BaseModel):
    agent_id: Optional[str] = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_governance_router(engine: GovernanceEngine) -> "APIRouter":
    """
    Create and return a FastAPI router with all governance endpoints.

    Args:
        engine: A configured GovernanceEngine instance.

    Returns:
        FastAPI APIRouter (mount at /governance).

    Example::

        app = FastAPI()
        engine = GovernanceEngine()
        app.include_router(create_governance_router(engine), prefix="/governance")
    """
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is not installed. Run: pip install fastapi")

    router = APIRouter(prefix="/governance", tags=["governance"])

    # ------------------------------------------------------------------
    # Approval endpoints
    # ------------------------------------------------------------------

    @router.get("/pending", summary="List pending approval requests")
    def get_pending_approvals() -> List[Dict[str, Any]]:
        """Return all approval requests awaiting human decision."""
        requests = engine.approval_gate.get_pending()
        return [r.to_dict() for r in requests]

    @router.get("/approvals/{request_id}", summary="Get a specific approval request")
    def get_approval(request_id: str) -> Dict[str, Any]:
        """Retrieve details for a specific approval request."""
        req = engine.approval_gate.get_request(request_id)
        if not req:
            raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
        return req.to_dict()

    @router.post("/approve/{request_id}", summary="Approve an action")
    def approve_action(request_id: str, body: ApproveRequest) -> Dict[str, Any]:
        """
        Approve a pending action request.

        This unblocks the waiting agent to proceed with the action.
        """
        success = engine.approval_gate.approve(
            request_id=request_id,
            approver_id=body.approver_id,
            notes=body.notes,
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Could not approve: request not found or not in PENDING state",
            )
        engine.audit_trail.log(
            actor=body.approver_id,
            action="approve_request",
            outcome="approved",
            risk_level=RiskLevel.LOW,
            approval_id=request_id,
            metadata={"notes": body.notes},
        )
        return {"status": "approved", "request_id": request_id}

    @router.post("/reject/{request_id}", summary="Reject an action")
    def reject_action(request_id: str, body: RejectRequest) -> Dict[str, Any]:
        """
        Reject a pending action request.

        The waiting agent will receive a rejection and must not proceed.
        """
        success = engine.approval_gate.reject(
            request_id=request_id,
            approver_id=body.approver_id,
            reason=body.reason,
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Could not reject: request not found or not in PENDING state",
            )
        engine.audit_trail.log(
            actor=body.approver_id,
            action="reject_request",
            outcome="rejected",
            risk_level=RiskLevel.LOW,
            approval_id=request_id,
            metadata={"reason": body.reason},
        )
        return {"status": "rejected", "request_id": request_id}

    @router.get("/review/{request_id}", summary="One-click review page")
    def review_request(request_id: str) -> Dict[str, Any]:
        """Get approval request details for the one-click review page."""
        req = engine.approval_gate.get_request(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        return {
            "request": req.to_dict(),
            "approve_url": f"/governance/approve/{request_id}",
            "reject_url": f"/governance/reject/{request_id}",
        }

    # ------------------------------------------------------------------
    # Audit trail endpoints
    # ------------------------------------------------------------------

    @router.get("/audit", summary="Query audit trail")
    def query_audit(
        actor: Optional[str] = Query(None),
        action: Optional[str] = Query(None),
        risk_level: Optional[str] = Query(None),
        outcome: Optional[str] = Query(None),
        limit: int = Query(100, le=10000),
    ) -> List[Dict[str, Any]]:
        """Query the audit log with optional filters."""
        rl = RiskLevel(risk_level) if risk_level else None
        entries = engine.audit_trail.query(
            actor=actor,
            action=action,
            risk_level=rl,
            outcome=outcome,
            limit=limit,
        )
        return [e.to_dict() for e in entries]

    @router.get("/audit/summary", summary="Audit summary statistics")
    def audit_summary() -> Dict[str, Any]:
        """Return aggregate statistics for the audit log."""
        return engine.audit_trail.summary_report()

    @router.get("/audit/anomalies", summary="Detected anomalies")
    def audit_anomalies() -> List[Dict[str, Any]]:
        """Return flagged anomalous audit entries."""
        entries = engine.audit_trail.detect_anomalies()
        return [e.to_dict() for e in entries]

    # ------------------------------------------------------------------
    # Compliance endpoints
    # ------------------------------------------------------------------

    @router.get("/compliance/{standard}", summary="Compliance report")
    def compliance_report(standard: str) -> Dict[str, Any]:
        """
        Generate a compliance audit report.

        Supported: SOC2, ISO27001, HIPAA, GDPR, SOX.
        """
        report = engine.compliance_monitor.audit_for_standard(standard.upper())
        return {
            "standard": report.standard,
            "compliant": report.compliant,
            "score": report.score,
            "controls_checked": report.controls_checked,
            "controls_passed": report.controls_passed,
            "summary": report.summary,
            "violations": [
                {"rule": v.rule, "description": v.description, "severity": v.severity}
                for v in report.violations
            ],
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

    @router.get("/violations", summary="List compliance violations")
    def get_violations(
        severity: Optional[str] = Query(None),
        resolved: Optional[bool] = Query(None),
    ) -> List[Dict[str, Any]]:
        """Return recorded compliance violations."""
        violations = engine.compliance_monitor.get_violations(
            severity=severity,
            resolved=resolved,
        )
        return [
            {
                "id": v.id,
                "action": v.action,
                "rule": v.rule,
                "severity": v.severity,
                "description": v.description,
                "detected_at": v.detected_at.isoformat(),
                "resolved": v.resolved,
            }
            for v in violations
        ]

    # ------------------------------------------------------------------
    # Intervention endpoints
    # ------------------------------------------------------------------

    @router.post("/pause", summary="Pause all or specific agent")
    def pause_agents(body: PauseAgentRequest) -> Dict[str, Any]:
        """
        Pause agent(s).

        If agent_id is provided, pauses that agent.
        Otherwise pauses ALL running agents.
        """
        if body.agent_id:
            success = engine.intervention_controller.pause_agent(body.agent_id)
            return {"paused": success, "agent_id": body.agent_id}
        else:
            count = engine.intervention_controller.pause_all()
            engine.audit_trail.log(
                actor="api",
                action="pause_all_agents",
                outcome="success",
                risk_level=RiskLevel.HIGH,
                metadata={"reason": body.reason, "count": count},
            )
            return {"paused_count": count}

    @router.post("/resume/{agent_id}", summary="Resume a paused agent")
    def resume_agent(agent_id: str) -> Dict[str, Any]:
        """Resume a specific paused agent."""
        success = engine.intervention_controller.resume_agent(agent_id)
        if not success:
            raise HTTPException(status_code=400, detail=f"Could not resume agent '{agent_id}'")
        return {"resumed": True, "agent_id": agent_id}

    @router.post("/emergency-stop", summary="Emergency stop ALL agents")
    def emergency_stop(authorized_by: str = Query(...)) -> Dict[str, Any]:
        """
        Immediately halt ALL agent activity.

        ⚠️ This is the nuclear option. All agents will stop immediately.
        """
        count = engine.intervention_controller.emergency_stop()
        engine.audit_trail.log(
            actor=authorized_by,
            action="emergency_stop",
            outcome="success",
            risk_level=RiskLevel.CRITICAL,
            metadata={"agents_stopped": count},
        )
        return {
            "emergency_stop_active": True,
            "agents_stopped": count,
            "authorized_by": authorized_by,
        }

    @router.post("/emergency-stop/clear", summary="Clear emergency stop")
    def clear_emergency_stop(authorized_by: str = Query(...)) -> Dict[str, Any]:
        """Clear the emergency stop and allow agents to resume."""
        engine.intervention_controller.clear_emergency_stop(authorized_by)
        return {"emergency_stop_active": False, "cleared_by": authorized_by}

    @router.post("/guardrail", summary="Add runtime guardrail")
    def add_guardrail(body: GuardrailRequest) -> Dict[str, Any]:
        """Add a runtime constraint to all agent actions."""
        engine.intervention_controller.set_guardrail(body.rule)
        return {"added": True, "rule": body.rule}

    @router.get("/agents", summary="List running agents")
    def list_agents() -> List[Dict[str, Any]]:
        """Return status of all registered agents."""
        agents = engine.intervention_controller.get_running_agents()
        return [
            {
                "agent_id": a.agent_id,
                "status": a.status,
                "current_task": a.current_task,
                "started_at": a.started_at.isoformat() if a.started_at else None,
            }
            for a in agents
        ]

    # ------------------------------------------------------------------
    # Dashboard endpoint
    # ------------------------------------------------------------------

    @router.get("/dashboard", summary="Governance dashboard overview")
    def dashboard() -> Dict[str, Any]:
        """Return real-time governance dashboard data."""
        return engine.get_dashboard_data()

    @router.get("/report", summary="Weekly governance report")
    def governance_report(period_days: int = Query(7, ge=1, le=365)) -> Dict[str, Any]:
        """Generate a governance summary report for the given period."""
        report = engine.generate_governance_report(period_days=period_days)
        return {
            "generated_at": report.generated_at.isoformat(),
            "period_start": report.period_start.isoformat() if report.period_start else None,
            "period_end": report.period_end.isoformat() if report.period_end else None,
            "total_actions": report.total_actions,
            "approvals_requested": report.approvals_requested,
            "approvals_granted": report.approvals_granted,
            "approvals_rejected": report.approvals_rejected,
            "auto_approved": report.auto_approved,
            "violations": report.violations,
            "by_risk_level": report.by_risk_level,
            "compliance_score": report.compliance_score,
        }

    return router
