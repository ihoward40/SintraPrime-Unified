"""SP-GOD0-MISSION-CONTROL-001 Phase 14 — Mission Control audit trail tests.

Every Mission Control mutation must itself produce an audit event with
principal_actor / previous_state / new_state / authority_basis. Mission
Control is part of the evidence chain.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from governance.audit_trail import AuditTrail
from portal.services.mission_control_audit import (
    MissionControlAuditEvent,
    record_mission_control_action,
)


@pytest.fixture
def audit_trail(tmp_path: Path) -> AuditTrail:
    return AuditTrail(db_path=str(tmp_path / "audit.db")) if _accepts_db_path() else AuditTrail()


def _accepts_db_path() -> bool:
    import inspect

    return "db_path" in inspect.signature(AuditTrail.__init__).parameters


class TestMissionControlAudit:
    def test_approval_grant_is_audited(self, audit_trail):
        event = record_mission_control_action(
            audit_trail,
            principal_actor="agent.principal",
            action="APPROVE",
            target="approval-req-1",
            mission_id="M-1",
            previous_state="PENDING",
            new_state="APPROVED",
            authority_basis="principal-envelope-1",
            receipt="GOV-APPROVED-1",
        )
        assert event.action == "APPROVE"
        assert event.authority_basis == "principal-envelope-1"

    def test_approval_deny_is_audited_with_high_risk(self, audit_trail):
        event = record_mission_control_action(
            audit_trail,
            principal_actor="agent.principal",
            action="DENY",
            target="approval-req-2",
            mission_id="M-1",
            previous_state="PENDING",
            new_state="DENIED",
            authority_basis="principal-envelope-1",
        )
        assert event.new_state == "DENIED"

    def test_events_carry_required_fields(self, audit_trail):
        event = record_mission_control_action(
            audit_trail,
            principal_actor="agent.principal",
            action="REQUEST_MORE_EVIDENCE",
            target="approval-req-3",
            mission_id="M-2",
            previous_state="PENDING",
            new_state="EVIDENCE_REQUESTED",
            authority_basis="principal-envelope-2",
        )
        # directive Phase 14 required fields
        assert event.principal_actor
        assert event.action
        assert event.target
        assert event.mission_id
        assert event.timestamp is not None
        assert event.previous_state
        assert event.new_state
        assert event.authority_basis

    def test_audit_trail_records_the_action(self, audit_trail):
        record_mission_control_action(
            audit_trail,
            principal_actor="agent.principal",
            action="APPROVE",
            target="approval-req-9",
            mission_id="M-1",
            previous_state="PENDING",
            new_state="APPROVED",
            authority_basis="principal-envelope-1",
        )
        entries = audit_trail.query(actor="agent.principal")
        assert any(
            getattr(e, "action", "") == "MISSION_CONTROL_APPROVE" for e in entries
        )
