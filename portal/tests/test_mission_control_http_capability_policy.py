"""Canonical HTTP tests for server-owned capability selection and approval policy."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_execution import Mission, Run
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.routers import mission_control, mission_control_commands
from portal.services import mission_control_capability_policy as policy_module
from portal.services.durable_orchestration_authority import DurableOrchestrationAuthority
from portal.services.mission_control_capability_policy import CapabilityDecision

TENANT_ID = "00000000-0000-0000-0000-000000000002"
USER_ID = "00000000-0000-0000-0000-000000000001"


def _user(*permissions: Permission, tenant_id: str = TENANT_ID) -> CurrentUser:
    return CurrentUser(
        {
            "sub": USER_ID,
            "tenant_id": tenant_id,
            "role": "FIRM_ADMIN",
            "permissions": list(permissions),
        }
    )


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    PermissionModel.__table__,
                    RolePermission.__table__,
                    User.__table__,
                    UserPermissionAssoc.__table__,
                    AuditLog.__table__,
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    Mission.__table__,
                    Run.__table__,
                ],
            )
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db: AsyncSession, monkeypatch) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(mission_control.router)
    app.include_router(mission_control_commands.router)

    async def _override_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _user(
        Permission.MISSION_COMMAND_CREATE,
        Permission.MISSION_RUN_START,
        Permission.MISSION_COMMAND_READ,
    )
    return TestClient(app)


def _patch_authority(monkeypatch, capability: str, decision: CapabilityDecision):
    """Install a test-only authority with a registered capability and a policy classification."""
    monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {capability: decision})
    engine = AsyncMock()
    if decision == CapabilityDecision.DIRECT_ALLOWED:
        engine.start_workflow.return_value = "workflow-1"
    engine._registered = {capability: lambda _context, _input: _input}
    authority = DurableOrchestrationAuthority(engine)
    monkeypatch.setattr(mission_control_commands, "mission_control_execution_authority", authority)
    return engine


@pytest.mark.asyncio
async def test_http_approval_required_reaches_server_classified_capability(client, db, monkeypatch):
    engine = _patch_authority(monkeypatch, "protected.approval", CapabilityDecision.APPROVAL_REQUIRED)

    mission = Mission(tenant_id=TENANT_ID, created_by=USER_ID, workflow_type="protected.approval", status="ACTIVE")
    db.add(mission)
    await db.flush()

    response = client.post(
        "/api/v1/mission-control/commands",
        json={
            "command_type": "START_GOVERNED_RUN",
            "target_type": "mission",
            "target_id": mission.mission_id,
            "idempotency_key": "http-approval-required-0001",
            "payload": {
                "require_approval": False,
                "workflow_type": "client-choice",
                "input_data": {" legitimate": "value"},
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "APPROVAL_REQUIRED"
    assert body["run_id"] is not None
    assert body["execution_ref"] is None
    engine.start_workflow.assert_not_awaited()


@pytest.mark.asyncio
async def test_http_direct_allowed_ignores_client_workflow_type(client, db, monkeypatch):
    engine = _patch_authority(monkeypatch, "protected.real", CapabilityDecision.DIRECT_ALLOWED)

    mission = Mission(tenant_id=TENANT_ID, created_by=USER_ID, workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()

    response = client.post(
        "/api/v1/mission-control/commands",
        json={
            "command_type": "START_GOVERNED_RUN",
            "target_type": "mission",
            "target_id": mission.mission_id,
            "idempotency_key": "http-direct-allowed-0001",
            "payload": {
                "require_approval": True,
                "workflow_type": "client-choice",
                "input_data": {" legitimate": "value"},
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "COMPLETED"
    assert body["execution_ref"] == "workflow-1"
    assert engine.start_workflow.await_count == 1
    assert engine.start_workflow.await_args.args[0] == "protected.real"


@pytest.mark.asyncio
async def test_http_unbound_mission_is_refused(client, db, monkeypatch):
    _patch_authority(monkeypatch, "protected.real", CapabilityDecision.DIRECT_ALLOWED)

    mission = Mission(tenant_id=TENANT_ID, created_by=USER_ID, workflow_type=None, status="ACTIVE")
    db.add(mission)
    await db.flush()

    response = client.post(
        "/api/v1/mission-control/commands",
        json={
            "command_type": "START_GOVERNED_RUN",
            "target_type": "mission",
            "target_id": mission.mission_id,
            "idempotency_key": "http-unbound-0001",
            "payload": {},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "REFUSED"
    assert body["reason_code"] == "MISSION_CAPABILITY_UNBOUND"
