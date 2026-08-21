"""Gate 3 PostgreSQL certification for canonical governed scheduler authority."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from portal.models.production_authority import ProductionOrchestrationRun
from portal.scripts.postgresql_bootstrap import (
    PRODUCTION_GATE_MIGRATION_SEQUENCE,
    apply_migrations,
)
from portal.services.governed_scheduler import (
    SchedulerIdempotencyConflictError,
    SchedulerStateError,
    cancel_schedule,
    create_schedule,
    dispatch_due_schedule,
    get_schedule,
    replay_schedule,
)

pytestmark = pytest.mark.postgresql

TENANT_ID = "00000000-0000-0000-0000-000000003285"
PRINCIPAL_ID = "00000000-0000-0000-0000-000000003386"


def _database_url() -> str:
    raw = os.environ.get("GOVERNED_SCHEDULER_DATABASE_URL")
    if not raw:
        pytest.skip("Governed Scheduler PostgreSQL URL not configured")
    return raw


async def _sessionmaker() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    database_url = _database_url()
    apply_migrations(database_url, reset_public_schema=True)
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession), engine


async def _seed(maker: async_sessionmaker[AsyncSession]) -> None:
    async with maker() as db:
        role_id = await db.scalar(text("SELECT id FROM roles WHERE name = 'SUPER_ADMIN'"))
        assert role_id is not None
        await db.execute(
            text("INSERT INTO tenants (id, name, slug) VALUES (CAST(:id AS uuid), :name, :slug)"),
            {"id": TENANT_ID, "name": "Scheduler Gate", "slug": "scheduler-gate"},
        )
        await db.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, role_id, email, first_name, last_name, hashed_password
                ) VALUES (
                    CAST(:id AS uuid), CAST(:tenant_id AS uuid), CAST(:role_id AS uuid),
                    :email, :first_name, :last_name, :hashed_password
                )
                """
            ),
            {
                "id": PRINCIPAL_ID,
                "tenant_id": TENANT_ID,
                "role_id": str(role_id),
                "email": "scheduler-gate@example.invalid",
                "first_name": "Scheduler",
                "last_name": "Principal",
                "hashed_password": "synthetic-not-a-real-password",
            },
        )
        await db.commit()


def test_scheduler_gate_is_in_authoritative_bootstrap() -> None:
    paths = [str(path).replace("\\", "/") for path in PRODUCTION_GATE_MIGRATION_SEQUENCE]
    assert paths[:3] == [
        "portal/migrations/add_governed_service_identities.sql",
        "portal/migrations/add_adaptive_orchestration_domain.sql",
        "portal/migrations/add_governed_scheduler_domain.sql",
    ]
    assert paths.count("portal/migrations/add_governed_scheduler_domain.sql") == 1


