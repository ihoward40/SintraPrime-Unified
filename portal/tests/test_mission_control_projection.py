"""Mission Control Foundation projection tests.

Tests:
1. Sigma gate — BLOCKED state, DISABLED controls, is_cancellation_blocked.
2. Projection service — tenant isolation for list_commands, get_command,
   list_run_controls, get_run_control, get_causation_chain.
3. Read-only API enforcement — no POST/PUT/PATCH/DELETE on projection routes.
4. Router integration — intent list, detail, run-control list, detail,
   causation chain, sigma-gate endpoints with auth and tenant scoping.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.routers import mission_control
from portal.services.sigma_gate import (
    GATE_ID,
    GATE_STATE,
    get_cancellation_status,
    get_gate_status,
    is_cancellation_blocked,
)

TENANT_A = "00000000-0000-0000-0000-000000000002"
TENANT_B = "00000000-0000-0000-0000-000000000003"
USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "00000000-0000-0000-0000-000000000004"


def _user(
    tenant_id: str = TENANT_A,
    user_id: str = USER_A,
    *permissions: Permission,
) -> CurrentUser:
    return CurrentUser(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": "FIRM_ADMIN",
            "permissions": list(permissions) or [Permission.MISSION_COMMAND_READ],
        }
    )


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
                    MissionControlRunControl.__table__,
                    MissionControlRunControlEvent.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db: AsyncSession) -> TestClient:
    app = FastAPI()
    app.include_router(mission_control.router)

    async def _override_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _user()
    return TestClient(app)


# ── Sigma gate tests ──────────────────────────────────────────────────────────


class TestSigmaGate:
    def test_gate_id_constant(self):
        assert GATE_ID == "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE"

    def test_gate_state_blocked(self):
        assert GATE_STATE == "BLOCKED"

    def test_get_gate_status_blocked(self):
        status = get_gate_status()
        assert status.gate_id == GATE_ID
        assert status.state == "BLOCKED"
        assert status.cancellation_controls == "DISABLED"
        assert status.blocking_phase_3b is True
        assert len(status.criteria) == 5

    def test_get_cancellation_status_all_disabled(self):
        status = get_cancellation_status()
        assert status.execution_scoped == "DISABLED"
        assert status.tenant_scoped == "DISABLED"
        assert status.platform_break_glass == "DISABLED"
        assert "BLOCKED" in status.reason

    def test_is_cancellation_blocked_true(self):
        assert is_cancellation_blocked() is True


# ── Sigma gate API ────────────────────────────────────────────────────────────


class TestSigmaGateAPI:
    def test_sigma_gate_endpoint(self, client: TestClient):
        response = client.get("/api/v1/mission-control/sigma-gate")
        assert response.status_code == 200
        body = response.json()
        assert body["gate"]["gate_id"] == GATE_ID
        assert body["gate"]["state"] == "BLOCKED"
        assert body["execution_scoped"] == "DISABLED"
        assert body["tenant_scoped"] == "DISABLED"
        assert body["platform_break_glass"] == "DISABLED"


# ── Read-only API enforcement ────────────────────────────────────────────────


class TestReadOnlyEnforcement:
    """Verify that no new mutation routes were introduced.

    The pre-existing POST /api/v1/mission-control/commands endpoint is
    refusal-only (returns COMMAND_EXECUTION_NOT_ENABLED) and remains
    unchanged. No new POST/PUT/PATCH/DELETE projection route was added.
    No cancellation, approval, retry, replay, lease, or dispatch mutation
    was added.
    """

    def test_no_post_on_intents(self, client: TestClient):
        response = client.post("/api/v1/mission-control/intents", json={})
        assert response.status_code == 405

    def test_no_put_on_intents(self, client: TestClient):
        response = client.put("/api/v1/mission-control/intents/abc", json={})
        assert response.status_code == 405

    def test_no_delete_on_intents(self, client: TestClient):
        response = client.delete("/api/v1/mission-control/intents/abc")
        assert response.status_code == 405

    def test_no_post_on_run_controls(self, client: TestClient):
        response = client.post("/api/v1/mission-control/run-controls", json={})
        assert response.status_code == 405

    def test_no_post_on_sigma_gate(self, client: TestClient):
        response = client.post("/api/v1/mission-control/sigma-gate", json={})
        assert response.status_code == 405

    def test_no_patch_on_intents(self, client: TestClient):
        response = client.patch("/api/v1/mission-control/intents/abc", json={})
        assert response.status_code == 405


# ── Projection service tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_commands_tenant_isolation(db: AsyncSession):
    """Commands from tenant A are not visible to tenant B."""
    from portal.services.mission_control_projection_service import list_commands

    # Seed a command for tenant A
    cmd_a = MissionControlCommand(
        id="cmd-a-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-key-tenant-a-001",
        request_hash="hash-a",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd_a)
    await db.flush()

    # Seed a command for tenant B
    cmd_b = MissionControlCommand(
        id="cmd-b-001",
        tenant_id=TENANT_B,
        requested_by=USER_B,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-002",
        idempotency_key="idem-key-tenant-b-001",
        request_hash="hash-b",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd_b)
    await db.flush()

    # Tenant A sees only its commands
    result_a = await list_commands(db, tenant_id=TENANT_A)
    assert result_a.total == 1
    assert result_a.items[0].id == "cmd-a-001"

    # Tenant B sees only its commands
    result_b = await list_commands(db, tenant_id=TENANT_B)
    assert result_b.total == 1
    assert result_b.items[0].id == "cmd-b-001"


@pytest.mark.asyncio
async def test_get_command_cross_tenant_returns_none(db: AsyncSession):
    """get_command returns None when the command belongs to another tenant."""
    from portal.services.mission_control_projection_service import get_command

    cmd = MissionControlCommand(
        id="cmd-x-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-key-x-001",
        request_hash="hash-x",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Tenant B cannot see tenant A's command
    result = await get_command(db, tenant_id=TENANT_B, command_id="cmd-x-001")
    assert result is None

    # Tenant A can see its own command
    result = await get_command(db, tenant_id=TENANT_A, command_id="cmd-x-001")
    assert result is not None
    assert result.id == "cmd-x-001"


@pytest.mark.asyncio
async def test_list_run_controls_tenant_isolation(db: AsyncSession):
    """Run-controls from tenant A are not visible to tenant B."""
    from portal.services.mission_control_projection_service import list_run_controls

    rc_a = MissionControlRunControl(
        id="rc-a-001",
        tenant_id=TENANT_A,
        workflow_id="wf-a-001",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc_a)
    await db.flush()

    rc_b = MissionControlRunControl(
        id="rc-b-001",
        tenant_id=TENANT_B,
        workflow_id="wf-b-001",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc_b)
    await db.flush()

    result_a = await list_run_controls(db, tenant_id=TENANT_A)
    assert result_a.total == 1
    assert result_a.items[0].id == "rc-a-001"

    result_b = await list_run_controls(db, tenant_id=TENANT_B)
    assert result_b.total == 1
    assert result_b.items[0].id == "rc-b-001"


@pytest.mark.asyncio
async def test_get_run_control_cross_tenant_returns_none(db: AsyncSession):
    """get_run_control returns None when run-control belongs to another tenant."""
    from portal.services.mission_control_projection_service import get_run_control

    rc = MissionControlRunControl(
        id="rc-x-001",
        tenant_id=TENANT_A,
        workflow_id="wf-x-001",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    result = await get_run_control(db, tenant_id=TENANT_B, run_control_id="rc-x-001")
    assert result is None

    result = await get_run_control(db, tenant_id=TENANT_A, run_control_id="rc-x-001")
    assert result is not None
    assert result.id == "rc-x-001"


@pytest.mark.asyncio
async def test_get_causation_chain_cross_tenant_returns_none(db: AsyncSession):
    """Causation chain returns None when command belongs to another tenant."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-chain-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-chain-001",
        request_hash="hash-chain",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Tenant B cannot access
    chain = await get_causation_chain(db, tenant_id=TENANT_B, command_id="cmd-chain-001")
    assert chain is None

    # Tenant A can access
    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-chain-001")
    assert chain is not None
    assert chain.command_id == "cmd-chain-001"


