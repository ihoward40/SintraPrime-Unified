"""Mission Control run-control projection tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_command import MissionControlCommand
from portal.models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from portal.models.user import Tenant, User
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


async def _seed_refs(session: AsyncSession) -> tuple[str, str, str]:
    tenant = Tenant(id="tenant-1", name="Tenant", slug="tenant")
    user = User(
        id="user-1",
        tenant_id="tenant-1",
        role_id="role-1",
        email="user@example.com",
        hashed_password="x",
        first_name="Test",
        last_name="User",
    )
    command = MissionControlCommand(
        id="command-1",
        tenant_id="tenant-1",
        requested_by="user-1",
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="workflow-1",
        idempotency_key="idem-123456789012",
        request_hash="a" * 64,
        state="REFUSED",
    )
    session.add_all([tenant, user, command])
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
