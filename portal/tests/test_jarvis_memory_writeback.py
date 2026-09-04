"""JARVIS-001-A3 focused proof: result -> bounded provenance-linked memory -> brief.

Directive tests A3-1..A3-8 plus regression tests for the two baseline defects
found and repaired while building this seam:
- memory_vault.store_memory wrote ``mem-xxxx`` string ids into the UUID
  MemoryEntry.id column (every store failed);
- remediation.validate_principal_approval used ``is_active is True`` (a Python
  identity check), which denied every actor including seeded authorities.
"""

from __future__ import annotations

import uuid as uuid_module
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import portal.services.jarvis_memory_writeback as writeback_module
from portal.database import Base
from portal.models.orchestration import MemoryEntry, PrincipalAuthority
from portal.services import principal_brief as principal_brief_module
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
)
from portal.services.memory_vault import memory_vault
from portal.services.remediation_service import remediation

REPO_ROOT = Path(__file__).resolve().parents[2]

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "33333333-3333-3333-3333-333333333333"
PRINCIPAL = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_request_and_authority(session: AsyncSession):
    """Authoritative A1 request plus a seeded active principal authority."""
    store = InMemoryPrincipalMissionRequestStore()
    request = await persist_principal_mission_request(
        store,
        tenant_id=TENANT,
        requested_by=PRINCIPAL,
        input_data=PrincipalMissionRequestInput(
            objective="Review the repository and identify attention items.",
            decision_context=DecisionContext(
                objective="Review the repository and identify attention items.",
                constraints=("read_only",),
            ),
        ),
    )
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
    return store, request


def _result_for(request) -> JarvisMissionResult:
    mission = AuthoritativeMission(
        mission_id=uuid4(),
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        created_by=request.requested_by,
    )
    return JarvisMissionResult(
        mission=mission,
        request_id=request.request_id,
        request_hash=request.request_hash,
        status="SUCCESS",
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
            "uncertainty": [
                "provider is a deterministic mock",
                "api_key=abc123 observed in provider logs",
            ],
            "recommended_next_actions": ["archive swarm artifacts"],
            "actions_requiring_approval": ["grant repository write access"],
            "note": "api_key=supersecret must not persist verbatim",
        },
        error="",
        task_provenance={
            "task_id": "jarvis-" + str(request.request_id),
            "request_id": str(request.request_id),
            "mission_id": str(mission.mission_id),
            "tenant_id": request.tenant_id,
            "capability": "jarvis.read_only",
            "worker_class": "ModelReasoningWorker",
        },
        swarm_id="jarvis-" + str(mission.mission_id),
        routed_to_swarm=True,
        legacy_delegate_used=False,
    )


# ── A3-1: one bounded provenance-linked memory record ──────────────────────────


@pytest.mark.asyncio
async def test_a3_1_one_bounded_provenance_linked_record(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)

    record = await store_mission_result_memory(db_session, store, result)

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
    assert len(rows) == 1  # exactly one record
    entry = rows[0]
    assert str(entry.id) == record.memory_id
    content = entry.content
    # mission/request provenance preserved (invariant #2)
    linkage = content["linkage"]
    assert linkage["mission_id"] == str(result.mission.mission_id)
    assert linkage["request_id"] == str(result.request_id)
    assert linkage["request_hash"] == request.request_hash
    assert linkage["tenant_id"] == TENANT
    assert linkage["swarm_id"] == result.swarm_id
    assert content["authority"] == "JARVIS_READ_ONLY"
    assert content["workflow_type"] == "jarvis.principal_mission"
    assert content["external_side_effects"] == 0
    assert "created_at" in content
    # evidence/artifact references preserved, bounded to shape
    assert content["evidence_references"] == [
        {
            "worker_id": "w1",
            "artifact_state": "completed",
            "provider": "fallback",
        }
    ]
    # bounded data: sensitive material is redacted by the existing vault path
    assert "supersecret" not in str(content)
    assert "[MASKED]" in str(content)


# ── A3-2: memory retrievable by mission/request ───────────────────────────────


