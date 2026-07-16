"""
Shared PostgreSQL test isolation helpers.

Provides a single, authoritative table cleanup function used by all
PostgreSQL test modules to ensure order-independent test execution.

Usage in fixtures:
    from portal.tests.pg_test_isolation import (
        assert_pg_disposable,
        clean_all_observatory_tables,
    )

    @pytest_asyncio.fixture
    async def pg_engine():
        engine = create_async_engine(PG_URL, ...)
        assert_pg_disposable(PG_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=OBSERVATORY_TABLES)
        await clean_all_observatory_tables(engine)   # clean before
        yield engine
        await clean_all_observatory_tables(engine)    # clean after
        await engine.dispose()
"""

from __future__ import annotations

import os
from typing import Sequence

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from portal.models.observatory import (
    Agent,
    Approval,
    Artifact,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)


# ── All observatory tables in FK-safe deletion order ──────────────────────────
# Child tables first, parent tables last.
# This is the single authoritative list — no test module should maintain
# its own partial cleanup list.

OBSERVATORY_TABLES_CLEANUP_ORDER: tuple[str, ...] = (
    # Events must be deleted before run_heads because FK
    "observatory_events",
    # Kill-switch state references events via activation_event_id
    "observatory_kill_switch_state",
    # Incidents reference missions (mission_id) and events
    "observatory_incidents",
    # Approvals reference missions
    "observatory_approvals",
    # Evidence references missions
    "observatory_evidence",
    # Artifacts reference missions
    "observatory_artifacts",
    # Mission-agent association references missions
    "observatory_mission_agents",
    # Run heads (no FK to missions, but logically dependent)
    "observatory_run_heads",
    # Missions (parent)
    "observatory_missions",
    # Agents (parent — no FK dependencies)
    "observatory_agents",
)

# Tables from other portal modules that hardening tests may create
EXTRA_CLEANUP_TABLES: tuple[str, ...] = (
    "audit_logs",
    "audit_records",
)

# ── Explicit observatory Table objects ──────────────────────────────────────
# These are the ONLY tables a focused Observatory cleanup-helper fixture may
# create or truncate. Using an explicit, immutable Table-object list — rather
# than Base.metadata.tables.values() — keeps the test independent of import
# order: importing portal.main (which registers ~42 router models on the
# global Base.metadata) must NOT change which tables a PG cleanup fixture
# creates. See G4.7_EXECUTION_GUARD.md decision evidence.
OBSERVATORY_TEST_TABLES: tuple = (
    ObservatoryEvent.__table__,
    ObservatoryRunHead.__table__,
    Mission.__table__,
    MissionAgent.__table__,
    Approval.__table__,
    KillSwitchState.__table__,
    Evidence.__table__,
    Artifact.__table__,
    Incident.__table__,
    Agent.__table__,
)

# Prohibited (non-disposable) database names
_PROHIBITED_DB_NAMES = frozenset({
    "production", "prod", "staging", "stage", "sintraprime",
})

# Approved disposable database name patterns
_DISPOSABLE_PATTERNS = (
    "gate4_test",
    "gate4_clean",
    "sintraprime_test",
    "test_",
    "tmp_test",
)


def assert_pg_disposable(url: str | None) -> None:
    """Verify the PostgreSQL URL points to a disposable test database.

    Raises RuntimeError if the database name is not in the approved list
    or is in the prohibited list.
    """
    if not url:
        raise RuntimeError("No PostgreSQL URL provided")

    # Extract database name from URL
    # Formats: postgresql+asyncpg://user:pass@host:port/dbname
    db_part = url.rsplit("/", 1)[-1]
    # Remove query params
    if "?" in db_part:
        db_part = db_part.split("?")[0]

    if db_part in _PROHIBITED_DB_NAMES:
        raise RuntimeError(
            f"Refusing to use non-disposable database '{db_part}'. "
            f"Prohibited: {_PROHIBITED_DB_NAMES}"
        )

    is_disposable = any(
        db_part == pattern or db_part.startswith(pattern)
        for pattern in _DISPOSABLE_PATTERNS
    )
    if not is_disposable:
        raise RuntimeError(
            f"Database '{db_part}' does not match any approved disposable pattern. "
            f"Allowed: {', '.join(_DISPOSABLE_PATTERNS)}"
        )


async def clean_all_observatory_tables(engine: AsyncEngine) -> None:
    """Delete all rows from observatory tables using TRUNCATE CASCADE.

    This is the single authoritative cleanup function. All PostgreSQL
    test fixtures must call this before and after yielding.

    The TRUNCATE / verification scope is the explicit ``OBSERVATORY_TEST_TABLES``
    set — the same tables the cleanup fixture creates. Using an explicit,
    immutable list (rather than the full global ``Base.metadata``) keeps
    cleanup independent of which models other test modules imported first.
    See G4.7_EXECUTION_GUARD.md decision evidence.

    Uses TRUNCATE ... RESTART IDENTITY CASCADE on PostgreSQL for:
    - Atomic cleanup (single statement, no partial states)
    - FK-safe (CASCADE handles dependencies)
    - Sequence reset (RESTART IDENTITY)

    Falls back to individual DELETE statements for non-PostgreSQL engines.
    """
    all_tables = tuple(t.name for t in OBSERVATORY_TEST_TABLES)

    async with engine.begin() as conn:
        # Try TRUNCATE first (PostgreSQL only)
        try:
            # Build a single TRUNCATE statement for all tables
            table_list = ", ".join(all_tables)
            await conn.execute(sa_text(
                f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"
            ))
            return
        except Exception:
            pass  # Not PostgreSQL — fall through to DELETE

        # Fallback: individual DELETE statements for SQLite etc.
        for table in all_tables:
            try:
                await conn.execute(sa_text(f"DELETE FROM {table}"))
            except Exception:
                pass  # Table may not exist


async def verify_pg_clean(engine: AsyncEngine) -> bool:
    """Verify that all observatory tables are empty.

    Returns True if all tables are empty (or don't exist),
    False if any table has rows.

    Iterates the explicit ``OBSERVATORY_TEST_TABLES`` set — the same
    tables the cleanup fixture creates and truncates — so verification is
    consistent with the schema scope regardless of global metadata state.
    """
    factory = async_sessionmaker(engine, class_=AsyncSession)
    async with factory() as session:
        for table in OBSERVATORY_TEST_TABLES:
            try:
                result = await session.execute(
                    sa_text(f"SELECT COUNT(*) FROM {table.name}")
                )
                count = result.scalar()
                if count and count > 0:
                    return False
            except Exception:
                pass  # Table doesn't exist
    return True
