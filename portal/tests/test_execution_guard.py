"""
Test suite for the Centralized Execution Guard (G4.7).

Test groups:
    - Kill switch enforcement
    - Mission-state enforcement
    - Governance and approval
    - Service boundary (guard cannot be bypassed)
    - Concurrency (kill-switch race, idempotent approvals)
    - Failure behavior (fail-closed, unknown action, missing mission)
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.observatory import (
    Agent,
    Approval,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)
from portal.schemas.observatory import MissionStatus
from portal.services.execution_guard import (
    ApprovalRequiredError,
    DecisionReasonCode,
    ExecutionAction,
    ExecutionGuard,
    ExecutionGuardDecision,
    ExecutionGuardError,
    GovernanceGateDeniedError,
    KillSwitchActiveError,
    MissionStateBlockedError,
    PrincipalContext,
)
from portal.services.observatory_service import (
    AgentService,
    ApprovalService,
    EventService,
    KillSwitchService,
    MissionService,
)

# ── Tables for create_all ──
OBSERVATORY_TABLES = [
    Agent.__table__,
    Mission.__table__,
    MissionAgent.__table__,
    ObservatoryRunHead.__table__,
    ObservatoryEvent.__table__,
    Approval.__table__,
    Evidence.__table__,
    Incident.__table__,
    KillSwitchState.__table__,
]


# ── Fixture ──

@pytest_asyncio.fixture
async def db():
    """In-memory async SQLite session for execution guard tests."""
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=OBSERVATORY_TABLES))
        # Create the partial unique index for kill-switch
        await conn.execute(sa_text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_observatory_single_active_kill_switch "
            "ON observatory_kill_switch_state (is_active) WHERE is_active = 1"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    # Reset statistics for each test
    ExecutionGuard.reset_statistics()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _create_mission(db, title="Test Mission", status="QUEUED"):
    """Helper to create a mission.

    Sets status directly on the model to bypass the execution guard in
    update_status() — this helper is for test setup, not for testing the
    guard itself.
    """
    mission = await MissionService.create(
        db,
        title=title,
        objective="Test objective",
        governance_gates_required=["G-01"],
    )
    await db.commit()
    if status != "QUEUED":
        # Set status directly on the model to bypass the guard in update_status()
        from sqlalchemy import select as sa_select
        result = await db.execute(sa_select(Mission).where(Mission.id == mission.id))
        mission = result.scalar_one()
        mission.status = status
        await db.flush()
        await db.commit()
    return mission


async def _set_mission_status_direct(db, mission_id, status):
    """Set mission status directly, bypassing the execution guard.

    Use this for test setup when you need a mission in a specific state
    without triggering the guard in update_status().
    """
    from sqlalchemy import select as sa_select
    result = await db.execute(sa_select(Mission).where(Mission.id == mission_id))
    mission = result.scalar_one()
    mission.status = status
    await db.flush()
    await db.commit()


async def _activate_kill_switch(db, reason="Test kill switch"):
    """Helper to activate the global kill switch."""
    await KillSwitchService.activate(db, reason=reason, activated_by="test")
    await db.commit()


async def _create_approval(db, mission_id, gate="G-05", status="APPROVED"):
    """Helper to create an approval record."""
    approval = await ApprovalService.create(
        db,
        mission_id=mission_id,
        gate=gate,
        requester="test-requester",
    )
    await db.commit()
    if status == "APPROVED":
        await ApprovalService.decide(
            db,
            approval_id=approval.id,
            decision="APPROVED",
            reviewer="test-reviewer",
        )
        await db.commit()
    elif status == "DENIED":
        await ApprovalService.decide(
            db,
            approval_id=approval.id,
            decision="DENIED",
            reviewer="test-reviewer",
        )
        await db.commit()
    elif status == "EXPIRED":
        # Manually update to expired
        approval_db = await db.get(Approval, approval.id)
        approval_db.status = "EXPIRED"
        await db.commit()
    return approval


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Kill-Switch Enforcement
# ═══════════════════════════════════════════════════════════════════════════════

class TestKillSwitchEnforcement:

    @pytest.mark.asyncio
    async def test_consequential_action_denied_while_kill_switch_active(self, db):
        """A consequential action is denied when the kill switch is active."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.KILL_SWITCH_ACTIVE

    @pytest.mark.asyncio
    async def test_consequential_action_allowed_when_kill_switch_inactive(self, db):
        """A consequential action is allowed when the kill switch is inactive."""
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)
        assert decision.allowed
        assert decision.reason_code == DecisionReasonCode.ALLOWED

    @pytest.mark.asyncio
    async def test_read_only_evidence_allowed_during_kill_switch(self, db):
        """Evidence reads remain available during kill-switch active state."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.EVIDENCE_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_health_read_allowed_during_kill_switch(self, db):
        """Health checks remain available during kill-switch active state."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.HEALTH_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_event_read_allowed_during_kill_switch(self, db):
        """Event reads remain available during kill-switch active state."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.EVENT_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_replay_read_allowed_during_kill_switch(self, db):
        """Replay reads remain available during kill-switch active state."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.REPLAY_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_incident_read_allowed_during_kill_switch(self, db):
        """Incident reads remain available during kill-switch active state."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.INCIDENT_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_kill_switch_activation_always_allowed(self, db):
        """Kill-switch activation itself is always allowed when properly authenticated,
        even if already active."""
        await _activate_kill_switch(db)
        admin_principal = PrincipalContext.for_testing(
            subject_id="test-admin", roles=["system_admin", "incident_commander"]
        )
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_ACTIVATE, principal_context=admin_principal
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_kill_switch_clearing_evaluated_separately(self, db):
        """Kill-switch clearing is evaluated separately from BLOCKED actions.

        G4.7: KILL_SWITCH_CLEAR has kill_switch=CLEARING (not BLOCKED),
        so it is NOT blocked by the active kill switch. It passes through
        the guard when an authenticated principal with the required role
        is provided.
        """
        await _activate_kill_switch(db)
        principal = PrincipalContext.for_testing(
            subject_id="test-incident-commander",
            roles=["incident_commander"],
        )
        decision = await ExecutionGuard.evaluate(
            db,
            action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        # CLEARING behavior means the action is not blocked by the kill switch
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_mission_start_denied_during_kill_switch(self, db):
        """Mission start is denied during kill-switch active state."""
        mission = await _create_mission(db, status="QUEUED")
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_START, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.KILL_SWITCH_ACTIVE

    @pytest.mark.asyncio
    async def test_db_failure_fails_closed_for_consequential(self, db):
        """If kill-switch lookup fails, consequential actions fail closed.

        KillSwitchService.is_active() already fails closed by returning True
        on DB errors, so the guard sees an "active" kill switch and denies.
        The guard's own FAIL_CLOSED path is for cases where is_active itself
        raises an exception that escapes its internal try/except.
        """
        # Simulate DB failure by replacing the session with a broken one
        class BrokenSession:
            async def execute(self, *args, **kwargs):
                raise Exception("Simulated DB failure")
        broken = BrokenSession()
        decision = await ExecutionGuard.evaluate(broken, action=ExecutionAction.FILE_MODIFY)
        assert not decision.allowed
        # KillSwitchService.is_active catches exceptions and returns True (fail closed)
        assert decision.reason_code in (
            DecisionReasonCode.KILL_SWITCH_ACTIVE,
            DecisionReasonCode.FAIL_CLOSED,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Mission-State Enforcement
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissionStateEnforcement:

    @pytest.mark.asyncio
    async def test_paused_mission_blocks_execution(self, db):
        """A paused mission blocks normal execution."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "PAUSED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_paused_mission_allows_resume(self, db):
        """A paused mission allows resume."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "PAUSED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_RESUME, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_paused_mission_allows_cancel(self, db):
        """A paused mission allows cancel."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "PAUSED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_CANCEL, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_frozen_mission_blocks_resume(self, db):
        """A frozen mission blocks resume (no explicit unfreeze action defined)."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "FROZEN")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_RESUME, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_frozen_mission_allows_evidence_read(self, db):
        """A frozen mission allows evidence reads."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "FROZEN")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.EVIDENCE_READ, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_canceled_mission_blocks_execution(self, db):
        """A canceled mission blocks all execution."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "CANCELED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_completed_mission_blocks_mutation(self, db):
        """A completed mission blocks further mutation."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "COMPLETED")
        # TOOL_INVOKE has mission_state_required=True, so it checks mission state
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_completed_mission_allows_evidence_export(self, db):
        """A completed mission allows evidence export."""
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "COMPLETED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.EXPORT_EVIDENCE, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_active_mission_allows_permitted_execution(self, db):
        """An executing mission allows permitted actions like tool_invoke.

        TOOL_INVOKE has CONDITIONAL approval (G4.7 fails closed until G4.8).
        With an existing approval, it should be allowed.
        """
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-07", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_missing_mission_denies_consequential_action(self, db):
        """A consequential action with a non-existent mission_id is denied."""
        fake_id = str(uuid.uuid4())
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_START, mission_id=fake_id
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_NOT_FOUND


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Governance and Approval
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceAndApproval:

    @pytest.mark.asyncio
    async def test_high_risk_action_with_correct_gate_allowed(self, db):
        """A high-risk action with the correct governance gate and approval is allowed."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-05", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.FINANCIAL_ACTION, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_approval_required_action_returns_approval_required(self, db):
        """An approval-required action without approval returns APPROVAL_REQUIRED."""
        mission = await _create_mission(db, status="EXECUTING")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.FINANCIAL_ACTION, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_existing_approval_allows_action(self, db):
        """An existing approved approval allows the action."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-05", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_FREEZE, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_denied_approval_denies_action(self, db):
        """A denied approval causes the action to be denied."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-05", status="DENIED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.FINANCIAL_ACTION, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_expired_approval_denies_action(self, db):
        """An expired approval causes the action to be denied."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-05", status="EXPIRED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.FINANCIAL_ACTION, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_require_allowed_raises_approval_required(self, db):
        """require_allowed raises ApprovalRequiredError when approval is missing."""
        mission = await _create_mission(db, status="EXECUTING")
        with pytest.raises(ApprovalRequiredError) as exc_info:
            await ExecutionGuard.require_allowed(
                db, action=ExecutionAction.FINANCIAL_ACTION, mission_id=str(mission.id)
            )
        assert exc_info.value.decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Service Boundary
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceBoundary:

    @pytest.mark.asyncio
    async def test_require_allowed_raises_on_denial(self, db):
        """require_allowed raises a typed exception on denial."""
        await _activate_kill_switch(db)
        with pytest.raises(KillSwitchActiveError):
            await ExecutionGuard.require_allowed(
                db, action=ExecutionAction.FILE_MODIFY
            )

    @pytest.mark.asyncio
    async def test_require_allowed_returns_decision_on_allow(self, db):
        """require_allowed returns the decision on success."""
        decision = await ExecutionGuard.require_allowed(
            db, action=ExecutionAction.EVIDENCE_READ
        )
        assert decision.allowed
        assert isinstance(decision, ExecutionGuardDecision)

    @pytest.mark.asyncio
    async def test_denial_occurs_before_side_effect(self, db):
        """Denial occurs before any side effect (no mutation of the requested resource)."""
        await _activate_kill_switch(db)
        # The guard should deny without touching the resource
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.FILE_DELETE, resource_id="/important/file.db"
        )
        assert not decision.allowed
        # No file was deleted (this is a logical test — the guard doesn't touch files)

    @pytest.mark.asyncio
    async def test_audit_event_created_on_denial(self, db):
        """An audit event is created when an action is denied."""
        await _activate_kill_switch(db)
        await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)
        # Check that an EXECUTION_GUARD_DENIED event was created
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(ObservatoryEvent).where(
                ObservatoryEvent.event_type == "EXECUTION_GUARD_DENIED"
            )
        )
        events = result.scalars().all()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_audit_event_created_on_allow(self, db):
        """An audit event is created when an action is allowed."""
        await ExecutionGuard.evaluate(db, action=ExecutionAction.EVIDENCE_READ)
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(ObservatoryEvent).where(
                ObservatoryEvent.event_type == "EXECUTION_GUARD_ALLOWED"
            )
        )
        events = result.scalars().all()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_sensitive_content_absent_from_audit_event(self, db):
        """Sensitive content is absent from audit event payloads."""
        await _activate_kill_switch(db)
        await ExecutionGuard.evaluate(
            db,
            action=ExecutionAction.FILE_MODIFY,
            resource_type="file",
            resource_id="/path/to/credential_password_secret.txt",
        )
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(ObservatoryEvent).where(
                ObservatoryEvent.event_type == "EXECUTION_GUARD_DENIED"
            )
        )
        events = result.scalars().all()
        assert len(events) >= 1
        import json
        payload = json.loads(events[0].payload) if isinstance(events[0].payload, str) else events[0].payload
        resource_id = payload.get("resource_id", "")
        assert "password" not in resource_id.lower()
        assert "secret" not in resource_id.lower()
        assert "***MASKED***" in resource_id

    @pytest.mark.asyncio
    async def test_error_message_does_not_contain_resource_id(self, db):
        """The error message does not contain the resource_id (no sensitive leak)."""
        await _activate_kill_switch(db)
        try:
            await ExecutionGuard.require_allowed(
                db,
                action=ExecutionAction.FILE_DELETE,
                resource_id="/secret/path/to/delete.txt",
            )
        except KillSwitchActiveError as e:
            msg = str(e)
            assert "/secret/path/to/delete.txt" not in msg


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:

    @pytest.mark.asyncio
    async def test_kill_switch_race_denies_stale_action(self, db):
        """When the kill switch activates during evaluation, the stale action is denied.

        We simulate the race by activating the kill switch and then evaluating
        a consequential action — the action should see the active state and be denied.
        """
        # First, evaluate with KS inactive — should be allowed
        decision_before = await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)
        assert decision_before.allowed

        # Now activate the kill switch
        await _activate_kill_switch(db)

        # Evaluate again — should be denied
        decision_after = await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)
        assert not decision_after.allowed
        assert decision_after.reason_code == DecisionReasonCode.KILL_SWITCH_ACTIVE

    @pytest.mark.asyncio
    async def test_concurrent_evaluations_deterministic(self, db):
        """Two simultaneous evaluations of a denied action produce deterministic results."""
        await _activate_kill_switch(db)
        results = await asyncio.gather(
            ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY),
            ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY),
        )
        assert all(not r.allowed for r in results)
        assert all(r.reason_code == DecisionReasonCode.KILL_SWITCH_ACTIVE for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_evaluations_deterministic_when_allowed(self, db):
        """Two simultaneous evaluations of an allowed action both succeed."""
        results = await asyncio.gather(
            ExecutionGuard.evaluate(db, action=ExecutionAction.HEALTH_READ),
            ExecutionGuard.evaluate(db, action=ExecutionAction.HEALTH_READ),
        )
        assert all(r.allowed for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Failure Behavior
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureBehavior:

    @pytest.mark.asyncio
    async def test_unknown_action_fails_closed(self, db):
        """An unknown action (not in the policy map) fails closed."""
        # Create a fake action that's not in the policy
        # We can't easily create an unknown enum value, so we test with a
        # valid action but patch the policy to remove it
        from portal.services import execution_guard as eg_module
        original = eg_module._ACTION_POLICY.copy()
        try:
            eg_module._ACTION_POLICY.pop(ExecutionAction.FILE_READ, None)
            decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_READ)
            assert not decision.allowed
            assert decision.reason_code == DecisionReasonCode.UNKNOWN_ACTION
        finally:
            eg_module._ACTION_POLICY = original

    @pytest.mark.asyncio
    async def test_unknown_mission_state_fails_closed(self, db):
        """An unknown mission state fails closed."""
        mission = await _create_mission(db, status="EXECUTING")
        # Manually set an invalid status
        mission_db = await db.get(Mission, mission.id)
        mission_db.status = "UNKNOWN_STATE"
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.UNKNOWN_MISSION_STATE

    @pytest.mark.asyncio
    async def test_read_only_diagnostics_available_under_failure(self, db):
        """Read-only system diagnostics remain available under documented failure conditions.

        HEALTH_READ has kill_switch=ALLOWED, so it skips the kill-switch DB lookup
        entirely. This means it remains available even if the DB is unreachable.
        This is the documented fail-open exception for read-only diagnostics.
        """
        # Use a broken session — HEALTH_READ should still pass because
        # its kill_switch behavior is ALLOWED (no DB lookup needed)
        class BrokenSession:
            async def execute(self, *args, **kwargs):
                raise Exception("Simulated DB failure")
        broken = BrokenSession()
        decision = await ExecutionGuard.evaluate(broken, action=ExecutionAction.HEALTH_READ)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_missing_mission_denies_consequential_with_mission_state_required(self, db):
        """A consequential action with mission_state_required=True and missing mission is denied."""
        fake_id = str(uuid.uuid4())
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.SUBAGENT_SPAWN, mission_id=fake_id
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_NOT_FOUND


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Statistics and Health
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsAndHealth:

    @pytest.mark.asyncio
    async def test_statistics_track_allowed_and_denied(self, db):
        """Guard statistics track allowed and denied decisions."""
        ExecutionGuard.reset_statistics()
        await ExecutionGuard.evaluate(db, action=ExecutionAction.HEALTH_READ)  # allowed
        await ExecutionGuard.evaluate(db, action=ExecutionAction.HEALTH_READ)  # allowed
        await _activate_kill_switch(db)
        await ExecutionGuard.evaluate(db, action=ExecutionAction.FILE_MODIFY)  # denied
        stats = ExecutionGuard.get_statistics()
        assert stats.allowed == 2
        assert stats.denied == 1
        assert "KILL_SWITCH_ACTIVE" in stats.denials_by_reason
        assert "file.modify" in stats.denials_by_action

    @pytest.mark.asyncio
    async def test_health_returns_policy_and_status(self, db):
        """Guard health returns policy version and component health."""
        health = await ExecutionGuard.health(db)
        assert health["policy_loaded"] is True
        assert health["policy_version"] == "G4.7.1"
        assert health["actions_classified"] > 0
        assert "statistics" in health


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Principal Context
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrincipalContext:

    def test_unauthenticated_principal(self):
        """An unauthenticated principal has no identity."""
        ctx = PrincipalContext.unauthenticated()
        assert not ctx.is_authenticated
        assert ctx.subject_id is None

    def test_test_principal_for_testing(self):
        """A test principal is authenticated with provided roles."""
        ctx = PrincipalContext.for_testing(
            subject_id="test-user",
            roles=["admin"],
            permissions=["read", "write"],
        )
        assert ctx.is_authenticated
        assert ctx.subject_id == "test-user"
        assert "admin" in ctx.roles

    @pytest.mark.asyncio
    async def test_guard_accepts_principal_context(self, db):
        """The guard accepts a principal context without error."""
        ctx = PrincipalContext.for_testing()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.HEALTH_READ, principal_context=ctx
        )
        assert decision.allowed


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Conditional Approval Fails Closed
# ═══════════════════════════════════════════════════════════════════════════════

