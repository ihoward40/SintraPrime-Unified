#!/usr/bin/env python3
"""Repository-native, reversible SQL migration runner (Increment 0 prototype).

Scope
-----
This module establishes the migration FRAMEWORK only. It creates and maintains a
migration ledger table and applies paired ``up`` / ``down`` SQL scripts in a
deterministic order. It does NOT define, create, or reference any AI-OS table.

Why not Alembic
---------------
See ``docs/adr/ADR-0001-ai-os-migration-framework.md``. The repository already
owns a raw-SQL migration corpus under ``portal/migrations/`` plus an authoritative
fresh-bootstrap sequence in ``portal/scripts/postgresql_bootstrap.py``. What is
missing is not a migration tool but a ledger, a deterministic order, and a proven
downgrade path. This runner supplies exactly those three things and nothing else.

Layout
------
Each migration is a directory::

    <root>/<version>_<slug>/
        up.sql                  # required, engine-neutral
        down.sql                # required, engine-neutral
        up.postgresql.sql       # optional engine override
        down.postgresql.sql     # optional engine override
        up.sqlite.sql           # optional engine override
        down.sqlite.sql         # optional engine override

``<version>`` is a zero-padded integer. Engine-specific files take precedence over
the neutral file for the matching dialect.

Ledger
------
Table ``schema_migrations`` (created on demand)::

    version      TEXT PRIMARY KEY
    name         TEXT NOT NULL
    checksum     TEXT NOT NULL      -- SHA-256 of the applied up script
    applied_at   TEXT NOT NULL      -- ISO-8601 UTC, application-set

Applying a migration whose recorded checksum differs from the on-disk script is
refused (fail closed). Downgrade removes the ledger row in the same transaction
that runs ``down.sql``.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

LEDGER_TABLE = "schema_migrations"
_VERSION_DIR = re.compile(r"^(?P<version>\d{4,})_(?P<slug>[a-z0-9_]+)$")


class MigrationError(RuntimeError):
    """Raised when a migration cannot be applied or reverted safely."""


@dataclass(frozen=True)
class Migration:
    """A single reversible migration on disk."""

    version: str
    slug: str
    path: Path

    @property
    def name(self) -> str:
        return f"{self.version}_{self.slug}"

    def script(self, direction: str, dialect: str) -> str:
        if direction not in {"up", "down"}:
            raise MigrationError(f"unknown direction: {direction}")
        specific = self.path / f"{direction}.{dialect}.sql"
        neutral = self.path / f"{direction}.sql"
        chosen = specific if specific.is_file() else neutral
        if not chosen.is_file():
            raise MigrationError(f"missing {direction} script for {self.name}")
        return chosen.read_text(encoding="utf-8")

    def checksum(self, dialect: str) -> str:
        payload = self.script("up", dialect).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def discover(root: Path) -> list[Migration]:
    """Return migrations under ``root`` ordered by version, ascending."""
    found: list[Migration] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        match = _VERSION_DIR.match(child.name)
        if match is None:
            continue
        found.append(
            Migration(
                version=match.group("version"),
                slug=match.group("slug"),
                path=child,
            )
        )
    versions = [m.version for m in found]
    if len(set(versions)) != len(versions):
        raise MigrationError(f"duplicate migration versions under {root}")
    return found


def dialect_of(engine: Engine) -> str:
    return engine.dialect.name


def ensure_ledger(engine: Engine) -> None:
    """Create the ledger table if it does not already exist."""
    ddl = (
        f"CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} ("
        " version VARCHAR(32) PRIMARY KEY,"
        " name VARCHAR(255) NOT NULL,"
        " checksum VARCHAR(64) NOT NULL,"
        " applied_at VARCHAR(40) NOT NULL"
        ")"
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))


def applied_versions(engine: Engine) -> dict[str, str]:
    """Return ``{version: checksum}`` for every applied migration."""
    ensure_ledger(engine)
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT version, checksum FROM {LEDGER_TABLE} ORDER BY version")
        ).all()
    return {row[0]: row[1] for row in rows}


def _exec_script(conn, script: str) -> None:
    for statement in (s.strip() for s in script.split(";")):
        if statement:
            conn.execute(text(statement))


def upgrade(engine: Engine, root: Path, target: str | None = None) -> list[str]:
    """Apply pending migrations up to and including ``target``."""
    dialect = dialect_of(engine)
    ensure_ledger(engine)
    already = applied_versions(engine)
    applied: list[str] = []
    for migration in discover(root):
        if target is not None and migration.version > target:
            break
        checksum = migration.checksum(dialect)
        recorded = already.get(migration.version)
        if recorded is not None:
            if recorded != checksum:
                raise MigrationError(
                    f"checksum drift for {migration.name}: " f"ledger={recorded} disk={checksum}"
                )
            continue
        with engine.begin() as conn:
            _exec_script(conn, migration.script("up", dialect))
            conn.execute(
                text(
                    f"INSERT INTO {LEDGER_TABLE} (version, name, checksum, applied_at)"
                    " VALUES (:v, :n, :c, :t)"
                ),
                {
                    "v": migration.version,
                    "n": migration.name,
                    "c": checksum,
                    "t": datetime.now(UTC).isoformat(),
                },
            )
        applied.append(migration.name)
    return applied


def downgrade(engine: Engine, root: Path, target: str | None = None) -> list[str]:
    """Revert applied migrations down to (but not including) ``target``."""
    dialect = dialect_of(engine)
    ensure_ledger(engine)
    already = applied_versions(engine)
    reverted: list[str] = []
    for migration in reversed(discover(root)):
        if migration.version not in already:
            continue
        if target is not None and migration.version <= target:
            break
        with engine.begin() as conn:
            _exec_script(conn, migration.script("down", dialect))
            conn.execute(
                text(f"DELETE FROM {LEDGER_TABLE} WHERE version = :v"),
                {"v": migration.version},
            )
        reverted.append(migration.name)
    return reverted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("upgrade", "downgrade", "status"))
    parser.add_argument("--url", required=True, help="synchronous SQLAlchemy URL")
    parser.add_argument("--root", required=True, help="migration directory")
    parser.add_argument("--target", default=None, help="target version")
    args = parser.parse_args()

    engine = create_engine(args.url, future=True)
    root = Path(args.root)
    if args.command == "status":
        for version, checksum in applied_versions(engine).items():
            print(f"{version} {checksum}")
        return 0
    if args.command == "upgrade":
        for name in upgrade(engine, root, args.target):
            print(f"applied {name}")
        return 0
    for name in downgrade(engine, root, args.target):
        print(f"reverted {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
