"""Mission Control permission provisioning tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from fastapi import Response

from portal.auth.jwt_handler import decode_access_token
from portal.database import Base
from portal.models.user import Permission, Role, RolePermission, Tenant, User
from portal.routers.auth import _build_login_response
from portal.services.permission_provisioning import (
    DriftSeverity,
    PermissionSyncError,
    inspect_permission_manifest,
    plan_permission_manifest,
    sync_permission_manifest,
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
                    Permission.__table__,
                    RolePermission.__table__,
                    User.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def _seed_roles(session: AsyncSession) -> None:
    session.add_all(
        [
            Role(id="role-super", name="SUPER_ADMIN", display_name="Super Admin", is_system=True),
            Role(id="role-firm", name="FIRM_ADMIN", display_name="Firm Admin", is_system=True),
            Role(id="role-attorney", name="ATTORNEY", display_name="Attorney", is_system=True),
            Role(id="role-paralegal", name="PARALEGAL", display_name="Paralegal", is_system=True),
            Role(id="role-accountant", name="ACCOUNTANT", display_name="Accountant", is_system=True),
            Role(id="role-client", name="CLIENT", display_name="Client", is_system=True),
            Role(id="role-viewer", name="VIEWER", display_name="Viewer", is_system=True),
            Role(id="role-custom", name="CUSTOM", display_name="Custom", is_system=False),
        ]
    )
    await session.flush()


@pytest.mark.asyncio
async def test_permission_sync_creates_missing_permissions_and_role_grants(db: AsyncSession):
    await _seed_roles(db)
    db.add(Permission(id="perm-1", name="case:read", resource="case", action="read"))
    await db.commit()

    report = await sync_permission_manifest(db)
    assert report.manifest_hash
    assert report.drift_detected is True
    assert report.permissions_created >= 1
    assert report.role_grants_created >= 1
    assert report.role_grants_removed == 0

    refreshed = await inspect_permission_manifest(db)
    assert refreshed.manifest_hash == report.manifest_hash
    assert refreshed.drift_detected is False
    assert refreshed.permissions_missing == []

    role_perm_rows = await db.execute(select(RolePermission))
    assert role_perm_rows.scalars().all()


@pytest.mark.asyncio
async def test_permission_sync_is_idempotent(db: AsyncSession):
    await _seed_roles(db)
    first = await sync_permission_manifest(db)
    await db.commit()
    second = await sync_permission_manifest(db)
    await db.commit()

    assert first.manifest_hash == second.manifest_hash
    assert second.permissions_created == 0
    assert second.role_grants_created == 0
    assert second.drift_detected is False


@pytest.mark.asyncio
async def test_synced_role_permissions_feed_login_and_refresh_access_tokens(db: AsyncSession):
    await _seed_roles(db)
    db.add(Tenant(id="tenant-1", name="Acme", slug="acme"))
    await db.commit()

    await sync_permission_manifest(db)
    await db.commit()

    db.add(
        User(
            id="user-1",
            tenant_id="tenant-1",
            role_id="role-attorney",
            email="attorney@example.com",
            hashed_password="hashed-password",
            first_name="Ada",
            last_name="Lawson",
            is_active=True,
        )
    )
    await db.commit()

    result = await db.execute(
        select(User)
        .options(selectinload(User.role_ref).selectinload(Role.permissions))
        .where(User.id == "user-1")
    )
    user = result.scalar_one()

    login_response, _refresh_token, _family_id = _build_login_response(user, Response())
    access_payload = decode_access_token(login_response.access_token)
    assert "mission_control:command_create" in access_payload["permissions"]
    assert "mission_control:run_pause" in access_payload["permissions"]

    attorney_permissions = [permission for permission in user.role_ref.permissions if permission.name != "mission_control:run_pause"]
    user.role_ref.permissions = attorney_permissions
    await db.commit()

    refreshed_user_result = await db.execute(
        select(User)
        .options(selectinload(User.role_ref).selectinload(Role.permissions))
        .where(User.id == "user-1")
    )
    refreshed_user = refreshed_user_result.scalar_one()
    refreshed_login_response, _refresh_token_2, _family_id_2 = _build_login_response(refreshed_user, Response())
    refreshed_payload = decode_access_token(refreshed_login_response.access_token)
    assert "mission_control:command_create" in refreshed_payload["permissions"]
    assert "mission_control:run_pause" not in refreshed_payload["permissions"]


@pytest.mark.asyncio
async def test_permission_sync_preserves_custom_roles(db: AsyncSession):
    await _seed_roles(db)
    db.add(Permission(id="perm-x", name="custom:read", resource="custom", action="read"))
    await db.flush()
    db.add(RolePermission(role_id="role-custom", permission_id="perm-x"))
    await db.commit()

    await sync_permission_manifest(db)
    await db.commit()

    custom_grant = await db.execute(
        select(RolePermission).where(RolePermission.role_id == "role-custom")
    )
    assert custom_grant.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_permission_dry_run_returns_same_manifest_hash_without_writes(db: AsyncSession):
    await _seed_roles(db)
    db.add(Permission(id="perm-2", name="case:update", resource="case", action="update"))
    await db.commit()
    before_permissions = await db.execute(select(Permission))
    before_roles = await db.execute(select(Role))
    before_grants = await db.execute(select(RolePermission))
    baseline_counts = (
        len(before_permissions.scalars().all()),
        len(before_roles.scalars().all()),
        len(before_grants.scalars().all()),
    )

    report = await plan_permission_manifest(db)
    after_permissions = await db.execute(select(Permission))
    after_roles = await db.execute(select(Role))
    after_grants = await db.execute(select(RolePermission))

    assert report.manifest_hash
    assert report.mode.value == "DRY_RUN"
    assert report.drift_detected is True
    assert report.current_state["permissions"]
    assert report.proposed_state["permissions"]
    assert (
        len(after_permissions.scalars().all()),
        len(after_roles.scalars().all()),
        len(after_grants.scalars().all()),
    ) == baseline_counts


@pytest.mark.asyncio
async def test_permission_sync_flags_ambiguous_system_role_identity(db: AsyncSession):
    db.add(
        Role(id="role-firm-custom", name="FIRM_ADMIN", display_name="Firm Admin Custom", is_system=False)
    )
    await db.commit()

    report = await inspect_permission_manifest(db)
    assert report.severity == DriftSeverity.BLOCKING
    assert "FIRM_ADMIN" in report.ambiguous_roles

    with pytest.raises(PermissionSyncError):
        await sync_permission_manifest(db)
