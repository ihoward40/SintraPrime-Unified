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
    """Helper to create a mission."""
    mission = await MissionService.create(
        db,
        title=title,
        objective="Test objective",
        governance_gates_required=["G-01"],
    )
    await db.commit()
    if status != "QUEUED":
        await MissionService.update_status(db, mission.id, status)
        await db.commit()
    return mission


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
        """Kill-switch activation itself is always allowed, even if already active."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.KILL_SWITCH_ACTIVATE)
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_kill_switch_clearing_evaluated_separately(self, db):
        """Kill-switch clearing is evaluated separately (requires approval)."""
        await _activate_kill_switch(db)
        decision = await ExecutionGuard.evaluate(db, action=ExecutionAction.KILL_SWITCH_CLEAR)
        # Clearing requires approval — denied without one
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED

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
        await MissionService.update_status(db, mission.id, "PAUSED")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_paused_mission_allows_resume(self, db):
        """A paused mission allows resume."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "PAUSED")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_RESUME, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_paused_mission_allows_cancel(self, db):
        """A paused mission allows cancel."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "PAUSED")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_CANCEL, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_frozen_mission_blocks_resume(self, db):
        """A frozen mission blocks resume (no explicit unfreeze action defined)."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "FROZEN")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.MISSION_RESUME, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_frozen_mission_allows_evidence_read(self, db):
        """A frozen mission allows evidence reads."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "FROZEN")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.EVIDENCE_READ, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_canceled_mission_blocks_execution(self, db):
        """A canceled mission blocks all execution."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "CANCELED")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.TOOL_INVOKE, mission_id=str(mission.id)
        )
        assert not decision.allowed
        assert decision.reason_code == DecisionReasonCode.MISSION_STATE_BLOCKED

    @pytest.mark.asyncio
    async def test_completed_mission_blocks_mutation(self, db):
        """A completed mission blocks further mutation."""
        mission = await _create_mission(db, status="EXECUTING")
        await MissionService.update_status(db, mission.id, "COMPLETED")
        await db.commit()
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
        await MissionService.update_status(db, mission.id, "COMPLETED")
        await db.commit()
        decision = await ExecutionGuard.evaluate(
            db, action=ExecutionAction.EXPORT_EVIDENCE, mission_id=str(mission.id)
        )
        assert decision.allowed

    @pytest.mark.asyncio
    async def test_active_mission_allows_permitted_execution(self, db):
        """An executing mission allows permitted actions like tool_invoke."""
        mission = await _create_mission(db, status="EXECUTING")
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
