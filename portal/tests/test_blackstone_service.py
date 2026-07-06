"""
Persistence tests for the Blackstone Evidence Ledger and evaluation service.

Uses an in-memory SQLite async engine so the tests do not require PostgreSQL.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.services.blackstone_service import BlackstoneEvaluationService, EvidenceLedgerService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh async SQLite in-memory session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def test_evidence_ledger_record(db_session):
    entry = await EvidenceLedgerService.record(
        db=db_session,
        object_type="claim",
        object_id="CLAIM-LEDGER-1",
        action="evaluated",
        actor="AGENT-BLACKSTONE-2-0",
        payload={"status": "controlling"},
        provenance_hash="abc123",
    )
    await db_session.commit()

    assert entry.id is not None
    assert entry.object_type == "claim"
    assert entry.provenance_hash == "abc123"

    chain = await EvidenceLedgerService.get_chain(
        db_session, object_type="claim", object_id="CLAIM-LEDGER-1"
    )
    assert len(chain) == 1
    assert chain[0].action == "evaluated"


async def test_save_evaluation_creates_record(db_session):
    evaluation = {
        "claim": {
            "id": "CLAIM-TEST-1",
            "status": "controlling",
            "confidence": "high",
            "text": "Test claim.",
            "subject": "test",
        },
        "authority": {
            "controlling_authority": {"id": "SRC-TEST-1", "citation": "Test Statute § 1"},
            "conflicts": [],
        },
        "recommendation": {
            "question": "Should we adopt the test claim?",
            "recommendation": "Adopt the claim as controlling authority permits.",
            "rationale": "High-confidence controlling authority.",
            "agents": ["AGENT-BLACKSTONE-2-0"],
        },
        "risks": [
            {"id": "RISK-TEST-1", "category": "test", "description": "Test risk", "score": 0.7}
        ],
    }
    snapshot = await BlackstoneEvaluationService.save(
        db=db_session,
        claim_id="CLAIM-TEST-1",
        evaluation=evaluation,
        case_id="CASE-TEST-1",
        tenant_id=None,
        evaluated_by="AGENT-BLACKSTONE-2-0",
    )
    await db_session.commit()

    assert snapshot.id is not None
    assert snapshot.claim_id == "CLAIM-TEST-1"
    assert snapshot.case_id == "CASE-TEST-1"
    assert snapshot.status == "controlling"
    assert snapshot.recommendation == evaluation["recommendation"]["recommendation"]


async def test_get_latest_evaluation(db_session):
    evaluation = {
        "claim": {"id": "CLAIM-TEST-1", "status": "controlling", "confidence": "high"},
        "authority": {"controlling_authority": None, "conflicts": []},
        "recommendation": {
            "question": "Test?",
            "recommendation": "Adopt.",
            "rationale": "Test rationale.",
            "agents": [],
        },
        "risks": [],
    }
    await BlackstoneEvaluationService.save(
        db=db_session,
        claim_id="CLAIM-TEST-1",
        evaluation=evaluation,
        evaluated_by="AGENT-BLACKSTONE-2-0",
    )
    await db_session.commit()

    latest = await BlackstoneEvaluationService.get_latest(db_session, claim_id="CLAIM-TEST-1")
    assert latest is not None
    assert latest.claim_id == "CLAIM-TEST-1"
    assert latest.recommendation == "Adopt."
