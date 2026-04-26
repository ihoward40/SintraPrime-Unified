"""
governance_engine.py — Master orchestrator for AI governance.

Ties together risk assessment, approval gates, audit logging,
intervention controls, and compliance monitoring into a unified
middleware layer for all agent actions.
"""

from __future__ import annotations

import functools
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from governance.approval_gate import ApprovalGate
from governance.audit_trail import AuditTrail
from governance.compliance_monitor import ComplianceMonitor
from governance.intervention_controller import InterventionController
from governance.risk_assessor import RiskAssessor
from governance.risk_types import (
    ApprovalStatus,
    GovernancePolicy,
    GovernanceReport,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class GovernanceEngine:
    """
    Master AI Governance Orchestrator for SintraPrime-Unified.

    Provides middleware hooks (before_action / after_action) that wrap
    every agent action with:
      1. Risk assessment
      2. Compliance verification
      3. Human approval (if required)
      4. Audit logging
      5. Intervention control checks

    Usage::

        engine = GovernanceEngine()

        # Programmatic use
        allowed = engine.before_action("send_payment", {"amount": 5000}, "agent-1")
        if allowed:
            result = send_payment(amount=5000)
            engine.after_action("send_payment", result, "agent-1")

        # Decorator use
        @engine.requires_approval(min_risk=RiskLevel.HIGH)
        def send_payment(amount: float): ...
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        base_url: str = "https://app.sintraprime.com",
        approval_timeout_seconds: int = 300,
        notification_callback: Optional[Callable] = None,
    ) -> None:
        self.risk_assessor = RiskAssessor()
        self.approval_gate = ApprovalGate(
            base_url=base_url,
            notification_callback=notification_callback,
        )
        self.audit_trail = AuditTrail(db_path=db_path)
        self.intervention_controller = InterventionController()
        self.compliance_monitor = ComplianceMonitor()
        self._policies: List[GovernancePolicy] = []
        self._approval_timeout = approval_timeout_seconds

    # ------------------------------------------------------------------
    # Core middleware hooks
    # ------------------------------------------------------------------

    def before_action(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        agent_id: str = "unknown",
        domain: str = "general",
        jurisdiction: Optional[str] = None,
    ) -> bool:
        """
        Pre-execution governance hook.

        Runs risk assessment, compliance check, guardrail check,
        and approval gate before allowing an action to proceed.

        Args:
            action: The action type identifier.
            payload: Action payload/context.
            agent_id: Performing agent's ID.
            domain: Action domain (legal, financial, general, etc.).
            jurisdiction: User/data jurisdiction for compliance.

        Returns:
            True if the action is approved to proceed, False otherwise.
        """
        payload = payload or {}

        # 1. Check emergency stop
        if self.intervention_controller.is_emergency_stopped:
            logger.warning("before_action: emergency stop active — blocking '%s'", action)
            self.audit_trail.log(
                actor=agent_id, action=action, outcome="blocked_emergency_stop",
                risk_level=RiskLevel.CRITICAL,
                metadata={"reason": "Emergency stop is active"},
            )
            return False

        # 2. Check guardrails
        if not self.intervention_controller.check_guardrail(action):
            self.audit_trail.log(
                actor=agent_id, action=action, outcome="blocked_guardrail",
                risk_level=RiskLevel.HIGH,
                metadata={"reason": "Guardrail violation"},
            )
            return False

        # 3. Assess risk
        risk = self.risk_assessor.assess(action, payload)

        # 4. Compliance check
        compliance = self.compliance_monitor.check_action(
            action, domain=domain, payload=payload, jurisdiction=jurisdiction
        )
        if not compliance.compliant:
            logger.warning("before_action: compliance violation for '%s': %s",
                           action, compliance.violations)
            self.audit_trail.log(
                actor=agent_id, action=action, outcome="blocked_compliance",
                risk_level=risk.risk_level,
                metadata={"violations": compliance.violations},
            )
            return False

        # 5. Approval gate (if required)
        if risk.requires_approval:
            approval_req = self.approval_gate.request_approval(
                action=action,
                risk=risk,
                context={**payload, "agent_id": agent_id, "domain": domain},
                requestor=agent_id,
            )

            if approval_req.status == ApprovalStatus.AUTO_APPROVED:
                self.audit_trail.log(
                    actor=agent_id, action=action, outcome="auto_approved",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                    metadata={"reason": approval_req.notes},
                )
                return True

            # Wait for human decision
            logger.info(
                "Waiting for human approval of '%s' (request_id=%s, link=%s)",
                action, approval_req.id, approval_req.approval_link
            )
            status = self.approval_gate.wait_for_approval(
                approval_req.id, timeout_seconds=self._approval_timeout
            )

            if status == ApprovalStatus.APPROVED:
                self.audit_trail.log(
                    actor=agent_id, action=action, outcome="approved",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                    metadata={"approver": approval_req.approver},
                )
                return True
            else:
                self.audit_trail.log(
                    actor=agent_id, action=action, outcome=f"not_approved_{status.value.lower()}",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                )
                logger.info("Action '%s' not approved (status=%s)", action, status.value)
                return False

        # Low risk: no approval required — log and allow
        self.audit_trail.log(
            actor=agent_id, action=action, outcome="auto_allowed",
            risk_level=risk.risk_level,
            metadata={"domain": domain},
        )
        return True

    def after_action(
        self,
        action: str,
        result: Any,
        agent_id: str = "unknown",
        error: Optional[Exception] = None,
    ) -> None:
        """
        Post-execution audit hook.

        Always logs the result, even if the action failed.

        Args:
            action: The action type identifier.
            result: The action result (any serializable value).
            agent_id: Performing agent's ID.
            error: If the action raised an exception, pass it here.
        """
        outcome = "failure" if error else "success"
        metadata: Dict[str, Any] = {}

        if error:
            metadata["error"] = str(error)
            metadata["error_type"] = type(error).__name__
        elif result is not None:
            try:
                metadata["result_type"] = type(result).__name__
                if isinstance(result, dict):
                    metadata["result_keys"] = list(result.keys())
            except Exception:
                pass

        self.audit_trail.log(
            actor=agent_id,
            action=action,
            outcome=outcome,
            risk_level=self.risk_assessor.assess(action).risk_level,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def enforce_policy(self, policy: GovernancePolicy) -> None:
        """
        Register and enforce a governance policy.

        Policies are applied during before_action risk assessment.
        """
        self._policies.append(policy)
        logger.info("Policy '%s' registered (applies_to=%s)", policy.name, policy.applies_to)

    def get_policies(self) -> List[GovernancePolicy]:
        """Return all registered governance policies."""
        return list(self._policies)

    # ------------------------------------------------------------------
    # Decorator
    # ------------------------------------------------------------------

    def requires_approval(
        self,
        min_risk: RiskLevel = RiskLevel.HIGH,
        domain: str = "general",
        agent_id: str = "decorator",
    ) -> Callable:
        """
        Decorator: wrap a function with governance approval gate.

        Example::

            @engine.requires_approval(min_risk=RiskLevel.HIGH)
            def send_payment(amount: float):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                action = func.__name__
                payload = {"args": str(args)[:200], "kwargs": str(kwargs)[:200]}

                allowed = self.before_action(
                    action=action,
                    payload=payload,
                    agent_id=agent_id,
                    domain=domain,
                )
                if not allowed:
                    raise PermissionError(
                        f"Governance: action '{action}' was not approved."
                    )

                try:
                    result = func(*args, **kwargs)
                    self.after_action(action, result, agent_id=agent_id)
                    return result
                except Exception as exc:
                    self.after_action(action, None, agent_id=agent_id, error=exc)
                    raise

            return wrapper
        return decorator

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_governance_report(
        self,
        period_days: int = 7,
    ) -> GovernanceReport:
        """
        Generate a weekly governance summary report.

        Args:
            period_days: Number of days to include in the report.

        Returns:
            GovernanceReport with aggregate statistics.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=period_days)

        summary = self.audit_trail.summary_report(date_range=(start, now))
        pending = self.approval_gate.get_pending()
        gate_stats = self.approval_gate.stats()
        violations = self.compliance_monitor.get_violations()

        report = GovernanceReport(
            generated_at=now,
            period_start=start,
            period_end=now,
            total_actions=summary["total_actions"],
            approvals_requested=gate_stats["total"],
            approvals_granted=gate_stats["approved"],
            approvals_rejected=gate_stats["rejected"],
            auto_approved=gate_stats["auto_approved"],
            violations=len(violations),
            by_risk_level=summary["by_risk_level"],
            top_actors=[{"actor": a, "count": c} for a, c in summary["top_actors"]],
            top_actions=[{"action": a, "count": c} for a, c in summary["top_actions"]],
            compliance_score=max(0, 100 - len(violations) * 5),
        )
        return report

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Return real-time governance dashboard data.

        Suitable for display in a web dashboard or TUI panel.
        """
        gate_stats = self.approval_gate.stats()
        pending = self.approval_gate.get_pending()
        agents = self.intervention_controller.get_running_agents()
        guardrails = self.intervention_controller.get_guardrails()
        violations = self.compliance_monitor.get_violations(resolved=False)
        anomalies = self.audit_trail.detect_anomalies()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emergency_stopped": self.intervention_controller.is_emergency_stopped,
            "approval_stats": gate_stats,
            "pending_approvals": [r.to_dict() for r in pending],
            "active_agents": len([a for a in agents if a.status == "running"]),
            "paused_agents": len([a for a in agents if a.status == "paused"]),
            "agents": [
                {
                    "id": a.agent_id,
                    "status": a.status,
                    "task": a.current_task,
                }
                for a in agents
            ],
            "active_guardrails": guardrails,
            "open_violations": len(violations),
            "anomalies_detected": len(anomalies),
            "compliance_score": max(0, 100 - len(violations) * 5),
        }