@pytest.mark.asyncio
async def test_scheduler_survives_restart_replays_and_dispatches_exactly_once() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        due_at = datetime.now(UTC) - timedelta(minutes=1)
        idempotency_key = "gate3-scheduler-durable-0001"

        async with maker() as db:
            created = await create_schedule(
                db,
                tenant_id=TENANT_ID,
                created_by=PRINCIPAL_ID,
                objective="Prepare a governed internal specialist review; external actions remain disabled",
                constraints={"gate": "scheduler", "external_actions": False},
                execution_mode="THINK_WORK_CHECK",
                budget_limits=None,
                run_at=due_at,
                idempotency_key=idempotency_key,
            )
            schedule_id = created["schedule_id"]
            assert created["status"] == "SCHEDULED"
            assert [event["event_type"] for event in created["events"]] == ["SCHEDULE_CREATED"]
            await db.commit()

        # New session simulates process/repository restart.
        async with maker() as db:
            restored = await get_schedule(db, schedule_id=schedule_id, tenant_id=TENANT_ID)
            assert restored is not None
            assert restored["status"] == "SCHEDULED"
            replay = await replay_schedule(db, schedule_id=schedule_id, tenant_id=TENANT_ID)
            assert replay is not None
            assert replay["projection_matches"] is True
            assert replay["event_count"] == 1

        async with maker() as db:
            dispatched = await dispatch_due_schedule(
                db,
                schedule_id=schedule_id,
                tenant_id=TENANT_ID,
                worker_id="gate3-certifier-a",
            )
            assert dispatched is not None
            assert dispatched["status"] == "DISPATCHED"
            run_id = dispatched["dispatched_run_id"]
            assert run_id
            assert [event["event_type"] for event in dispatched["events"]] == [
                "SCHEDULE_CREATED",
                "SCHEDULE_CLAIMED",
                "SCHEDULE_DISPATCHED",
            ]
            await db.commit()

        # Second restart: replay verifies the hash chain and duplicate dispatch is idempotent.
        async with maker() as db:
            replay = await replay_schedule(db, schedule_id=schedule_id, tenant_id=TENANT_ID)
            assert replay is not None
            assert replay["status"] == "DISPATCHED"
            assert replay["projection_matches"] is True
            assert replay["event_count"] == 3
            assert replay["dispatched_run_id"] == run_id

            repeated = await dispatch_due_schedule(
                db,
                schedule_id=schedule_id,
                tenant_id=TENANT_ID,
                worker_id="gate3-certifier-b",
            )
            assert repeated is not None
            assert repeated["dispatched_run_id"] == run_id
            assert len(repeated["events"]) == 3
            run_count = await db.scalar(
                select(func.count()).select_from(ProductionOrchestrationRun).where(
                    ProductionOrchestrationRun.id == run_id
                )
            )
            assert run_count == 1

        # Identical schedule creation replays; conflicting content with the same key is rejected.
        async with maker() as db:
            replayed_create = await create_schedule(
                db,
                tenant_id=TENANT_ID,
                created_by=PRINCIPAL_ID,
                objective="Prepare a governed internal specialist review; external actions remain disabled",
                constraints={"gate": "scheduler", "external_actions": False},
                execution_mode="THINK_WORK_CHECK",
                budget_limits=None,
                run_at=due_at,
                idempotency_key=idempotency_key,
            )
            assert replayed_create["schedule_id"] == schedule_id

            with pytest.raises(SchedulerIdempotencyConflictError):
                await create_schedule(
                    db,
                    tenant_id=TENANT_ID,
                    created_by=PRINCIPAL_ID,
                    objective="Different objective must not reuse authority",
                    constraints={},
                    execution_mode="THINK_WORK_CHECK",
                    budget_limits=None,
                    run_at=due_at,
                    idempotency_key=idempotency_key,
                )

        # Cancellation is durable, replayable, and cannot later dispatch.
        future_at = datetime.now(UTC) + timedelta(hours=1)
        async with maker() as db:
            cancellable = await create_schedule(
                db,
                tenant_id=TENANT_ID,
                created_by=PRINCIPAL_ID,
                objective="Future bounded mission",
                constraints={},
                execution_mode="THINK_WORK_CHECK",
                budget_limits=None,
                run_at=future_at,
                idempotency_key="gate3-scheduler-cancel-0001",
            )
            cancelled = await cancel_schedule(
                db,
                schedule_id=cancellable["schedule_id"],
                tenant_id=TENANT_ID,
                actor_id=PRINCIPAL_ID,
                reason="Principal cancellation certification",
            )
            assert cancelled is not None
            assert cancelled["status"] == "CANCELLED"
            await db.commit()

        async with maker() as db:
            cancelled_replay = await replay_schedule(
                db,
                schedule_id=cancellable["schedule_id"],
                tenant_id=TENANT_ID,
            )
            assert cancelled_replay is not None
            assert cancelled_replay["status"] == "CANCELLED"
            assert cancelled_replay["event_count"] == 2
            with pytest.raises(SchedulerStateError):
                await dispatch_due_schedule(
                    db,
                    schedule_id=cancellable["schedule_id"],
                    tenant_id=TENANT_ID,
                    worker_id="gate3-certifier-c",
                    now=future_at + timedelta(minutes=1),
                )
    finally:
        await engine.dispose()