@pytest.mark.asyncio
async def test_a3_2_memory_retrievable_by_request(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)
    record = await store_mission_result_memory(db_session, store, result)

    entries = await retrieve_mission_memory(
        db_session, store, tenant_id=TENANT, request_id=request.request_id
    )
    assert len(entries) == 1
    assert str(entries[0].id) == record.memory_id
    assert entries[0].content["linkage"]["mission_id"] == str(result.mission.mission_id)


# ── A3-3: cross-tenant substitution fails closed ──────────────────────────────


@pytest.mark.asyncio
async def test_a3_3_cross_tenant_retrieval_and_write_fail_closed(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)
    await store_mission_result_memory(db_session, store, result)

    # cross-tenant retrieval returns nothing (structurally scoped to caller)
    foreign = await retrieve_mission_memory(
        db_session, store, tenant_id=OTHER_TENANT, request_id=request.request_id
    )
    assert foreign == []

    # a result claiming another tenant for the same request is rejected
    tampered_mission = AuthoritativeMission(
        mission_id=uuid4(),
        request_id=request.request_id,
        tenant_id=OTHER_TENANT,
        created_by=request.requested_by,
    )
    tampered = JarvisMissionResult(
        mission=tampered_mission,
        request_id=request.request_id,
        request_hash=request.request_hash,
        status="SUCCESS",
        evidence=(),
        summary={},
        error="",
        task_provenance={},
        swarm_id="jarvis-tampered",
        routed_to_swarm=True,
        legacy_delegate_used=False,
    )
    with pytest.raises(PermissionError, match="TENANT_MISMATCH"):
        await store_mission_result_memory(db_session, store, tampered)

    # non-UUID tenant identity fails closed
    object.__setattr__(result.mission, "tenant_id", "tenant-1")
    with pytest.raises(PermissionError, match="TENANT_ID_INVALID"):
        await store_mission_result_memory(db_session, store, result)


# ── A3-4: workers cannot author authoritative memory ──────────────────────────


@pytest.mark.asyncio
async def test_a3_4_worker_memory_prohibition(db_session):
    store, _request = await _seed_request_and_authority(db_session)

    # a raw worker output dict is rejected before any persistence
    worker_output = {"findings": {"provider": "fallback"}, "state": "completed"}
    with pytest.raises(PermissionError, match="TYPED_RESULT_REQUIRED"):
        await store_mission_result_memory(db_session, store, worker_output)  # type: ignore[arg-type]

    # structural: no swarm_runtime production source can reach the writeback
    # seam or the portal memory vault.
    forbidden = (
        "jarvis_memory_writeback",
        "store_mission_result_memory",
        "memory_vault",
        "store_memory",
    )
    for path in REPO_ROOT.glob("swarm_runtime/*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} references {token}"


# ── A3-5: the existing Principal Brief service is invoked ─────────────────────


@pytest.mark.asyncio
async def test_a3_5_existing_brief_service_invoked(db_session, monkeypatch):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)

    calls: list[tuple[str, str]] = []
    real_create_brief = principal_brief_module.brief_service.create_brief

    async def spy(session, tenant_id, actor_id):
        calls.append((tenant_id, actor_id))
        return await real_create_brief(session, tenant_id, actor_id)

    monkeypatch.setattr(principal_brief_module.brief_service, "create_brief", spy)

    report = await synthesize_mission_brief(
        db_session, store, result, actor_id=PRINCIPAL
    )
    assert calls == [(TENANT, PRINCIPAL)]  # existing service, correct arguments
    # existing brief sections prove the real engine produced the report
    assert report["sections"]["memory_summary"]["total_knowledge"] == 0
    assert report["sections"]["operations"]["status"] == "HARDENED"


# ── A3-6: brief carries request/mission/result/evidence/memory linkage ────────


