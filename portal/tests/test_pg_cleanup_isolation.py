"""Import-order regression tests for the Observatory PostgreSQL cleanup helper.

These prove that the cleanup-helper fixture is independent of global
``Base.metadata`` registration order. Importing ``portal.main`` (which
registers ~42 router models on the shared ``Base.metadata``) must NOT
change whether the cleanup fixture's schema setup succeeds or which tables
it cleans.

Root cause of G4.7 socket leak (PROVEN via A/B test): the original fixture
used ``Base.metadata.create_all(engine, tables=Base.metadata.tables.values())``
— i.e. the *entire* global metadata. When a SQLite-side module imported
``portal.main`` first, that pulled in ``notifications`` (FK to
``tenants``/``users``). On a database where those parent tables did not yet
exist, ``create_all`` raised ``ProgrammingError``; the fixture setup failed,
the ``yield`` never ran, and ``engine.dispose()`` never executed — leaking
the PostgreSQL socket to session-end GC.

The fix: the cleanup fixture uses an explicit, immutable
``OBSERVATORY_TEST_TABLES`` (Table-object) list. This test file locks that
behavior in.
"""
from __future__ import annotations

import asyncio
import gc
import os

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.tests.pg_test_isolation import (
    OBSERVATORY_TEST_TABLES,
    assert_pg_disposable,
    clean_all_observatory_tables,
    verify_pg_clean,
)

PG_URL = os.environ.get("GATE4_TEST_DATABASE_URL")
PG_MODE = os.environ.get("GATE4_TEST_MODE", "") == "true"

pytestmark = pytest.mark.skipif(
    not PG_URL or not PG_MODE,
    reason="PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL and GATE4_TEST_MODE=true)",
)


def _make_engine() -> AsyncEngine:
    assert_pg_disposable(PG_URL)
    return create_async_engine(PG_URL)


async def _explicit_scope_create_all(engine: AsyncEngine) -> None:
    """Mirror the cleanup fixture's explicit-scope schema creation."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=list(OBSERVATORY_TEST_TABLES)
            )
        )


async def _dispose_clean(engine: AsyncEngine) -> None:
    await clean_all_observatory_tables(engine)
    assert engine.pool.checkedout() == 0, "connection leaked during regression test"
    await engine.dispose()
    gc.collect()
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_explicit_scope_create_all_without_portal_main():
    """Explicit-scope create_all succeeds WITHOUT importing portal.main.

    This is the deterministic property: the fixture never iterates the full
    global metadata, so it cannot raise a FK-ordering error regardless of
    which models were imported.
    """
    engine = _make_engine()
    try:
        await _explicit_scope_create_all(engine)  # must not raise
        assert await verify_pg_clean(engine)
    finally:
        await _dispose_clean(engine)


@pytest.mark.asyncio
async def test_explicit_scope_create_all_after_portal_main_import():
    """Importing portal.main first must NOT make create_all raise.

    This is the exact regression: on the unfixed code, importing portal.main
    (which registers ``notifications`` with FKs to tenants/users) caused the
    full-metadata ``create_all`` to raise ProgrammingError and leak a socket.
    With explicit scope, setup succeeds.
    """
    import portal.main  # noqa: F401  — registers ~42 router models
    engine = _make_engine()
    try:
        await _explicit_scope_create_all(engine)  # must not raise
        assert await verify_pg_clean(engine)
    finally:
        await _dispose_clean(engine)


@pytest.mark.asyncio
async def test_explicit_scope_ignores_unrelated_temp_model():
    """Registering an unrelated temporary model must not affect cleanup scope."""
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import declarative_base

    TempBase = declarative_base()

    class TempUnrelated(TempBase):  # noqa: N801
        __tablename__ = "temp_unrelated_model"
        id = Column(Integer, primary_key=True)
        name = Column(String(50))

    # Attach the temp model to the SAME global Base.metadata to mimic a real
    # cross-module registration side effect.
    for tbl in TempBase.metadata.tables.values():
        tbl.to_metadata(Base.metadata)

    engine = _make_engine()
    try:
        # Explicit-scope create_all must ignore temp_unrelated_model entirely
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=list(OBSERVATORY_TEST_TABLES)
                )
            )
        assert await verify_pg_clean(engine)
        # temp_unrelated_model is not part of the explicit scope list
        assert TempUnrelated.__table__ not in OBSERVATORY_TEST_TABLES
    finally:
        Base.metadata.remove(TempUnrelated.__table__)
        await _dispose_clean(engine)


@pytest.mark.asyncio
async def test_cleanup_result_identical_regardless_of_import_order():
    """The cleaned table set is identical with or without portal.main imported."""
    async def _scope(import_main_first: bool) -> set[str]:
        if import_main_first:
            import portal.main  # noqa: F401
        engine = _make_engine()
        try:
            await _explicit_scope_create_all(engine)
            # Insert into one observatory table, then clean
            async with async_sessionmaker(engine, class_=AsyncSession)() as s:
                await s.execute(sa_text(
                    "INSERT INTO observatory_missions (id, title, status, "
                    "governance_gates_required, governance_gates_passed, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'X', 'QUEUED', '[]', '[]', now(), now())"
                ))
                await s.commit()
            await clean_all_observatory_tables(engine)
            cleaned = set()
            async with async_sessionmaker(engine, class_=AsyncSession)() as s:
                for t in OBSERVATORY_TEST_TABLES:
                    n = (await s.execute(sa_text(f"SELECT COUNT(*) FROM {t.name}"))).scalar()
                    if n == 0:
                        cleaned.add(t.name)
            return cleaned
        finally:
            await _dispose_clean(engine)

    without_main = await _scope(import_main_first=False)
    with_main = await _scope(import_main_first=True)
    assert without_main == with_main, (
        f"cleanup scope differs by import order: {without_main} != {with_main}"
    )
    expected = {t.name for t in OBSERVATORY_TEST_TABLES}
    assert without_main == expected
