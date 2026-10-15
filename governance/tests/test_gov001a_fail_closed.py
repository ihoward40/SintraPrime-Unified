"""
GOV-001A fail-closed regression suite.

This suite restores the historical governance/security gate as executable
coverage. It verifies that consequential actions require explicit approval,
intervention controls block execution, compliance failures deny actions, and
audit tampering is detectable.

The suite is intentionally side-effect free: it exercises in-memory and
SQLite-backed governance components only; it never calls external services.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from governance.approval_gate import ApprovalGate
from governance.audit_trail import AuditTrail
from governance.governance_engine import GovernanceEngine
from governance.intervention_controller import InterventionController
from governance.risk_assessor import RiskAssessor
from governance.risk_types import ActionRisk, ApprovalStatus, RiskLevel


@pytest.mark.parametrize(
    "action",
    [
        "send_payment",
        "wire_transfer",
        "delete_all_data",
        "file_legal_document",
        "sign_contract",
    ],
)
def test_critical_actions_require_explicit_approval(action: str) -> None:
    risk = RiskAssessor().assess(action)
    assert risk.risk_level == RiskLevel.CRITICAL
    assert risk.requires_approval is True


@pytest.mark.parametrize(
    "action",
    [
        "send_email_to_client",
        "update_financial_record",
        "publish_document",
        "schedule_court_filing",
        "modify_permissions",
    ],
)
def test_high_risk_actions_require_explicit_approval(action: str) -> None:
    risk = RiskAssessor().assess(action)
    assert risk.risk_level == RiskLevel.HIGH
    assert risk.requires_approval is True


@pytest.mark.parametrize(
    "action",
    [
        "read_data",
        "search_database",
        "list_records",
        "get_status",
        "draft_document",
    ],
)
def test_non_consequential_actions_do_not_auto_require_approval(action: str) -> None:
    risk = RiskAssessor().assess(action)
    assert risk.requires_approval is False


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("send_payment", ApprovalStatus.PENDING),
        ("wire_transfer", ApprovalStatus.PENDING),
        ("file_legal_document", ApprovalStatus.PENDING),
    ],
)
def test_high_risk_requests_start_pending(action: str, expected_status: ApprovalStatus) -> None:
    risk = RiskAssessor().assess(action)
    gate = ApprovalGate(auto_approve_threshold=RiskLevel.LOW)
    request = gate.request_approval(action, risk, requestor="gov-001a-test")
    assert request.status == expected_status
    assert gate.is_approved(request.id) == ApprovalStatus.PENDING


@pytest.mark.parametrize("action", ["send_payment", "sign_contract"])
def test_rejected_approval_cannot_be_reused(action: str) -> None:
    gate = ApprovalGate(auto_approve_threshold=RiskLevel.LOW)
    request = gate.request_approval(action, RiskAssessor().assess(action))
    assert gate.reject(request.id, "human-reviewer", "拒否") is True
    assert gate.is_approved(request.id) == ApprovalStatus.REJECTED
    assert gate.approve(request.id, "second-reviewer") is False
    assert gate.is_approved(request.id) == ApprovalStatus.REJECTED


@pytest.mark.parametrize("action", ["send_payment", "wire_transfer"])
def test_expired_approval_cannot_be_approved(action: str) -> None:
    gate = ApprovalGate(auto_approve_threshold=RiskLevel.LOW)
    request = gate.request_approval(
        action,
        RiskAssessor().assess(action),
        timeout_hours=-1,
    )
    assert gate.is_approved(request.id) == ApprovalStatus.EXPIRED
    assert gate.approve(request.id, "human-reviewer") is False


def test_unknown_approval_id_fails_closed() -> None:
    gate = ApprovalGate(auto_approve_threshold=RiskLevel.LOW)
    assert gate.is_approved("does-not-exist") == ApprovalStatus.EXPIRED
    assert gate.approve("does-not-exist", "human-reviewer") is False
    assert gate.reject("does-not-exist", "human-reviewer", "unknown") is False


@pytest.mark.parametrize("action", ["send_payment", "publish_document", "delete_records"])
def test_read_only_guardrail_blocks_mutations(action: str) -> None:
    controller = InterventionController(dead_mans_switch_hours=24)
    controller.set_guardrail("read_only_mode")
    assert controller.check_guardrail(action) is False


@pytest.mark.parametrize("action", ["read_data", "get_status"])
def test_read_only_guardrail_allows_safe_reads(action: str) -> None:
    controller = InterventionController(dead_mans_switch_hours=24)
    controller.set_guardrail("read_only_mode")
    assert controller.check_guardrail(action) is True


@pytest.mark.parametrize("action", ["search_external_api", "send_data_to_external"])
def test_external_api_guardrail_blocks_external_actions(action: str) -> None:
    controller = InterventionController(dead_mans_switch_hours=24)
    controller.set_guardrail("no_external_api_calls")
    assert controller.check_guardrail(action) is False


def test_emergency_stop_blocks_new_engine_actions(tmp_path: Path) -> None:
    engine = GovernanceEngine(db_path=str(tmp_path / "audit.db"))
    engine.intervention_controller.emergency_stop()
    assert engine.before_action("read_data", agent_id="gov-001a-test") is False
    entries = engine.audit_trail.query(actor="gov-001a-test", outcome="blocked_emergency_stop")
    assert len(entries) == 1


@pytest.mark.parametrize(
    ("action", "domain", "payload", "jurisdiction"),
    [
        ("send_legal_advice", "legal", {}, None),
        ("publish_financial_forecast", "financial", {}, None),
        ("export_data", "data", {"destination_region": "US"}, "EU"),
    ],
)
def test_compliance_violations_are_not_compliant(
    action: str,
    domain: str,
    payload: dict[str, Any],
    jurisdiction: str | None,
) -> None:
    from governance.compliance_monitor import ComplianceMonitor

    result = ComplianceMonitor().check_action(
        action,
        domain=domain,
        payload=payload,
        jurisdiction=jurisdiction,
    )
    assert result.compliant is False
    assert result.violations


def test_engine_blocks_non_compliant_action(tmp_path: Path) -> None:
    engine = GovernanceEngine(db_path=str(tmp_path / "audit.db"))
    assert (
        engine.before_action(
            "send_legal_advice",
            agent_id="gov-001a-test",
            domain="legal",
        )
        is False
    )
    entries = engine.audit_trail.query(actor="gov-001a-test", outcome="blocked_compliance")
    assert len(entries) == 1


def test_audit_integrity_is_clean_for_untampered_records(tmp_path: Path) -> None:
    trail = AuditTrail(db_path=tmp_path / "audit.db")
    trail.log("gov-001a-test", "read_data", "success", RiskLevel.LOW)
    checked, tampered = trail.verify_integrity()
    assert checked == 1
    assert tampered == []


def test_audit_integrity_detects_tampered_outcome(tmp_path: Path) -> None:
    db_path = tmp_path / "audit.db"
    trail = AuditTrail(db_path=db_path)
    entry = trail.log("gov-001a-test", "read_data", "success", RiskLevel.LOW)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE audit_log SET outcome = ? WHERE id = ?", ("success-forged", entry.id))
        conn.commit()
    checked, tampered = trail.verify_integrity()
    assert checked == 1
    assert tampered == [entry.id]
