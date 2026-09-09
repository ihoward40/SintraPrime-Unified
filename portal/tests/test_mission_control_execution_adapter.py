"""Tests for the governed Mission Control durable execution adapter."""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_execution import Mission, Run
from portal.services.durable_orchestration_authority import (
    DurableOrchestrationAuthority,
)
from portal.services.mission_control_capability_policy import CapabilityDecision


# PortableUUID boundary (PR #294): identity columns are strict UUID; legacy
# readable labels in this file are derived to stable UUIDs via uuid5.
def _uuid(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "sintraprime-test:" + label))


TENANT_A = _uuid("tenant-a")
TENANT_B = _uuid("tenant-b")
USER_A = _uuid("user-a")
USER_B = _uuid("user-b")


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection, tables=[Mission.__table__, Run.__table__]
            )
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_start_maps_durable_workflow_id_to_execution_ref(db):
    authority = DurableOrchestrationAuthority()
    mission = await authority.create_mission(db, tenant_id=TENANT_A, created_by=USER_A)

    async def workflow(_context, _input):
        return "ok"

    authority.engine.register_workflow("test", workflow)
    run = await authority.start_run(
        db,
        mission_id=mission.mission_id,
        tenant_id=TENANT_A,
        created_by=USER_A,
        workflow_type="test",
        input_data={},
        policy_decision=CapabilityDecision.DIRECT_ALLOWED,
    )

    assert run.run_id != run.execution_ref
    assert run.execution_ref
    assert run.status == "ACTIVE"
    assert authority.engine.get_workflow(run.execution_ref) is not None


@pytest.mark.asyncio
async def test_cancel_routes_using_persisted_execution_ref(db):
    authority = DurableOrchestrationAuthority()
    mission = await authority.create_mission(db, tenant_id=TENANT_A, created_by=USER_A)

    block = asyncio.Event()

    async def workflow(_context, _input):
        await block.wait()
        return "ok"

    authority.engine.register_workflow("test", workflow)
    run = await authority.start_run(
        db,
        mission_id=mission.mission_id,
        tenant_id=TENANT_A,
        created_by=USER_A,
        workflow_type="test",
        input_data={},
        policy_decision=CapabilityDecision.DIRECT_ALLOWED,
    )
    assert await authority.cancel_run(db, run_id=run.run_id, tenant_id=TENANT_A)
    assert run.status == "CANCELLED"
    block.set()


@pytest.mark.asyncio
async def test_start_rejects_cross_tenant_mission(db):
    authority = DurableOrchestrationAuthority()
    mission = await authority.create_mission(db, tenant_id=TENANT_A, created_by=USER_A)

    with pytest.raises(ValueError, match="MISSION_NOT_FOUND"):
        await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id=TENANT_B,
            created_by=USER_B,
            workflow_type="missing",
            input_data={},
            policy_decision=CapabilityDecision.DIRECT_ALLOWED,
        )


@pytest.mark.asyncio
async def test_approval_required_does_not_start_engine(db):
    authority = DurableOrchestrationAuthority()
    mission = await authority.create_mission(db, tenant_id=TENANT_A, created_by=USER_A)
    run = await authority.start_run(
        db,
        mission_id=mission.mission_id,
        tenant_id=TENANT_A,
        created_by=USER_A,
        workflow_type="not-registered-yet",
        input_data={},
        policy_decision=CapabilityDecision.APPROVAL_REQUIRED,
    )
    assert run.status == "APPROVAL_REQUIRED"
    assert run.execution_ref is None


@pytest.mark.asyncio
async def test_unknown_durable_workflow_never_becomes_active(db):
    authority = DurableOrchestrationAuthority()
    mission = await authority.create_mission(db, tenant_id=TENANT_A, created_by=USER_A)
    with pytest.raises(ValueError, match="Unknown workflow type"):
        await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id=TENANT_A,
            created_by=USER_A,
            workflow_type="unknown",
            input_data={},
            policy_decision=CapabilityDecision.DIRECT_ALLOWED,
        )

    result = await db.execute(select(Run).where(Run.mission_id == mission.mission_id))
    runs = result.scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "FAILED"
    assert runs[0].execution_ref is None
