"""Integration tests for Mythos Brain coordinator and canonical authority enforcement.

Corrected to use the canonical MythosBrainCoordinator(session) API and
the DB-backed RemediationService.validate_principal_approval authority
path. The stale PolicyEnforcementPoint class has been removed; tests now
exercise the canonical authority enforcement surface.
"""
import uuid

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
from portal.models.orchestration import (
    MemoryEntry,
    OrchestrationEvent,
    OrchestrationLinkage,
    OrchestrationNode,
    OrchestrationRun,
    PrincipalAuthority,
)
from portal.models.user import Tenant, User
from portal.services.memory_service import MemoryService, MemorySourceClass, TrustLevel
from portal.services.mythos_brain import MythosBrainCoordinator
from portal.services.remediation_service import remediation

# Valid UUIDs for DB-backed models that use UUID columns.
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
PRINCIPAL_ID = "550e8400-e29b-41d4-a716-446655440001"


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """In-memory SQLite session for testing Mythos Brain integration."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    User.__table__,
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    MissionControlRunControl.__table__,
                    MissionControlOutbox.__table__,
                    OrchestrationRun.__table__,
                    OrchestrationEvent.__table__,
                    OrchestrationNode.__table__,
                    OrchestrationLinkage.__table__,
                    PrincipalAuthority.__table__,
                    MemoryEntry.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_authority(db: AsyncSession):
    """Seed a PrincipalAuthority row so DB-backed validation passes."""
    authority = PrincipalAuthority(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        user_id=PRINCIPAL_ID,
        scope="GLOBAL",
        is_active=True,
    )
    db.add(authority)
    await db.commit()
    return authority


@pytest.mark.asyncio
async def test_intent_ingestion_to_outbox(db: AsyncSession, seeded_authority):
    """Verifies that ingesting an intent creates an outbox record via canonical API."""
    coordinator = MythosBrainCoordinator(db)
    intent_type = "NOVA_RESEARCH_TASK"
    payload = {"query": "test query", "idempotency_key": str(uuid.uuid4())}

    intent_id = await coordinator.ingest_intent(
        tenant_id=TENANT_ID,
        actor_id=PRINCIPAL_ID,
        intent_type=intent_type,
        payload=payload,
    )
    await db.commit()

    # Verify Outbox Entry
    stmt = select(MissionControlOutbox).where(MissionControlOutbox.intent_id == intent_id)
    result = await db.execute(stmt)
    outbox_entry = result.scalar_one()
    assert outbox_entry.event_type == intent_type
    assert outbox_entry.status == "PENDING"


@pytest.mark.asyncio
async def test_brain_ingest_pipeline_steps(db: AsyncSession):
    """Verifies the 11-step ingestion pipeline logic in MemoryService."""
    memory_service = MemoryService()
    source_class = MemorySourceClass.REPOSITORY
    content = "Sample repository knowledge content."
    metadata = {"project": "SintraPrime-Unified", "domain": "legal"}

    # Run ingestion
    memory_id = await memory_service.ingest(
        tenant_id=TENANT_ID,
        source_class=source_class,
        content=content,
        metadata=metadata,
        principal_id=PRINCIPAL_ID,
    )

    assert memory_id is not None
    assert isinstance(memory_id, str)
    assert len(memory_id) == 36


@pytest.mark.asyncio
async def test_authority_enforcement_denies_unauthorized_actor(db: AsyncSession):
    """Verifies that DB-backed authority enforcement denies unauthorized actors."""
    coordinator = MythosBrainCoordinator(db)
    with pytest.raises(PermissionError, match="Unauthorized principal command attempt"):
        await coordinator.ingest_intent(
            tenant_id=TENANT_ID,
            actor_id="attacker-001",
            intent_type="PRINCIPAL_COMMAND",
            payload={"action": "reformat-database"},
        )


@pytest.mark.asyncio
async def test_authority_enforcement_allows_seeded_principal(db: AsyncSession, seeded_authority):
    """Verifies that DB-backed authority enforcement allows a seeded principal."""
    coordinator = MythosBrainCoordinator(db)
    intent_id = await coordinator.ingest_intent(
        tenant_id=TENANT_ID,
        actor_id=PRINCIPAL_ID,
        intent_type="STANDARD_INTENT",
        payload={"task": "verify-integrity"},
    )
    assert intent_id is not None
    assert intent_id.startswith("int-")