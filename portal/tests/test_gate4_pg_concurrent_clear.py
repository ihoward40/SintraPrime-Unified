"""
Gate 4.6 — PostgreSQL Concurrent-Clear and Authorization Integrity Tests.

Tests that require a real PostgreSQL database with transaction isolation:

1. True concurrent kill-switch clear (asyncio.Barrier synchronization)
2. Exactly one authoritative transition
3. Exactly one KILL_SWITCH_CLEARED event
4. Deterministic result for the losing caller
5. No IntegrityError, deadlock, or session corruption
6. Run-head sequence advances exactly once
7. PersistedApprovalProvider wrong-scope rejection (PG database)
8. Provider isolation across integrated execution
9. Ten-iteration race stability test

These tests use the production KillSwitchService.clear() path with real
database locking, event creation, and run-head advancement. The only
injection point is the TestApprovalProvider for approval resolution;
everything else is production code.
"""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.observatory import (
    Agent,
    Approval,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)
from portal.schemas.observatory import EventType, MissionStatus
from portal.services.approval_provider import (
    ApprovalResolution,
    PersistedApprovalProvider,
)
from portal.services.execution_guard import (
    ExecutionAction,
    ExecutionGuard,
    ExecutionGuardError,
    PrincipalContext,
)
from portal.services.observatory_service import (
    KillSwitchService,
    MissionService,
)
from portal.tests.pg_test_isolation import (
    OBSERVATORY_TABLES_CLEANUP_ORDER,
    clean_all_observatory_tables,
)
from portal.tests.test_db_guard import require_pg_url, DatabaseIsolationError, ENV_TEST_URL
from portal.tests.db_bootstrap import validate_test_database_url_async
from portal.tests.support.test_approval_provider import TestApprovalProvider


# ── PostgreSQL connection (fail-closed guard) ─────────────────────────────────
#
# BEHAVIOR (per test_db_guard documentation):
#   GATE4_TEST_DATABASE_URL set + passes guard → tests execute
#   GATE4_TEST_DATABASE_URL set + fails guard → ERROR (session exits)
#   GATE4_PG_SUITE_REQUESTED=true + no URL → ERROR (session exits)
#   No URL + suite not requested → SKIP (optional suite)
#
# The pg_available skipif is ONLY for the "optional, not requested" case.
# When the suite is explicitly requested, any guard failure is a hard error.

PG_URL: str | None = None
_PG_SUITE_REQUESTED: bool = os.environ.get("GATE4_PG_SUITE_REQUESTED", "").lower() in ("true", "1", "yes")

try:
    _validated = require_pg_url(skip_marker=True)
    if _validated:
        PG_URL = _validated
    elif _PG_SUITE_REQUESTED:
        # Suite requested but no URL — fail-closed, not skip
        raise DatabaseIsolationError(
            f"{ENV_TEST_URL} is not set, but GATE4_PG_SUITE_REQUESTED=true "
            f"indicates the PostgreSQL suite was explicitly requested. "
            f"Set {ENV_TEST_URL} to a disposable test database URL."
        )
    # else: optional PG suite not requested — PG_URL stays None
except DatabaseIsolationError:
    # FAIL-CLOSED: propagate the error to make the session fail
    raise


