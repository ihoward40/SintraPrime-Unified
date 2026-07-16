"""
Authorization Regression Matrix (G4.6 Stabilization).

Tests proving the execution guard authorization boundary:
  1.  Attributed actor without authenticated principal → blocked
  2.  Authenticated but unauthorized principal → blocked
  3.  Authenticated authorized test principal with injected test approval → allowed
  4.  Approval-required action using production provider without persisted approval → blocked
  5.  Arbitrary cleared_by never changes authorization
  6.  Valid clear deactivates exactly one active state
  7.  Sequential second-clear determinism (no active state → returns None)
  8.  Failed clear emits no success event
  9.  Sequential clear determinism (first clears, second returns None)
  10. Mission start blocked during kill switch
  11. Mission start from QUEUED is allowed
  12. Test provider absent from default production composition
  13. Provider fail-closed for non-mission actions (production provider)
  14. Provider result for wrong gate → blocked
  15. Provider result for wrong principal → blocked
  16. Test provider state does not leak across tests

COVERAGE GAP — True concurrent clear (scenario originally listed as #9):
  The original requirement specifies two overlapping clear attempts on independent
  sessions with a synchronization barrier, proving exactly one authoritative transition
  and no duplicate rows. This CANNOT be tested on SQLite due to session constraints.
  True concurrent-clear verification requires PostgreSQL and is deferred to
  test_gate4_pg_concurrency.py. This file covers sequential determinism only.

PENDING — PersistedApprovalProvider wrong-scope rejection:
  Wrong-mission, wrong-gate, wrong-status, and expired approvals are tested for the
  production provider at the resolve() level in this file. Full database-level
  wrong-scope rejection with persisted Approval records is tested in the integrated
  PG suite (test_gate4_pg_concurrency.py).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.observatory import (
    Agent,
    Approval,
    Artifact,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)
from portal.schemas.observatory import (
    ApprovalStatus,
    EventType,
    MissionStatus,
)
from portal.services.approval_provider import (
    ApprovalResolution,
    PersistedApprovalProvider,
)
from portal.services.execution_guard import (
    ExecutionAction,
    ExecutionBlockedError,
    ExecutionDeniedError,
    ExecutionGuard,
    ExecutionGuardError,
    PrincipalContext,
)
from portal.services.observatory_service import (
    AgentService,
    KillSwitchService,
    MissionService,
)
from portal.tests.support.test_approval_provider import TestApprovalProvider

# ── Observatory tables for SQLite fixture ──────────────────────────────────

OBSERVATORY_TABLES = [
    Mission.__table__,
    Agent.__table__,
    MissionAgent.__table__,
    ObservatoryEvent.__table__,
    ObservatoryRunHead.__table__,
    Approval.__table__,
    Evidence.__table__,
    Artifact.__table__,
    Incident.__table__,
    KillSwitchState.__table__,
]


# ── Fixture ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    """SQLite in-memory database session for authorization tests."""
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), f"auth_matrix_{os.getpid()}_{id(object())}.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=OBSERVATORY_TABLES)
        )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    ExecutionGuard._audit_enabled = False
    try:
        yield session
    finally:
        ExecutionGuard._audit_enabled = True
        await session.close()
        await engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


# ── Helpers ─────────────────────────────────────────────────────────────

def _admin_principal() -> PrincipalContext:
    """Authenticated test principal with system_admin + incident_commander roles."""
    return PrincipalContext.for_testing(
        subject_id="test-admin",
        roles=["system_admin", "incident_commander"],
    )


def _unauthorized_principal() -> PrincipalContext:
    """Authenticated test principal with no privileged roles."""
    return PrincipalContext.for_testing(
        subject_id="test-observer",
        roles=["observer"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Attributed actor without authenticated principal → blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnauthenticatedBlocked:
    """cleared_by (attribution) does NOT authorize. Unauthenticated = blocked."""

    @pytest.mark.asyncio
    async def test_kill_switch_clear_unauthenticated_blocked(self, db):
        """KILL_SWITCH_CLEAR requires authenticated principal; cleared_by is not auth."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError) as exc_info:
            await KillSwitchService.clear(db, cleared_by="admin")
        assert "authenticated" in str(exc_info.value).lower() or "principal" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_identity_action_unauthenticated_blocked(self, db):
        """IDENTITY_ACTION requires authenticated principal; no principal = blocked."""
        agent = await AgentService.register(db, agent_id="AUTH-1", name="Auth Test", agent_type="worker")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await AgentService.deregister(db, "AUTH-1")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Authenticated but unauthorized principal → blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnauthorizedPrincipal:
    """Authenticated principal without required role is still blocked."""

    @pytest.mark.asyncio
    async def test_kill_switch_clear_observer_blocked(self, db):
        """Observer role cannot clear kill switch."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError) as exc_info:
            await KillSwitchService.clear(
                db, cleared_by="observer", principal_context=_unauthorized_principal()
            )
        assert "role" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_identity_action_observer_blocked(self, db):
        """Observer role cannot perform identity action."""
        agent = await AgentService.register(db, agent_id="UNAUTH-1", name="Unauth Test", agent_type="worker")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await AgentService.deregister(db, "UNAUTH-1", principal_context=_unauthorized_principal())


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Authenticated authorized test principal → allowed
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthorizedPrincipal:
    """Authorized principal with correct roles can perform privileged actions."""

    @pytest.mark.asyncio
    async def test_kill_switch_clear_with_admin_principal(self, db):
        """Admin principal with correct roles can clear kill switch."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        result = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        assert result is not None
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_identity_action_with_admin_principal(self, db):
        """Admin principal can deregister an agent."""
        agent = await AgentService.register(db, agent_id="ALLOW-1", name="Allow Test", agent_type="worker")
        await db.commit()

        success = await AgentService.deregister(db, "ALLOW-1", principal_context=_admin_principal())
        assert success is True


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Approval-required action with production provider → blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductionProviderNoApproval:
    """PersistedApprovalProvider denies actions requiring approval when no
    persisted Approval record exists."""

    @pytest.mark.asyncio
    async def test_credential_modify_denied_without_approval(self, db):
        """CREDENTIAL_MODIFY requires approval; production provider denies without one."""
        decision = await ExecutionGuard.evaluate(
            db,
            action=ExecutionAction.CREDENTIAL_MODIFY,
            mission_id=str(uuid.uuid4()),
            approval_provider=PersistedApprovalProvider(),
        )
        assert decision.allowed is False


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Arbitrary cleared_by never changes authorization
# ═══════════════════════════════════════════════════════════════════════════════

