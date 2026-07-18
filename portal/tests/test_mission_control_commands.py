"""Mission Control governed command substrate tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.routers import mission_control, mission_control_commands
from portal.services import mission_control_command_service
from portal.services.mission_control_command_service import (
    IDEMPOTENCY_KEY_MAX_LENGTH,
    IDEMPOTENCY_KEY_MIN_LENGTH,
    compute_event_hash,
)

TENANT_ID = "00000000-0000-0000-0000-000000000002"
USER_ID = "00000000-0000-0000-0000-000000000001"

SUPPORTED_COMMANDS = [
    "START_GOVERNED_RUN",
    "PAUSE_RUN",
    "RESUME_RUN",
    "CANCEL_RUN",
    "ASSIGN_AGENT",
    "REASSIGN_AGENT",
]

COMMAND_PERMISSIONS = {
    "START_GOVERNED_RUN": Permission.MISSION_RUN_START,
    "PAUSE_RUN": Permission.MISSION_RUN_PAUSE,
    "RESUME_RUN": Permission.MISSION_RUN_RESUME,
    "CANCEL_RUN": Permission.MISSION_RUN_CANCEL,
    "ASSIGN_AGENT": Permission.MISSION_AGENT_ASSIGN,
    "REASSIGN_AGENT": Permission.MISSION_AGENT_REASSIGN,
}


def _user(*permissions: Permission, tenant_id: str = TENANT_ID) -> CurrentUser:
    return CurrentUser(
        {
            "sub": USER_ID,
            "tenant_id": tenant_id,
            "role": "FIRM_ADMIN",
            "permissions": list(permissions),
        }
    )


def _body(command_type: str = "PAUSE_RUN", key: str = "idem-12345678901") -> dict:
    return {
        "command_type": command_type,
        "target_type": "run",
        "target_id": "run-123",
        "idempotency_key": key,
        "reason": "operator requested hold",
        "payload": {"nested": {"b": 2, "a": 1}},
        "metadata": {"source": "test"},
        "tenant_id": "attacker-tenant",
        "requested_by": "attacker-user",
        "role": "SUPER_ADMIN",
        "permissions": ["*"],
    }


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
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
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db: AsyncSession) -> TestClient:
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
        Permission.MISSION_RUN_PAUSE,
        Permission.MISSION_RUN_RESUME,
        Permission.MISSION_RUN_CANCEL,
        Permission.MISSION_AGENT_ASSIGN,
        Permission.MISSION_AGENT_REASSIGN,
        Permission.ADMIN_DASHBOARD,
    )
    return TestClient(app)


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count(model.id)))
    return result.scalar_one()


def test_authentication_is_required(db: AsyncSession) -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(mission_control_commands.router)
    response = TestClient(app).post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 401


def test_generic_command_create_permission_is_required(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: _user(Permission.MISSION_RUN_PAUSE)
    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 403


def test_command_specific_permission_is_required(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: _user(
        Permission.MISSION_COMMAND_CREATE,
        Permission.MISSION_RUN_START,
    )
    response = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN"))
    assert response.status_code == 403


def test_unsupported_command_type_is_rejected(client: TestClient) -> None:
    body = _body("EXECUTE_RUN")
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("command_type", "target_type"),
    [
        ("START_GOVERNED_RUN", "run"),
        ("START_GOVERNED_RUN", "mission"),
        ("PAUSE_RUN", "run"),
        ("RESUME_RUN", "run"),
        ("CANCEL_RUN", "run"),
        ("ASSIGN_AGENT", "run"),
        ("ASSIGN_AGENT", "task"),
        ("ASSIGN_AGENT", "mission"),
        ("REASSIGN_AGENT", "run"),
        ("REASSIGN_AGENT", "task"),
        ("REASSIGN_AGENT", "mission"),
    ],
)
def test_valid_command_target_combinations_are_accepted(
    client: TestClient,
    command_type: str,
    target_type: str,
) -> None:
    body = _body(command_type, key=f"compat-{command_type}-{target_type}-1234567890")
    body["target_type"] = target_type
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 201
    assert response.json()["state"] == "REFUSED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command_type", "target_type"),
    [
        ("START_GOVERNED_RUN", "task"),
        ("START_GOVERNED_RUN", "agent"),
        ("PAUSE_RUN", "agent"),
        ("PAUSE_RUN", "mission"),
        ("RESUME_RUN", "task"),
        ("CANCEL_RUN", "mission"),
        ("ASSIGN_AGENT", "agent"),
        ("REASSIGN_AGENT", "agent"),
    ],
)
async def test_invalid_command_target_combinations_return_422_without_persistence(
    client: TestClient,
    db: AsyncSession,
    command_type: str,
    target_type: str,
) -> None:
    body = _body(command_type, key=f"invalid-{command_type}-{target_type}-1234567890")
    body["target_type"] = target_type
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 422
    assert response.json()["detail"]["reason_code"] == "INVALID_COMMAND_TARGET"
    assert await _count(db, MissionControlCommand) == 0
    assert await _count(db, MissionControlCommandEvent) == 0
    assert await _count(db, AuditLog) == 0
    assert await _count(db, MissionControlCommandReceipt) == 0


def test_idempotency_key_below_minimum_returns_422(client: TestClient) -> None:
    body = _body(key="x" * (IDEMPOTENCY_KEY_MIN_LENGTH - 1))
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 422


def test_idempotency_key_exact_minimum_is_accepted(client: TestClient) -> None:
    body = _body(key="x" * IDEMPOTENCY_KEY_MIN_LENGTH)
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 201


def test_idempotency_key_exact_maximum_is_accepted(client: TestClient) -> None:
    body = _body(key="x" * IDEMPOTENCY_KEY_MAX_LENGTH)
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 201


def test_idempotency_key_above_maximum_returns_422(client: TestClient) -> None:
    body = _body(key="x" * (IDEMPOTENCY_KEY_MAX_LENGTH + 1))
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("command_type", SUPPORTED_COMMANDS)
async def test_supported_commands_persist_and_refuse(
    client: TestClient,
    db: AsyncSession,
    command_type: str,
) -> None:
    response = client.post(
        "/api/v1/mission-control/commands",
        json=_body(command_type, key=f"key-{command_type}-1234567890"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "REFUSED"
    assert body["reason_code"] == "COMMAND_EXECUTION_NOT_ENABLED"
    assert body["duplicate"] is False
    assert len(body["event_ids"]) == 3
    assert body["receipt_id"]
    assert body["audit_log_id"]

    result = await db.execute(
        select(MissionControlCommand).where(MissionControlCommand.id == body["command_id"])
    )
    command = result.scalar_one()
    assert command.command_type == command_type
    assert command.tenant_id == TENANT_ID
    assert command.requested_by == USER_ID
    assert command.state == "REFUSED"


@pytest.mark.asyncio
async def test_no_operational_mutation_routes_are_added(client: TestClient, db: AsyncSession) -> None:
    paths = {route.path for route in client.app.routes}
    assert "/runs/{id}/pause" not in paths
    assert "/runs/{id}/resume" not in paths
    assert "/runs/{id}/cancel" not in paths
    assert "/agents/{id}/assign" not in paths
    assert "/agents/{id}/reassign" not in paths

    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 201
    assert await _count(db, MissionControlCommand) == 1


@pytest.mark.asyncio
async def test_same_idempotency_key_and_request_replays(client: TestClient, db: AsyncSession) -> None:
    first = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", "same-key-1234567890"))
    second = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", "same-key-1234567890"))

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["command_id"] == first.json()["command_id"]
    assert await _count(db, MissionControlCommand) == 1
    assert await _count(db, MissionControlCommandReceipt) == 1
    assert await _count(db, AuditLog) == 1
    assert await _count(db, MissionControlCommandEvent) == 3


@pytest.mark.asyncio
async def test_idempotency_collision_reloads_winning_command(
    client: TestClient,
    db: AsyncSession,
    monkeypatch,
) -> None:
    key = "race-key-1234567890"
    first = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", key))
    assert first.status_code == 201

    original_find = mission_control_command_service._find_existing
    calls = 0

    async def _stale_initial_lookup(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return await original_find(*args, **kwargs)

    monkeypatch.setattr(
        mission_control_command_service,
        "_find_existing",
        _stale_initial_lookup,
    )
    replay = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", key))

    assert replay.status_code == 200
    assert replay.json()["duplicate"] is True
    assert replay.json()["command_id"] == first.json()["command_id"]
    assert await _count(db, MissionControlCommand) == 1
    assert await _count(db, MissionControlCommandEvent) == 3
    assert await _count(db, AuditLog) == 1
    assert await _count(db, MissionControlCommandReceipt) == 1


@pytest.mark.asyncio
async def test_idempotency_collision_with_changed_request_returns_conflict(
    client: TestClient,
    db: AsyncSession,
    monkeypatch,
) -> None:
    key = "race-conflict-1234567890"
    first = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", key))
    assert first.status_code == 201

    original_find = mission_control_command_service._find_existing
    calls = 0

    async def _stale_initial_lookup(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return await original_find(*args, **kwargs)

    monkeypatch.setattr(
        mission_control_command_service,
        "_find_existing",
        _stale_initial_lookup,
    )
    changed = _body("PAUSE_RUN", key)
    changed["target_id"] = "run-456"
    replay = client.post("/api/v1/mission-control/commands", json=changed)

    assert replay.status_code == 409
    assert replay.json()["detail"]["state"] == "DUPLICATE_CONFLICT"
    assert replay.json()["detail"]["reason_code"] == "IDEMPOTENCY_KEY_CONFLICT"
    assert await _count(db, MissionControlCommand) == 1
    assert await _count(db, MissionControlCommandEvent) == 3
    assert await _count(db, AuditLog) == 1
    assert await _count(db, MissionControlCommandReceipt) == 1


@pytest.mark.asyncio
async def test_same_idempotency_key_and_changed_request_conflicts(
    client: TestClient,
    db: AsyncSession,
) -> None:
    first = client.post("/api/v1/mission-control/commands", json=_body("PAUSE_RUN", "conflict-key-1234567890"))
    changed = _body("PAUSE_RUN", "conflict-key-1234567890")
    changed["target_id"] = "run-456"
    second = client.post("/api/v1/mission-control/commands", json=changed)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"]["state"] == "DUPLICATE_CONFLICT"
    assert await _count(db, MissionControlCommand) == 1


def test_missing_idempotency_key_returns_422(client: TestClient) -> None:
    body = _body()
    del body["idempotency_key"]
    response = client.post("/api/v1/mission-control/commands", json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tenant_and_actor_come_from_server_context(client: TestClient, db: AsyncSession) -> None:
    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 201
    result = await db.execute(select(MissionControlCommand))
    command = result.scalar_one()
    assert command.tenant_id == TENANT_ID
    assert command.requested_by == USER_ID


@pytest.mark.asyncio
async def test_command_event_hashes_are_deterministic(client: TestClient, db: AsyncSession) -> None:
    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 201

    result = await db.execute(
        select(MissionControlCommandEvent).order_by(MissionControlCommandEvent.sequence)
    )
    events = result.scalars().all()
    previous_hash = None
    for event in events:
        assert event.previous_hash == previous_hash
        assert event.event_hash == compute_event_hash(
            command_id=event.command_id,
            sequence=event.sequence,
            event_type=event.event_type,
            state=event.state,
            payload=event.payload,
            previous_hash=previous_hash,
        )
        previous_hash = event.event_hash


@pytest.mark.asyncio
async def test_audit_record_and_receipt_are_created(client: TestClient, db: AsyncSession) -> None:
    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 201
    body = response.json()
    assert await _count(db, AuditLog) == 1
    assert await _count(db, MissionControlCommandReceipt) == 1

    receipt_result = await db.execute(select(MissionControlCommandReceipt))
    receipt = receipt_result.scalar_one()
    assert receipt.id == body["receipt_id"]
    assert receipt.receipt_type == "REFUSAL"
    assert receipt.audit_log_id == body["audit_log_id"]


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_command(client: TestClient, db: AsyncSession, monkeypatch) -> None:
    async def _fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        "portal.services.mission_control_command_service.audit",
        _fail_audit,
    )
    error_client = TestClient(client.app, raise_server_exceptions=False)
    response = error_client.post("/api/v1/mission-control/commands", json=_body())

    assert response.status_code == 500
    assert await _count(db, MissionControlCommand) == 0
    assert await _count(db, MissionControlCommandEvent) == 0
    assert await _count(db, MissionControlCommandReceipt) == 0


@pytest.mark.asyncio
async def test_realtime_failure_does_not_change_refusal_outcome(
    client: TestClient,
    db: AsyncSession,
    monkeypatch,
) -> None:
    async def _fail_send(*args, **kwargs):
        raise RuntimeError("websocket unavailable")

    monkeypatch.setattr(
        "portal.services.mission_control_command_service.ws_manager.send_to_user",
        _fail_send,
    )
    response = client.post("/api/v1/mission-control/commands", json=_body())
    assert response.status_code == 201
    assert response.json()["state"] == "REFUSED"
    assert await _count(db, MissionControlCommand) == 1


def test_existing_mission_control_summary_contract_remains_unchanged(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(mission_control, "_check_database", lambda: {"status": "healthy", "type": "sqlite"})
    monkeypatch.setattr(mission_control, "_check_recovery_api", lambda: {"status": "healthy", "external_action": "locked"})
    monkeypatch.setattr(mission_control, "_check_evidence_platform", lambda: {"status": "healthy", "cases": [{"evidence_items": 3}]})
    monkeypatch.setattr(mission_control, "_check_scheduler", lambda: {"status": "healthy", "jobs": 4})
    monkeypatch.setattr(mission_control, "_check_agents", lambda: {"status": "healthy", "running": 2})

    response = client.get("/api/v1/mission-control/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["active_runs"] == {"value": None, "status": "unavailable"}
    assert body["pending_decisions"]["value"] is None
    assert body["kill_switch"]["value"] == "locked"
