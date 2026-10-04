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
from governance.risk_assessor import RiskAssessor, safe_action_label
from governance.risk_types import (
    ActionRisk,
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

    def assess_effective_risk(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        min_risk: Optional[RiskLevel] = None,
    ) -> ActionRisk:
        """
        Assess an action's risk and reconcile it against a declared
        min_risk floor and the org-wide risk threshold.

        GOV-001A (builder-002, findings 1 & 2): a min_risk floor must
        never silently leave requires_approval stale. This is reconciled
        unconditionally — including when the assessed risk already equals
        the declared floor exactly, which a prior "only reconcile when the
        level actually changes" check incorrectly skipped.

        Exposed publicly so a caller that needs the effective risk for its
        own audit/logging (e.g. to avoid re-assessing from scratch and
        losing the floor, per finding 5) can compute it once and reuse it
        for both before_action() (via precomputed_risk=) and after_action()
        (via risk_level=).
        """
        payload = payload or {}
        risk = self.risk_assessor.assess(action, payload)

        if min_risk is not None:
            effective_level = max(risk.risk_level, min_risk)
            if effective_level != risk.risk_level:
                risk.metadata["min_risk_floor_applied"] = True
                risk.metadata["original_risk_level"] = risk.risk_level.value
                risk.reason = f"{risk.reason} (floor raised to {min_risk.value} by declared min_risk)"
                risk.risk_level = effective_level

            # Always reconcile requires_approval against the effective
            # level and the org threshold, regardless of whether elevation
            # actually changed the level (the equality case — assessed
            # risk already == min_risk — must be reconciled too).
            risk.requires_approval = (
                risk.requires_approval
                or effective_level.requires_approval
                or effective_level >= self.risk_assessor.org_risk_threshold
            )

        return risk

    def before_action(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        agent_id: str = "unknown",
        domain: str = "general",
        jurisdiction: Optional[str] = None,
        min_risk: Optional[RiskLevel] = None,
        precomputed_risk: Optional[ActionRisk] = None,
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
            min_risk: Optional declared risk floor (e.g. from the
                @requires_approval decorator). GOV-001A: the assessed risk
                must never be reduced below this floor — effective_risk is
                max(assessed_risk, min_risk).
            precomputed_risk: Optional ActionRisk already computed via
                assess_effective_risk() for this same action/payload/
                min_risk. When given, before_action() reuses it instead of
                assessing again, so a caller (e.g. the @requires_approval
                decorator) can share the identical effective risk with
                after_action() rather than letting after_action()
                re-assess from scratch and lose any min_risk floor
                (GOV-001A finding 5).

        Returns:
            True if the action is approved to proceed, False otherwise.
        """
        payload = payload or {}

        # GOV-001A (builder-002, findings 3 & 4): a malformed (non-string)
        # action identifier must never reach a downstream string-based
        # consumer (guardrail checks, compliance checks) or be implicitly
        # stringified via str()/repr() in a log/audit message — an
        # attacker-controlled object's __repr__/__str__ could raise, have
        # side effects, or leak data. Compute a bounded, type-only safe
        # label up front, before anything else touches `action`, and use
        # it for every downstream call below. The original `action` is
        # still passed to the risk assessor, which performs its own
        # isinstance check before any string operation and never invokes
        # repr()/str() on a malformed value either.
        safe_action = action if isinstance(action, str) else safe_action_label(action)

        # 1. Check emergency stop
        if self.intervention_controller.is_emergency_stopped:
            logger.warning("before_action: emergency stop active — blocking '%s'", safe_action)
            self.audit_trail.log(
                actor=agent_id,
                action=safe_action,
                outcome="blocked_emergency_stop",
                risk_level=RiskLevel.CRITICAL,
                metadata={"reason": "Emergency stop is active"},
            )
            return False

        # 2. Check guardrails
        if not self.intervention_controller.check_guardrail(safe_action):
            self.audit_trail.log(
                actor=agent_id,
                action=safe_action,
                outcome="blocked_guardrail",
                risk_level=RiskLevel.HIGH,
                metadata={"reason": "Guardrail violation"},
            )
            return False

        # 3. Assess risk (and apply the declared min_risk floor, GOV-001A).
        risk = (
            precomputed_risk
            if precomputed_risk is not None
            else self.assess_effective_risk(action, payload, min_risk)
        )

        # 4. Compliance check
        compliance = self.compliance_monitor.check_action(
            safe_action, domain=domain, payload=payload, jurisdiction=jurisdiction
        )
        if not compliance.compliant:
            logger.warning(
                "before_action: compliance violation for '%s': %s", safe_action, compliance.violations
            )
            self.audit_trail.log(
                actor=agent_id,
                action=safe_action,
                outcome="blocked_compliance",
                risk_level=risk.risk_level,
                metadata={"violations": compliance.violations},
            )
            return False

        # 5. Approval gate (if required)
        if risk.requires_approval:
            approval_req = self.approval_gate.request_approval(
                action=safe_action,
                risk=risk,
                context={**payload, "agent_id": agent_id, "domain": domain},
                requestor=agent_id,
            )

            if approval_req.status == ApprovalStatus.AUTO_APPROVED:
                self.audit_trail.log(
                    actor=agent_id,
                    action=safe_action,
                    outcome="auto_approved",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                    metadata={"reason": approval_req.notes},
                )
                return True

            # Wait for human decision
            logger.info(
                "Waiting for human approval of '%s' (request_id=%s, link=%s)",
                safe_action,
                approval_req.id,
                approval_req.approval_link,
            )
            status = self.approval_gate.wait_for_approval(
                approval_req.id, timeout_seconds=self._approval_timeout
            )

            if status == ApprovalStatus.APPROVED:
                self.audit_trail.log(
                    actor=agent_id,
                    action=safe_action,
                    outcome="approved",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                    metadata={"approver": approval_req.approver},
                )
                return True
            else:
                self.audit_trail.log(
                    actor=agent_id,
                    action=safe_action,
                    outcome=f"not_approved_{status.value.lower()}",
                    risk_level=risk.risk_level,
                    approval_id=approval_req.id,
                )
                logger.info("Action '%s' not approved (status=%s)", safe_action, status.value)
                return False

        # Low risk: no approval required — log and allow
        self.audit_trail.log(
            actor=agent_id,
            action=safe_action,
            outcome="auto_allowed",
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
        risk_level: Optional[RiskLevel] = None,
    ) -> None:
        """
        Post-execution audit hook.

        Always logs the result, even if the action failed.

        Args:
            action: The action type identifier.
            result: The action result (any serializable value).
            agent_id: Performing agent's ID.
            error: If the action raised an exception, pass it here.
            risk_level: The effective risk level that governed this
                action (e.g. computed by assess_effective_risk()/
                before_action(), including any min_risk floor). GOV-001A
                (builder-002, finding 5): when omitted, this falls back to
                a fresh risk re-assessment for backward compatibility with
                callers that invoke after_action() standalone — but that
                fallback has no knowledge of any min_risk floor that was
                applied to the original governing decision, so any caller
                that already computed the effective risk (e.g. the
                @requires_approval decorator) MUST pass it explicitly here
                to avoid the post-action audit silently losing the floor.
        """
        # GOV-001A (builder-002, findings 3 & 4): sanitize a malformed
        # (non-string) action before it reaches audit_trail.log(), which
        # otherwise would attempt to store/format the raw object.
        safe_action = action if isinstance(action, str) else safe_action_label(action)

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

        effective_risk_level = (
            risk_level if risk_level is not None else self.risk_assessor.assess(action).risk_level
        )

        self.audit_trail.log(
            actor=agent_id,
            action=safe_action,
            outcome=outcome,
            risk_level=effective_risk_level,
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

                # GOV-001A (builder-002, finding 5): compute the effective
                # risk once and share it with both before_action() and
                # after_action(), so the post-action audit reflects the
                # same min_risk-floored risk that actually governed the
                # decision instead of re-assessing from scratch and losing
                # the floor.
                risk = self.assess_effective_risk(action, payload, min_risk)

                allowed = self.before_action(
                    action=action,
                    payload=payload,
                    agent_id=agent_id,
                    domain=domain,
                    min_risk=min_risk,
                    precomputed_risk=risk,
                )
                if not allowed:
                    raise PermissionError(f"Governance: action '{action}' was not approved.")

                # GOV-001A: AUDIT_FAILURE != ACTION_SUCCESS. If func() raises,
                # that is an action failure and is audited as such. If func()
                # succeeds but the post-action audit log itself fails, that
                # exception must propagate on its own — it must never be
                # relabeled as the action's failure, and the function's
                # result must never be returned to the caller as if the
                # governed action had completed successfully.
                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    self.after_action(
                        action, None, agent_id=agent_id, error=exc, risk_level=risk.risk_level
                    )
                    raise
                else:
                    self.after_action(action, result, agent_id=agent_id, risk_level=risk.risk_level)
                    return result

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
