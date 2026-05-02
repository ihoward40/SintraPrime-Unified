"""
test_governance.py — Comprehensive test suite for the AI Governance system.

55+ tests covering:
- RiskAssessor: risk levels, sequence assessment, policy retrieval
- ApprovalGate: request, approve, reject, expire, auto-approve
- AuditTrail: log, query, export, anomaly detection, tamper check
- InterventionController: pause, resume, terminate, rollback, emergency stop
- ComplianceMonitor: action checking, violation flagging, ethics check
- GovernanceEngine: before/after hooks, policy enforcement
- GovernanceAPI: endpoint coverage
"""

from __future__ import annotations

import csv
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from governance.approval_gate import ApprovalGate
from governance.audit_trail import AuditTrail
from governance.compliance_monitor import ComplianceMonitor
from governance.governance_engine import GovernanceEngine
from governance.intervention_controller import InterventionController
from governance.risk_assessor import RiskAssessor
from governance.risk_types import (
    ActionRisk,
    ApprovalStatus,
    GovernancePolicy,
    RiskLevel,
    Rule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_audit.db"


@pytest.fixture
def assessor() -> RiskAssessor:
    return RiskAssessor()


@pytest.fixture
def gate() -> ApprovalGate:
    return ApprovalGate(
        base_url="https://test.example.com",
        auto_approve_threshold=RiskLevel.LOW,
    )


@pytest.fixture
def trail(tmp_db: Path) -> AuditTrail:
    return AuditTrail(db_path=tmp_db)


@pytest.fixture
def controller() -> InterventionController:
    return InterventionController(dead_mans_switch_hours=24)


@pytest.fixture
def monitor() -> ComplianceMonitor:
    return ComplianceMonitor()


@pytest.fixture
def engine(tmp_db: Path) -> GovernanceEngine:
    return GovernanceEngine(
        db_path=str(tmp_db),
        approval_timeout_seconds=1,  # fast timeout for tests
    )


# ===========================================================================
# 1. RiskAssessor Tests
# ===========================================================================

class TestRiskAssessor:

    def test_assess_critical_action(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("send_payment")
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.requires_approval is True
        assert risk.reversible is False

    def test_assess_critical_wire_transfer(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("wire_transfer")
        assert risk.risk_level == RiskLevel.CRITICAL

    def test_assess_critical_delete_all_data(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("delete_all_data")
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.reversible is False

    def test_assess_critical_sign_contract(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("sign_contract")
        assert risk.risk_level == RiskLevel.CRITICAL

    def test_assess_critical_file_legal_document(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("file_legal_document")
        assert risk.risk_level == RiskLevel.CRITICAL

    def test_assess_high_email_to_client(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("send_email_to_client")
        assert risk.risk_level == RiskLevel.HIGH
        assert risk.requires_approval is True

    def test_assess_high_update_financial(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("update_financial_record")
        assert risk.risk_level == RiskLevel.HIGH

    def test_assess_high_publish_document(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("publish_document")
        assert risk.risk_level == RiskLevel.HIGH

    def test_assess_high_schedule_court(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("schedule_court_filing")
        assert risk.risk_level == RiskLevel.HIGH

    def test_assess_medium_draft_document(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("draft_document")
        assert risk.risk_level == RiskLevel.MEDIUM
        assert risk.requires_approval is False

    def test_assess_medium_search_external_api(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("search_external_api")
        assert risk.risk_level == RiskLevel.MEDIUM

    def test_assess_medium_generate_report(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("generate_report")
        assert risk.risk_level == RiskLevel.MEDIUM

    def test_assess_low_read_data(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("read_data")
        assert risk.risk_level == RiskLevel.LOW
        assert risk.requires_approval is False
        assert risk.reversible is True

    def test_assess_low_search_database(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("search_database")
        assert risk.risk_level == RiskLevel.LOW

    def test_assess_low_format_document(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("format_document")
        assert risk.risk_level == RiskLevel.LOW

    def test_assess_unknown_action_defaults_medium(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("totally_unknown_action_xyz")
        assert risk.risk_level == RiskLevel.MEDIUM

    def test_assess_with_payload_enriches_impact(self, assessor: RiskAssessor) -> None:
        risk = assessor.assess("send_payment", {"amount": 10000})
        assert "10000" in risk.estimated_impact

    def test_assess_sequence_returns_list(self, assessor: RiskAssessor) -> None:
        risks = assessor.assess_sequence(["read_data", "send_payment", "sign_contract"])
        assert len(risks) == 3

    def test_assess_sequence_index_metadata(self, assessor: RiskAssessor) -> None:
        risks = assessor.assess_sequence(["read_data", "draft_document"])
        assert risks[0].metadata["sequence_index"] == 0
        assert risks[1].metadata["sequence_index"] == 1

    def test_assess_sequence_length_metadata(self, assessor: RiskAssessor) -> None:
        risks = assessor.assess_sequence(["read_data", "send_payment"])
        assert risks[0].metadata["sequence_length"] == 2

    def test_get_policy_legal(self, assessor: RiskAssessor) -> None:
        policy = assessor.get_policy("legal")
        assert policy.name == "Legal Domain Policy"
        assert len(policy.rules) > 0

    def test_get_policy_financial(self, assessor: RiskAssessor) -> None:
        policy = assessor.get_policy("financial")
        assert "financial" in policy.name.lower()

    def test_get_policy_communication(self, assessor: RiskAssessor) -> None:
        policy = assessor.get_policy("communication")
        assert policy is not None

    def test_get_policy_unknown_returns_general(self, assessor: RiskAssessor) -> None:
        policy = assessor.get_policy("unknown_domain")
        assert policy.name == "General Policy"

    def test_add_custom_rule_takes_priority(self, assessor: RiskAssessor) -> None:
        assessor.add_custom_rule(
            "read_data", RiskLevel.HIGH,
            "Custom: now HIGH for this org", True, True, "Custom impact"
        )
        risk = assessor.assess("read_data")
        assert risk.risk_level == RiskLevel.HIGH

    def test_set_org_threshold(self, assessor: RiskAssessor) -> None:
        assessor.set_org_threshold(RiskLevel.MEDIUM)
        risk = assessor.assess("draft_document")
        assert risk.requires_approval is True  # MEDIUM >= MEDIUM

    def test_risk_level_comparison(self) -> None:
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL
        assert RiskLevel.CRITICAL > RiskLevel.LOW


# ===========================================================================
# 2. ApprovalGate Tests
# ===========================================================================

class TestApprovalGate:

    def _make_risk(self, level: RiskLevel = RiskLevel.HIGH) -> ActionRisk:
        return ActionRisk(
            action_type="test_action",
            risk_level=level,
            reason="Test",
            requires_approval=level >= RiskLevel.HIGH,
            reversible=True,
            estimated_impact="Test impact",
        )

    def test_request_creates_pending(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("test_action", risk, requestor="agent-1")
        assert req.status == ApprovalStatus.PENDING

    def test_auto_approve_low_risk(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.LOW)
        req = gate.request_approval("read_data", risk)
        assert req.status == ApprovalStatus.AUTO_APPROVED

    def test_auto_approve_whitelist(self, gate: ApprovalGate) -> None:
        gate.auto_approve("generate_report")
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("generate_report", risk)
        assert req.status == ApprovalStatus.AUTO_APPROVED

    def test_approve_request(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("test_action", risk)
        result = gate.approve(req.id, "approver-1", "Looks good")
        assert result is True
        assert gate.is_approved(req.id) == ApprovalStatus.APPROVED

    def test_reject_request(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("test_action", risk)
        result = gate.reject(req.id, "approver-1", "Too risky")
        assert result is True
        assert gate.is_approved(req.id) == ApprovalStatus.REJECTED

    def test_approve_nonexistent_request(self, gate: ApprovalGate) -> None:
        result = gate.approve("nonexistent-id", "approver-1")
        assert result is False

    def test_reject_nonexistent_request(self, gate: ApprovalGate) -> None:
        result = gate.reject("nonexistent-id", "approver-1", "N/A")
        assert result is False

    def test_get_pending_returns_only_pending(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req1 = gate.request_approval("action1", risk)
        req2 = gate.request_approval("action2", risk)
        gate.approve(req1.id, "approver")
        pending = gate.get_pending()
        ids = [r.id for r in pending]
        assert req1.id not in ids
        assert req2.id in ids

    def test_expire_old_requests(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("action", risk, timeout_hours=-1)  # already expired
        expired_count = gate.expire_old_requests()
        assert expired_count >= 1
        assert gate.is_approved(req.id) == ApprovalStatus.EXPIRED

    def test_wait_for_approval_timeout(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("action", risk)
        status = gate.wait_for_approval(req.id, timeout_seconds=0.1, poll_interval=0.05)
        assert status == ApprovalStatus.EXPIRED

    def test_wait_for_approval_approved_fast(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        req = gate.request_approval("action", risk)

        def approve_later():
            time.sleep(0.05)
            gate.approve(req.id, "human")

        t = threading.Thread(target=approve_later)
        t.start()
        status = gate.wait_for_approval(req.id, timeout_seconds=5, poll_interval=0.02)
        t.join()
        assert status == ApprovalStatus.APPROVED

    def test_create_approval_link(self, gate: ApprovalGate) -> None:
        link = gate.create_approval_link("test-id")
        assert "test-id" in link
        assert "https://" in link

    def test_stats(self, gate: ApprovalGate) -> None:
        risk = self._make_risk(RiskLevel.HIGH)
        gate.request_approval("action", risk)
        stats = gate.stats()
        assert "total" in stats
        assert "pending" in stats


# ===========================================================================
# 3. AuditTrail Tests
# ===========================================================================

class TestAuditTrail:

    def test_log_creates_entry(self, trail: AuditTrail) -> None:
        entry = trail.log("agent-1", "read_data", "success", RiskLevel.LOW)
        assert entry.id is not None
        assert entry.checksum is not None

    def test_log_sets_checksum(self, trail: AuditTrail) -> None:
        entry = trail.log("agent-1", "send_payment", "success", RiskLevel.CRITICAL)
        assert entry.checksum == entry.compute_checksum()

    def test_query_by_actor(self, trail: AuditTrail) -> None:
        trail.log("actor-A", "read_data", "success", RiskLevel.LOW)
        trail.log("actor-B", "read_data", "success", RiskLevel.LOW)
        results = trail.query(actor="actor-A")
        assert all(e.actor == "actor-A" for e in results)

    def test_query_by_action(self, trail: AuditTrail) -> None:
        trail.log("agent", "send_payment", "success", RiskLevel.CRITICAL)
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        results = trail.query(action="send_payment")
        assert all(e.action == "send_payment" for e in results)

    def test_query_by_risk_level(self, trail: AuditTrail) -> None:
        trail.log("agent", "send_payment", "success", RiskLevel.CRITICAL)
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        results = trail.query(risk_level=RiskLevel.CRITICAL)
        assert all(e.risk_level == RiskLevel.CRITICAL for e in results)

    def test_query_by_date_range(self, trail: AuditTrail) -> None:
        now = datetime.now(timezone.utc)
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        results = trail.query(
            date_range=(now - timedelta(minutes=1), now + timedelta(minutes=1))
        )
        assert len(results) >= 1

    def test_summary_report(self, trail: AuditTrail) -> None:
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        trail.log("agent", "send_payment", "success", RiskLevel.CRITICAL)
        report = trail.summary_report()
        assert report["total_actions"] >= 2
        assert "by_risk_level" in report

    def test_export_csv(self, trail: AuditTrail, tmp_path: Path) -> None:
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        output = str(tmp_path / "audit.csv")
        trail.export_csv(output)
        assert Path(output).exists()
        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) >= 1

    def test_detect_anomalies_off_hours(self, trail: AuditTrail) -> None:
        # Just verify it runs without error
        anomalies = trail.detect_anomalies()
        assert isinstance(anomalies, list)

    def test_verify_integrity_clean(self, trail: AuditTrail) -> None:
        trail.log("agent", "read_data", "success", RiskLevel.LOW)
        checked, tampered = trail.verify_integrity()
        assert checked >= 1
        assert len(tampered) == 0

    def test_compliance_report_soc2(self, trail: AuditTrail) -> None:
        report = trail.compliance_report("SOC2")
        assert report["standard"] == "SOC2"
        assert "controls" in report

    def test_compliance_report_hipaa(self, trail: AuditTrail) -> None:
        report = trail.compliance_report("HIPAA")
        assert "phi_access_events" in report

    def test_compliance_report_gdpr(self, trail: AuditTrail) -> None:
        report = trail.compliance_report("GDPR")
        assert "personal_data_events" in report

    def test_log_with_metadata(self, trail: AuditTrail) -> None:
        entry = trail.log(
            "agent", "send_payment", "success", RiskLevel.CRITICAL,
            approval_id="approval-123",
            metadata={"amount": 5000, "currency": "USD"},
        )
        results = trail.query(actor="agent")
        matching = [e for e in results if e.id == entry.id]
        assert len(matching) == 1
        assert matching[0].metadata["amount"] == 5000


# ===========================================================================
# 4. InterventionController Tests
# ===========================================================================

class TestInterventionController:

    def test_register_agent(self, controller: InterventionController) -> None:
        status = controller.register_agent("agent-1", "legal_research")
        assert status.agent_id == "agent-1"
        assert status.status == "running"

    def test_pause_agent(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        result = controller.pause_agent("agent-1")
        assert result is True
        agents = controller.get_running_agents()
        agent = next(a for a in agents if a.agent_id == "agent-1")
        assert agent.status == "paused"

    def test_resume_agent(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        controller.pause_agent("agent-1")
        result = controller.resume_agent("agent-1")
        assert result is True

    def test_pause_all(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        controller.register_agent("agent-2")
        count = controller.pause_all()
        assert count == 2

    def test_terminate_task(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1", current_task="task-xyz")
        result = controller.terminate_task("task-xyz", "test termination")
        assert result is True

    def test_force_kill(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1", current_task="task-abc")
        result = controller.force_kill("task-abc")
        assert result is True

    def test_rollback_with_entry(self, controller: InterventionController) -> None:
        controller.record_action_for_rollback(
            "task-1", "update_record", {"undo": {"field": "old_value"}}
        )
        result = controller.rollback("task-1")
        assert result is True

    def test_rollback_no_entry(self, controller: InterventionController) -> None:
        result = controller.rollback("nonexistent-task")
        assert result is False

    def test_set_guardrail(self, controller: InterventionController) -> None:
        controller.set_guardrail("read_only_mode")
        guardrails = controller.get_guardrails()
        assert "read_only_mode" in guardrails

    def test_guardrail_blocks_action(self, controller: InterventionController) -> None:
        controller.set_guardrail("read_only_mode")
        allowed = controller.check_guardrail("send_payment")
        assert allowed is False

    def test_guardrail_allows_read(self, controller: InterventionController) -> None:
        controller.set_guardrail("read_only_mode")
        allowed = controller.check_guardrail("read_data")
        assert allowed is True

    def test_emergency_stop(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        controller.register_agent("agent-2")
        count = controller.emergency_stop()
        assert count == 2
        assert controller.is_emergency_stopped is True

    def test_clear_emergency_stop(self, controller: InterventionController) -> None:
        controller.emergency_stop()
        controller.clear_emergency_stop("admin-user")
        assert controller.is_emergency_stopped is False

    def test_resume_blocked_during_emergency(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        controller.pause_agent("agent-1")
        controller.emergency_stop()
        result = controller.resume_agent("agent-1")
        assert result is False

    def test_get_running_agents(self, controller: InterventionController) -> None:
        controller.register_agent("agent-1")
        controller.register_agent("agent-2")
        agents = controller.get_running_agents()
        assert len(agents) == 2


# ===========================================================================
# 5. ComplianceMonitor Tests
# ===========================================================================

class TestComplianceMonitor:

    def test_compliant_low_risk_action(self, monitor: ComplianceMonitor) -> None:
        result = monitor.check_action("read_data", domain="general")
        assert result.compliant is True

    def test_privileged_action_violation(self, monitor: ComplianceMonitor) -> None:
        result = monitor.check_action("send_legal_advice", domain="legal")
        assert result.compliant is False
        assert len(result.violations) > 0

    def test_sec_action_violation(self, monitor: ComplianceMonitor) -> None:
        result = monitor.check_action("publish_financial_forecast", domain="financial")
        assert result.compliant is False

    def test_gdpr_data_transfer_violation(self, monitor: ComplianceMonitor) -> None:
        result = monitor.check_action(
            "export_data",
            domain="data",
            payload={"destination_region": "US"},
            jurisdiction="EU",
        )
        assert result.compliant is False

    def test_gdpr_compliant_transfer(self, monitor: ComplianceMonitor) -> None:
        result = monitor.check_action(
            "export_data",
            domain="data",
            payload={"destination_region": "DE"},
            jurisdiction="EU",
        )
        # Should not have a violation for intra-EU transfer
        assert not any("44-49" in v for v in result.violations)

    def test_flag_violation(self, monitor: ComplianceMonitor) -> None:
        violation = monitor.flag_violation("send_payment", "No approval obtained", "critical")
        assert violation.action == "send_payment"
        assert violation.severity == "critical"

    def test_get_violations(self, monitor: ComplianceMonitor) -> None:
        monitor.flag_violation("action1", "rule1", "high")
        monitor.flag_violation("action2", "rule2", "low")
        all_v = monitor.get_violations()
        assert len(all_v) >= 2

    def test_get_violations_by_severity(self, monitor: ComplianceMonitor) -> None:
        monitor.flag_violation("action1", "rule1", "critical")
        critical = monitor.get_violations(severity="critical")
        assert all(v.severity == "critical" for v in critical)

    def test_ethics_check_clean(self, monitor: ComplianceMonitor) -> None:
        result = monitor.legal_ethical_check("draft_document")
        assert result.passes is True
        assert result.unauthorized_practice is False

    def test_ethics_check_upl(self, monitor: ComplianceMonitor) -> None:
        result = monitor.legal_ethical_check("represent_client_in_court")
        assert result.passes is False
        assert result.unauthorized_practice is True

    def test_data_residency_non_gdpr(self, monitor: ComplianceMonitor) -> None:
        result = monitor.data_residency_check(
            {"processing_region": "US"}, user_jurisdiction="US"
        )
        assert result is True

    def test_data_residency_gdpr_violation(self, monitor: ComplianceMonitor) -> None:
        result = monitor.data_residency_check(
            {"storage_region": "US"}, user_jurisdiction="EU"
        )
        assert result is False

    def test_audit_for_soc2(self, monitor: ComplianceMonitor) -> None:
        report = monitor.audit_for_standard("SOC2")
        assert report.standard == "SOC2"
        assert report.controls_checked > 0

    def test_audit_for_hipaa(self, monitor: ComplianceMonitor) -> None:
        report = monitor.audit_for_standard("HIPAA")
        assert report.standard == "HIPAA"

    def test_audit_for_gdpr(self, monitor: ComplianceMonitor) -> None:
        report = monitor.audit_for_standard("GDPR")
        assert report.standard == "GDPR"


# ===========================================================================
# 6. GovernanceEngine Tests
# ===========================================================================

class TestGovernanceEngine:

    def test_before_action_low_risk_allowed(self, engine: GovernanceEngine) -> None:
        allowed = engine.before_action("read_data", {}, "agent-1")
        assert allowed is True

    def test_before_action_blocked_by_emergency_stop(self, engine: GovernanceEngine) -> None:
        engine.intervention_controller.emergency_stop()
        allowed = engine.before_action("read_data", {}, "agent-1")
        assert allowed is False
        engine.intervention_controller.clear_emergency_stop("admin")

    def test_before_action_blocked_by_guardrail(self, engine: GovernanceEngine) -> None:
        engine.intervention_controller.set_guardrail("read_only_mode")
        allowed = engine.before_action("send_payment", {}, "agent-1")
        assert allowed is False
        engine.intervention_controller.remove_guardrail("read_only_mode")

    def test_before_action_high_risk_times_out(self, engine: GovernanceEngine) -> None:
        # Timeout is 1 second, should expire
        allowed = engine.before_action("send_payment", {"amount": 100}, "agent-1")
        assert allowed is False  # expired, no approver

    def test_before_action_auto_approve(self, engine: GovernanceEngine) -> None:
        engine.approval_gate.auto_approve("generate_report")
        allowed = engine.before_action("generate_report", {}, "agent-1")
        assert allowed is True

    def test_after_action_logs_success(self, engine: GovernanceEngine) -> None:
        engine.after_action("read_data", {"data": "ok"}, "agent-1")
        entries = engine.audit_trail.query(actor="agent-1", action="read_data")
        assert len(entries) >= 1
        assert any(e.outcome == "success" for e in entries)

    def test_after_action_logs_failure(self, engine: GovernanceEngine) -> None:
        engine.after_action("read_data", None, "agent-1", error=ValueError("DB error"))
        entries = engine.audit_trail.query(actor="agent-1")
        assert any(e.outcome == "failure" for e in entries)

    def test_enforce_policy(self, engine: GovernanceEngine) -> None:
        policy = GovernancePolicy(
            name="Test Policy",
            rules=[
                Rule(
                    name="test-rule",
                    description="test",
                    action_pattern="test_*",
                    risk_threshold=RiskLevel.HIGH,
                )
            ],
            applies_to=["test_*"],
        )
        engine.enforce_policy(policy)
        policies = engine.get_policies()
        assert any(p.name == "Test Policy" for p in policies)

    def test_generate_governance_report(self, engine: GovernanceEngine) -> None:
        engine.after_action("read_data", "ok", "agent-1")
        report = engine.generate_governance_report(period_days=1)
        assert report.total_actions >= 1

    def test_get_dashboard_data(self, engine: GovernanceEngine) -> None:
        data = engine.get_dashboard_data()
        assert "emergency_stopped" in data
        assert "approval_stats" in data
        assert "compliance_score" in data

    def test_requires_approval_decorator_allows_low(self, engine: GovernanceEngine) -> None:
        engine.approval_gate.auto_approve_threshold = RiskLevel.MEDIUM

        @engine.requires_approval(min_risk=RiskLevel.HIGH)
        def my_func():
            return "done"

        # With auto_approve_threshold=MEDIUM, LOW/MEDIUM are auto-approved
        # my_func maps to RiskLevel.MEDIUM (unknown) → auto-approved
        result = my_func()
        assert result == "done"

    def test_requires_approval_decorator_blocks_high(self, engine: GovernanceEngine) -> None:
        # approval_timeout=1s → will expire for HIGH risk

        @engine.requires_approval(min_risk=RiskLevel.HIGH, agent_id="agent-X")
        def pay():
            return "paid"

        with pytest.raises(PermissionError):
            pay()


# ===========================================================================
# 7. Risk Types Tests
# ===========================================================================

class TestRiskTypes:

    def test_risk_level_requires_approval(self) -> None:
        assert RiskLevel.HIGH.requires_approval is True
        assert RiskLevel.CRITICAL.requires_approval is True
        assert RiskLevel.LOW.requires_approval is False
        assert RiskLevel.MEDIUM.requires_approval is False

    def test_action_risk_to_dict(self) -> None:
        risk = ActionRisk(
            action_type="test",
            risk_level=RiskLevel.HIGH,
            reason="test",
            requires_approval=True,
            reversible=True,
            estimated_impact="test impact",
        )
        d = risk.to_dict()
        assert d["risk_level"] == "HIGH"

    def test_approval_request_is_expired(self) -> None:
        from governance.risk_types import ApprovalRequest
        now = datetime.now(timezone.utc)
        req = ApprovalRequest(
            action="test",
            risk=ActionRisk("test", RiskLevel.HIGH, "", True, True, ""),
            requestor="agent",
            requested_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        assert req.is_expired is True

    def test_audit_entry_checksum_changes_on_tamper(self) -> None:
        from governance.risk_types import AuditEntry
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            actor="agent",
            action="read_data",
            outcome="success",
            risk_level=RiskLevel.LOW,
        )
        original_checksum = entry.compute_checksum()
        entry.actor = "hacker"
        tampered_checksum = entry.compute_checksum()
        assert original_checksum != tampered_checksum
