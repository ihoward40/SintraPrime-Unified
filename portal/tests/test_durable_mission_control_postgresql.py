"""PostgreSQL certification for durable orchestration and Mission Control authority."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from portal import models as _models  # noqa: F401
from portal.auth.rbac import CurrentUser, Permission
from portal.scripts.postgresql_bootstrap import apply_migrations
from portal.services.durable_orchestration_authority import (
    approve_durable_run,
    get_durable_run,
)
from portal.services.mission_control_command_service import (
    CommandSubmission,
    CommandTargetType,
    CommandType,
)
from portal.services.mission_control_execution_service import (
    ACTIVATION_MODE,
    submit_durable_orchestration_command,
)
from portal.services.orchestration import orchestrator

pytestmark = pytest.mark.postgresql

TENANT_ID = "00000000-0000-0000-0000-00000000d285"
PRINCIPAL_ID = "00000000-0000-0000-0000-000000000d85"


def _database_url() -> str:
    raw = os.environ.get("DURABLE_MISSION_CONTROL_DATABASE_URL")
    if not raw:
        pytest.skip("Durable Mission Control PostgreSQL URL not configured")
    return raw


def _principal() -> CurrentUser:
    return CurrentUser(
        {
            "sub": PRINCIPAL_ID,
            "tenant_id": TENANT_ID,
            "role": "SUPER_ADMIN",
            "permissions": [
                Permission.MISSION_COMMAND_CREATE.value,
                Permission.MISSION_COMMAND_ADMIN.value,
                Permission.MISSION_RUN_START.value,
                Permission.MISSION_RUN_CANCEL.value,
                Permission.ORCHESTRATION_CREATE.value,
                Permission.ORCHESTRATION_READ.value,
                Permission.ORCHESTRATION_APPROVE.value,
                Permission.ORCHESTRATION_CANCEL.value,
            ],
        }
    )


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
            text(
                """
                INSERT INTO tenants (id, name, slug)
                VALUES (CAST(:tenant_id AS uuid), :name, :slug)
                """
            ),
            {"tenant_id": TENANT_ID, "name": "Durable Gate", "slug": "durable-gate"},
        )
        await db.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, role_id, email, first_name, last_name, hashed_password
                )
                VALUES (
                    CAST(:principal_id AS uuid),
                    CAST(:tenant_id AS uuid),
                    CAST(:role_id AS uuid),
                    :email,
                    :first_name,
                    :last_name,
                    :hashed_password
                )
                """
            ),
            {
                "principal_id": PRINCIPAL_ID,
                "tenant_id": TENANT_ID,
                "role_id": str(role_id),
                "email": "durable-gate@example.invalid",
                "first_name": "Durable",
                "last_name": "Principal",
                "hashed_password": "synthetic-not-a-real-password",
            },
        )
        await db.commit()


@pytest.mark.asyncio
async def test_mission_control_start_replay_restart_approval_and_cancel_are_durable() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        principal = _principal()
        start = CommandSubmission(
            command_type=CommandType.START_GOVERNED_RUN,
            target_type=CommandTargetType.MISSION,
            target_id="durable-certification",
            idempotency_key="durable-mission-control-start-0001",
            reason="Gate 2 PostgreSQL certification",
            payload={
                "activation_mode": ACTIVATION_MODE,
                "objective": (
                    "Implement code with specialist review, then send external communications "
                    "only after Principal approval"
                ),
                "constraints": {"gate": "durable-mission-control"},
            },
            metadata={"source": "gate-2-certification"},
        )

        async with maker() as db:
            result, run_id = await submit_durable_orchestration_command(db, start, principal)
            assert result.command.state == "COMPLETED"
            assert run_id
            await db.commit()

        orchestrator.RUNS.clear()
        async with maker() as db:
            persisted = await get_durable_run(db, run_id=run_id, tenant_id=TENANT_ID)
            assert persisted is not None
            assert persisted["status"] == "APPROVAL_REQUIRED"
            assert persisted["approvals"][0]["status"] == "REQUESTED"
            assert len(persisted["routing_decisions"]) >= 2
            assert all(decision["node_id"] for decision in persisted["routing_decisions"])

            replay, replay_ref = await submit_durable_orchestration_command(db, start, principal)
            assert replay.duplicate is True
            assert replay_ref == run_id
            assert replay.command.id == result.command.id
            await db.commit()

        orchestrator.RUNS.clear()
        async with maker() as db:
            approved = await approve_durable_run(
                db,
                run_id=run_id,
                tenant_id=TENANT_ID,
                principal_id=PRINCIPAL_ID,
                approved=True,
                reason="Exact bounded result reviewed",
            )
            assert approved is not None
            assert approved["status"] == "COMPLETED"
            assert approved["approvals"][0]["status"] == "APPROVED"
            assert approved["events"][-1]["event_type"] == "APPROVAL_DECIDED"
            assert approved["events"][-1]["previous_event_hash"] == approved["events"][-2]["event_hash"]
            await db.commit()

        second_start = CommandSubmission(
            command_type=CommandType.START_GOVERNED_RUN,
            target_type=CommandTargetType.MISSION,
            target_id="durable-cancel-certification",
            idempotency_key="durable-mission-control-start-0002",
            reason="Create cancellable run",
            payload={
                "activation_mode": ACTIVATION_MODE,
                "objective": (
                    "Prepare external communication draft and require Principal approval before send"
                ),
            },
            metadata={"source": "gate-2-certification"},
        )
        async with maker() as db:
            second_result, second_run_id = await submit_durable_orchestration_command(
                db, second_start, principal
            )
            assert second_result.command.state == "COMPLETED"
            assert second_run_id
            await db.commit()

        orchestrator.RUNS.clear()
        cancel = CommandSubmission(
            command_type=CommandType.CANCEL_RUN,
            target_type=CommandTargetType.RUN,
            target_id=second_run_id,
            idempotency_key="durable-mission-control-cancel-0001",
            reason="Principal cancels durable run",
            payload={"activation_mode": ACTIVATION_MODE},
            metadata={"source": "gate-2-certification"},
        )
        async with maker() as db:
            cancelled_command, cancelled_ref = await submit_durable_orchestration_command(
                db, cancel, principal
            )
            assert cancelled_command.command.state == "COMPLETED"
            assert cancelled_ref == second_run_id
            await db.commit()

        orchestrator.RUNS.clear()
        async with maker() as db:
            cancelled = await get_durable_run(
                db, run_id=second_run_id, tenant_id=TENANT_ID
            )
            assert cancelled is not None
            assert cancelled["status"] == "CANCELLED"
            assert cancelled["events"][-1]["event_type"] == "RUN_CANCELLED"
    finally:
        await engine.dispose()