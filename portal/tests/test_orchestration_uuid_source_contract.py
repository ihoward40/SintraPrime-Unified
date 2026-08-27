"""Guards for the declared orchestration string-UUID model contract."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import UUID, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from portal.database import Base
from portal.models.orchestration import (
    ApprovalRequest,
    BudgetUsage,
    EvidenceReference,
    MemoryEntry,
    OrchestrationEvent,
    OrchestrationLinkage,
    OrchestrationNode,
    OrchestrationRun,
    PrincipalAuthority,
    ProviderDefinition,
    ReconciliationResult,
    RoutingDecision,
    VerificationResult,
)
from portal.models.user import Role, Tenant, User

ORCHESTRATION_MODELS = (
    OrchestrationRun,
    OrchestrationNode,
    OrchestrationEvent,
    ProviderDefinition,
    RoutingDecision,
    VerificationResult,
    ReconciliationResult,
    ApprovalRequest,
    OrchestrationLinkage,
    PrincipalAuthority,
    BudgetUsage,
    EvidenceReference,
    MemoryEntry,
)


def _uuid_contract_columns():
    return [
        column
        for model in ORCHESTRATION_MODELS
        for column in model.__table__.columns
        if column.primary_key or column.foreign_keys
    ]


def test_declared_and_effective_uuid_contract_is_string_preserving():
    columns = _uuid_contract_columns()

    assert len(columns) == 31
    assert all(isinstance(column.type, UUID) for column in columns)
    assert all(column.type.as_uuid is False for column in columns)


def test_models_package_has_no_import_time_type_rewrite_functions():
    import portal.models as models_package

    assert not hasattr(models_package, "_align_orchestration_uuid_python_representation")
    assert not hasattr(models_package, "_align_external_identity_foreign_keys")


@pytest.mark.asyncio
async def test_sqlite_round_trip_preserves_string_uuid_results():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    User.__table__,
                    OrchestrationRun.__table__,
                    OrchestrationEvent.__table__,
                    OrchestrationNode.__table__,
                    BudgetUsage.__table__,
                    RoutingDecision.__table__,
                    OrchestrationLinkage.__table__,
                ],
            )
        )

    tenant_id = str(uuid.uuid4())
    role_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    linkage_id = str(uuid.uuid4())

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Canonical portal identity models store UUIDs as String(36), while the
        # orchestration FK columns use SQLite's UUID text encoding (32 hex
        # characters). Seed the parent identities in that storage-equivalent
        # form so SQLite can enforce the cross-domain FK relationship.
        session.add(Tenant(id=tenant_id.replace("-", ""), name="UUID Contract", slug=f"uuid-{tenant_id[:8]}"))
        session.add(
            Role(
                id=role_id,
                name=f"UUID_ROLE_{role_id[:8]}",
                display_name="UUID Contract Role",
                description="test",
            )
        )
        session.add(
            User(
                id=user_id.replace("-", ""),
                tenant_id=tenant_id.replace("-", ""),
                role_id=role_id,
                email=f"uuid-{user_id[:8]}@example.com",
                hashed_password="not-a-real-secret",
                first_name="UUID",
                last_name="Contract",
            )
        )
        await session.flush()
        session.add(
            OrchestrationRun(
                id=run_id,
                tenant_id=tenant_id,
                created_by=user_id,
                objective="UUID contract round trip",
                constraints={},
                task_type="mixed",
                sensitivity="INTERNAL",
                execution_mode="SINGLE",
            )
        )
        await session.flush()
        session.add(
            OrchestrationEvent(
                id=event_id,
                run_id=run_id,
                sequence=1,
                event_type="UUID_CONTRACT",
                event_hash="a" * 64,
            )
        )
        session.add(
            OrchestrationNode(
                id=node_id,
                run_id=run_id,
                node_id="uuid-contract-node",
                sequence=1,
                role="WORKER",
                objective="Round trip",
            )
        )
        await session.flush()
        session.add(
            OrchestrationLinkage(
                id=linkage_id,
                event_id=event_id,
                node_id=node_id,
                tenant_id=tenant_id,
            )
        )
        await session.commit()

    async with session_factory() as session:
        run = await session.get(OrchestrationRun, run_id)
        orchestration_event = await session.get(OrchestrationEvent, event_id)
        node = await session.get(OrchestrationNode, node_id)
        linkage = await session.get(OrchestrationLinkage, linkage_id)

        values = (
            run.id,
            run.tenant_id,
            run.created_by,
            orchestration_event.id,
            orchestration_event.run_id,
            node.id,
            node.run_id,
            linkage.id,
            linkage.event_id,
            linkage.node_id,
            linkage.tenant_id,
        )
        assert all(isinstance(value, str) for value in values)
        assert linkage.event_id == orchestration_event.id
        assert linkage.node_id == node.id

    await engine.dispose()
