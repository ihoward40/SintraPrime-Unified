"""
Migration Backfill Integration Test (G4.6.7).

Tests that the migration chain correctly backfills hash_version=1 for
pre-existing events and sets server_default=2 for new events.

This test uses real Alembic migrations (NOT create_all()) and passes
a caller-supplied connection through config.attributes, guaranteeing
the migration runs against the exact temporary database.

A migration test guard refuses to run against non-disposable databases.
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import UTC, datetime
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from portal.services.event_canonicalization import compute_hash_v1
from portal.services.observatory_service import EventService

from alembic.config import Config
from alembic import command
import pytest_asyncio


# ── Migration test guard ─────────────────────────────────────────────────────
from portal.tests.test_db_guard import validate_test_database_url, DatabaseIsolationError


def _check_sqlite_is_temporary(db_path: str) -> None:
    """Refuse to migrate a non-temporary SQLite database."""
    # Allow any path under the OS temp directory or containing 'test' or 'backfill'
    normalized = os.path.normcase(os.path.normpath(db_path))
    tmp = os.path.normcase(os.path.normpath(tempfile.gettempdir()))
    if normalized.startswith(tmp):
        return
    basename = os.path.basename(normalized)
    for disposable in DISPOSABLE_DB_NAMES:
        if disposable in basename:
            return
    raise RuntimeError(
        f"Migration test guard: refusing to migrate non-disposable SQLite database: {db_path}"
    )


def _check_pg_is_disposable(url: str) -> None:
    """Refuse to migrate a non-disposable PostgreSQL database (using centralized guard)."""
    if "postgresql" not in url:
        return
    try:
        validate_test_database_url(url, skip_marker_check=True, skip_reachability=True)
    except DatabaseIsolationError as e:
        raise RuntimeError(str(e))


class TestMigrationBackfill:
    """Prove that hash_version backfill works correctly through real migrations."""

    def test_alembic_url_precedence_caller_connection_overrides_settings(self):
        """A caller-supplied Alembic connection must override settings.DATABASE_URL."""
        import os
        from pathlib import Path

        tmp = Path(tempfile.gettempdir()) / "sintraprime_alembic_precedence"
        tmp.mkdir(exist_ok=True)
        connection_db = tmp / "connection.db"
        settings_db = tmp / "settings.db"
        for p in [connection_db, settings_db]:
            if p.exists():
                p.unlink()

        connection_url = f"sqlite:///{connection_db.as_posix()}"
        settings_url = f"sqlite:///{settings_db.as_posix()}"

        old_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = settings_url
        try:
            engine = create_engine(connection_url)
            with engine.connect() as connection:
                cfg = Config()
                cfg.set_main_option("script_location", "portal/alembic")
                # Set an explicit sqlalchemy.url that differs from both to prove
                # the connection still wins over the explicit URL as well.
                cfg.set_main_option("sqlalchemy.url", settings_url)
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")
            engine.dispose()

            # The connected DB must have the Alembic revision
            conn = sqlite3.connect(str(connection_db))
            rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
            conn.close()
            assert len(rows) == 1, f"Expected one revision in connection DB, got {rows}"
            assert rows[0][0] == "905b70986558"

            # The settings DB must NOT have been touched
            conn = sqlite3.connect(str(settings_db))
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            conn.close()
            assert len(tables) == 0, f"settings.DATABASE_URL DB was migrated unexpectedly: {tables}"
        finally:
            if old_db_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = old_db_url
            for p in [connection_db, settings_db]:
                if p.exists():
                    p.unlink()

    @pytest.mark.asyncio
    async def test_hash_version_backfill_postgresql(self):
        """PostgreSQL: v1 events backfilled to hash_version=1, new events get hash_version=2,
        mixed chain verifies. Uses real Alembic migrations, NOT create_all()."""
        import os
        from urllib.parse import urlparse, urlunparse
        from uuid import uuid4

        pg_url = os.environ.get("GATE4_TEST_DATABASE_URL")
        if not pg_url:
            pytest.skip("GATE4_TEST_DATABASE_URL not set")
        _check_pg_is_disposable(pg_url)

        # Convert async URL to sync for Alembic
        sync_url = pg_url.replace("+asyncpg", "+psycopg2")
        async_url = pg_url

        # Fully recreate the disposable test database to avoid leftover tables
        parsed = urlparse(sync_url)
        target_db = parsed.path.lstrip("/")
        maintenance_url = urlunparse(parsed._replace(path="/sintraprime"))

        from sqlalchemy import create_engine as sync_create_engine
        admin_engine = sync_create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{target_db}' AND pid <> pg_backend_pid()"
            ))
            conn.execute(text(f"DROP DATABASE IF EXISTS {target_db}"))
            conn.execute(text(f"CREATE DATABASE {target_db}"))
        admin_engine.dispose()

        # Step 1: Upgrade to 4f3f0432cf9d (pre-hash_version)
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            cfg = Config()
            cfg.set_main_option("script_location", "portal/alembic")
            cfg.set_main_option("sqlalchemy.url", sync_url)
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "4f3f0432cf9d")
        engine.dispose()

        # Step 2: Insert two valid v1 events
        from sqlalchemy import insert

        run_id = str(uuid4())
        ts1 = "2026-01-01T00:00:00+00:00"
        h1 = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "create", "mission": "alpha"},
            previous_hash=None,
            timestamp=ts1,
        )
        ts2 = "2026-01-02T00:00:00+00:00"
        h2 = compute_hash_v1(
            event_type="MISSION_STARTED",
            payload={"action": "start", "mission": "alpha"},
            previous_hash=h1,
            timestamp=ts2,
        )

        evt1_id = str(uuid4())
        evt2_id = str(uuid4())
        engine = create_engine(sync_url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO observatory_run_heads "
                    "(run_id, last_sequence, last_event_hash, created_at, updated_at, version) "
                    "VALUES (:run_id, 0, NULL, :ts, :ts, 1)"
                ),
                {"run_id": run_id, "ts": ts1},
            )
            conn.execute(
                text(
                    "INSERT INTO observatory_events "
                    "(id, run_id, sequence, event_type, mission_id, agent_id, "
                    "payload, metadata, event_hash, previous_hash, timestamp, created_at) "
                    "VALUES (:id, :run_id, 1, 'MISSION_CREATED', "
                    "NULL, NULL, :payload, NULL, :hash, NULL, :ts, :ts)"
                ),
                {
                    "id": evt1_id,
                    "run_id": run_id,
                    "payload": '{"action": "create", "mission": "alpha"}',
                    "hash": h1,
                    "ts": ts1,
                },
            )
            conn.execute(
                text("UPDATE observatory_run_heads SET last_sequence = 1, last_event_hash = :hash WHERE run_id = :run_id"),
                {"hash": h1, "run_id": run_id},
            )
            conn.execute(
                text(
                    "INSERT INTO observatory_events "
                    "(id, run_id, sequence, event_type, mission_id, agent_id, "
                    "payload, metadata, event_hash, previous_hash, timestamp, created_at) "
                    "VALUES (:id, :run_id, 2, 'MISSION_STARTED', "
                    "NULL, NULL, :payload, NULL, :hash, :prev, :ts, :ts)"
                ),
                {
                    "id": evt2_id,
                    "run_id": run_id,
                    "payload": '{"action": "start", "mission": "alpha"}',
                    "hash": h2,
                    "prev": h1,
                    "ts": ts2,
                },
            )
            conn.execute(
                text("UPDATE observatory_run_heads SET last_sequence = 2, last_event_hash = :hash WHERE run_id = :run_id"),
                {"hash": h2, "run_id": run_id},
            )
        engine.dispose()

        # Step 3: Upgrade to 905b70986558
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            cfg = Config()
            cfg.set_main_option("script_location", "portal/alembic")
            cfg.set_main_option("sqlalchemy.url", sync_url)
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "905b70986558")
        engine.dispose()

        # Step 4: Verify backfill
        engine = create_engine(sync_url)
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, hash_version FROM observatory_events ORDER BY sequence")
            ).fetchall()
            assert len(rows) == 2
            assert rows[0][1] == 1
            assert rows[1][1] == 1

            stored = conn.execute(
                text("SELECT event_hash FROM observatory_events WHERE id = :id"),
                {"id": evt1_id},
            ).fetchone()[0]
            assert stored == h1, "v1 hash changed after migration on PostgreSQL"

            revision = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()[0]
            assert revision == "905b70986558"
        engine.dispose()

        # Step 5: Create v2 event through EventService
        async_engine = create_async_engine(async_url, echo=False)
        factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as session:
            event3 = await EventService.create(
                session, event_type="EVIDENCE_CAPTURED",
                payload={"action": "capture"},
                run_id=run_id,
            )
            await session.commit()
            assert event3.hash_version == 2
            assert event3.sequence == 3

        # Step 6: Verify mixed chain
        async with factory() as session:
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, f"Mixed v1/v2 chain failed on PostgreSQL: {result.reason} {result.detail}"

        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_hash_version_backfill_sqlite(self):
        """SQLite: v1 events backfilled to hash_version=1, new events get hash_version=2,
        mixed chain verifies. Uses real Alembic migrations, NOT create_all()."""

        # ── Setup: temporary database ─────────────────────────────────────
        tmp = os.path.join(tempfile.gettempdir(), "sintraprime_backfill_test")
        os.makedirs(tmp, exist_ok=True)
        db_path = os.path.join(tmp, "test_backfill.db")
        if os.path.exists(db_path):
            os.unlink(db_path)

        _check_sqlite_is_temporary(db_path)

        db_path_forward = db_path.replace(os.sep, "/")
        sync_url = f"sqlite:///{db_path_forward}"
        async_url = f"sqlite+aiosqlite:///{db_path_forward}"

        # ── Step 1-2: Upgrade to 4f3f0432cf9d (pre-hash_version) ──────────
        # Use caller-supplied connection to guarantee target database.
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            cfg = Config()
            cfg.set_main_option("script_location", "portal/alembic")
            # Set URL for offline mode fallback, but connection takes precedence
            cfg.set_main_option("sqlalchemy.url", sync_url)
            cfg.attributes["connection"] = connection

            command.upgrade(cfg, "8b349f2cd639")
            command.upgrade(cfg, "4f3f0432cf9d")

        engine.dispose()

        # Insert v1 events BEFORE hash_version column exists
        # Use real UUIDs because PortableUUID type validates format
        from uuid import uuid4
        evt1_id = str(uuid4())
        evt2_id = str(uuid4())
        run_id = str(uuid4())

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO observatory_run_heads "
            "(run_id, last_sequence, last_event_hash, created_at, updated_at, version) "
            "VALUES (?, 0, NULL, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 1)",
            (run_id,)
        )

        ts1 = "2026-01-01T00:00:00+00:00"
        h1 = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "create", "mission": "alpha"},
            previous_hash=None,
            timestamp=ts1,
        )
        cursor.execute(
            "INSERT INTO observatory_events "
            "(id, run_id, sequence, event_type, mission_id, agent_id, "
            "payload, metadata, event_hash, previous_hash, timestamp, created_at) "
            "VALUES (?, ?, 1, 'MISSION_CREATED', "
            "NULL, NULL, "
            "'{\"action\": \"create\", \"mission\": \"alpha\"}', NULL, ?, NULL, "
            "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')",
            (evt1_id, run_id, h1)
        )
        cursor.execute(
            "UPDATE observatory_run_heads SET last_sequence = 1, last_event_hash = ? "
            "WHERE run_id = ?",
            (h1, run_id)
        )

        ts2 = "2026-01-02T00:00:00+00:00"
        h2 = compute_hash_v1(
            event_type="MISSION_STARTED",
            payload={"action": "start", "mission": "alpha"},
            previous_hash=h1,
            timestamp=ts2,
        )
        cursor.execute(
            "INSERT INTO observatory_events "
            "(id, run_id, sequence, event_type, mission_id, agent_id, "
            "payload, metadata, event_hash, previous_hash, timestamp, created_at) "
            "VALUES (?, ?, 2, 'MISSION_STARTED', "
            "NULL, NULL, "
            "'{\"action\": \"start\", \"mission\": \"alpha\"}', NULL, ?, ?, "
            "'2026-01-02T00:00:00+00:00', '2026-01-02T00:00:00+00:00')",
            (evt2_id, run_id, h2, h1)
        )
        cursor.execute(
            "UPDATE observatory_run_heads SET last_sequence = 2, last_event_hash = ? "
            "WHERE run_id = ?",
            (h2, run_id)
        )
        conn.commit()
        conn.close()

        # ── Step 4: Upgrade to 905b70986558 (add hash_version + backfill) ─
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            cfg = Config()
            cfg.set_main_option("script_location", "portal/alembic")
            cfg.set_main_option("sqlalchemy.url", sync_url)
            cfg.attributes["connection"] = connection

            command.upgrade(cfg, "905b70986558")
        engine.dispose()

        # ── Step 5: Verify backfilled events have hash_version=1 ──────────
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT id, hash_version FROM observatory_events ORDER BY sequence"
        ).fetchall()
        assert len(rows) == 2, f"Expected 2 events, got {len(rows)}"
        assert rows[0][1] == 1, f"Event 1 hash_version={rows[0][1]}, expected 1"
        assert rows[1][1] == 1, f"Event 2 hash_version={rows[1][1]}, expected 1"

        # ── Step 6: Verify v1 hashes UNCHANGED after migration ────────────
        stored_hash = conn.execute(
            "SELECT event_hash FROM observatory_events WHERE id = ?",
            (evt1_id,)
        ).fetchone()[0]
        assert stored_hash == h1, "v1 hash changed after migration!"
        conn.close()

        # ── Step 7: Create v2 event through EventService ──────────────────
        async_engine = create_async_engine(async_url, echo=False)
        factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as session:
            event3 = await EventService.create(
                session, event_type="EVIDENCE_CAPTURED",
                payload={"action": "capture"},
                run_id=run_id,
            )
            await session.commit()
            assert event3.hash_version == 2, f"Event 3 hash_version={event3.hash_version}, expected 2"
            assert event3.sequence == 3

        # ── Step 8: Verify mixed v1/v2 chain ──────────────────────────────
        async with factory() as session:
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, f"Mixed v1/v2 chain should verify: {result.reason} {result.detail}"

        # ── Step 9: Verify run head matches terminal event ─────────────────
        async with factory() as session:
            head_result = await session.execute(text(
                "SELECT last_sequence, last_event_hash FROM observatory_run_heads "
                "WHERE run_id = :run_id"
            ).bindparams(run_id=run_id))
            head = head_result.fetchone()
            assert head[0] == 3, f"last_sequence={head[0]}, expected 3"
            assert head[1] == event3.event_hash

        # ── Step 10: Verify Alembic revision ──────────────────────────────
        conn = sqlite3.connect(db_path)
        revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert revision == "905b70986558", f"Expected revision 905b70986558, got {revision}"
        conn.close()

        # ── Verify application database was NOT touched ────────────────────
        app_db = os.path.join(os.getcwd(), "data", "portal.db")
        # The application database should still exist (from test suite setup)
        # but should NOT contain our backfill test data
        if os.path.exists(app_db):
            app_conn = sqlite3.connect(app_db)
            app_tables = app_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            # Our test run should not appear in the application database
            if any(t[0] == "observatory_events" for t in app_tables):
                count = app_conn.execute(
                    "SELECT COUNT(*) FROM observatory_events WHERE run_id = ?",
                    (run_id,)
                ).fetchone()[0]
                assert count == 0, "Backfill test data leaked into application database!"
            app_conn.close()

        await async_engine.dispose()

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)