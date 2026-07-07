"""
Tests for the Blackstone case workflow endpoints and live case scripts.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from blackstone.engines import BlackstoneOrchestrator
from portal.database import Base, get_db
from portal.main import app
from portal.models.blackstone import BlackstoneEvaluation, EvidenceLedger
from portal.services.blackstone_service import BlackstoneEvaluationService

client = TestClient(app)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Override the FastAPI DB dependency with an in-memory SQLite session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[BlackstoneEvaluation.__table__, EvidenceLedger.__table__]
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        app.dependency_overrides[get_db] = lambda: session
        yield session
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def test_case_intake_endpoint_creates_evaluation(db: AsyncSession) -> None:
    response = client.post(
        "/api/v1/blackstone/cases",
        json={
            "case_id": "case-test-001",
            "tenant_id": "tenant-test",
            "title": "LVNV validation test",
            "question": "Should we dispute this debt?",
            "claim": {
                "id": "claim-test-001",
                "text": "The collection letter omits validation notice.",
                "subject": "FDCPA validation",
                "assumptions": ["Letter is first communication"],
                "missing_evidence": ["Certified mail receipt"],
                "tags": ["fdcpa", "test"],
            },
            "sources": [
                {
                    "id": "src-fdcpa",
                    "citation": "15 U.S.C. § 1692g",
                    "classification": "primary_legal",
                }
            ],
            "evidence": [
                {
                    "id": "ev-test-1",
                    "source_id": "src-fdcpa",
                    "claim_text": "FDCPA requires validation notice.",
                    "quotation": "within five days...",
                    "context": "initial communication",
                    "confidence": "high",
                }
            ],
            "counter_evidence": [],
            "risks": [],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["case_id"] == "case-test-001"
    assert body["ledger_entries"] >= 1
    assert body["evaluation_id"]


@pytest.mark.asyncio
async def test_case_status_endpoint_returns_evaluations(db: AsyncSession) -> None:
    await BlackstoneEvaluationService.save(
        db=db,
        claim_id="claim-status-001",
        evaluation={
            "claim": {"status": "controlling", "confidence": "high"},
            "recommendation": {
                "recommendation": "Adopt",
                "rationale": "strong evidence",
            },
            "authority": {"controlling_authority": None, "conflicts": []},
            "provenance": {"verified": True},
        },
        case_id="case-status-001",
        tenant_id="tenant-status",
    )
    await db.commit()

    response = client.get(
        "/api/v1/blackstone/cases/case-status-001",
        params={"tenant_id": "tenant-status"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "case-status-001"
    assert body["total_evaluations"] == 1
    assert body["latest_status"] == "controlling"
    assert body["latest_confidence"] == "high"


@pytest.mark.parametrize(
    "module_name",
    [
        "blackstone.cases.irs_3176c_cnc_case",
        "blackstone.cases.lvnv_deficiency_case",
        "blackstone.cases.paypal_collection_case",
        "blackstone.cases.self_financial_case",
        "blackstone.cases.uacc_repossession_case",
        "blackstone.cases.affirm_financial_case",
        "blackstone.cases.lvnv_counter_claim_case",
    ],
)
def test_live_case_scripts_run_without_error(module_name: str) -> None:
    import importlib

    module = importlib.import_module(module_name)

    build_case_fn = module.build_case
    orchestrator, claim_id = build_case_fn()
    assert isinstance(orchestrator, BlackstoneOrchestrator)

    evaluation = orchestrator.evaluate(
        claim_id,
        question="Is this case ready to file?",
        actor="AGENT-BLACKSTONE-2-0",
    )
    assert evaluation["claim"]["status"] in {
        "controlling",
        "persuasive",
        "emerging",
        "disputed",
        "unverified",
    }
    assert evaluation["provenance"]["verified"] is True
    assert evaluation["recommendation"]["recommendation"]
