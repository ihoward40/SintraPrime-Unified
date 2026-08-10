"""Portal test fixtures shared across database backends."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.mission_control_command import MissionControlCommand
from portal.models.user import Role, Tenant, User

_PG_RACE_MODULE = "portal.tests.test_mission_control_run_controls"
_TEST_UUID_NAMESPACE = uuid.UUID("8f443c9e-49c3-4d4e-8a87-dc61f4358870")


def _stable_uuid(label: str) -> str:
    """Return a deterministic UUID string for a human-readable fixture label."""

    return str(uuid.uuid5(_TEST_UUID_NAMESPACE, label))


@pytest.fixture(autouse=True)
def _postgresql_uuid_seed_adapter(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[None, None]:
    """Make Mission Control race fixtures valid for native PostgreSQL UUID columns.

    The historical race tests use readable identifiers such as ``tenant-pg``.
    ``PortableUUIDString`` intentionally becomes a native UUID on PostgreSQL, so
    those placeholders are invalid there. Patch only that test module, and only
    for PostgreSQL runs, with deterministic UUID-backed seed records.
    """

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql") or request.module.__name__ != _PG_RACE_MODULE:
        yield
        return

    async def seed_refs(
        session: AsyncSession,
        *,
        tenant_id: str = "tenant-1",
    ) -> tuple[str, str, str]:
        tenant_label = tenant_id
        persisted_tenant_id = _stable_uuid(f"tenant:{tenant_label}")
        role_id = _stable_uuid("role:canonical")
        user_id = _stable_uuid(f"user:{tenant_label}")
        command_id = _stable_uuid(f"command:{tenant_label}")

        tenant = Tenant(
            id=persisted_tenant_id,
            name=f"Tenant {tenant_label}",
            slug=tenant_label.replace("-", ""),
        )
        session.add(tenant)
        await session.flush()

        role = await session.get(Role, role_id)
        if role is None:
            role = Role(
                id=role_id,
                name="role-1",
                display_name="Role 1",
                description="seed role",
                is_system=True,
            )
            session.add(role)
            await session.flush()

        user = User(
            id=user_id,
            tenant_id=persisted_tenant_id,
            role_id=role.id,
            email=f"user-{tenant_label}@example.com",
            hashed_password="x",
            first_name="Test",
            last_name="User",
        )
        session.add(user)
        await session.flush()

        command = MissionControlCommand(
            id=command_id,
            tenant_id=persisted_tenant_id,
            requested_by=user.id,
            command_type="PAUSE_RUN",
            target_type="run",
            target_id=f"workflow-{tenant_label}",
            idempotency_key="idem-123456789012",
            request_hash="a" * 64,
            state="REFUSED",
        )
        session.add(command)
        await session.flush()
        await session.commit()

        return persisted_tenant_id, user_id, command_id

    monkeypatch.setattr(request.module, "_seed_refs", seed_refs)
    yield
