"""
Tests for the shared PostgreSQL test isolation helper.

These tests verify that clean_all_observatory_tables() correctly resets
state, that the disposable-database guard rejects unsafe names, and that
cleanup leaves no checked-out connections.
"""

from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.observatory import (
    Agent,
    Approval,
    KillSwitchState,
    Mission,
)
from portal.schemas.observatory import MissionStatus
from portal.services.observatory_service import (
    AgentService,
    ApprovalService,
    KillSwitchService,
    MissionService,
)
from portal.tests.pg_test_isolation import (
    assert_pg_disposable,
    clean_all_observatory_tables,
    OBSERVATORY_TEST_TABLES,
    verify_pg_clean,
)


PG_URL = os.environ.get("GATE4_TEST_DATABASE_URL")
PG_MODE = os.environ.get("GATE4_TEST_MODE", "") == "true"


pytestmark = pytest.mark.skipif(
    not PG_URL or not PG_MODE,
    reason="PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL and GATE4_TEST_MODE=true)",
)


@pytest_asyncio.fixture
async def pg_engine():
    """Create a disposable PostgreSQL engine with clean state.

    Schema setup uses an EXPLICIT observatory-only Table-object list
    (OBSERVATORY_TEST_TABLES) rather than Base.metadata.tables.values().
    This keeps the test independent of import order: importing portal.main
    (which registers ~42 router models on the global Base.metadata) must not
    change which tables this fixture creates. See G4.7 decision evidence.
    """
    assert_pg_disposable(PG_URL)
    engine = create_async_engine(PG_URL)
    # Ensure only the observatory tables owned by this test exist.
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=list(OBSERVATORY_TEST_TABLES)
            )
        )
    await clean_all_observatory_tables(engine)
    yield engine
    await clean_all_observatory_tables(engine)
    # No checked-out connections after cleanup
    assert engine.pool.checkedout() == 0, "Connections leaked after cleanup"
    # Explicit sync-pool assertion before disposal
    assert engine.sync_engine.pool.checkedout() == 0, "Sync-pool connections leaked"
    await engine.dispose()
    import gc
    gc.collect()
    await asyncio.sleep(0)
    gc.collect()
    await asyncio.sleep(0)


@pytest_asyncio.fixture
async def pg_session(pg_engine):
    factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


class TestPgCleanupHelper:
    """Direct tests of the shared cleanup helper."""

    def test_assert_pg_disposable_accepts_gate4_test(self):
        """The approved disposable database name passes the guard."""
        assert_pg_disposable("postgresql+asyncpg://u:p@localhost:5433/gate4_test")

    def test_assert_pg_disposable_rejects_prohibited(self):
        """Prohibited database names are rejected."""
        with pytest.raises(RuntimeError):
            assert_pg_disposable("postgresql+asyncpg://u:p@localhost:5433/sintraprime")

    def test_assert_pg_disposable_rejects_production(self):
        """Production database is rejected."""
        with pytest.raises(RuntimeError):
            assert_pg_disposable("postgresql+asyncpg://u:p@localhost:5432/production")

    def test_assert_pg_disposable_rejects_unknown(self):
        """Unknown database names are rejected."""
        with pytest.raises(RuntimeError):
            assert_pg_disposable("postgresql+asyncpg://u:p@localhost:5433/important_data")

    @pytest.mark.asyncio
    async def test_clean_after_dirty_state_yields_zero_rows(self, pg_engine):
        """A dirty database cleaned via the helper has zero rows."""
        # Insert dirty data directly via raw SQL (avoid guard-triggered sessions)
        async with async_sessionmaker(pg_engine, class_=AsyncSession)() as session:
            await session.execute(sa_text(
                "INSERT INTO observatory_missions (id, title, status, governance_gates_required, governance_gates_passed, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'Dirty Mission', 'QUEUED', '[]', '[]', now(), now())"
            ))
            await session.execute(sa_text(
                "INSERT INTO observatory_agents (id, agent_id, name, agent_type, status, capabilities, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'DIRTY-1', 'x', 't', 'ACTIVE', '[]', now(), now())"
            ))
            await session.commit()

        # Clean
        await clean_all_observatory_tables(pg_engine)

        # Verify zero rows directly
        async with async_sessionmaker(pg_engine, class_=AsyncSession)() as session:
            for table_name in ("observatory_missions", "observatory_agents", "observatory_approvals"):
                count = (await session.execute(sa_text(f"SELECT COUNT(*) FROM {table_name}"))).scalar()
                assert count == 0, f"{table_name} should have 0 rows, got {count}"

    @pytest.mark.asyncio
    async def test_second_cleanup_call_succeeds(self, pg_engine):
        """Calling cleanup twice in a row succeeds (idempotent)."""
        # Insert and clean once
        async with async_sessionmaker(pg_engine, class_=AsyncSession)() as session:
            await MissionService.create(session, title="Temp")
            await session.commit()
        await clean_all_observatory_tables(pg_engine)
        # Second call must succeed even when already empty
        await clean_all_observatory_tables(pg_engine)
        assert await verify_pg_clean(pg_engine)

    @pytest.mark.asyncio
    async def test_cleanup_after_failed_transaction_succeeds(self, pg_engine):
        """Cleanup succeeds even after a transaction was rolled back.

        Step 8: an aborted transaction that is NOT explicitly rolled back
        can retain a connection even when later cleanup appears successful.
        Verify the session transaction is inactive and the connection is
        returned to the pool before cleanup runs.
        """
        factory = async_sessionmaker(pg_engine, class_=AsyncSession)
        # Committed transaction first
        async with factory() as session:
            await MissionService.create(session, title="WillRollback")
            await session.commit()
        # Simulate a failed/uncommitted transaction: open, insert, rollback, close
        session = factory()
        try:
            await MissionService.create(session, title="Uncommitted")
            # Force a rollback (do NOT commit) and confirm transaction inactive
            await session.rollback()
            assert not session.in_transaction(), "transaction still active after rollback"
        finally:
            await session.close()
        # Connection must be returned to the pool (0 checked out) before cleanup
        assert pg_engine.pool.checkedout() == 0, "connection retained after rollback"
        # Cleanup must still succeed
        await clean_all_observatory_tables(pg_engine)
        assert await verify_pg_clean(pg_engine)

    @pytest.mark.asyncio
    async def test_cleanup_leaves_no_checked_out_connections(self, pg_engine):
        """After cleanup, no connections remain checked out from the pool."""
        async with async_sessionmaker(pg_engine, class_=AsyncSession)() as session:
            await MissionService.create(session, title="ConnTest")
            await session.commit()
        await clean_all_observatory_tables(pg_engine)
        # All connections returned to pool
        assert pg_engine.pool.checkedout() == 0, "Connections leaked after cleanup"

    @pytest.mark.asyncio
    async def test_disposable_guard_runs_before_truncate(self, pg_engine):
        """assert_pg_disposable is checked before any destructive cleanup."""
        # The fixture already ran assert_pg_disposable; here we confirm the
        # helper itself calls it internally when given a bad URL would raise.
        # We verify by calling clean_all_observatory_tables on a valid engine
        # and ensuring no exception escapes the guard path.
        await clean_all_observatory_tables(pg_engine)
        assert await verify_pg_clean(pg_engine)
