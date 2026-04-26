"""Tests for Agent Nova — Autonomous real-world execution engine."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nova.nova_agent import (
    NovaAgent,
    ActionSpec,
    ExecutionRecord,
    ApprovalLevel,
    ActionStatus,
)
from agents.nova.action_registry import (
    ActionRegistry,
    ActionNotFoundError,
    ActionAlreadyRegisteredError,
    ActionValidationError,
    ActionCategory,
    ApprovalLevel as RegApprovalLevel,
    ActionSpec as RegActionSpec,
)
from agents.nova.execution_ledger import (
    ExecutionLedger,
    LedgerEntry,
    LedgerIntegrityError,
)
from agents.nova.approval_gateway import (
    ApprovalGateway,
    ApprovalRequest,
    ApprovalStatus as GWApprovalStatus,
    ApprovalTier,
    AUTO_APPROVE_ACTIONS,
    LEGAL_REVIEW_ACTIONS,
)


@pytest.fixture
def nova(tmp_path):
    ledger = str(tmp_path / "ledger.jsonl")
    return NovaAgent(user_id="test-user", ledger_path=ledger)


@pytest.fixture
def registry():
    return ActionRegistry()


@pytest.fixture
def ledger(tmp_path):
    return ExecutionLedger(ledger_path=str(tmp_path / "test_ledger.jsonl"))


@pytest.fixture
def gateway():
    return ApprovalGateway(auto_approve_enabled=True)


# ── NovaAgent Tests ───────────────────────────────────────────────


class TestNovaInit:
    def test_default_init(self, tmp_path):
        agent = NovaAgent(ledger_path=str(tmp_path / "l.jsonl"))
        assert agent.user_id == "system"

    def test_custom_user(self, nova):
        assert nova.user_id == "test-user"

    def test_default_actions_registered(self, nova):
        assert "SEND_DISPUTE_LETTER" in nova._registry
        assert "FILE_COURT_MOTION" in nova._registry
        assert "GENERATE_AFFIDAVIT" in nova._registry

    def test_all_eight_actions(self, nova):
        expected = {
            "SEND_DISPUTE_LETTER", "FILE_COURT_MOTION", "SUBMIT_CREDIT_DISPUTE",
            "DRAFT_TRUST_AMENDMENT", "SEND_DEMAND_LETTER", "NOTIFY_CREDITOR",
            "SCHEDULE_COURT_DATE", "GENERATE_AFFIDAVIT",
        }
        assert expected == set(nova._registry.keys())


class TestExecuteAction:
    def test_auto_approve_low_risk(self, nova):
        record = nova.execute_action("NOTIFY_CREDITOR", {
            "creditor_name": "Acme Corp",
            "creditor_address": "123 Main St",
            "notification_type": "dispute",
            "message": "We dispute this debt.",
        })
        assert record.status == ActionStatus.COMPLETED.value
        assert record.result is not None

    def test_human_approval_required(self, nova):
        record = nova.execute_action("SEND_DISPUTE_LETTER", {
            "recipient_name": "Bank",
            "recipient_address": "456 Wall St",
            "dispute_reason": "Incorrect balance",
            "account_number": "12345",
        })
        assert record.status == ActionStatus.AWAITING_APPROVAL.value

    def test_missing_params_raises(self, nova):
        with pytest.raises(ValueError, match="Missing required"):
            nova.execute_action("SEND_DISPUTE_LETTER", {"recipient_name": "Bank"})

    def test_unknown_action_raises(self, nova):
        with pytest.raises(ValueError, match="Unknown action"):
            nova.execute_action("NONEXISTENT_ACTION", {})

    def test_force_no_approval(self, nova):
        record = nova.execute_action("SEND_DISPUTE_LETTER", {
            "recipient_name": "Bank",
            "recipient_address": "456 Wall St",
            "dispute_reason": "Error",
            "account_number": "99999",
        }, approval_required=False)
        assert record.status == ActionStatus.COMPLETED.value

    def test_schedule_court_date(self, nova):
        record = nova.execute_action("SCHEDULE_COURT_DATE", {
            "case_number": "CV-2025-001",
            "court_name": "Superior Court",
            "date": "2025-06-15",
            "time": "09:00",
        })
        assert record.status == ActionStatus.COMPLETED.value
        assert "event_id" in record.result


class TestApprovalFlow:
    def test_approve_execution(self, nova):
        record = nova.execute_action("FILE_COURT_MOTION", {
            "case_number": "CV-2025-001",
            "court_name": "Superior Court",
            "motion_type": "Dismiss",
            "motion_body": "Motion to dismiss...",
        })
        assert record.status == ActionStatus.AWAITING_APPROVAL.value
        assert nova.approve_execution(record.execution_id, "admin") is True

    def test_reject_execution(self, nova):
        record = nova.execute_action("SEND_DEMAND_LETTER", {
            "recipient_name": "Debtor",
            "recipient_email": "debtor@example.com",
            "demand_amount": "5000",
            "demand_reason": "Breach of contract",
        })
        assert nova.reject_execution(record.execution_id, "Not ready") is True

    def test_reject_already_rejected(self, nova):
        record = nova.execute_action("SEND_DEMAND_LETTER", {
            "recipient_name": "X", "recipient_email": "x@x.com",
            "demand_amount": "100", "demand_reason": "test",
        })
        nova.reject_execution(record.execution_id, "reason")
        assert nova.reject_execution(record.execution_id, "again") is False


class TestRollback:
    def test_rollback_completed(self, nova):
        record = nova.execute_action("NOTIFY_CREDITOR", {
            "creditor_name": "C", "creditor_address": "A",
            "notification_type": "t", "message": "m",
        })
        result = nova.rollback_action(record.execution_id)
        assert result is not None
        assert result["status"] == "rolled_back"

    def test_rollback_nonexistent(self, nova):
        assert nova.rollback_action("nonexistent-id") is None


class TestExecutionHistory:
    def test_history_empty(self, nova):
        assert nova.get_execution_history() == []

    def test_history_filter_by_type(self, nova):
        nova.execute_action("NOTIFY_CREDITOR", {
            "creditor_name": "C", "creditor_address": "A",
            "notification_type": "t", "message": "m",
        })
        history = nova.get_execution_history(action_type="NOTIFY_CREDITOR")
        assert len(history) == 1

    def test_log_execution(self, nova):
        eid = nova.log_execution("CUSTOM", {"status": "ok"}, {"proof": "data"})
        assert eid is not None


# ── ActionRegistry Tests ──────────────────────────────────────────


class TestRegistryBasics:
    def test_register_action(self, registry):
        spec = RegActionSpec(
            action_type="TEST_ACTION", name="Test", description="Test action",
            category="test", required_params=["param1"],
        )
        registry.register_action(spec)
        assert registry.has_action("TEST_ACTION")

    def test_duplicate_raises(self, registry):
        spec = RegActionSpec(
            action_type="DUP", name="Dup", description="d",
            category="test", required_params=[],
        )
        registry.register_action(spec)
        with pytest.raises(ActionAlreadyRegisteredError):
            registry.register_action(spec)

    def test_overwrite(self, registry):
        spec = RegActionSpec(
            action_type="OW", name="OW1", description="d",
            category="test", required_params=[],
        )
        registry.register_action(spec)
        spec2 = RegActionSpec(
            action_type="OW", name="OW2", description="d2",
            category="test", required_params=[],
        )
        registry.register_action(spec2, overwrite=True)
        assert registry.get_action("OW").name == "OW2"

    def test_get_nonexistent_raises(self, registry):
        with pytest.raises(ActionNotFoundError):
            registry.get_action("NOPE")

    def test_list_actions(self, registry):
        spec = RegActionSpec(
            action_type="LA", name="LA", description="d",
            category="cat1", required_params=[],
        )
        registry.register_action(spec)
        actions = registry.list_actions()
        assert len(actions) == 1

    def test_list_by_category(self, registry):
        for i, cat in enumerate(["legal", "legal", "dispute"]):
            spec = RegActionSpec(
                action_type=f"ACT_{i}", name=f"A{i}", description="d",
                category=cat, required_params=[],
            )
            registry.register_action(spec)
        assert len(registry.list_actions(category="legal")) == 2
        assert len(registry.list_actions(category="dispute")) == 1

    def test_unregister(self, registry):
        spec = RegActionSpec(
            action_type="UR", name="UR", description="d",
            category="test", required_params=[],
        )
        registry.register_action(spec)
        assert registry.unregister_action("UR") is True
        assert not registry.has_action("UR")

    def test_validate_params(self, registry):
        spec = RegActionSpec(
            action_type="VP", name="VP", description="d",
            category="test", required_params=["a", "b"],
        )
        registry.register_action(spec)
        errors = registry.validate_params("VP", {"a": "1"})
        assert len(errors) == 1

    def test_enable_disable(self, registry):
        spec = RegActionSpec(
            action_type="ED", name="ED", description="d",
            category="test", required_params=[],
        )
        registry.register_action(spec)
        registry.disable_action("ED")
        assert len(registry.list_actions()) == 0
        registry.enable_action("ED")
        assert len(registry.list_actions()) == 1

    def test_stats(self, registry):
        stats = registry.get_stats()
        assert "total_actions" in stats

    def test_export_schema(self, registry):
        schema = registry.export_schema()
        assert "registry_version" in schema


# ── ExecutionLedger Tests ─────────────────────────────────────────


class TestLedgerBasics:
    def test_empty_ledger(self, ledger):
        assert ledger.size == 0

    def test_append_entry(self, ledger):
        entry = LedgerEntry(
            entry_id="e1", action_id="a1", action_type="TEST",
            params={"x": 1}, result={"ok": True}, status="COMPLETED",
            user_id="u1", approval_status="APPROVED",
        )
        ledger.append(entry)
        assert ledger.size == 1
        assert entry.entry_hash != ""

    def test_hash_chain(self, ledger):
        for i in range(5):
            entry = LedgerEntry(
                entry_id=f"e{i}", action_id=f"a{i}", action_type="TEST",
                params={}, result={}, status="COMPLETED",
                user_id="u1", approval_status="OK",
            )
            ledger.append(entry)
        assert ledger.verify_integrity() is True

    def test_get_history(self, ledger):
        for i in range(3):
            ledger.append(LedgerEntry(
                entry_id=f"e{i}", action_id=f"a{i}",
                action_type="TYPE_A" if i < 2 else "TYPE_B",
                params={}, result={}, status="COMPLETED",
                user_id="u1", approval_status="OK",
            ))
        assert len(ledger.get_history(action_type="TYPE_A")) == 2
        assert len(ledger.get_history(action_type="TYPE_B")) == 1

    def test_get_entry(self, ledger):
        ledger.append(LedgerEntry(
            entry_id="find-me", action_id="a1", action_type="T",
            params={}, result={}, status="OK", user_id="u", approval_status="OK",
        ))
        assert ledger.get_entry("find-me") is not None
        assert ledger.get_entry("missing") is None

    def test_export_evidence(self, ledger, tmp_path):
        for i in range(3):
            ledger.append(LedgerEntry(
                entry_id=f"e{i}", action_id=f"a{i}", action_type="TEST",
                params={}, result={}, status="COMPLETED",
                user_id="u1", approval_status="OK", case_id="CASE-001",
            ))
        zip_path = ledger.export_evidence_bundle("CASE-001")
        assert os.path.exists(zip_path)

    def test_export_no_entries_raises(self, ledger):
        with pytest.raises(ValueError):
            ledger.export_evidence_bundle("NONEXISTENT")

    def test_stats(self, ledger):
        stats = ledger.get_stats()
        assert "total_entries" in stats

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "persist.jsonl")
        l1 = ExecutionLedger(ledger_path=path)
        l1.append(LedgerEntry(
            entry_id="p1", action_id="a1", action_type="T",
            params={}, result={}, status="OK", user_id="u", approval_status="OK",
        ))
        l2 = ExecutionLedger(ledger_path=path)
        assert l2.size == 1


# ── ApprovalGateway Tests ────────────────────────────────────────


class TestGatewayBasics:
    def test_submit_auto_approve(self, gateway):
        req = gateway.submit_for_approval("NOTIFY_CREDITOR", {
            "description": "Notify creditor"
        })
        assert req.status == GWApprovalStatus.AUTO_APPROVED.value

    def test_submit_requires_human(self, gateway):
        req = gateway.submit_for_approval("SEND_DISPUTE_LETTER", {
            "description": "Send dispute"
        })
        assert req.status == GWApprovalStatus.PENDING.value

    def test_approve(self, gateway):
        req = gateway.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        approved = gateway.approve(req.request_id, "admin")
        assert approved.status == GWApprovalStatus.APPROVED.value

    def test_reject(self, gateway):
        req = gateway.submit_for_approval("SEND_DEMAND_LETTER", {"description": "d"})
        rejected = gateway.reject(req.request_id, "Not ready")
        assert rejected.status == GWApprovalStatus.REJECTED.value

    def test_reject_already_approved_raises(self, gateway):
        req = gateway.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        gateway.approve(req.request_id, "admin")
        with pytest.raises(ValueError):
            gateway.reject(req.request_id, "too late")

    def test_escalate(self, gateway):
        req = gateway.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        escalated = gateway.escalate(req.request_id)
        assert escalated.tier in [t.value for t in ApprovalTier]

    def test_pending_requests(self, gateway):
        gateway.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        pending = gateway.get_pending_requests()
        assert len(pending) == 1

    def test_legal_tier(self, gateway):
        req = gateway.submit_for_approval("FILE_COURT_MOTION", {"description": "d"})
        assert req.tier == ApprovalTier.LEGAL.value

    def test_history(self, gateway):
        req = gateway.submit_for_approval("NOTIFY_CREDITOR", {"description": "d"})
        history = gateway.get_history()
        assert len(history) >= 1

    def test_stats(self, gateway):
        stats = gateway.get_stats()
        assert "total_requests" in stats

    def test_notification_callback(self):
        cb = MagicMock()
        gw = ApprovalGateway(notification_callback=cb)
        gw.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        cb.assert_called()

    def test_get_request_status(self, gateway):
        req = gateway.submit_for_approval("SEND_DISPUTE_LETTER", {"description": "d"})
        status = gateway.get_request_status(req.request_id)
        assert status["status"] == GWApprovalStatus.PENDING.value

    def test_nonexistent_request_raises(self, gateway):
        with pytest.raises(ValueError):
            gateway.approve("nonexistent-id", "admin")

    def test_auto_approve_disabled(self):
        gw = ApprovalGateway(auto_approve_enabled=False)
        req = gw.submit_for_approval("NOTIFY_CREDITOR", {"description": "d"})
        assert req.status == GWApprovalStatus.PENDING.value
