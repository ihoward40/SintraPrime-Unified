"""JARVIS-001-A4 focused acceptance proof: full read-only Principal-to-Brief chain.

One integrated acceptance mission proves the certified A1+A2+A3 chain works
end to end: an ordinary-language Principal instruction becomes one
PrincipalMissionRequest, one authoritative Mission, real certified S1 swarm
execution with governed inference, an evidence-backed JarvisMissionResult,
bounded provenance-linked memory writeback, and a Principal Brief produced by
the EXISTING brief service with full linkage. No new engines, no new receipt
architecture, no consequential external side effects.

Defect-demonstration tests (A4-6 idempotency, A4-10 actor pre-validation) are
written FIRST and must fail before any seam correction is applied.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.orchestration import MemoryEntry, PrincipalAuthority
from portal.services.jarvis_memory_writeback import (
    MEMORY_TYPE_JARVIS_MISSION_RESULT,
    retrieve_mission_memory,
    store_mission_result_memory,
    synthesize_mission_brief,
)
from portal.services.jarvis_principal_mission import (
    EXTERNAL_SIDE_EFFECTS,
    DecisionContext,
    InMemoryPrincipalMissionRequestStore,
    PrincipalMissionRequestInput,
    persist_principal_mission_request,
)
from portal.services.jarvis_read_only_workflow import (
    AuthoritativeMission,
    JarvisMissionResult,
    JarvisReadOnlyWorkflow,
)

REPO_ROOT_HINT = "Review the repository and identify attention items."

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "33333333-3333-3333-3333-333333333333"
PRINCIPAL = "22222222-2222-2222-2222-222222222222"
INTRUDER = "44444444-4444-4444-4444-444444444444"


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_principal_authority(session: AsyncSession) -> None:
    session.add(
        PrincipalAuthority(
            id=uuid4(),
            tenant_id=TENANT,
            user_id=PRINCIPAL,
            scope="GLOBAL",
            is_active=True,
        )
    )
    await session.flush()


async def _principal_instruction(session: AsyncSession):
    """Ordinary-language Principal instruction through the certified A1 seam."""
    store = InMemoryPrincipalMissionRequestStore()
    request = await persist_principal_mission_request(
        store,
        tenant_id=TENANT,
        requested_by=PRINCIPAL,
        input_data=PrincipalMissionRequestInput(
            objective=REPO_ROOT_HINT,
            decision_context=DecisionContext(
                objective=REPO_ROOT_HINT,
                constraints=("read_only",),
            ),
        ),
    )
    return store, request


def _real_bridge(request) -> JarvisMissionResult:
    with tempfile.TemporaryDirectory(prefix="a4-bridge-") as run_dir:
        return JarvisReadOnlyWorkflow(
            repo_path=str(Path(__file__).resolve().parents[2]), run_dir=run_dir
        ).execute(request)


def _synthetic_result(
    request,
    *,
    tenant_id=None,
    request_hash=None,
    mission_id=None,
    status="SUCCESS",
) -> JarvisMissionResult:
    mission = AuthoritativeMission(
        mission_id=mission_id or uuid4(),
        request_id=request.request_id,
        tenant_id=tenant_id or request.tenant_id,
        created_by=request.requested_by,
    )
    return JarvisMissionResult(
        mission=mission,
        request_id=request.request_id,
        request_hash=request_hash or request.request_hash,
        status=status,
        evidence=(
            {
                "worker_id": "w1",
                "artifact": {
                    "state": "completed",
                    "findings": {"provider": "fallback", "result": "attention items found"},
                },
            },
        ),
        summary={
            "uncertainty": ["deterministic mock provider"],
            "recommended_next_actions": ["archive swarm artifacts"],
            "actions_requiring_approval": ["grant repository write access"],
        },
        error="",
        task_provenance={
            "task_id": "jarvis-" + str(request.request_id),
            "worker_class": "ModelReasoningWorker",
        },
        swarm_id="jarvis-" + str(mission.mission_id),
        routed_to_swarm=True,
        legacy_delegate_used=False,
    )


# ── A4-1/A4-3: one instruction -> one request -> one authoritative Mission ────


@pytest.mark.asyncio
async def test_a4_1_instruction_to_request_to_mission(db_session):
    store, request = await _principal_instruction(db_session)
    # ordinary-language instruction became exactly one authoritative request
    assert request.objective == REPO_ROOT_HINT
    fetched = await store.get(request.request_id)
    assert fetched is not None
    assert fetched.request_id == request.request_id
    # server-authoritative bounded DecisionContext
    assert request.decision_context.objective == REPO_ROOT_HINT
    assert request.decision_context.constraints == ("read_only",)
    with pytest.raises(ValidationError):
        DecisionContext(
            objective=REPO_ROOT_HINT,
            constraints=("read_only",),
            unauthorized_field="client cannot inject context",
        )
    # one authoritative Mission from the certified A2 workflow
    result = _real_bridge(request)
    assert isinstance(result.mission.mission_id, object)
    assert result.mission.request_id == request.request_id
    assert result.mission.workflow_type == "jarvis.principal_mission"
    assert result.mission.authority == "JARVIS_READ_ONLY"


# ── A4-2/A4-4/A4-5: provenance + hash intact; real S1 path; governed inference ─


@pytest.mark.asyncio
async def test_a4_real_s1_path_provenance_and_governance(db_session):
    _store, request = await _principal_instruction(db_session)
    result = _real_bridge(request)

    # A4-4: execution reached the certified A2 real S1 path
    assert result.status == "SUCCESS"
    assert result.routed_to_swarm is True
    assert result.legacy_delegate_used is False
    # A4-5: inference stayed governed (router provider recorded, failover log kept)
    artifact = result.evidence[0]["artifact"]
    assert artifact["state"] == "completed"
    assert artifact["findings"]["provider"] == "fallback"
    assert artifact["findings"]["provider_attempts"]
    # A4-2: request provenance and hash intact at the result boundary
    assert result.request_id == request.request_id
    assert result.request_hash == request.request_hash


# ── A4-6: retry idempotency (defect demonstration — expected to FAIL first) ───


@pytest.mark.asyncio
async def test_a4_6_retry_does_not_duplicate_memory(db_session):
    store, request = await _principal_instruction(db_session)
    result = _synthetic_result(request)

    first = await store_mission_result_memory(db_session, store, result)
    retry = await store_mission_result_memory(db_session, store, result)

    assert retry.memory_id == first.memory_id  # same semantic record
    rows = (
        (
            await db_session.execute(
                select(MemoryEntry).where(
                    MemoryEntry.tenant_id == TENANT,
                    MemoryEntry.type == MEMORY_TYPE_JARVIS_MISSION_RESULT,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1  # no duplicate authoritative memory row


# ── A4-7/A4-8: evidence provenance preserved; memory retrievable ──────────────


@pytest.mark.asyncio
async def test_a4_evidence_and_memory_retrieval(db_session):
    store, request = await _principal_instruction(db_session)
    result = _synthetic_result(request)
    record = await store_mission_result_memory(db_session, store, result)

    entries = await retrieve_mission_memory(
        db_session, store, tenant_id=TENANT, request_id=request.request_id
    )
    assert len(entries) == 1
    content = entries[0].content
    assert str(entries[0].id) == record.memory_id
    # A4-7: evidence/artifact provenance preserved in the bounded record
    assert content["evidence_references"] == [
        {"worker_id": "w1", "artifact_state": "completed", "provider": "fallback"}
    ]
    assert content["linkage"]["request_hash"] == request.request_hash
    assert content["linkage"]["swarm_id"] == result.swarm_id


# ── A4-9/A4-11: existing brief produced with full linkage; side effects zero ──


@pytest.mark.asyncio
async def test_a4_brief_linkage_and_zero_side_effects(db_session):
    await _seed_principal_authority(db_session)
    store, request = await _principal_instruction(db_session)
    result = _real_bridge(request)

    report = await synthesize_mission_brief(db_session, store, result, actor_id=PRINCIPAL)
    section = report["sections"]["jarvis_mission"]

    # A4-9: the EXISTING brief engine produced the report (its own sections)
    assert report["sections"]["operations"]["status"] == "HARDENED"
    assert "memory_summary" in report["sections"]
    # A4-11: request <-> mission <-> memory <-> evidence linkage visible
    assert section["linkage"]["request_id"] == str(request.request_id)
    assert section["linkage"]["mission_id"] == str(result.mission.mission_id)
    assert section["linkage"]["request_hash"] == request.request_hash
    assert section["linkage"]["tenant_id"] == TENANT
    assert section["evidence_references"][0]["worker_id"]
    # A4-11: external side effects remain zero end to end
    assert EXTERNAL_SIDE_EFFECTS == 0
    assert result.external_side_effects == 0
    assert section["external_side_effects"] == 0
    assert section["authority"] == "JARVIS_READ_ONLY"


# ── A4-10: unauthorized actor rejected BEFORE memory mutation (defect demo) ───


@pytest.mark.asyncio
async def test_a4_10_unauthorized_actor_zero_memory_mutation(db_session):
    store, request = await _principal_instruction(db_session)
    result = _synthetic_result(request)

    with pytest.raises(PermissionError):
        await synthesize_mission_brief(db_session, store, result, actor_id=INTRUDER)

    rows = (
        (
            await db_session.execute(
                select(MemoryEntry).where(
                    MemoryEntry.tenant_id == TENANT,
                    MemoryEntry.type == MEMORY_TYPE_JARVIS_MISSION_RESULT,
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []  # ZERO authoritative memory mutation


# ── A4-12: evidence receipt chain from existing artifacts ─────────────────────


@pytest.mark.asyncio
async def test_a4_12_evidence_receipt_chain(db_session):
    await _seed_principal_authority(db_session)
    store, request = await _principal_instruction(db_session)
    result = _real_bridge(request)
    report = await synthesize_mission_brief(db_session, store, result, actor_id=PRINCIPAL)
    section = report["sections"]["jarvis_mission"]

    entries = await retrieve_mission_memory(
        db_session, store, tenant_id=TENANT, request_id=request.request_id
    )
    receipt = {
        "principal_actor_id": PRINCIPAL,
        "tenant_id": TENANT,
        "request_id": str(request.request_id),
        "mission_id": str(result.mission.mission_id),
        "swarm_id": result.swarm_id,
        "authority_source": result.mission.authority,
        "result_hash": result.request_hash,
        "memory_id": section["memory_id"],
        "brief_reference": report["timestamp"],
        "created_at": entries[0].content["created_at"],
    }
    # every stage of the chain is evidenced without inventing a new architecture
    assert receipt["authority_source"] == "JARVIS_READ_ONLY"
    assert receipt["request_id"] == section["linkage"]["request_id"]
    assert receipt["mission_id"] == section["linkage"]["mission_id"]
    assert receipt["swarm_id"] == section["linkage"]["swarm_id"]
    assert receipt["result_hash"] == section["linkage"]["request_hash"]
    assert receipt["memory_id"] == str(entries[0].id)
    assert receipt["brief_reference"]
    datetime.fromisoformat(receipt["created_at"])


# ── negative acceptance: every rejection fails closed ─────────────────────────


@pytest.mark.asyncio
async def test_a4_negatives_fail_closed(db_session):
    store, request = await _principal_instruction(db_session)

    # cross-tenant substitution
    tampered = _synthetic_result(request, tenant_id=OTHER_TENANT)
    with pytest.raises(PermissionError, match="TENANT_MISMATCH"):
        await store_mission_result_memory(db_session, store, tampered)

    # tampered result hash
    bad_hash = _synthetic_result(request, request_hash="0" * 64)
    with pytest.raises(PermissionError, match="HASH_MISMATCH"):
        await store_mission_result_memory(db_session, store, bad_hash)

    # unknown request id
    bogus_store = InMemoryPrincipalMissionRequestStore()
    wrong_request = _synthetic_result(request)
    wrong_request = JarvisMissionResult(
        mission=wrong_request.mission,
        request_id=uuid4(),
        request_hash=wrong_request.request_hash,
        status=wrong_request.status,
        evidence=wrong_request.evidence,
        summary=wrong_request.summary,
        error=wrong_request.error,
        task_provenance=wrong_request.task_provenance,
        swarm_id=wrong_request.swarm_id,
        routed_to_swarm=True,
        legacy_delegate_used=False,
    )
    with pytest.raises(PermissionError, match="PROVENANCE_UNVERIFIED"):
        await store_mission_result_memory(db_session, bogus_store, wrong_request)

    # malformed mission result (worker output dict)
    with pytest.raises(PermissionError, match="TYPED_RESULT_REQUIRED"):
        await store_mission_result_memory(
            db_session, store, {"findings": {"provider": "fallback"}}
        )

    # unauthorized principal still fails closed after corrections
    with pytest.raises(PermissionError):
        await synthesize_mission_brief(
            db_session, store, _synthetic_result(request), actor_id=INTRUDER
        )