@pytest.mark.asyncio
async def test_causation_chain_includes_events_and_receipts(db: AsyncSession):
    """Causation chain links command events and receipts."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-cc-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-cc-001",
        request_hash="hash-cc",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    event = MissionControlCommandEvent(
        id="evt-cc-001",
        command_id="cmd-cc-001",
        sequence=1,
        event_type="RECEIVED",
        state="RECEIVED",
        payload={},
        previous_hash=None,
        event_hash="evt-hash-001",
    )
    db.add(event)
    await db.flush()

    receipt = MissionControlCommandReceipt(
        id="rct-cc-001",
        command_id="cmd-cc-001",
        receipt_type="REFUSAL",
        receipt_hash="rct-hash-001",
        evidence_refs=[],
    )
    db.add(receipt)
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-cc-001")
    assert chain is not None
    assert len(chain.links) >= 2
    source_types = {link.source_type for link in chain.links}
    assert "command_event" in source_types
    assert "receipt" in source_types


# ── Router integration tests ─────────────────────────────────────────────────


class TestRouterIntents:
    def test_list_intents_empty(self, client: TestClient):
        response = client.get("/api/v1/mission-control/intents")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_get_intent_not_found(self, client: TestClient):
        response = client.get("/api/v1/mission-control/intents/nonexistent")
        assert response.status_code == 404

    def test_list_intents_with_data(self, client: TestClient, db: AsyncSession):
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            cmd = MissionControlCommand(
                id="cmd-router-001",
                tenant_id=TENANT_A,
                requested_by=USER_A,
                command_type="PAUSE_RUN",
                target_type="run",
                target_id="run-001",
                idempotency_key="idem-router-001",
                request_hash="hash-router",
                state="REFUSED",
                payload={},
                metadata_json={},
            )
            db.add(cmd)
            loop.run_until_complete(db.flush())

            response = client.get("/api/v1/mission-control/intents")
            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 1
            assert body["items"][0]["id"] == "cmd-router-001"
            assert body["items"][0]["command_type"] == "PAUSE_RUN"
        finally:
            loop.close()

    def test_list_run_controls_empty(self, client: TestClient):
        response = client.get("/api/v1/mission-control/run-controls")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_get_run_control_not_found(self, client: TestClient):
        response = client.get("/api/v1/mission-control/run-controls/nonexistent")
        assert response.status_code == 404

    def test_causation_chain_not_found(self, client: TestClient):
        response = client.get("/api/v1/mission-control/intents/nonexistent/causation-chain")
        assert response.status_code == 404


# ── Auth enforcement ──────────────────────────────────────────────────────────


class TestAuthEnforcement:
    def test_intents_require_auth(self):
        app = FastAPI()
        app.include_router(mission_control.router)
        # No dependency override for get_current_user — should fail
        client = TestClient(app)
        response = client.get("/api/v1/mission-control/intents")
        assert response.status_code in (401, 403)

    def test_sigma_gate_requires_auth(self):
        app = FastAPI()
        app.include_router(mission_control.router)
        client = TestClient(app)
        response = client.get("/api/v1/mission-control/sigma-gate")
        assert response.status_code in (401, 403)