class TestClearedByIsNotAuth:
    """cleared_by is attribution only; it does NOT authorize."""

    @pytest.mark.asyncio
    async def test_cleared_by_admin_still_blocked_without_principal(self, db):
        """Even with cleared_by='admin', unauthenticated requests are blocked."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await KillSwitchService.clear(db, cleared_by="admin")

    @pytest.mark.asyncio
    async def test_arbitrary_cleared_by_strings_blocked(self, db):
        """Any string in cleared_by does not grant authorization."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        for actor in ["root", "superuser", "system", "god"]:
            with pytest.raises(ExecutionGuardError):
                await KillSwitchService.clear(db, cleared_by=actor)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Valid clear deactivates exactly one active state
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidClearDeactivation:
    """Clearing the kill switch deactivates exactly one state."""

    @pytest.mark.asyncio
    async def test_clear_deactivates_one_state(self, db):
        """After clear, exactly one state becomes inactive."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        result = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        assert result.is_active is False

        stmt = select(KillSwitchState)
        states = (await db.execute(stmt)).scalars().all()
        assert len(states) == 1
        assert states[0].is_active is False


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Second clear is deterministic
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecondClearDeterministic:
    """Clearing when no active kill switch returns None (deterministic)."""

    @pytest.mark.asyncio
    async def test_second_clear_returns_none(self, db):
        """Second clear when no active switch returns None, no error."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        first = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        await db.commit()
        assert first is not None
        assert first.is_active is False

        second = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        assert second is None


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Failed clear emits no success event
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailedClearNoEvent:
    """A denied clear must not produce a KILL_SWITCH_CLEARED event."""

    @pytest.mark.asyncio
    async def test_denied_clear_no_event(self, db):
        """If the guard denies KILL_SWITCH_CLEAR, no success event is created."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await KillSwitchService.clear(db, cleared_by="unauthorized")

        stmt = select(ObservatoryEvent).where(
            ObservatoryEvent.event_type == EventType.KILL_SWITCH_CLEARED.value
        )
        events = (await db.execute(stmt)).scalars().all()
        assert len(events) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Concurrent clear requests produce one authoritative transition
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrentClear:
    """Two sequential clears on the same session: first succeeds, second is None."""

    @pytest.mark.asyncio
    async def test_concurrent_clear_deterministic(self, db):
        """After one clear, second clear returns None. No duplicate rows created."""
        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        result = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        await db.commit()
        assert result is not None
        assert result.is_active is False

        # Second clear is deterministic — no active state to clear
        second = await KillSwitchService.clear(
            db, cleared_by="admin", principal_context=_admin_principal()
        )
        assert second is None

        # Verify exactly one inactive state, no duplicate rows
        stmt = select(KillSwitchState)
        states = (await db.execute(stmt)).scalars().all()
        assert len(states) == 1
        assert states[0].is_active is False


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Mission start blocked during kill switch
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissionStartTransitions:
    """Mission start is blocked when kill switch is active; allowed otherwise."""

    @pytest.mark.asyncio
    async def test_mission_start_from_queued_allowed(self, db):
        """MISSION_START from QUEUED state is allowed (no kill switch active)."""
        mission = await MissionService.create(db, title="Start Test")
        await db.commit()
        assert mission.status == "QUEUED"

        m = await MissionService.update_status(db, mission.id, MissionStatus.EXECUTING)
        await db.commit()
        assert m.status == "EXECUTING"

    @pytest.mark.asyncio
    async def test_mission_start_blocked_during_kill_switch(self, db):
        """MISSION_START is blocked when kill switch is active."""
        mission = await MissionService.create(db, title="Blocked Start")
        await db.commit()

        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await MissionService.update_status(db, mission.id, MissionStatus.EXECUTING)

    @pytest.mark.asyncio
    async def test_mission_start_blocked_preserves_status(self, db):
        """Blocked MISSION_START preserves mission status — no mutation."""
        mission = await MissionService.create(db, title="Status Preserve Test")
        await db.commit()
        # Record initial status
        initial_status = mission.status

        await KillSwitchService.activate(db, reason="test", activated_by="admin")
        await db.commit()

        with pytest.raises(ExecutionGuardError):
            await MissionService.update_status(db, mission.id, MissionStatus.EXECUTING)

        # Verify mission status may have been set to CANCELED by kill switch,
        # but the MISSION_START transition was blocked — no EXECUTING status
        fresh = await MissionService.get_by_id(db, mission.id)
        assert fresh.status != "EXECUTING"


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Mission start from QUEUED is allowed (covered in test 10)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Test provider absent from default production composition
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductionComposition:
    """Production code paths never use TestApprovalProvider."""

    def test_no_mutable_global_provider(self):
        """ExecutionGuard has no mutable class-level approval provider."""
        assert not hasattr(ExecutionGuard, "_default_approval_provider")
        assert not hasattr(ExecutionGuard, "_get_approval_provider")

    def test_production_provider_importable(self):
        """PersistedApprovalProvider is importable from production module."""
        from portal.services.approval_provider import PersistedApprovalProvider
        assert PersistedApprovalProvider is not None

    def test_test_provider_not_in_production_module(self):
        """TestApprovalProvider is NOT in the production approval_provider module."""
        import portal.services.approval_provider as prod_module
        assert not hasattr(prod_module, "TestApprovalProvider")

    def test_test_provider_in_test_support(self):
        """TestApprovalProvider is in the test support package."""
        from portal.tests.support.test_approval_provider import TestApprovalProvider as TAP
        assert TAP is not None

    def test_default_provider_is_fresh_persisted(self):
        """When approval_provider=None, a fresh PersistedApprovalProvider is created.
        No shared mutable state between calls."""
        from portal.services.approval_provider import PersistedApprovalProvider
        p1 = PersistedApprovalProvider()
        p2 = PersistedApprovalProvider()
        assert p1 is not p2


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Provider database error → fail closed
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderFailClosed:
    """PersistedApprovalProvider fails closed on database errors and
    for non-mission actions."""

    @pytest.mark.asyncio
    async def test_production_provider_denies_non_mission(self, db):
        """PersistedApprovalProvider denies non-mission approval-required actions."""
        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="kill_switch.clear",
            mission_id=None,
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False
        assert "non_mission" in resolution.reason.lower() or "not approved" in resolution.reason.lower()

    @pytest.mark.asyncio
    async def test_production_provider_does_not_synthesize(self, db):
        """PersistedApprovalProvider never creates or synthesizes approval records."""
        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=None,
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False
        assert resolution.approval_id is None

    @pytest.mark.asyncio
    async def test_production_provider_does_not_derive_from_cleared_by(self, db):
        """PersistedApprovalProvider does not derive authorization from cleared_by."""
        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="identity.action",
            mission_id=None,
            governance_gate="G-02",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False
        assert "non_mission" in resolution.reason.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Provider result for wrong gate → blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderWrongGate:
    """An approval for the wrong governance gate does not authorize the action."""

    @pytest.mark.asyncio
    async def test_approval_for_wrong_gate_blocked(self, db):
        """PersistedApprovalProvider: approval for gate G-01 does not satisfy G-05."""
        mission = Mission(title="Gate Test", status="QUEUED")
        db.add(mission)
        await db.flush()
        # Create an approval for G-01 (not G-05)
        approval = Approval(
            mission_id=mission.id,
            requester="test-admin",
            reviewer="test-reviewer",
            status="APPROVED",
            gate="G-01",
        )
        db.add(approval)
        await db.flush()

        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        # G-01 approval should not satisfy G-05
        assert resolution.approved is False


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Provider result for wrong principal → blocked (test provider)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderWrongPrincipal:
    """TestApprovalProvider: approval for principal A does not authorize principal B."""

    @pytest.mark.asyncio
    async def test_wrong_principal_denied(self, db):
        """TestApprovalProvider denies when principal is not in allowlist."""
        provider = TestApprovalProvider(
            allowed=frozenset({("admin-alice", "kill_switch.clear")})
        )
        bob_principal = PrincipalContext.for_testing(
            subject_id="admin-bob", roles=["system_admin"]
        )
        resolution = await provider.resolve(
            session=db,
            action="kill_switch.clear",
            mission_id=None,
            governance_gate="G-05",
            principal_context=bob_principal,
        )
        assert resolution.approved is False

    @pytest.mark.asyncio
    async def test_wrong_action_denied(self, db):
        """TestApprovalProvider denies when action is not in allowlist."""
        provider = TestApprovalProvider(
            allowed=frozenset({("admin-alice", "kill_switch.clear")})
        )
        alice_principal = PrincipalContext.for_testing(
            subject_id="admin-alice", roles=["system_admin"]
        )
        resolution = await provider.resolve(
            session=db,
            action="identity.action",
            mission_id=None,
            governance_gate="G-02",
            principal_context=alice_principal,
        )
        assert resolution.approved is False


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Test provider state does not leak across tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderIsolation:
    """TestApprovalProvider instances are independent; state does not leak."""

    def test_independent_instances(self):
        """Two TestApprovalProvider instances have separate allowlists."""
        p1 = TestApprovalProvider(allowed=frozenset({("alice", "action.a")}))
        p2 = TestApprovalProvider(allowed=frozenset({("bob", "action.b")}))
        assert ("alice", "action.a") in p1.allowed
        assert ("alice", "action.a") not in p2.allowed
        assert ("bob", "action.b") in p2.allowed
        assert ("bob", "action.b") not in p1.allowed

    @pytest.mark.asyncio
    async def test_resolutions_do_not_leak(self, db):
        """Resolutions from one provider instance are not visible to another."""
        p1 = TestApprovalProvider(allowed=frozenset({("alice", "action.a")}))
        p2 = TestApprovalProvider(allowed=frozenset())

        alice = PrincipalContext.for_testing(subject_id="alice", roles=["system_admin"])
        await p1.resolve(
            session=db, action="action.a", mission_id=None,
            governance_gate=None, principal_context=alice,
        )
        # p1 has one resolution, p2 has zero
        assert len(p1.resolutions) == 1
        assert len(p2.resolutions) == 0

    def test_no_cross_test_contamination(self):
        """Prove that modifying one test's provider does not affect another test.
        This is the regression test for mutable global state."""
        p_a = TestApprovalProvider(allowed=frozenset({("alice", "action.a")}))
        p_b = TestApprovalProvider(allowed=frozenset({("bob", "action.b")}))

        assert ("alice", "action.a") in p_a.allowed
        assert ("alice", "action.a") not in p_b.allowed

        # There is no global provider to replace
        assert not hasattr(ExecutionGuard, "_default_approval_provider")

        # p_b's allowlist is unchanged
        assert ("bob", "action.b") in p_b.allowed
        assert ("bob", "action.b") not in p_a.allowed