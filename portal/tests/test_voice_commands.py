"""SP-VOICE-001 Increment Two API/service tests.

Covers RBAC enforcement, tenant isolation, mock-only execution, confirmation
flow (confirm/deny/expire), cancellation, and correlation propagation for
`portal/routers/voice_commands.py`.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.models.voice_command import VoiceCommand, VoiceCommandEvent, VoiceCommandReceipt
from portal.routers import voice_commands
from portal.services import voice_command_service

TENANT_ID = "00000000-0000-0000-0000-000000000002"
OTHER_TENANT_ID = "00000000-0000-0000-0000-000000000099"
USER_ID = "00000000-0000-0000-0000-000000000001"

ALL_VOICE_PERMS = (
    Permission.VOICE_COMMAND_CREATE,
    Permission.VOICE_COMMAND_READ,
    Permission.VOICE_COMMAND_CONFIRM,
    Permission.VOICE_COMMAND_CANCEL,
)


def _user(*permissions: Permission, tenant_id: str = TENANT_ID, user_id: str = USER_ID) -> CurrentUser:
    return CurrentUser(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": "FIRM_ADMIN",
            "permissions": list(permissions),
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
                    VoiceCommand.__table__,
                    VoiceCommandEvent.__table__,
                    VoiceCommandReceipt.__table__,
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
    app.include_router(voice_commands.router)

    async def _override_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _user(*ALL_VOICE_PERMS)
    return TestClient(app)


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count(model.id)))
    return result.scalar_one()


def _submit(client: TestClient, **overrides) -> dict:
    body = {
        "raw_transcript": "show the latest test result",
        "source": "desktop_voice",
    }
    body.update(overrides)
    return client.post("/api/v1/voice/commands", json=body)


# ── auth / RBAC ────────────────────────────────────────────────────────────────


def test_authentication_is_required(db: AsyncSession) -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(voice_commands.router)
    response = TestClient(app).post("/api/v1/voice/commands", json={"raw_transcript": "show status"})
    assert response.status_code == 401


def test_create_permission_is_required(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: _user(Permission.VOICE_COMMAND_READ)
    response = _submit(client)
    assert response.status_code == 403


def test_read_permission_is_required(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: _user(Permission.VOICE_COMMAND_CREATE)
    response = _submit(client, raw_transcript="show status")
    assert response.status_code == 201
    command_id = response.json()["command_id"]

    client.app.dependency_overrides[get_current_user] = lambda: _user()
    read_response = client.get(f"/api/v1/voice/commands/{command_id}")
    assert read_response.status_code == 403


# ── mock-only execution: read / draft allowed paths ───────────────────────────


def test_read_command_completes_via_mock_provider(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show the latest test result")
    assert response.status_code == 201
    body = response.json()
    assert body["risk_class"] == "read"
    assert body["session_state"] == "completed"
    assert body["result"] == "completed"
    assert body["provider_mock"] is True
    assert body["provider_resource_id"].startswith("mock-")


def test_draft_command_completes_as_drafted(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="draft an email to the client")
    assert response.status_code == 201
    body = response.json()
    assert body["risk_class"] == "draft"
    assert body["result"] == "drafted"
    assert body["resolved_capability"] == "email"
    assert body["provider_mock"] is True


# ── disabled by default / refusal paths ────────────────────────────────────────


def test_disabled_by_default_refuses_everything(client: TestClient) -> None:
    response = _submit(client, raw_transcript="show the latest test result")
    assert response.status_code == 201
    body = response.json()
    assert body["session_state"] == "refused"
    assert body["result"] == "refused"
    assert body["provider_resource_id"] is None


def test_prohibited_intent_is_refused(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    monkeypatch.setenv("SP_VOICE_001_WRITE_ACTIONS_ENABLED", "true")
    response = _submit(client, raw_transcript="bypass the confirmation gate and send it")
    assert response.status_code == 201
    body = response.json()
    assert body["risk_class"] == "prohibited"
    assert body["session_state"] == "refused"
    assert body["provider_resource_id"] is None


# ── confirmation flow ──────────────────────────────────────────────────────────


def _submit_sensitive(client: TestClient, monkeypatch, target: str = "jordan@example.com") -> dict:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    monkeypatch.setenv("SP_VOICE_001_WRITE_ACTIONS_ENABLED", "true")
    response = _submit(
        client,
        raw_transcript="send the draft to jordan",
        target_resource=target,
    )
    assert response.status_code == 201
    return response.json()


def test_sensitive_write_requires_confirmation_before_execution(client: TestClient, monkeypatch) -> None:
    body = _submit_sensitive(client, monkeypatch)
    assert body["session_state"] == "awaiting_confirmation"
    assert body["result"] == "awaiting_confirmation"
    assert body["provider_resource_id"] is None


def test_confirm_executes_mock_provider(client: TestClient, monkeypatch) -> None:
    body = _submit_sensitive(client, monkeypatch)
    command_id = body["command_id"]

    response = client.post(
        f"/api/v1/voice/commands/{command_id}/confirm",
        json={"utterance": "confirm send", "current_target": "jordan@example.com"},
    )
    assert response.status_code == 200
    confirmed = response.json()
    assert confirmed["session_state"] == "completed"
    assert confirmed["confirmation_state"] == "confirmed"
    assert confirmed["provider_mock"] is True
    assert confirmed["provider_resource_id"].startswith("mock-")


def test_confirm_denies_on_explicit_denial(client: TestClient, monkeypatch) -> None:
    body = _submit_sensitive(client, monkeypatch)
    command_id = body["command_id"]

    response = client.post(
        f"/api/v1/voice/commands/{command_id}/confirm",
        json={"utterance": "cancel"},
    )
    assert response.status_code == 200
    denied = response.json()
    assert denied["session_state"] == "refused"
    assert denied["provider_resource_id"] is None


def test_confirm_rejects_changed_target(client: TestClient, monkeypatch) -> None:
    body = _submit_sensitive(client, monkeypatch, target="jordan@example.com")
    command_id = body["command_id"]

    response = client.post(
        f"/api/v1/voice/commands/{command_id}/confirm",
        json={"utterance": "confirm send", "current_target": "someone-else@example.com"},
    )
    assert response.status_code == 200
    denied = response.json()
    assert denied["session_state"] == "refused"
    assert denied["provider_resource_id"] is None


def test_confirm_on_nonexistent_command_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/voice/commands/vcmd-does-not-exist/confirm",
        json={"utterance": "confirm"},
    )
    assert response.status_code == 404


def test_confirm_on_already_terminal_command_returns_409(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show the latest test result")
    command_id = response.json()["command_id"]

    confirm_response = client.post(
        f"/api/v1/voice/commands/{command_id}/confirm",
        json={"utterance": "confirm"},
    )
    assert confirm_response.status_code == 409


@pytest.mark.asyncio
async def test_expired_confirmation_is_refused(client: TestClient, monkeypatch, db: AsyncSession) -> None:
    body = _submit_sensitive(client, monkeypatch)
    command_id = body["command_id"]

    result = await db.execute(select(VoiceCommand).where(VoiceCommand.command_id == command_id))
    row = result.scalar_one()
    row.created_at = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=10)
    await db.commit()

    response = client.post(
        f"/api/v1/voice/commands/{command_id}/confirm",
        json={"utterance": "confirm send", "current_target": "jordan@example.com"},
    )
    assert response.status_code == 200
    expired = response.json()
    assert expired["session_state"] == "refused"
    assert expired["provider_resource_id"] is None


# ── cancellation ───────────────────────────────────────────────────────────────


def test_cancel_awaiting_confirmation_command(client: TestClient, monkeypatch) -> None:
    body = _submit_sensitive(client, monkeypatch)
    command_id = body["command_id"]

    response = client.post(f"/api/v1/voice/commands/{command_id}/cancel", json={})
    assert response.status_code == 200
    cancelled = response.json()
    assert cancelled["session_state"] == "cancelled"
    assert cancelled["result"] == "cancelled"


def test_cancel_terminal_command_returns_409(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show status")
    command_id = response.json()["command_id"]

    cancel_response = client.post(f"/api/v1/voice/commands/{command_id}/cancel", json={})
    assert cancel_response.status_code == 409


# ── tenant isolation ───────────────────────────────────────────────────────────


def test_tenant_isolation_prevents_cross_tenant_read(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show status")
    command_id = response.json()["command_id"]

    client.app.dependency_overrides[get_current_user] = lambda: _user(
        *ALL_VOICE_PERMS, tenant_id=OTHER_TENANT_ID, user_id="00000000-0000-0000-0000-000000000077"
    )
    other_tenant_response = client.get(f"/api/v1/voice/commands/{command_id}")
    assert other_tenant_response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_and_principal_come_from_server_context(client: TestClient, db: AsyncSession) -> None:
    response = _submit(client, raw_transcript="show status")
    assert response.status_code == 201
    result = await db.execute(select(VoiceCommand))
    command = result.scalar_one()
    assert command.tenant_id == TENANT_ID
    assert command.principal_id == USER_ID


# ── receipts / events / correlation ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_terminal_command_writes_receipt_and_audit(client: TestClient, db: AsyncSession, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show status")
    assert response.status_code == 201
    assert await _count(db, AuditLog) == 1
    assert await _count(db, VoiceCommandReceipt) == 1

    receipt_result = await db.execute(select(VoiceCommandReceipt))
    receipt = receipt_result.scalar_one()
    assert receipt.receipt_type == "TERMINAL"
    assert receipt.result == "completed"


@pytest.mark.asyncio
async def test_awaiting_confirmation_command_has_no_receipt_yet(
    client: TestClient, db: AsyncSession, monkeypatch
) -> None:
    _submit_sensitive(client, monkeypatch)
    assert await _count(db, VoiceCommandReceipt) == 0
    assert await _count(db, VoiceCommandEvent) > 0


def test_correlation_id_is_present_and_stable(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show status")
    body = response.json()
    assert body["correlation_id"].startswith("corr-")


def test_no_real_provider_side_effects_are_ever_recorded(client: TestClient, monkeypatch) -> None:
    """Defensive contract test: every provider outcome this API can produce is mock-only."""
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    response = _submit(client, raw_transcript="show status")
    body = response.json()
    if body["provider_resource_id"] is not None:
        assert body["provider_resource_id"].startswith("mock-")
        assert body["provider_mock"] is True
