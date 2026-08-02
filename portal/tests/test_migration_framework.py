"""Migration-framework tests (Increment 0).

Proves the repository-native migration runner is deterministic, ledgered, and
reversible on SQLite always, and on PostgreSQL when a disposable database URL is
supplied via ``AI_OS_MIGRATION_TEST_POSTGRES_URL``.

No AI-OS table is created by these tests. The fixture migrations under
``portal/tests/support/migration_probe`` exist solely to exercise the runner.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from portal.scripts.migration_runner import (
    LEDGER_TABLE,
    MigrationError,
    applied_versions,
    discover,
    downgrade,
    upgrade,
)

PROBE_ROOT = Path(__file__).resolve().parent / "support" / "migration_probe"
PROBE_TABLE = "migration_framework_probe"
POSTGRES_URL_ENV = "AI_OS_MIGRATION_TEST_POSTGRES_URL"


def _sqlite_engine(tmp_path: Path):
    return create_engine(f"sqlite+pysqlite:///{tmp_path / 'probe.db'}", future=True)


def _postgres_engine():
    url = os.environ.get(POSTGRES_URL_ENV)
    if not url:
        pytest.skip(f"{POSTGRES_URL_ENV} not set")
    return create_engine(url, future=True)


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _columns(engine, table: str) -> set[str]:
    return {col["name"] for col in inspect(engine).get_columns(table)}


def test_discover_returns_ordered_versions() -> None:
    migrations = discover(PROBE_ROOT)
    assert [m.version for m in migrations] == ["0001", "0002"]


def test_every_migration_has_a_down_script() -> None:
    for migration in discover(PROBE_ROOT):
        assert migration.script("down", "sqlite").strip()


def test_sqlite_upgrade_then_downgrade_round_trip(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    before = _tables(engine)

    applied = upgrade(engine, PROBE_ROOT)
    assert applied == ["0001_framework_probe", "0002_framework_probe_extend"]
    assert PROBE_TABLE in _tables(engine)
    assert "note" in _columns(engine, PROBE_TABLE)
    assert set(applied_versions(engine)) == {"0001", "0002"}

    reverted = downgrade(engine, PROBE_ROOT)
    assert reverted == ["0002_framework_probe_extend", "0001_framework_probe"]
    assert PROBE_TABLE not in _tables(engine)
    assert applied_versions(engine) == {}
    assert _tables(engine) - before == {LEDGER_TABLE}


def test_sqlite_upgrade_is_idempotent(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, PROBE_ROOT)
    assert upgrade(engine, PROBE_ROOT) == []


def test_sqlite_targeted_upgrade_and_partial_downgrade(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    assert upgrade(engine, PROBE_ROOT, target="0001") == ["0001_framework_probe"]
    assert "note" not in _columns(engine, PROBE_TABLE)

    upgrade(engine, PROBE_ROOT)
    assert downgrade(engine, PROBE_ROOT, target="0001") == ["0002_framework_probe_extend"]
    assert PROBE_TABLE in _tables(engine)
    assert set(applied_versions(engine)) == {"0001"}


def test_checksum_drift_fails_closed(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, PROBE_ROOT, target="0001")
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(
            text(f"UPDATE {LEDGER_TABLE} SET checksum = :c WHERE version = '0001'"),
            {"c": "0" * 64},
        )
    with pytest.raises(MigrationError, match="checksum drift"):
        upgrade(engine, PROBE_ROOT)


@pytest.mark.postgresql
def test_postgresql_upgrade_then_downgrade_round_trip() -> None:
    engine = _postgres_engine()
    try:
        assert upgrade(engine, PROBE_ROOT) == [
            "0001_framework_probe",
            "0002_framework_probe_extend",
        ]
        assert PROBE_TABLE in _tables(engine)
        assert "note" in _columns(engine, PROBE_TABLE)
        assert set(applied_versions(engine)) == {"0001", "0002"}

        assert downgrade(engine, PROBE_ROOT) == [
            "0002_framework_probe_extend",
            "0001_framework_probe",
        ]
        assert PROBE_TABLE not in _tables(engine)
        assert applied_versions(engine) == {}
    finally:
        downgrade(engine, PROBE_ROOT)
        engine.dispose()
