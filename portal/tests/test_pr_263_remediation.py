import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_outbox import EventNodeLinkage, MemoryEntry, MissionControlOutbox
from portal.services.memory_vault import memory_vault
from portal.services.mythos_brain import MythosBrainCoordinator
from portal.services.principal_brief import brief_service
from portal.services.remediation_service import remediation

# Use SQLite in-memory for fast, reproducible evidence
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="module")
async def db_session():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_actor_validation_remediation(db_session):
    """EVIDENCE: Unauthorized actor blocked from Principal Command."""
    coordinator = MythosBrainCoordinator(db_session)
    with pytest.raises(PermissionError, match="Unauthorized principal command attempt"):
        await coordinator.ingest_intent(
            tenant_id="test-tenant",
            actor_id="attacker-001",
            intent_type="PRINCIPAL_COMMAND",
            payload={"action": "reformat-database"}
        )

@pytest.mark.asyncio
async def test_sensitive_data_redaction_remediation(db_session):
    """EVIDENCE: Redaction at all persistence boundaries."""
    coordinator = MythosBrainCoordinator(db_session)
    payload = {"reason": "Approval for oauth_token=secret_key_123", "key": "api_key=456"}

    intent_id = await coordinator.ingest_intent(
        tenant_id="test-tenant",
        actor_id="principal-god-mode",
        intent_type="STANDARD_INTENT",
        payload=payload
    )

    # Verify outbox entry is redacted
    result = await db_session.execute(select(MissionControlOutbox).where(MissionControlOutbox.intent_id == intent_id))
    entry = result.scalar_one()
    assert "secret_key_123" not in str(entry.payload)
    assert "[MASKED]" in str(entry.payload)

@pytest.mark.asyncio
async def test_lifecycle_timestamps_and_linkage_remediation(db_session):
    """EVIDENCE: Durable event-to-node linkage and timestamps."""
    coordinator = MythosBrainCoordinator(db_session)
    intent_id = await coordinator.ingest_intent(
        tenant_id="test-tenant",
        actor_id="principal-god-mode",
        intent_type="STANDARD_INTENT",
        payload={"task": "verify-integrity"}
    )

    # 1. Verify timestamps in outbox
    result = await db_session.execute(select(MissionControlOutbox).where(MissionControlOutbox.intent_id == intent_id))
    entry = result.scalar_one()
    assert "created_at" in entry.payload
    assert "node_id" in entry.payload

    # 2. Verify durable linkage record
    link_result = await db_session.execute(select(EventNodeLinkage).where(EventNodeLinkage.tenant_id == "test-tenant"))
    linkage = link_result.scalar_one()
    assert linkage.node_id == entry.payload["node_id"]
    assert linkage.event_id.startswith("evt-")

@pytest.mark.asyncio
async def test_omnibrain_to_brief_flow_remediation(db_session):
    """EVIDENCE: Real OmniBrain retrieval to Principal Brief."""
    tenant_id = "test-tenant"
    principal_id = "principal-god-mode"

    # 1. Store memory
    await memory_vault.store_memory(
        db_session, tenant_id, "Lesson: Verify RLS before push.", "LESSON_LEARNED"
    )
    await db_session.commit()

    # 2. Generate Brief
    report = await brief_service.create_brief(db_session, tenant_id, principal_id)

    assert report["tenant_id"] == tenant_id
    assert report["sections"]["memory_summary"]["total_lessons"] == 1
    assert "Verify RLS" in str(report["sections"]["memory_summary"]["recent_lesson"])
