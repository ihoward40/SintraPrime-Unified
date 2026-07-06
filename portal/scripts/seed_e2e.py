"""Seed E2E tenant, role, user, and a test document.

Run before Playwright E2E suite:
    python -m portal.scripts.seed_e2e

Environment variables:
    DATABASE_URL, JWT_SECRET_KEY, REDIS_URL, etc. mirror portal config.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

# Make the portal package importable from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.auth.password_handler import hash_password
from portal.database import AsyncSessionLocal
from portal.models.document import Document
from portal.models.user import Role, Tenant, User

E2E_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000e2e")
E2E_EMAIL = os.environ.get("E2E_EMAIL", "e2e-attorney@sintraprime.test")
E2E_PASSWORD = os.environ.get("E2E_PASSWORD", "E2E-Test-Pass-1234!")
E2E_ROLE = "ATTORNEY"


async def seed_e2e_data() -> None:
    """Create deterministic E2E tenant, role, and user if missing."""
    async with AsyncSessionLocal() as session:
        await _ensure_tenant(session)
        role = await _ensure_role(session)
        user = await _ensure_user(session, role)
        await _ensure_document(session, user)
        await session.commit()
        print(f"✅ E2E data seeded: {user.email} ({role.name})")


async def _ensure_tenant(session: AsyncSession) -> Tenant:
    tenant = await session.get(Tenant, str(E2E_TENANT_ID))
    if tenant is None:
        tenant = Tenant(
            id=str(E2E_TENANT_ID),
            name="E2E Tenant",
            slug="e2e-tenant",
            is_active=True,
        )
        session.add(tenant)
        await session.flush()
    return tenant


async def _ensure_role(session: AsyncSession) -> Role:
    result = await session.execute(select(Role).where(Role.name == E2E_ROLE))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(
            id=str(uuid.uuid4()),
            name=E2E_ROLE,
            display_name="E2E Attorney",
            is_system=True,
            description="Role used by Playwright E2E tests",
        )
        session.add(role)
        await session.flush()
    return role


async def _ensure_user(session: AsyncSession, role: Role) -> User:
    result = await session.execute(
        select(User).where(
            User.email == E2E_EMAIL,
            User.tenant_id == str(E2E_TENANT_ID),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            tenant_id=str(E2E_TENANT_ID),
            role_id=str(role.id),
            email=E2E_EMAIL,
            email_verified=True,
            hashed_password=hash_password(E2E_PASSWORD),
            first_name="E2E",
            last_name="Attorney",
            is_active=True,
            is_locked=False,
            failed_login_attempts=0,
        )
        session.add(user)
        await session.flush()
    else:
        user.hashed_password = hash_password(E2E_PASSWORD)
        user.is_active = True
        user.is_locked = False
        user.failed_login_attempts = 0
    return user


async def _ensure_document(session: AsyncSession, user: User) -> Document:
    """Create a tiny test document so the vault list is non-empty on first run."""
    result = await session.execute(
        select(Document).where(
            Document.uploaded_by == user.id,
            Document.tenant_id == str(E2E_TENANT_ID),
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        document = Document(
            id=str(uuid.uuid4()),
            tenant_id=str(E2E_TENANT_ID),
            uploaded_by=str(user.id),
            name="E2E Test Evidence.pdf",
            mime_type="application/pdf",
            file_extension="pdf",
            size_bytes=1234,
            storage_key=f"e2e/{uuid.uuid4()}.pdf",
            storage_bucket="sintraprime-documents",
            checksum_sha256="0" * 64,
            status="active",
            is_confidential=False,
            tags=["e2e", "evidence"],
        )
        session.add(document)
        await session.flush()
    return document


def main() -> None:
    asyncio.run(seed_e2e_data())


if __name__ == "__main__":
    main()