@pytest.mark.asyncio
async def test_a3_6_brief_linkage_complete(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)

    report = await synthesize_mission_brief(db_session, store, result, actor_id=PRINCIPAL)
    section = report["sections"]["jarvis_mission"]

    assert section["linkage"]["request_id"] == str(request.request_id)
    assert section["linkage"]["mission_id"] == str(result.mission.mission_id)
    assert section["linkage"]["request_hash"] == request.request_hash
    assert section["linkage"]["tenant_id"] == TENANT
    assert section["evidence_references"][0]["worker_id"] == "w1"
    assert section["findings"]["status"] == "SUCCESS"
    # memory record id resolves to the durable MemoryEntry row
    row = (
        await db_session.execute(
            select(MemoryEntry).where(MemoryEntry.id == UUID(section["memory_id"]))
        )
    ).scalar_one()
    assert row.content["linkage"]["request_id"] == str(request.request_id)


# ── A3-7: uncertainty and approval-required fields survive synthesis ──────────


@pytest.mark.asyncio
async def test_a3_7_uncertainty_and_approval_signals_survive(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)

    report = await synthesize_mission_brief(db_session, store, result, actor_id=PRINCIPAL)
    section = report["sections"]["jarvis_mission"]

    assert section["uncertainty"] == [
        "provider is a deterministic mock",
        "[MASKED] observed in provider logs",
    ]
    assert section["recommended_next_actions"] == ["archive swarm artifacts"]
    assert section["actions_requiring_approval"] == ["grant repository write access"]
    # the same fields survive in the durable memory record itself
    entries = await retrieve_mission_memory(
        db_session, store, tenant_id=TENANT, request_id=request.request_id
    )
    stored = entries[0].content
    assert stored["uncertainty"] == section["uncertainty"]
    assert stored["recommended_next_actions"] == section["recommended_next_actions"]
    assert stored["actions_requiring_approval"] == section["actions_requiring_approval"]


# ── A3-8: external side effects remain zero ───────────────────────────────────


@pytest.mark.asyncio
async def test_a3_8_external_side_effects_zero(db_session):
    store, request = await _seed_request_and_authority(db_session)
    result = _result_for(request)

    record = await store_mission_result_memory(db_session, store, result)
    report = await synthesize_mission_brief(db_session, store, result, actor_id=PRINCIPAL)

    assert EXTERNAL_SIDE_EFFECTS == 0
    assert record.external_side_effects == 0
    assert report["sections"]["jarvis_mission"]["external_side_effects"] == 0
    assert report["sections"]["jarvis_mission"]["authority"] == "JARVIS_READ_ONLY"


# ── baseline-defect regression locks ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_vault_memory_entry_id_satisfies_uuid_column(db_session):
    """Regression: vault ids are UUID-compatible (store actually persists)."""
    memory_id = await memory_vault.store_memory(
        db_session, TENANT, {"lesson": "verify before push"}, "LESSON_LEARNED"
    )
    uuid_module.UUID(memory_id)  # canonical UUID string
    row = (
        await db_session.execute(select(MemoryEntry).where(MemoryEntry.id == UUID(memory_id)))
    ).scalar_one()
    assert row.type == "LESSON_LEARNED"


@pytest.mark.asyncio
async def test_validate_principal_approval_accepts_seeded_active_authority(db_session):
    """Regression: SQL predicate accepts active, denies inactive and unknown."""
    active = uuid4()
    inactive = uuid4()
    db_session.add_all(
        [
            PrincipalAuthority(
                id=uuid4(), tenant_id=TENANT, user_id=active, scope="GLOBAL", is_active=True
            ),
            PrincipalAuthority(
                id=uuid4(), tenant_id=TENANT, user_id=inactive, scope="GLOBAL", is_active=False
            ),
        ]
    )
    await db_session.flush()
    assert await remediation.validate_principal_approval(db_session, TENANT, str(active), "BRIEF_SYNTHESIS") is True
    assert await remediation.validate_principal_approval(db_session, TENANT, str(inactive), "BRIEF_SYNTHESIS") is False
    assert await remediation.validate_principal_approval(db_session, TENANT, str(uuid4()), "BRIEF_SYNTHESIS") is False