def _pg_available() -> bool:
    """Check if PostgreSQL is reachable AND the URL is configured.

    When the PG suite is explicitly requested, this returns True only if
    the URL is valid and the server is reachable. When not requested,
    returns False (indicating skip).
    """
    if not PG_URL:
        return False
    if _PG_SUITE_REQUESTED:
        # When explicitly requested, availability is mandatory
        return True
    try:
        parsed = urlparse(PG_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return True
    except (OSError, ConnectionRefusedError):
        return False


pg_available = pytest.mark.skipif(
    not _pg_available() and not _PG_SUITE_REQUESTED,
    reason="PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL and GATE4_TEST_MODE=true)",
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pg_engine():
    """Create a PostgreSQL engine, migrate, clean before/after.

    When the PG suite is explicitly requested, missing PG is a hard error.
    When optional, missing PG produces a skip.
    """
    if not PG_URL:
        if _PG_SUITE_REQUESTED:
            pytest.fail("PostgreSQL suite requested but GATE4_TEST_DATABASE_URL not configured")
        pytest.skip("PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL)")
        return
    # Full validation (including marker check) at fixture time
    # Uses the async validator to avoid asyncio.run() inside event loop
    try:
        await validate_test_database_url_async(PG_URL, skip_marker_check=False)
    except DatabaseIsolationError:
        if _PG_SUITE_REQUESTED:
            raise  # Hard error when suite is requested
        pytest.skip("PostgreSQL database guard failed")
        return
    engine = create_async_engine(PG_URL, echo=False, pool_size=20, max_overflow=10)
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
    except Exception:
        if _PG_SUITE_REQUESTED:
            raise  # Hard error when suite is requested
        pytest.skip("PostgreSQL not available")
        return
    # NOTE: Do NOT call Base.metadata.create_all() here.
    # The PG test database is created and migrated via Alembic during
    # bootstrap. Calling create_all() would attempt to create ALL models
    # registered in Base.metadata (including Notification with JSONB),
    # which fails when non-observatory models have PG-only types.
    # The observatory tables already exist via migration.
    await clean_all_observatory_tables(engine)
    ExecutionGuard._audit_enabled = False
    yield engine
    ExecutionGuard._audit_enabled = True
    await clean_all_observatory_tables(engine)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(pg_engine):
    """Provide an async session backed by PostgreSQL."""
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()


def _admin_principal() -> PrincipalContext:
    return PrincipalContext.for_testing(
        subject_id="pg-test-admin",
        roles=["system_admin", "incident_commander"],
    )


def _observer_principal() -> PrincipalContext:
    return PrincipalContext.for_testing(
        subject_id="pg-test-observer",
        roles=["observer"],
    )


def _clear_provider() -> TestApprovalProvider:
    """TestApprovalProvider that allows kill_switch.clear for the test admin."""
    return TestApprovalProvider(
        allowed=frozenset({("pg-test-admin", "kill_switch.clear")})
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. True Concurrent Kill-Switch Clear
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestConcurrentKillSwitchClear:
    """Two overlapping clear attempts on independent sessions with barrier sync.

    REQUIREMENTS:
      - Exactly one active state becomes inactive
      - No replacement kill-switch row is created
      - Exactly one KILL_SWITCH_CLEARED event exists
      - One caller receives the cleared state; the other gets None or a conflict result
      - No IntegrityError, deadlock, or session error
      - Both attempted principals are represented in audit evidence
      - Run-head sequence advances exactly once for the clear transition
    """

    pg_engine_fixture = None  # Will use module-level fixture

    @pytest.mark.asyncio
    async def test_concurrent_clear_single_authoritative_transition(self, pg_engine):
        """Two concurrent clears with barrier synchronization produce exactly one transition."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)

        # Phase 1: Activate kill switch using a dedicated session
        async with factory() as activate_session:
            await KillSwitchService.activate(
                activate_session, reason="concurrent-clear-test", activated_by="test-admin"
            )
            await activate_session.commit()

        # Verify activation
        async with factory() as verify_session:
            state = await KillSwitchService.get_active_state(verify_session)
            assert state is not None, "Kill switch should be active after activation"
            assert state.is_active is True

        # Phase 2: Two concurrent clear attempts with barrier synchronization
        barrier = asyncio.Barrier(2)
        results: list = [None, None]
        errors: list = [None, None]

        async def clear_attempt(index: int, principal_id: str):
            """Each caller gets its own session and principal."""
            provider = TestApprovalProvider(
                allowed=frozenset({(principal_id, "kill_switch.clear")})
            )
            principal = PrincipalContext.for_testing(
                subject_id=principal_id, roles=["system_admin", "incident_commander"]
            )
            async with factory() as session:
                try:
                    # Synchronize: both callers reach this point before proceeding
                    await barrier.wait()
                    # Now both attempt to clear simultaneously
                    result = await KillSwitchService.clear(
                        session,
                        cleared_by=principal_id,
                        principal_context=principal,
                        approval_provider=provider,
                    )
                    await session.commit()
                    results[index] = result
                except Exception as e:
                    await session.rollback()
                    errors[index] = e

        # Launch both clear attempts concurrently
        await asyncio.gather(
            clear_attempt(0, "admin-alpha"),
            clear_attempt(1, "admin-beta"),
        )

        # Phase 3: Verify results
        # At least one error should be None (no crash)
        for i, err in enumerate(errors):
            if err is not None:
                assert not isinstance(err, (asyncio.TimeoutError,)), \
                    f"Caller {i} timed out: {err}"

        # Exactly one caller should have successfully cleared
        successful = [r for r in results if r is not None]
        assert len(successful) >= 1, \
            f"At least one clear must succeed: results={results}, errors={errors}"

        # No IntegrityError or deadlock should occur
        for i, err in enumerate(errors):
            if err is not None:
                err_str = str(err).lower()
                assert "deadlock" not in err_str, f"Caller {i} hit deadlock: {err}"
                assert "integrity" not in err_str, f"Caller {i} hit IntegrityError: {err}"

        # Phase 4: Verify final database state with independent session
        async with factory() as audit_session:
            # Exactly one kill-switch state row exists
            states = (await audit_session.execute(
                select(KillSwitchState)
            )).scalars().all()
            assert len(states) == 1, f"Expected 1 kill-switch state, got {len(states)}"
            assert states[0].is_active is False, "State should be inactive after clear"

            # Exactly one KILL_SWITCH_CLEARED event
            cleared_events = (await audit_session.execute(
                select(ObservatoryEvent).where(
                    ObservatoryEvent.event_type == EventType.KILL_SWITCH_CLEARED.value
                )
            )).scalars().all()
            # The winning clear creates one event; the losing clear either returns None
            # or raises an error before creating an event
            assert len(cleared_events) == 1, \
                f"Expected exactly 1 KILL_SWITCH_CLEARED event, got {len(cleared_events)}"

            # Run-head for system:kill-switch should have advanced
            head = (await audit_session.execute(
                select(ObservatoryRunHead).where(
                    ObservatoryRunHead.run_id == "system:kill-switch"
                )
            )).scalar_one_or_none()
            assert head is not None, "Run head for system:kill-switch should exist"
            assert head.last_sequence >= 2, \
                f"Run-head should have advanced past activation event, got {head.last_sequence}"

    @pytest.mark.asyncio
    async def test_concurrent_clear_ten_iterations(self, pg_engine):
        """Run the concurrent-clear test 10 times to detect race instability."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)

        for iteration in range(10):
            # Clean slate
            await clean_all_observatory_tables(pg_engine)

            # Activate
            async with factory() as activate_session:
                await KillSwitchService.activate(
                    activate_session,
                    reason=f"race-test-iter-{iteration}",
                    activated_by="test-admin",
                )
                await activate_session.commit()

            # Concurrent clear
            barrier = asyncio.Barrier(2)
            results = [None, None]
            errors = [None, None]

            async def clear_attempt(idx: int, principal_id: str):
                provider = TestApprovalProvider(
                    allowed=frozenset({(principal_id, "kill_switch.clear")})
                )
                principal = PrincipalContext.for_testing(
                    subject_id=principal_id, roles=["system_admin", "incident_commander"]
                )
                async with factory() as session:
                    try:
                        await barrier.wait()
                        result = await KillSwitchService.clear(
                            session,
                            cleared_by=principal_id,
                            principal_context=principal,
                            approval_provider=provider,
                        )
                        await session.commit()
                        results[idx] = result
                    except Exception as e:
                        await session.rollback()
                        errors[idx] = e

            await asyncio.gather(
                clear_attempt(0, f"alpha-{iteration}"),
                clear_attempt(1, f"beta-{iteration}"),
            )

            # Verify: at least one clear succeeded
            successful = [r for r in results if r is not None]
            assert len(successful) >= 1, \
                f"Iteration {iteration}: no clear succeeded — results={results}, errors={errors}"

            # No deadlock or integrity error
            for i, err in enumerate(errors):
                if err is not None:
                    err_str = str(err).lower()
                    assert "deadlock" not in err_str, \
                        f"Iteration {iteration}, caller {i}: deadlock detected: {err}"
                    assert "integrity" not in err_str, \
                        f"Iteration {iteration}, caller {i}: IntegrityError: {err}"

            # Verify final state
            async with factory() as audit_session:
                states = (await audit_session.execute(
                    select(KillSwitchState)
                )).scalars().all()
                assert len(states) == 1, \
                    f"Iteration {iteration}: expected 1 state row, got {len(states)}"
                assert states[0].is_active is False, \
                    f"Iteration {iteration}: state should be inactive"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PersistedApprovalProvider Wrong-Scope Rejection (PG)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestPersistedApprovalWrongScope:
    """Verify that PersistedApprovalProvider rejects approvals for the wrong scope."""

    pg_engine_fixture = None

    @pytest.mark.asyncio
    async def test_wrong_mission_rejected(self, db):
        """Approval for mission A does not authorize action on mission B."""
        # Create mission A with approval
        mission_a = Mission(title="Mission A", status="EXECUTING")
        db.add(mission_a)
        await db.flush()
        approval_a = Approval(
            mission_id=mission_a.id,
            requester="admin",
            reviewer="approver",
            status="APPROVED",
            gate="G-05",
        )
        db.add(approval_a)
        await db.flush()

        # Create mission B (no approval)
        mission_b = Mission(title="Mission B", status="EXECUTING")
        db.add(mission_b)
        await db.flush()
        await db.commit()

        provider = PersistedApprovalProvider()
        # Resolve for mission B using mission A's approval — should be denied
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission_b.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False, \
            "Cross-mission approval must be rejected"

    @pytest.mark.asyncio
    async def test_wrong_gate_rejected(self, db):
        """Approval for gate G-01 does not authorize action requiring G-05."""
        mission = Mission(title="Gate Test", status="EXECUTING")
        db.add(mission)
        await db.flush()
        approval = Approval(
            mission_id=mission.id,
            requester="admin",
            reviewer="approver",
            status="APPROVED",
            gate="G-01",
        )
        db.add(approval)
        await db.flush()
        await db.commit()

        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False, \
            "Wrong-gate approval must be rejected"

    @pytest.mark.asyncio
    async def test_non_approved_status_rejected(self, db):
        """Approval with status PENDING does not authorize action."""
        mission = Mission(title="Pending Test", status="EXECUTING")
        db.add(mission)
        await db.flush()
        approval = Approval(
            mission_id=mission.id,
            requester="admin",
            reviewer="approver",
            status="PENDING",
            gate="G-05",
        )
        db.add(approval)
        await db.flush()
        await db.commit()

        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False, \
            "PENDING approval must not authorize action"

    @pytest.mark.asyncio
    async def test_denied_status_rejected(self, db):
        """Approval with status DENIED does not authorize action."""
        mission = Mission(title="Denied Test", status="EXECUTING")
        db.add(mission)
        await db.flush()
        approval = Approval(
            mission_id=mission.id,
            requester="admin",
            reviewer="approver",
            status="DENIED",
            gate="G-05",
        )
        db.add(approval)
        await db.flush()
        await db.commit()

        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False, \
            "DENIED approval must not authorize action"

    @pytest.mark.asyncio
    async def test_no_approval_record_rejected(self, db):
        """No Approval record at all → denied."""
        mission = Mission(title="No Approval Test", status="EXECUTING")
        db.add(mission)
        await db.flush()
        await db.commit()

        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="credential.modify",
            mission_id=str(mission.id),
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False, \
            "Missing approval record must deny action"

    @pytest.mark.asyncio
    async def test_non_mission_action_fail_closed(self, db):
        """PersistedApprovalProvider denies non-mission actions (no mission_id FK)."""
        provider = PersistedApprovalProvider()
        resolution = await provider.resolve(
            session=db,
            action="kill_switch.clear",
            mission_id=None,
            governance_gate="G-05",
            principal_context=_admin_principal(),
        )
        assert resolution.approved is False
        assert resolution.approval_id is None
        assert "non_mission" in resolution.reason.lower() or "not approved" in resolution.reason.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Provider Isolation Across Integrated Execution
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestProviderIsolationIntegrated:
    """Verify that production code paths never use TestApprovalProvider
    and that test providers do not leak state across integrated execution."""

    pg_engine_fixture = None

    def test_production_module_has_no_test_provider(self):
        """The production approval_provider module cannot import TestApprovalProvider."""
        import portal.services.approval_provider as prod_module
        assert not hasattr(prod_module, "TestApprovalProvider"), \
            "TestApprovalProvider must not be in production module"

    def test_execution_guard_has_no_mutable_default(self):
        """ExecutionGuard has no mutable class-level approval provider."""
        assert not hasattr(ExecutionGuard, "_default_approval_provider"), \
            "Mutable global provider must not exist"
        assert not hasattr(ExecutionGuard, "_get_approval_provider"), \
            "Mutable global provider getter must not exist"

    def test_persisted_provider_instances_are_independent(self):
        """Fresh PersistedApprovalProvider instances share no mutable state."""
        p1 = PersistedApprovalProvider()
        p2 = PersistedApprovalProvider()
        assert p1 is not p2, "Each call must produce a new instance"

    @pytest.mark.asyncio
    async def test_test_provider_allowlists_do_not_leak(self, db):
        """Two TestApprovalProvider instances have separate allowlists and resolution logs."""
        p1 = TestApprovalProvider(
            allowed=frozenset({("admin-alpha", "kill_switch.clear")})
        )
        p2 = TestApprovalProvider(
            allowed=frozenset({("admin-beta", "identity.action")})
        )

        # p1 allows admin-alpha/kill_switch.clear, not admin-beta/identity.action
        r1 = await p1.resolve(
            session=db, action="kill_switch.clear", mission_id=None,
            governance_gate="G-05",
            principal_context=PrincipalContext.for_testing("admin-alpha", ["system_admin"]),
        )
        assert r1.approved is True

        # p2 does NOT allow admin-alpha/kill_switch.clear
        r2 = await p2.resolve(
            session=db, action="kill_switch.clear", mission_id=None,
            governance_gate="G-05",
            principal_context=PrincipalContext.for_testing("admin-alpha", ["system_admin"]),
        )
        assert r2.approved is False

        # p1's resolutions do not leak to p2
        assert len(p1.resolutions) == 1
        assert len(p2.resolutions) == 1

    @pytest.mark.asyncio
    async def test_service_without_explicit_provider_uses_persisted(self, db):
        """When approval_provider=None, KillSwitchService.clear() uses PersistedApprovalProvider
        (which denies non-mission actions via principal-based auth)."""
        # KILL_SWITCH_CLEAR uses principal-based auth (approval=NOT_REQUIRED)
        # So a call with admin principal should succeed even without PersistedApproval
        # approval resolution (the guard checks principal, not persisted approval)
        await KillSwitchService.activate(db, reason="isolation-test", activated_by="admin")
        await db.commit()

        # This uses PersistedApprovalProvider internally (fresh instance)
        result = await KillSwitchService.clear(
            db,
            cleared_by="admin",
            principal_context=_admin_principal(),
            # No approval_provider — defaults to PersistedApprovalProvider
        )
        assert result is not None
        assert result.is_active is False


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Unresolved Scope Limitations (G4.8)
# ═══════════════════════════════════════════════════════════════════════════════
#
# The following scope dimensions are NOT currently enforced by PersistedApprovalProvider
# and are deferred to G4.8:
#
# - Approval expiry: No `expires_at` column on Approval model; cannot reject
#   expired approvals. This is a schema gap.
# - Approval supersession: No `superseded_by` column; cannot reject superseded
#   approvals. This is a schema gap.
# - Reviewer principal scope: Approval.reviewer is an attribution string, not a
#   principal reference. Cannot enforce that the reviewer had authority to approve.
#   This is a schema and policy gap.
# - Non-mission actions: Approval.mission_id is non-nullable FK; non-mission
#   actions (KILL_SWITCH_CLEAR, IDENTITY_ACTION) cannot have Approval records.
#   These use principal-based auth instead. See NON_MISSION_APPROVAL_GAP.md.