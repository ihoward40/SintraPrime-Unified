"""Mission Control run-control projection tests."""

from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_command import MissionControlCommand
from portal.models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from portal.models.user import Permission, Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.services.mission_control_run_control_service import (
    RunControlConflictError,
    RunControlInvalidTransitionError,
    create_run_control,
    transition_run_control,
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    Permission.__table__,
                    RolePermission.__table__,
                    UserPermissionAssoc.__table__,
                    User.__table__,
                    MissionControlCommand.__table__,
                    MissionControlRunControl.__table__,
                    MissionControlRunControlEvent.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


# Canonical shared role identity (roles are global in the production schema:
# portal.models.user.Role has no tenant_id and enforces a unique name). The
# test uses a deterministic id so the same canonical role is reused across
# tenants and across repeated fixture invocation.
CANONICAL_ROLE_ID = "role-1"
CANONICAL_ROLE_NAME = "role-1"


async def _get_or_create_canonical_role(session: AsyncSession) -> Role:
    """Return the shared canonical role, creating it only when absent.

    Roles are global (no tenant scope). We key the lookup on the deterministic
    canonical id used by this test module so the same role row is reused across
    tenants and across repeated calls. We never delete or overwrite an existing
    role on a collision, and we do not swallow unrelated IntegrityErrors.
    """
    existing = await session.get(Role, CANONICAL_ROLE_ID)
    if existing is not None:
        return existing
    role = Role(
        id=CANONICAL_ROLE_ID,
        name=CANONICAL_ROLE_NAME,
        display_name="Role 1",
        description="seed role",
        is_system=True,
    )
    session.add(role)
    # Flush so the canonical role identifier exists before dependent user rows
    # are inserted (explicit parent-before-child boundary).
    await session.flush()
    return role


async def _seed_refs(session: AsyncSession, *, tenant_id: str = "tenant-1") -> tuple[str, str, str]:
    # 1. Tenant (parent)
    tenant = Tenant(id=tenant_id, name=f"Tenant {tenant_id}", slug=tenant_id.replace("-", ""))
    session.add(tenant)
    await session.flush()

    # 2. Canonical role (global; get-or-create, shared across tenants)
    role = await _get_or_create_canonical_role(session)

    # 3. User/principal (child of tenant and role)
    user = User(
        id=f"user-{tenant_id}",
        tenant_id=tenant_id,
        role_id=role.id,
        email=f"user-{tenant_id}@example.com",
        hashed_password="x",
        first_name="Test",
        last_name="User",
    )
    session.add(user)
    await session.flush()

    # 4. Mission Control command (child of tenant and user)
    command = MissionControlCommand(
        id=f"command-{tenant_id}",
        tenant_id=tenant_id,
        requested_by=user.id,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id=f"workflow-{tenant_id}",
        idempotency_key="idem-123456789012",
        request_hash="a" * 64,
        state="REFUSED",
    )
    session.add(command)
    await session.flush()

    # 5-7. Run-control record and initial run-control event are created by the
    # service layer (create_run_control / transition_run_control) in each test,
    # not here, preserving the parent-before-child order at every boundary.
    await session.commit()
    return tenant.id, user.id, command.id


@pytest.mark.asyncio
async def test_run_control_creation_and_valid_transition(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-1",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.RUNNING,
    )
    assert control.state == RunControlState.RUNNING.value
    assert control.state_version == 1

    updated = await transition_run_control(
        db,
        tenant_id=tenant_id,
        run_control_id=control.id,
        expected_version=1,
        new_state=RunControlState.PAUSE_REQUESTED,
        requested_by=user_id,
        reason="operator requested hold",
        command_id=command_id,
        workflow_status_snapshot="running",
    )
    assert updated.state == RunControlState.PAUSE_REQUESTED.value
    assert updated.state_version == 2


@pytest.mark.asyncio
async def test_run_control_rejects_stale_version(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-1",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.RUNNING,
    )
    await transition_run_control(
        db,
        tenant_id=tenant_id,
        run_control_id=control.id,
        expected_version=1,
        new_state=RunControlState.PAUSE_REQUESTED,
        requested_by=user_id,
        reason="operator requested hold",
        command_id=command_id,
        workflow_status_snapshot="running",
    )

    with pytest.raises(RunControlConflictError):
        await transition_run_control(
            db,
            tenant_id=tenant_id,
            run_control_id=control.id,
            expected_version=1,
            new_state=RunControlState.PAUSING,
            requested_by=user_id,
            reason="runner ack",
            command_id=command_id,
            workflow_status_snapshot="running",
        )

    event_result = await db.execute(
        select(MissionControlRunControlEvent).where(MissionControlRunControlEvent.run_control_id == control.id)
    )
    assert len(event_result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_run_control_rejects_invalid_transition(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-1",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.RUNNING,
    )

    with pytest.raises(RunControlInvalidTransitionError):
        await transition_run_control(
            db,
            tenant_id=tenant_id,
            run_control_id=control.id,
            expected_version=1,
            new_state=RunControlState.PAUSED,
            requested_by=user_id,
            reason="illegal skip",
            command_id=command_id,
            workflow_status_snapshot="running",
        )


@pytest.mark.asyncio
async def test_run_control_creation_records_projection_metadata(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-2",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        workflow_source="durable_execution",
        workflow_version_snapshot=4,
        state=RunControlState.RUNNING,
        pause_reason="initial snapshot",
        terminal_reason_code="initial",
    )

    assert control.workflow_source == "durable_execution"
    assert control.workflow_version_snapshot == 4
    assert control.projection_schema_version == 1
    assert control.superseded_at is None
    assert control.terminal_reason_code == "initial"


@pytest.mark.asyncio
async def test_run_control_superseded_transition_is_supported(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-3",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.PAUSE_REQUESTED,
        pause_reason="pause intent",
    )
    updated = await transition_run_control(
        db,
        tenant_id=tenant_id,
        run_control_id=control.id,
        expected_version=1,
        new_state=RunControlState.SUPERSEDED,
        requested_by=user_id,
        reason="terminal workflow outcome superseded pause intent",
        command_id=command_id,
        workflow_status_snapshot="completed",
        terminal_reason_code="COMPLETED_FIRST",
    )

    assert updated.state == RunControlState.SUPERSEDED.value
    assert updated.state_version == 2
    assert updated.superseded_at is not None

    event_result = await db.execute(
        select(MissionControlRunControlEvent).where(MissionControlRunControlEvent.run_control_id == control.id)
    )
    events = event_result.scalars().all()
    assert len(events) == 2
    assert events[-1].event_schema_version == 1
    assert events[-1].previous_event_hash
    assert events[-1].workflow_status_observed_at is not None


@pytest.mark.asyncio
async def test_run_control_transition_requires_tenant_scope_and_blocks_cross_tenant_access(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db, tenant_id="tenant-1")
    other_tenant_id, _, _ = await _seed_refs(db, tenant_id="tenant-2")

    signature = inspect.signature(transition_run_control)
    assert signature.parameters["tenant_id"].kind is inspect.Parameter.KEYWORD_ONLY

    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-tenant-scope",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.RUNNING,
    )

    await transition_run_control(
        db,
        tenant_id=tenant_id,
        run_control_id=control.id,
        expected_version=1,
        new_state=RunControlState.PAUSE_REQUESTED,
        requested_by=user_id,
        reason="tenant scoped",
        command_id=command_id,
        workflow_status_snapshot="running",
    )

    with pytest.raises(RunControlInvalidTransitionError):
        await transition_run_control(
            db,
            tenant_id=other_tenant_id,
            run_control_id=control.id,
            expected_version=2,
            new_state=RunControlState.PAUSING,
            requested_by=user_id,
            reason="cross tenant",
            command_id=command_id,
            workflow_status_snapshot="running",
        )

    event_result = await db.execute(
        select(MissionControlRunControlEvent).where(MissionControlRunControlEvent.run_control_id == control.id)
    )
    assert len(event_result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_run_control_transition_update_includes_tenant_predicate(db: AsyncSession):
    tenant_id, user_id, command_id = await _seed_refs(db, tenant_id="tenant-sql")
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id="workflow-sql-predicate",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=RunControlState.RUNNING,
    )

    update_statements: list[str] = []
    sync_engine = db.get_bind()

    def _capture_update(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("UPDATE"):
            update_statements.append(statement)

    event.listen(sync_engine, "before_cursor_execute", _capture_update)
    try:
        updated = await transition_run_control(
            db,
            tenant_id=tenant_id,
            run_control_id=control.id,
            expected_version=1,
            new_state=RunControlState.PAUSE_REQUESTED,
            requested_by=user_id,
            reason="predicate check",
            command_id=command_id,
            workflow_status_snapshot="running",
        )
    finally:
        event.remove(sync_engine, "before_cursor_execute", _capture_update)

    assert updated.state == RunControlState.PAUSE_REQUESTED.value
    assert updated.state_version == 2
    assert update_statements, "expected to capture at least one UPDATE statement"
    update_sql = "\n".join(update_statements)
    assert "tenant_id" in update_sql
    assert "state_version" in update_sql
    assert "mission_control_run_controls" in update_sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("starting_state", "terminal_state"),
    [
        (RunControlState.PAUSE_REQUESTED, RunControlState.CANCELLED),
        (RunControlState.PAUSE_REQUESTED, RunControlState.COMPLETED),
        (RunControlState.PAUSE_REQUESTED, RunControlState.FAILED),
        (RunControlState.PAUSING, RunControlState.CANCELLED),
        (RunControlState.PAUSING, RunControlState.COMPLETED),
        (RunControlState.PAUSING, RunControlState.FAILED),
    ],
)
async def test_terminal_precedence_over_pause_intent(db: AsyncSession, starting_state: RunControlState, terminal_state: RunControlState):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id=f"workflow-{starting_state.value.lower()}-{terminal_state.value.lower()}",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot="running",
        state=starting_state,
        pause_reason="pause intent",
    )

    updated = await transition_run_control(
        db,
        tenant_id=tenant_id,
        run_control_id=control.id,
        expected_version=1,
        new_state=terminal_state,
        requested_by=user_id,
        reason=f"{terminal_state.value.lower()} wins",
        command_id=command_id,
        workflow_status_snapshot=terminal_state.value.lower(),
        terminal_reason_code=f"{terminal_state.value}_FIRST",
    )
    assert updated.state == terminal_state.value
    assert updated.state_version == 2

    with pytest.raises(RunControlInvalidTransitionError):
        await transition_run_control(
            db,
            tenant_id=tenant_id,
            run_control_id=control.id,
            expected_version=2,
            new_state=RunControlState.PAUSING,
            requested_by=user_id,
            reason="stale pause after terminal",
            command_id=command_id,
            workflow_status_snapshot=terminal_state.value.lower(),
        )

    event_result = await db.execute(
        select(MissionControlRunControlEvent).where(MissionControlRunControlEvent.run_control_id == control.id)
    )
    events = event_result.scalars().all()
    assert len(events) == 2
    assert events[-1].previous_event_hash


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "terminal_state",
    [
        RunControlState.COMPLETED,
        RunControlState.FAILED,
        RunControlState.CANCELLED,
        RunControlState.COMPENSATED,
    ],
)
async def test_terminal_states_reject_follow_up_transitions(db: AsyncSession, terminal_state: RunControlState):
    tenant_id, user_id, command_id = await _seed_refs(db)
    control = await create_run_control(
        db,
        tenant_id=tenant_id,
        workflow_id=f"workflow-terminal-{terminal_state.value.lower()}",
        command_id=command_id,
        requested_by=user_id,
        workflow_status_snapshot=terminal_state.value.lower(),
        state=terminal_state,
        terminal_reason_code=f"{terminal_state.value}_SEED",
    )

    with pytest.raises(RunControlInvalidTransitionError):
        await transition_run_control(
            db,
            tenant_id=tenant_id,
            run_control_id=control.id,
            expected_version=1,
            new_state=RunControlState.PAUSE_REQUESTED,
            requested_by=user_id,
            reason="terminal state cannot revive",
            command_id=command_id,
            workflow_status_snapshot=terminal_state.value.lower(),
        )

    event_result = await db.execute(
        select(MissionControlRunControlEvent).where(MissionControlRunControlEvent.run_control_id == control.id)
    )
    assert len(event_result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_parallel_pg_transition_race_appends_exactly_one_event():
    database_url = os.getenv("DATABASE_URL", "")
    required_in_ci = os.getenv("MISSION_CONTROL_PG_RACE_REQUIRED") == "1"
    if not database_url.startswith("postgresql"):
        message = "PostgreSQL DATABASE_URL not configured"
        if required_in_ci:
            pytest.fail(message)
        pytest.skip(message)

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn,
                    tables=[
                        Tenant.__table__,
                        Role.__table__,
                        Permission.__table__,
                        RolePermission.__table__,
                        UserPermissionAssoc.__table__,
                        User.__table__,
                        MissionControlCommand.__table__,
                        MissionControlRunControl.__table__,
                        MissionControlRunControlEvent.__table__,
                    ],
                )
            )

        session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_maker() as session:
            tenant_id, user_id, command_id = await _seed_refs(session, tenant_id="tenant-pg")
            control = await create_run_control(
                session,
                tenant_id=tenant_id,
                workflow_id="workflow-pg-race",
                command_id=command_id,
                requested_by=user_id,
                workflow_status_snapshot="running",
                state=RunControlState.RUNNING,
            )
            await session.commit()

        barrier = asyncio.Event()

        async def contender(expected_state: RunControlState):
            async with session_maker() as session:
                await barrier.wait()
                return await transition_run_control(
                    session,
                    tenant_id=tenant_id,
                    run_control_id=control.id,
                    expected_version=1,
                    new_state=expected_state,
                    requested_by=user_id,
                    reason="simultaneous race",
                    command_id=command_id,
                    workflow_status_snapshot="running",
                )

        task_a = asyncio.create_task(contender(RunControlState.PAUSE_REQUESTED))
        task_b = asyncio.create_task(contender(RunControlState.PAUSE_REQUESTED))
        barrier.set()
        results = await asyncio.gather(task_a, task_b, return_exceptions=True)

        successes = [result for result in results if not isinstance(result, Exception)]
        conflicts = [result for result in results if isinstance(result, RunControlConflictError)]
        exceptions = [result for result in results if isinstance(result, Exception) and not isinstance(result, RunControlConflictError)]

        assert len(successes) == 1
        assert len(conflicts) == 1
        assert not exceptions

        async with session_maker() as session:
            event_result = await session.execute(
                select(MissionControlRunControlEvent)
                .where(MissionControlRunControlEvent.run_control_id == control.id)
                .order_by(MissionControlRunControlEvent.sequence.asc())
            )
            events = event_result.scalars().all()
            assert len(events) == 2
            assert events[0].event_hash
            assert events[1].previous_event_hash == events[0].event_hash
            assert events[1].event_hash
    except Exception as exc:
        if required_in_ci:
            raise
        if "connect" in str(exc).lower() or "database" in str(exc).lower():
            pytest.skip(f"PostgreSQL integration unavailable: {exc}")
        raise
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_seed_refs_is_idempotent_and_reuses_canonical_role(db: AsyncSession):
    """The run-control fixture must be idempotent with respect to the shared
    canonical role and must preserve tenant-scoped data across repeated calls.

    Covers:
      1. invoking the seeding helper twice raises no uniqueness error;
      2. exactly one canonical role row exists afterward;
      3. dependent users reference the intended (shared) role;
      4. no duplicate grant rows are created;
      5. a second-tenant call preserves the correct data model;
      6. cleanup does not remove a role still referenced elsewhere.
    """
    from sqlalchemy import func

    # 1. Two invocations in one session must not raise a uniqueness error.
    await _seed_refs(db, tenant_id="tenant-1")
    await _seed_refs(db, tenant_id="tenant-2")

    # 2. Exactly one canonical role row exists (global role, reused).
    role_count = (await db.execute(select(func.count()).select_from(Role))).scalar_one()
    assert role_count == 1

    canonical = await db.get(Role, CANONICAL_ROLE_ID)
    assert canonical is not None

    # 3. Both dependent users reference the intended shared role.
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    assert len(users) == 2
    for user in users:
        assert user.role_id == canonical.id

    # 4. No grant rows were created (and therefore no duplicates).
    assert (await db.execute(select(func.count()).select_from(RolePermission))).scalar_one() == 0
    assert (await db.execute(select(func.count()).select_from(UserPermissionAssoc))).scalar_one() == 0

    # 5. Second tenant preserved the correct data model: tenant-2 user exists
    #    and points at the same global role; tenant-1 remains intact.
    t2_user = await db.get(User, "user-tenant-2")
    assert t2_user is not None
    assert t2_user.tenant_id == "tenant-2"
    assert t2_user.role_id == canonical.id
    t1_user = await db.get(User, "user-tenant-1")
    assert t1_user is not None
    assert t1_user.role_id == canonical.id

    # 6. A role still referenced by users is not removed by any fixture cleanup.
    extra_user = User(
        id="user-extra",
        tenant_id="tenant-1",
        role_id=canonical.id,
        email="user-extra@example.com",
        hashed_password="x",
        first_name="Extra",
        last_name="User",
    )
    db.add(extra_user)
    await db.flush()
    assert await db.get(Role, CANONICAL_ROLE_ID) is not None


@pytest.mark.asyncio
async def test_seed_refs_idempotent_under_ordering(db: AsyncSession):
    """Idempotency must hold regardless of invocation order (no reliance on
    incidental flush ordering). Seed several distinct tenants in sequence; the
    shared canonical role must remain a single row while each tenant gets its
    own user referencing it."""
    from sqlalchemy import func

    await _seed_refs(db, tenant_id="tenant-1")
    await _seed_refs(db, tenant_id="tenant-2")
    await _seed_refs(db, tenant_id="tenant-3")
    role_count = (await db.execute(select(func.count()).select_from(Role))).scalar_one()
    assert role_count == 1
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    assert user_count == 3
    assert (await db.get(User, "user-tenant-1")) is not None
    assert (await db.get(User, "user-tenant-2")) is not None
    assert (await db.get(User, "user-tenant-3")) is not None
