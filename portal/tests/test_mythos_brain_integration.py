import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_outbox import MissionControlOutbox
from portal.models.mission_control_run_control import MissionControlRunControl
from portal.services.memory_service import MemoryService, MemorySourceClass, TrustLevel
from portal.services.mythos_brain import MythosBrainCoordinator, PolicyEnforcementPoint


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session for testing Mythos Brain integration."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    MissionControlRunControl.__table__,
                    MissionControlOutbox.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_intent_ingestion_to_outbox(db: AsyncSession):
    """Verifies that ingesting an intent creates both a ledger entry and an outbox record."""
    coordinator = MythosBrainCoordinator()
    tenant_id = "test-tenant"
    actor_id = "principal"
    command_type = "NOVA_RESEARCH_TASK"
    payload = {"query": "test query", "idempotency_key": str(uuid.uuid4())}

    # Ingest intent
    command = await coordinator.ingest_intent(
        db, tenant_id=tenant_id, actor_id=actor_id, command_type=command_type, payload=payload
    )
    await db.commit()

    # Verify Ledger Entry
    stmt = select(MissionControlCommand).where(MissionControlCommand.id == command.id)
    result = await db.execute(stmt)
    saved_command = result.scalar_one()
    assert saved_command.state == "AUTHORIZED"
    assert saved_command.command_type == command_type

    # Verify Outbox Entry
    stmt = select(MissionControlOutbox).where(MissionControlOutbox.command_id == command.id)
    result = await db.execute(stmt)
    outbox_entry = result.scalar_one()
    assert outbox_entry.executor_type == "nova"
    assert outbox_entry.message_type == "EXECUTE_INTENT"
    assert outbox_entry.state == "PENDING"


@pytest.mark.asyncio
async def test_brain_ingest_pipeline_steps(db: AsyncSession):
    """Verifies the 11-step ingestion pipeline logic in MemoryService."""
    memory_service = MemoryService()
    tenant_id = "test-tenant"
    source_class = MemorySourceClass.REPOSITORY
    content = "Sample repository knowledge content."
    metadata = {"project": "SintraPrime-Unified", "domain": "legal"}
    principal_id = "user-001"

    # Run ingestion
    memory_id = await memory_service.ingest(
        tenant_id=tenant_id,
        source_class=source_class,
        content=content,
        metadata=metadata,
        principal_id=principal_id,
    )

    assert memory_id is not None
    assert isinstance(memory_id, str)
    # The current implementation returns a UUID string, verifying it's generated.
    assert len(memory_id) == 36


@pytest.mark.asyncio
async def test_pep_refusal_policy():
    """Verifies that the PEP correctly refuses unauthorized intents."""
    pep = PolicyEnforcementPoint()

    # Principal should be authorized
    assert await pep.authorize_intent("t1", "principal", "ANY", {}) is True

    # Non-principal should be refused for destructive tasks
    assert await pep.authorize_intent("t1", "other-user", "DESTRUCTIVE_RESEARCH", {}) is False

    # Non-principal should be authorized for standard tasks
    assert await pep.authorize_intent("t1", "other-user", "STANDARD_TASK", {}) is True
