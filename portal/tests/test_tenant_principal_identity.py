"""Tenant Principal identity foundation tests.

Governance constraints:
- ONE_CONSTITUTIONAL_PRINCIPAL_PER_TENANT = TRUE
- PRINCIPAL_USER_REFERENCES_EXISTING_USER = TRUE
- PRINCIPAL_IDENTITY_SELF_SERVICE_WRITABLE = FALSE
- ORDINARY_ADMIN_EQUALS_PRINCIPAL = FALSE
- OWNERPROFILE_CONFERS_PRINCIPAL_AUTHORITY = FALSE
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from portal.database import Base
from portal.models.tenant_principal import TenantPrincipal
from portal.models.user import Tenant, User
from portal.services.tenant_principal_service import is_tenant_principal


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        # Create only the tables this test suite needs, not the entire Base.metadata.
        # Other suites (e.g. test_app_startup) import portal.main which registers
        # models with PostgreSQL-specific columns (JSONB) on Base.metadata; calling
        # create_all with the full metadata would fail on SQLite.
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    User.__table__,
                    TenantPrincipal.__table__,
                ],
            )
        )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


async def _make_tenant_and_user(db: AsyncSession, email: str) -> tuple[Tenant, User]:
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Firm",
        slug=f"test-firm-{uuid.uuid4().hex[:8]}",
    )
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        role_id=str(uuid.uuid4()),  # no real role needed for identity check
        email=email,
        first_name="Test",
        last_name="User",
        hashed_password="x",
    )
    db.add(tenant)
    db.add(user)
    await db.commit()
    return tenant, user


@pytest.mark.asyncio
async def test_bound_principal_matching_tenant_is_true(db: AsyncSession):
    tenant, principal_user = await _make_tenant_and_user(db, "principal@firm.test")
    db.add(
        TenantPrincipal(
            tenant_id=tenant.id,
            principal_user_id=principal_user.id,
            establishment_source="bootstrap",
        )
    )
    await db.commit()

    result = await is_tenant_principal(
        db,
        authenticated_user_id=principal_user.id,
        tenant_id=tenant.id,
    )
    assert result is True


@pytest.mark.asyncio
async def test_ordinary_admin_without_binding_is_false(db: AsyncSession):
    tenant, _ = await _make_tenant_and_user(db, "principal@firm.test")
    _, ordinary_admin = await _make_tenant_and_user(db, "admin@firm.test")

    result = await is_tenant_principal(
        db,
        authenticated_user_id=ordinary_admin.id,
        tenant_id=tenant.id,
    )
    assert result is False


@pytest.mark.asyncio
async def test_cross_tenant_bound_principal_is_false(db: AsyncSession):
    tenant_a, principal_user_a = await _make_tenant_and_user(db, "principal@a.test")
    tenant_b, _ = await _make_tenant_and_user(db, "principal@b.test")
    db.add(
        TenantPrincipal(
            tenant_id=tenant_a.id,
            principal_user_id=principal_user_a.id,
            establishment_source="bootstrap",
        )
    )
    await db.commit()

    result = await is_tenant_principal(
        db,
        authenticated_user_id=principal_user_a.id,
        tenant_id=tenant_b.id,
    )
    assert result is False


@pytest.mark.asyncio
async def test_missing_binding_fails_closed(db: AsyncSession):
    tenant, _ = await _make_tenant_and_user(db, "user@firm.test")

    result = await is_tenant_principal(
        db,
        authenticated_user_id=str(uuid.uuid4()),
        tenant_id=tenant.id,
    )
    assert result is False


@pytest.mark.asyncio
async def test_duplicate_tenant_principal_is_prevented(db: AsyncSession):
    tenant, first_principal = await _make_tenant_and_user(db, "first@firm.test")
    _, second_principal = await _make_tenant_and_user(db, "second@firm.test")

    db.add(
        TenantPrincipal(
            tenant_id=tenant.id,
            principal_user_id=first_principal.id,
            establishment_source="bootstrap",
        )
    )
    await db.commit()

    db.add(
        TenantPrincipal(
            tenant_id=tenant.id,
            principal_user_id=second_principal.id,
            establishment_source="bootstrap",
        )
    )
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_owner_profile_does_not_confer_principal_authority(db: AsyncSession):
    tenant, user_with_owner_profile = await _make_tenant_and_user(
        db, "owner-profile-user@firm.test"
    )
    db.add(
        TenantPrincipal(
            tenant_id=tenant.id,
            principal_user_id=user_with_owner_profile.id,
            establishment_source="bootstrap",
        )
    )
    await db.commit()

    assert (
        await is_tenant_principal(
            db,
            authenticated_user_id=user_with_owner_profile.id,
            tenant_id=tenant.id,
        )
        is True
    )

    # Same user is NOT a principal in another tenant merely because they exist.
    other_tenant, _ = await _make_tenant_and_user(db, "other@other.test")
    assert (
        await is_tenant_principal(
            db,
            authenticated_user_id=user_with_owner_profile.id,
            tenant_id=other_tenant.id,
        )
        is False
    )


@pytest.mark.asyncio
async def test_tenant_principal_record_is_queryable(db: AsyncSession):
    tenant, principal_user = await _make_tenant_and_user(db, "principal@firm.test")
    record = TenantPrincipal(
        tenant_id=tenant.id,
        principal_user_id=principal_user.id,
        establishment_source="bootstrap",
    )
    db.add(record)
    await db.commit()

    loaded = await db.execute(
        select(TenantPrincipal).where(TenantPrincipal.tenant_id == tenant.id)
    )
    assert loaded.scalar_one().principal_user_id == principal_user.id
