"""Drop and recreate the gate4_test PostgreSQL database, then run all Alembic migrations.

Uses GATE4_TEST_DATABASE_URL for the target database. Derives the maintenance
connection by replacing the database name with the 'sintraprime' management
database.
"""
import asyncio
import os
import sys
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command

TARGET_URL = os.environ.get("GATE4_TEST_DATABASE_URL")
if not TARGET_URL:
    print("ERROR: GATE4_TEST_DATABASE_URL is not set", file=sys.stderr)
    sys.exit(1)

# Normalize to sync URL for Alembic and admin operations
def _to_sync(url: str) -> str:
    return url.replace("+asyncpg", "+psycopg2")

TARGET_SYNC_URL = _to_sync(TARGET_URL)
TARGET_ASYNC_URL = TARGET_URL if TARGET_URL.startswith("postgresql+asyncpg") else TARGET_URL.replace("+psycopg2", "+asyncpg")

# Derive maintenance URL by replacing the path (database name) with /sintraprime
parsed = urlparse(TARGET_SYNC_URL)
maintenance_path = "/sintraprime"
MAINTENANCE_URL = urlunparse(parsed._replace(path=maintenance_path))


def recreate_database():
    """Drop and create the target database outside any transaction."""
    engine = create_engine(MAINTENANCE_URL, isolation_level="AUTOCOMMIT")
    target_db = parsed.path.lstrip("/")
    with engine.connect() as conn:
        conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{target_db}' AND pid <> pg_backend_pid()"
        ))
        conn.execute(text(f"DROP DATABASE IF EXISTS {target_db}"))
        conn.execute(text(f"CREATE DATABASE {target_db}"))
    engine.dispose()
    print(f"Recreated {target_db}")


async def main():
    recreate_database()

    # Run all Alembic migrations against the new database.
    engine = create_engine(TARGET_SYNC_URL)
    with engine.connect() as connection:
        cfg = Config()
        cfg.set_main_option("script_location", "portal/alembic")
        cfg.set_main_option("sqlalchemy.url", TARGET_SYNC_URL)
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    engine.dispose()
    print("Alembic migrations applied to gate4_test")

    # Verify final state.
    verify_engine = create_async_engine(TARGET_ASYNC_URL)
    async with verify_engine.begin() as conn:
        rev = await conn.execute(text("SELECT version_num FROM alembic_version"))
        version = rev.scalar()
        print(f"Alembic current: {version}")

        counts = {}
        for table in ["observatory_events", "observatory_run_heads", "observatory_kill_switch_state"]:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()
        print(f"Counts: {counts}")
    await verify_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