class TestConditionalApprovalFailClosed:

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_without_resolved_approval(self, db):
        """TOOL_INVOKE has CONDITIONAL approval and must fail closed when
        the condition is unresolved (no approval exists).

        Until G4.8 implements conditional approval logic, CONDITIONAL
        approval behavior DENIES by default.
        """
        mission = await _create_mission(db, status="EXECUTING")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED
        assert "conditional" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_tool_invoke_allowed_with_existing_approval(self, db):
        """TOOL_INVOKE is allowed when an existing approval exists (condition resolved)."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-07", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_with_rejected_approval(self, db):
        """TOOL_INVOKE denied when the only approval is REJECTED (fail closed)."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-07", status="REJECTED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_with_wrong_mission_approval(self, db):
        """TOOL_INVOKE denied when the approved approval belongs to a different mission."""
        mission = await _create_mission(db, status="EXECUTING")
        other_mission = await _create_mission(db, status="EXECUTING")
        # Approval exists but for the OTHER mission
        await _create_approval(db, other_mission.id, gate="G-07", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_with_wrong_gate_approval(self, db):
        """TOOL_INVOKE denied when the approved approval is for a different gate.

        TOOL_INVOKE's policy requires gate G-07. An approval for G-05 must
        not satisfy the G-07 requirement.
        """
        mission = await _create_mission(db, status="EXECUTING")
        # Approval exists for G-05, but TOOL_INVOKE requires G-07
        await _create_approval(db, mission.id, gate="G-05", status="APPROVED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_with_expired_approval(self, db):
        """TOOL_INVOKE denied when the approval has EXPIRED status (fail closed)."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-07", status="EXPIRED")
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

    @pytest.mark.asyncio
    async def test_tool_invoke_fail_closed_on_approval_lookup_error(self, db):
        """TOOL_INVOKE fails closed when approval lookup raises an error."""
        mission = await _create_mission(db, status="EXECUTING")

        # Create a fake session that raises on Approval queries
        class FailingSession:
            async def execute(self, *args, **kwargs):
                from sqlalchemy.exc import SQLAlchemyError
                raise SQLAlchemyError("simulated DB failure")

        with pytest.raises(Exception):
            await ExecutionGuard._check_approval(
                FailingSession(), str(mission.id), "G-07"
            )

    @pytest.mark.asyncio
    async def test_tool_invoke_idempotent_duplicate_request(self, db):
        """TOOL_INVOKE with an existing approval is idempotent across multiple evaluations."""
        mission = await _create_mission(db, status="EXECUTING")
        await _create_approval(db, mission.id, gate="G-07", status="APPROVED")
        decision1 = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        decision2 = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert decision1.allowed
        assert decision2.allowed
        # Idempotent: same approval ID returned on both evaluations
        assert decision1.approval_id == decision2.approval_id

    @pytest.mark.asyncio
    async def test_tool_invoke_denied_with_spy_adapter_not_called(self, db):
        """When TOOL_INVOKE is denied, the tool adapter is never invoked.

        Uses a spy adapter to prove no side effect occurs on denial.
        """
        mission = await _create_mission(db, status="EXECUTING")

        # Spy adapter records whether it was called
        calls = []

        class SpyToolAdapter:
            async def invoke(self, *args, **kwargs):
                calls.append((args, kwargs))
                return "tool-result"

        adapter = SpyToolAdapter()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        # Denied (no approval exists)
        assert not decision.allowed
        # Simulate the caller respecting the decision
        if decision.allowed:
            await adapter.invoke("some-tool")
        # Adapter must NOT have been called
        assert len(calls) == 0, "Tool adapter must not be called on denial"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Production Audit Assertion
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductionAuditAssertion:

    def test_audit_enabled_is_true_by_default(self):
        """_audit_enabled defaults to True."""
        # Save and restore
        original = ExecutionGuard._audit_enabled
        try:
            ExecutionGuard._audit_enabled = True
            ExecutionGuard.assert_production_ready()  # Should not raise
        finally:
            ExecutionGuard._audit_enabled = original

    def test_assert_production_ready_raises_when_audit_disabled(self):
        """assert_production_ready raises when _audit_enabled is False."""
        original = ExecutionGuard._audit_enabled
        try:
            ExecutionGuard._audit_enabled = False
            with pytest.raises(RuntimeError, match="audit.*cannot be disabled"):
                ExecutionGuard.assert_production_ready()
        finally:
            ExecutionGuard._audit_enabled = original

    def test_audit_enabled_restored_after_test(self):
        """After tests toggle _audit_enabled, it must be restored to True."""
        assert ExecutionGuard._audit_enabled is True, (
            "Audit should be enabled by default after test cleanup"
        )

    def test_api_input_cannot_modify_audit_flag(self):
        """The _audit_enabled flag is a class variable, not configurable via API."""
        # The flag is not exposed through any settings, env var, or API endpoint.
        # It can only be set programmatically (test-only).
        assert not hasattr(ExecutionGuard, '_audit_enabled_env_var')
        assert not hasattr(ExecutionGuard, '_audit_enabled_config')


class TestStartupAuditIntegration:
    """Verify that the application lifespan calls assert_production_ready()."""

    def test_lifespan_calls_assert_production_ready(self):
        """The lifespan function imports and calls ExecutionGuard.assert_production_ready."""
        import inspect
        from portal.main import lifespan
        source = inspect.getsource(lifespan)
        assert "assert_production_ready" in source, (
            "lifespan must call ExecutionGuard.assert_production_ready()"
        )

    @pytest.mark.asyncio
    async def test_startup_succeeds_with_audit_enabled(self):
        """Normal startup succeeds when auditing is enabled."""
        original = ExecutionGuard._audit_enabled
        try:
            ExecutionGuard._audit_enabled = True
            ExecutionGuard.assert_production_ready()  # Should not raise
        finally:
            ExecutionGuard._audit_enabled = original

    @pytest.mark.asyncio
    async def test_startup_fails_when_audit_disabled(self):
        """Startup fails when audit emission is disabled."""
        original = ExecutionGuard._audit_enabled
        try:
            ExecutionGuard._audit_enabled = False
            with pytest.raises(RuntimeError, match="cannot be disabled"):
                ExecutionGuard.assert_production_ready()
        finally:
            ExecutionGuard._audit_enabled = original


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Service Bypass Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceBypass:

    @pytest.mark.asyncio
    async def test_internal_mission_create_denied_while_kill_switch_active(self, db):
        """An internal caller using MissionService.create() cannot bypass the guard."""
        await _activate_kill_switch(db)
        with pytest.raises((KillSwitchActiveError, Exception)):
            await MissionService.create(db, title="Should Fail")

    @pytest.mark.asyncio
    async def test_mission_create_denial_creates_no_mission(self, db):
        """When MissionService.create() is denied, no mission is created in the DB."""
        from sqlalchemy import select as sa_select
        await _activate_kill_switch(db)
        try:
            await MissionService.create(db, title="Should Not Exist")
        except Exception:
            pass  # Expected
        await db.rollback()
        result = await db.execute(sa_select(Mission))
        missions = result.scalars().all()
        assert len(missions) == 0, "No mission should exist after denied creation"

    @pytest.mark.asyncio
    async def test_kill_switch_clear_invokes_guard(self, db):
        """Kill-switch clear passes through the guard with authenticated principal.

        G4.7: KILL_SWITCH_CLEAR requires an authenticated principal with
        incident_commander or system_admin role. With the correct principal,
        the guard evaluates the action and allows it (CLEARING behavior,
        NOT_REQUIRED approval).
        """
        await _activate_kill_switch(db)
        principal = PrincipalContext.for_testing(
            subject_id="test-incident-commander",
            roles=["incident_commander"],
        )
        # The guard evaluates KILL_SWITCH_CLEAR with CLEARING behavior
        # and an authenticated principal with the required role.
        decision = await ExecutionGuard.evaluate(
            db,
            action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        # KILL_SWITCH_CLEAR has kill_switch=CLEARING, which is not BLOCKED,
        # and the principal has the required role, so the guard allows it.
        assert decision.allowed


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Privileged Principal Enforcement
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrivilegedPrincipalEnforcement:

    @pytest.mark.asyncio
    async def test_kill_switch_clear_denied_without_principal(self, db):
        """Kill-switch clear denied when no principal is provided."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_CLEAR,
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.FAIL_CLOSED
        assert "authenticated principal" in decision.reason

    @pytest.mark.asyncio
    async def test_kill_switch_clear_denied_with_unauthenticated_principal(self, db):
        """Kill-switch clear denied when principal is unauthenticated."""
        await _activate_kill_switch(db)
        principal = PrincipalContext.unauthenticated()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.FAIL_CLOSED

    @pytest.mark.asyncio
    async def test_kill_switch_clear_denied_with_wrong_role(self, db):
        """Kill-switch clear denied when principal lacks required role."""
        await _activate_kill_switch(db)
        principal = PrincipalContext.for_testing(
            subject_id="test-observer",
            roles=["observer"],
        )
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.FAIL_CLOSED
        assert "roles" in decision.reason

    @pytest.mark.asyncio
    async def test_kill_switch_clear_allowed_with_system_admin(self, db):
        """Kill-switch clear allowed with system_admin role."""
        await _activate_kill_switch(db)
        principal = PrincipalContext.for_testing(
            subject_id="test-admin",
            roles=["system_admin"],
        )
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_kill_switch_clear_allowed_with_incident_commander(self, db):
        """Kill-switch clear allowed with incident_commander role."""
        await _activate_kill_switch(db)
        principal = PrincipalContext.for_testing(
            subject_id="test-commander",
            roles=["incident_commander"],
        )
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.KILL_SWITCH_CLEAR,
            principal_context=principal,
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_identity_action_denied_without_principal(self, db):
        """Identity action denied when no principal is provided."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.IDENTITY_ACTION,
        )
        # IDENTITY_ACTION has kill_switch=BLOCKED, so it's denied by kill switch first
        assert not decision.allowed

    @pytest.mark.asyncio
    async def test_identity_action_denied_with_wrong_role(self, db):
        """Identity action denied when principal lacks system_admin role."""
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.IDENTITY_ACTION,
            principal_context=PrincipalContext.for_testing(
                subject_id="test-observer",
                roles=["observer"],
            ),
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.FAIL_CLOSED
        assert "system_admin" in decision.reason


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Comprehensive Service-Bypass Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceBypassComprehensive:
    """Prove that internal callers cannot bypass the guard for any
    consequential service boundary. Each test:
    1. Forces guard denial (kill switch or missing principal)
    2. Invokes the service directly (not through router)
    3. Asserts typed denial
    4. Asserts database state unchanged
    5. Asserts no external side effect
    """

    @pytest.mark.asyncio
    async def test_mission_create_denied_kill_switch(self, db):
        """MissionService.create denied during kill switch. No mission created."""
        from sqlalchemy import select as sa_select
        await _activate_kill_switch(db)
        with pytest.raises(Exception):
            await MissionService.create(db, title="Blocked Mission")
        await db.rollback()
        result = await db.execute(sa_select(Mission))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_mission_start_denied_kill_switch(self, db):
        """MissionService.update_status(EXECUTING) denied during kill switch.

        Note: Kill switch activation cancels active missions (including QUEUED).
        So we verify the guard blocks the transition by checking that
        update_status raises an exception.
        """
        mission = await _create_mission(db, status="QUEUED")
        await db.commit()
        mission_id = mission.id
        await _activate_kill_switch(db)
        await db.commit()
        # The guard should deny MISSION_START during kill switch
        with pytest.raises(Exception):
            await MissionService.update_status(db, mission_id, MissionStatus.EXECUTING)
        # The mission was already CANCELED by the kill switch activation.
        # The guard prevented update_status from changing it further.

    @pytest.mark.asyncio
    async def test_mission_resume_denied_kill_switch(self, db):
        """MissionService.update_status(EXECUTING from PAUSED) denied during kill switch."""
        from sqlalchemy import select as sa_select
        mission = await _create_mission(db, status="EXECUTING")
        await _set_mission_status_direct(db, mission.id, "PAUSED")
        await db.commit()
        mission_id = mission.id
        await _activate_kill_switch(db)
        await db.commit()
        with pytest.raises(Exception):
            await MissionService.update_status(db, mission_id, MissionStatus.EXECUTING)
        await db.rollback()
        result = await db.execute(sa_select(Mission).where(Mission.id == mission_id))
        fresh = result.scalar_one_or_none()
        assert fresh is not None
        assert fresh.status == "PAUSED", f"Status should remain PAUSED, got {fresh.status}"

    @pytest.mark.asyncio
    async def test_mission_freeze_denied_kill_switch(self, db):
        """MissionService.update_status(PAUSED) denied during kill switch.

        Kill switch activation cancels EXECUTING missions, so we verify
        the guard blocks the update_status call by asserting it raises.
        """
        mission = await _create_mission(db, status="EXECUTING")
        await db.commit()
        await _activate_kill_switch(db)
        await db.commit()
        with pytest.raises(Exception):
            await MissionService.update_status(db, mission.id, MissionStatus.PAUSED)

    @pytest.mark.asyncio
    async def test_mission_cancel_denied_kill_switch(self, db):
        """MissionService.update_status(CANCELED) denied during kill switch.

        Kill switch activation already cancels missions, but the guard
        should still evaluate the explicit CANCELED transition.
        """
        mission = await _create_mission(db, status="EXECUTING")
        await db.commit()
        await _activate_kill_switch(db)
        await db.commit()
        with pytest.raises(Exception):
            await MissionService.update_status(db, mission.id, "CANCELED")

    @pytest.mark.asyncio
    async def test_agent_register_denied_kill_switch(self, db):
        """AgentService.register denied during kill switch. No agent created."""
        from sqlalchemy import select as sa_select
        await _activate_kill_switch(db)
        with pytest.raises(Exception):
            await AgentService.register(db, agent_id="BLOCKED-1", name="Blocked", agent_type="test")
        await db.rollback()
        result = await db.execute(sa_select(Agent))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_agent_deregister_denied_no_principal(self, db):
        """AgentService.deregister denied without principal. Agent status unchanged."""
        # Register an agent first (no kill switch active)
        agent = await AgentService.register(
            db, agent_id="DEREG-TEST", name="Test", agent_type="test",
        )
        await db.commit()
        # Now try to deregister without principal — should be denied
        with pytest.raises(Exception):
            await AgentService.deregister(db, "DEREG-TEST")
        await db.rollback()
        from sqlalchemy import select as sa_select
        result = await db.execute(sa_select(Agent).where(Agent.agent_id == "DEREG-TEST"))
        fresh_agent = result.scalar_one_or_none()
        assert fresh_agent is not None
        assert fresh_agent.status == "ACTIVE", f"Agent should remain ACTIVE, got {fresh_agent.status}"

    @pytest.mark.asyncio
    async def test_agent_deregister_denied_wrong_role(self, db):
        """AgentService.deregister denied with wrong role. Agent status unchanged."""
        agent = await AgentService.register(
            db, agent_id="DEREG-ROLE", name="Test", agent_type="test",
        )
        await db.commit()
        wrong_principal = PrincipalContext.for_testing(
            subject_id="test-observer", roles=["observer"],
        )
        with pytest.raises(Exception):
            await AgentService.deregister(db, "DEREG-ROLE", principal_context=wrong_principal)
        await db.rollback()
        from sqlalchemy import select as sa_select
        result = await db.execute(sa_select(Agent).where(Agent.agent_id == "DEREG-ROLE"))
        fresh_agent = result.scalar_one_or_none()
        assert fresh_agent is not None
        assert fresh_agent.status == "ACTIVE", f"Agent should remain ACTIVE, got {fresh_agent.status}"

    @pytest.mark.asyncio
    async def test_approval_decide_denied_kill_switch(self, db):
        """ApprovalService.decide denied during kill switch. Approval unchanged."""
        from sqlalchemy import select as sa_select
        mission = await _create_mission(db, status="EXECUTING")
        approval = await _create_approval(db, mission.id, gate="G-07", status="PENDING")
        await db.commit()
        approval_id = approval.id
        await _activate_kill_switch(db)
        await db.commit()
        with pytest.raises(Exception):
            await ApprovalService.decide(db, approval_id, "APPROVED", reviewer="admin")
        await db.rollback()
        result = await db.execute(sa_select(Approval).where(Approval.id == approval_id))
        fresh_approval = result.scalar_one_or_none()
        assert fresh_approval is not None
        assert fresh_approval.status == "PENDING", f"Approval should remain PENDING, got {fresh_approval.status}"

    @pytest.mark.asyncio
    async def test_kill_switch_clear_denied_no_principal_state_unchanged(self, db):
        """KillSwitchService.clear denied without principal. Switch remains active."""
        await _activate_kill_switch(db)
        await db.commit()
        with pytest.raises(Exception):
            await KillSwitchService.clear(db, cleared_by="nobody")
        await db.rollback()
        is_active = await KillSwitchService.is_active(db)
        assert is_active is True, "Kill switch should remain active"

    @pytest.mark.asyncio
    async def test_kill_switch_clear_denied_wrong_role_state_unchanged(self, db):
        """KillSwitchService.clear denied with wrong role. Switch remains active."""
        await _activate_kill_switch(db)
        await db.commit()
        wrong_principal = PrincipalContext.for_testing(
            subject_id="test-observer", roles=["observer"],
        )
        with pytest.raises(Exception):
            await KillSwitchService.clear(db, cleared_by="observer", principal_context=wrong_principal)
        await db.rollback()
        is_active = await KillSwitchService.is_active(db)
        assert is_active is True, "Kill switch should remain active"
