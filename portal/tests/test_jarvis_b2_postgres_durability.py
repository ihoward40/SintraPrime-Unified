"""Focused tests for the database-backed B2 lease CAS boundary.

These tests are opt-in and require a real PostgreSQL URL. They intentionally
skip when no explicit test database is supplied; skipped means not certified.
"""
from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.services.jarvis_authority_lease import AuthorityLease, LeaseDeniedError
from portal.services.jarvis_durable_lease import DurableAuthorityLeaseStore

pytestmark = pytest.mark.postgresql


@pytest.fixture
def postgres_url():
    value = os.getenv("JARVIS_B2_POSTGRES_URL")
    if not value:
        pytest.skip("JARVIS_B2_POSTGRES_URL is required; PostgreSQL certification is not claimed")
    return value


def make_lease():
    return AuthorityLease.issue(
        tenant_id="tenant-a", principal_id="principal-a", capability_id="cap",
        capability_version="1", capability_contract_hash="contract", registry_revision=1,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", ttl=timedelta(minutes=5), now=datetime.now(UTC),
    )


def context(lease):
    return {
        "tenant_id": lease.tenant_id, "principal_id": lease.principal_id,
        "capability_id": lease.capability_id, "capability_version": lease.capability_version,
        "capability_contract_hash": lease.capability_contract_hash,
        "registry_revision": lease.registry_revision, "action_id": lease.action_id,
        "approval_id": lease.approval_id, "operation": lease.operation,
        "target": lease.target, "params_hash": lease.params_hash,
        "now": datetime.now(UTC),
    }


@pytest.mark.asyncio
async def test_real_postgres_concurrent_claim_has_one_winner(postgres_url):
    engine = create_async_engine(postgres_url, poolclass=None)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    original = make_lease()
    async with factory() as setup:
        await DurableAuthorityLeaseStore(setup).persist(original)
        await setup.commit()

    async def attempt():
        async with factory() as session:
            try:
                claimed = await DurableAuthorityLeaseStore(session).claim(original, **context(original))
                await session.commit()
                return claimed
            except LeaseDeniedError:
                await session.rollback()
                return None

    results = await asyncio.gather(attempt(), attempt())
    assert sum(result is not None for result in results) == 1
    await engine.dispose()
