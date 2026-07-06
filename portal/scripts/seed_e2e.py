"""Seed E2E tenant, role, user, and a test document.

Run before Playwright E2E suite:
    python -m portal.scripts.seed_e2e

Environment variables:
    DATABASE_URL, JWT_SECRET_KEY, REDIS_URL, etc. must point at the E2E target.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import select

from portal.auth.password_handler import hash_password
from portal.database import AsyncSessionLocal, init_db
from portal.models.user import Permission, Role, RolePermission, Tenant, User

E2E_TENANT_ID = uuid.UUID("e2e00000-0000-0000-0000-000000000001")
E2E_USER_ID = uuid.UUID("e2e00000-0000-0000-0000-000000000002")
E2E_ROLE_ID = uuid.UUID("e2e00000-0000-0000-0000-000000000003")
E2E_EMAIL = "e2e-attorney@sintraprime.test"
E2E_PASSWORD = "E2E-Test-Pass-1234!"


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create E2E tenant if missing
        tenant = await db.execute(select(Tenant).where(Tenant.id == E2E_TENANT_ID))
        tenant = tenant.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                id=E2E_TENANT_ID,
                name="E2E Test Firm",
                slug="e2e-test-firm",
                is_active=True,
            )
            db.add(tenant)

        # Create E2E attorney role with DOC_READ + DOC_UPLOAD
        role = await db.execute(select(Role).where(Role.id == E2E_ROLE_ID))
        role = role.scalar_one_or_none()
        if not role:
            role = Role(
                id=E2E_ROLE_ID,
                name="E2E_ATTORNEY",
                display_name="E2E Attorney",
                description="Attorney role scoped for end-to-end tests",
                is_system=False,
            )
            db.add(role)
            await db.flush()

        # Ensure permissions exist
        needed = {"document:read", "document:upload", "case:read"}
        existing = await db.execute(select(Permission).where(Permission.name.in_(needed)))
        existing_names = {p.name for p in existing.scalars().all()}
        for name in needed - existing_names:
            resource, action = name.split(":", 1)
            db.add(Permission(name=name, resource=resource, action=action))
        await db.flush()

        # Grant role permissions
        perms = await db.execute(select(Permission).where(Permission.name.in_(needed)))
        for perm in perms.scalars().all():
            assoc = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if not assoc.scalar_one_or_none():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        # Create test user
        user = await db.execute(select(User).where(User.id == E2E_USER_ID))
        user = user.scalar_one_or_none()
        if not user:
            user = User(
                id=E2E_USER_ID,
                tenant_id=E2E_TENANT_ID,
                role_id=role.id,
                email=E2E_EMAIL,
                email_verified=True,
                hashed_password=hash_password(E2E_PASSWORD),
                first_name="E2E",
                last_name="Attorney",
                is_active=True,
                is_locked=False,
                failed_login_attempts=0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(user)

        await db.commit()
        print(f"seeded tenant={E2E_TENANT_ID} role={role.name} user={E2E_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
