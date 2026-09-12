from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from portal.services.mission_control_projection_service import get_run_control


TENANT_A = "00000000-0000-0000-0000-000000000002"


def _uuid(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "sintraprime-test:" + label))


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    MissionControlRunControl.__table__,
                    MissionControlRunControlEvent.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_projection_includes_copilot_worker_fields(db: AsyncSession):
    rc = MissionControlRunControl(
        id=_uuid("rc-copilot-embedded-001"),
        tenant_id=TENANT_A,
        workflow_id="wf-copilot-embedded-001",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    event = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-001"),
        run_control_id=rc.id,
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=0,
        new_version=1,
        event_hash="event-hash-copilot-embedded-001",
        payload={
            "actor_id": "copilot.engineering.01",
            "worker_role": "ENGINEERING_WORKER",
            "parent_coordinator": "hermes.canonical",
            "work_order_id": "WO-EMBED-001",
            "write_scope": ["web/src/pages/mission-control/**"],
            "lease_state": "ACTIVE",
            "authority_source": "NONE",
            "external_effects": 0,
        },
    )
    db.add(event)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id=rc.id)
    assert projection is not None
    assert projection.actor_id == "copilot.engineering.01"
    assert projection.worker_role == "ENGINEERING_WORKER"
    assert projection.parent_coordinator == "hermes.canonical"
    assert projection.work_order_id == "WO-EMBED-001"
    assert projection.write_scope == ["web/src/pages/mission-control/**"]
    assert projection.lease_state == "ACTIVE"
    assert projection.authority_source == "NONE"
    assert projection.external_effects == 0


@pytest.mark.asyncio
async def test_projection_preserves_worker_fields_across_partial_updates(db: AsyncSession):
    rc = MissionControlRunControl(
        id=_uuid("rc-copilot-embedded-002"),
        tenant_id=TENANT_A,
        workflow_id="wf-copilot-embedded-002",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    initial = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-002"),
        run_control_id=rc.id,
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=0,
        new_version=1,
        event_hash="event-hash-copilot-embedded-002",
        payload={
            "actor_id": "copilot.engineering.01",
            "worker_role": "ENGINEERING_WORKER",
            "parent_coordinator": "hermes.canonical",
            "work_order_id": "WO-EMBED-002",
            "write_scope": ["web/src/pages/mission-control/**"],
            "lease_state": "ACTIVE",
            "authority_source": "NONE",
            "external_effects": 0,
        },
    )
    db.add(initial)
    await db.flush()

    partial = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-003"),
        run_control_id=rc.id,
        sequence=2,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=1,
        new_version=2,
        event_hash="event-hash-copilot-embedded-003",
        payload={"test_status": "PASS"},
    )
    db.add(partial)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id=rc.id)
    assert projection is not None
    assert projection.actor_id == "copilot.engineering.01"
    assert projection.work_order_id == "WO-EMBED-002"
    assert projection.write_scope == ["web/src/pages/mission-control/**"]
    assert projection.test_status == "PASS"


@pytest.mark.asyncio
async def test_projection_rejects_boolean_external_effects(db: AsyncSession):
    rc = MissionControlRunControl(
        id=_uuid("rc-copilot-embedded-003"),
        tenant_id=TENANT_A,
        workflow_id="wf-copilot-embedded-003",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    event = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-004"),
        run_control_id=rc.id,
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=0,
        new_version=1,
        event_hash="event-hash-copilot-embedded-004",
        payload={"external_effects": True},
    )
    db.add(event)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id=rc.id)
    assert projection is not None
    assert projection.external_effects is None


@pytest.mark.asyncio
async def test_projection_rejects_non_string_write_scope_entries(db: AsyncSession):
    rc = MissionControlRunControl(
        id=_uuid("rc-copilot-embedded-004"),
        tenant_id=TENANT_A,
        workflow_id="wf-copilot-embedded-004",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    event = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-005"),
        run_control_id=rc.id,
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=0,
        new_version=1,
        event_hash="event-hash-copilot-embedded-005",
        payload={"write_scope": ["web/src/**", None]},
    )
    db.add(event)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id=rc.id)
    assert projection is not None
    assert projection.write_scope == []


@pytest.mark.asyncio
async def test_projection_rejects_non_string_worker_fields(db: AsyncSession):
    rc = MissionControlRunControl(
        id=_uuid("rc-copilot-embedded-005"),
        tenant_id=TENANT_A,
        workflow_id="wf-copilot-embedded-005",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    event = MissionControlRunControlEvent(
        id=_uuid("rce-copilot-embedded-006"),
        run_control_id=rc.id,
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="RUNNING",
        previous_version=0,
        new_version=1,
        event_hash="event-hash-copilot-embedded-006",
        payload={
            "actor_id": 123,
            "worker_role": ["ENGINEERING_WORKER"],
            "parent_coordinator": {"value": "hermes.canonical"},
            "work_order_id": 999,
            "lease_state": {"state": "ACTIVE"},
            "test_status": 1,
            "authority_source": False,
        },
    )
    db.add(event)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id=rc.id)
    assert projection is not None
    assert projection.actor_id is None
    assert projection.worker_role is None
    assert projection.parent_coordinator is None
    assert projection.work_order_id is None
    assert projection.lease_state is None
    assert projection.test_status is None
    assert projection.authority_source is None
