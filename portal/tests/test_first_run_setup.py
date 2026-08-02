from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from portal.auth.jwt_handler import decode_access_token
from portal.auth.rbac import Permission
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User
from portal.routers import auth


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
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
                    AuditLog.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as db:
        yield db
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def _setup_payload() -> dict[str, str]:
    return {
        "owner_name": "Ada Lawson",
        "email": "owner@example.com",
        "password": "OwnerPass729!",
        "organization_name": "Acme Legal Ops",
    }


@pytest.mark.asyncio
async def test_first_run_setup_available_only_before_users_exist(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    status_before = await client.get("/api/v1/auth/setup/status")
    assert status_before.status_code == 200
    assert status_before.json() == {"available": True}

    response = await client.post("/api/v1/auth/setup", json=await _setup_payload())
    assert response.status_code == 201

    status_after = await client.get("/api/v1/auth/setup/status")
    assert status_after.status_code == 200
    assert status_after.json() == {"available": False}

    blocked = await client.post("/api/v1/auth/setup", json=await _setup_payload())
    assert blocked.status_code == 409

    users = (await session.execute(select(User))).scalars().all()
    tenants = (await session.execute(select(Tenant))).scalars().all()
    assert len(users) == 1
    assert len(tenants) == 1


@pytest.mark.asyncio
async def test_first_run_setup_creates_owner_with_voice_permissions(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    response = await client.post("/api/v1/auth/setup", json=await _setup_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["role"] == "FIRM_ADMIN"

    payload = decode_access_token(body["access_token"])
    assert payload["tenant_id"] == body["tenant_id"]
    assert Permission.VOICE_COMMAND_CREATE.value in payload["permissions"]
    assert Permission.VOICE_COMMAND_READ.value in payload["permissions"]
    assert Permission.VOICE_COMMAND_CONFIRM.value in payload["permissions"]
    assert Permission.VOICE_COMMAND_CANCEL.value in payload["permissions"]

    owner = await session.scalar(
        select(User)
        .options(selectinload(User.role_ref).selectinload(Role.permissions))
        .where(User.email == "owner@example.com")
    )
    assert owner is not None
    assert owner.email_verified is True
    assert owner.role_ref.name == "FIRM_ADMIN"


@pytest.mark.asyncio
async def test_first_run_owner_can_use_normal_login(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/setup", json=await _setup_payload())

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "OwnerPass729!"},
    )
    assert response.status_code == 200
    payload = decode_access_token(response.json()["access_token"])
    assert payload["role"] == "FIRM_ADMIN"
    assert Permission.VOICE_COMMAND_CREATE.value in payload["permissions"]
