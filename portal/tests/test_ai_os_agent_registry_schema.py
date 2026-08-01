"""M-001 — AI-OS agent registry schema tests.

Covers the eighteen-point M-001 evidence requirement items 1-15. Items 16-18
(existing PostgreSQL bootstrap certification, PostgreSQL race lane, and the
relevant regression suite) are separate existing suites and are run separately.

PostgreSQL cases require ``AI_OS_MIGRATION_TEST_POSTGRES_URL`` (a synchronous
psycopg2 URL for a DISPOSABLE database). They reset the public schema and apply
the legacy raw-SQL bootstrap corpus first, because the AI-OS tables reference
``tenants`` and ``users``.

Nothing here seeds or activates an agent.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from portal.database import Base
from portal.models.ai_os_agent import AIOSAgent, AIOSAgentVersion
from portal.scripts.migration_runner import (
    LEDGER_TABLE,
    MigrationError,
    applied_versions,
    discover,
    downgrade,
    upgrade,
)
from portal.scripts.postgresql_bootstrap import apply_migrations

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_OS_ROOT = REPO_ROOT / "portal" / "migrations" / "ai_os"
AI_OS_TABLES = ("ai_os_agents", "ai_os_agent_versions")
POSTGRES_URL_ENV = "AI_OS_MIGRATION_TEST_POSTGRES_URL"


# ── helpers ───────────────────────────────────────────────────────────────────


def _sqlite_engine(tmp_path: Path):
    return create_engine(f"sqlite+pysqlite:///{tmp_path / 'ai_os.db'}", future=True)


def _postgres_url() -> str:
    url = os.environ.get(POSTGRES_URL_ENV)
    if not url:
        pytest.skip(f"{POSTGRES_URL_ENV} not set")
    return url


def _fresh_postgres_engine():
    """Reset the disposable database and apply the legacy raw-SQL corpus."""
    url = _postgres_url()
    apply_migrations(url, reset_public_schema=True)
    return create_engine(url, future=True)


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _norm(value: object) -> str:
    return " ".join(str(value).lower().split())


def _describe(engine, table: str) -> dict:
    insp = inspect(engine)
    columns = {
        col["name"]: {
            "type": _norm(col["type"]),
            "nullable": bool(col["nullable"]),
            "default": _norm(col["default"]) if col["default"] is not None else None,
        }
        for col in insp.get_columns(table)
    }
    pk = sorted(insp.get_pk_constraint(table).get("constrained_columns") or [])
    fks = sorted(
        (
            fk.get("name") or "",
            tuple(fk["constrained_columns"]),
            fk["referred_table"],
            tuple(fk["referred_columns"]),
            _norm((fk.get("options") or {}).get("ondelete")),
        )
        for fk in insp.get_foreign_keys(table)
    )
    uniques = sorted(
        (uq["name"], tuple(uq["column_names"])) for uq in insp.get_unique_constraints(table)
    )
    checks = sorted((ck["name"], _norm(ck["sqltext"])) for ck in insp.get_check_constraints(table))
    indexes = sorted(
        (ix["name"], tuple(ix["column_names"]), bool(ix.get("unique")))
        for ix in insp.get_indexes(table)
    )
    return {
        "columns": columns,
        "primary_key": pk,
        "foreign_keys": fks,
        "unique_constraints": uniques,
        "check_constraints": checks,
        "indexes": indexes,
    }


def _catalog_column(engine, table: str, column: str) -> dict:
    info = next(col for col in inspect(engine).get_columns(table) if col["name"] == column)
    return {
        "type": _norm(info["type"]),
        "nullable": bool(info["nullable"]),
        "default": _norm(info["default"]) if info["default"] is not None else None,
        "length": getattr(info["type"], "length", None),
    }


def _compiled_type(column, dialect) -> str:
    return _norm(column.type.compile(dialect=dialect))


def _seed_parent_rows(engine) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a minimal tenant + user so FK-enforcing engines accept inserts."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        if engine.dialect.name != "postgresql":
            return tenant_id, user_id
        role_id = conn.execute(text("SELECT id FROM roles ORDER BY name LIMIT 1")).scalar_one()
        conn.execute(
            text("INSERT INTO tenants (id, name, slug) VALUES (:i, 'T', :s)"),
            {"i": tenant_id, "s": f"t-{tenant_id.hex[:8]}"},
        )
        conn.execute(
            text(
                "INSERT INTO users (id, tenant_id, role_id, email, first_name,"
                " last_name, hashed_password) VALUES"
                " (:i, :t, :r, :e, 'A', 'B', 'x')"
            ),
            {"i": user_id, "t": tenant_id, "r": role_id, "e": f"{user_id.hex[:8]}@example.test"},
        )
    return tenant_id, user_id


def _insert_agent(engine, tenant_id, user_id, agent_id: str, row_id=None):
    row_id = row_id or uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai_os_agents (id, tenant_id, agent_id, display_name,"
                " role, created_by) VALUES (:i, :t, :a, :d, :r, :u)"
            ),
            {
                "i": str(row_id),
                "t": str(tenant_id),
                "a": agent_id,
                "d": agent_id.title(),
                "r": "Test Role",
                "u": str(user_id),
            },
        )
    return row_id


def _insert_version(engine, tenant_id, user_id, agent_row_id, semver, definition):
    version_id = uuid.uuid4()
    digest = hashlib.sha256(definition.encode()).hexdigest()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai_os_agent_versions (id, tenant_id, agent_row_id,"
                " semver, definition, definition_sha256, created_by)"
                " VALUES (:i, :t, :a, :s, :d, :h, :u)"
            ),
            {
                "i": str(version_id),
                "t": str(tenant_id),
                "a": str(agent_row_id),
                "s": semver,
                "d": definition,
                "h": digest,
                "u": str(user_id),
            },
        )
    return version_id


# ── structural tests ─────────────────────────────────────────────────────────


def test_migration_is_discoverable_and_reversible_on_disk() -> None:
    migrations = discover(AI_OS_ROOT)
    assert [m.version for m in migrations] == ["0001"]
    only = migrations[0]
    assert only.slug == "agents_and_versions"
    for dialect in ("sqlite", "postgresql"):
        assert only.script("up", dialect).strip()
        assert only.script("down", dialect).strip()


def test_migration_contains_no_prohibited_sql_constructs() -> None:
    """K-5: the semicolon splitter is only safe for simple transactional DDL."""
    forbidden = ("do $$", "create function", "create procedure", "create trigger", "plpgsql")
    for path in sorted(AI_OS_ROOT.rglob("*.sql")):
        executable = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("--")
        ]
        body = "\n".join(executable).lower()
        for token in forbidden:
            assert token not in body, f"{path.name} contains prohibited construct {token!r}"


# ── SQLite lane (items 1, 2, 3, 7, 8, 10-15) ──────────────────────────────────


def test_sqlite_fresh_upgrade(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    assert upgrade(engine, AI_OS_ROOT) == ["0001_agents_and_versions"]
    assert set(AI_OS_TABLES) <= _tables(engine)
    assert set(applied_versions(engine)) == {"0001"}


def test_sqlite_fresh_downgrade(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    assert downgrade(engine, AI_OS_ROOT) == ["0001_agents_and_versions"]
    assert applied_versions(engine) == {}


def test_sqlite_upgrade_downgrade_upgrade_cycle(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    first = _describe(engine, "ai_os_agents")
    downgrade(engine, AI_OS_ROOT)
    upgrade(engine, AI_OS_ROOT)
    assert _describe(engine, "ai_os_agents") == first


def test_sqlite_upgrade_is_idempotent(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    assert upgrade(engine, AI_OS_ROOT) == []


def test_sqlite_checksum_drift_is_refused(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE {LEDGER_TABLE} SET checksum = :c WHERE version = '0001'"),
            {"c": "0" * 64},
        )
    with pytest.raises(MigrationError, match="checksum drift"):
        upgrade(engine, AI_OS_ROOT)


def test_sqlite_downgrade_leaves_no_ai_os_residue(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    before = _tables(engine)
    upgrade(engine, AI_OS_ROOT)
    downgrade(engine, AI_OS_ROOT)
    after = _tables(engine)
    assert not [t for t in after if t.startswith("ai_os_")]
    assert after - before == {LEDGER_TABLE}
    with engine.connect() as conn:
        indexes = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'index'")
        ).scalars()
        assert not [i for i in indexes if i and i.startswith("ix_ai_os_")]


def test_sqlite_inactive_by_default_database_value(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    tenant_id, user_id = _seed_parent_rows(engine)
    _insert_agent(engine, tenant_id, user_id, "probe")
    with engine.connect() as conn:
        status, active = conn.execute(text("SELECT status, active FROM ai_os_agents")).one()
    assert status == "seed"
    assert bool(active) is False


def test_sqlite_seed_agent_cannot_be_active(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    tenant_id, user_id = _seed_parent_rows(engine)
    row_id = _insert_agent(engine, tenant_id, user_id, "probe")
    with pytest.raises(IntegrityError, match="ck_ai_os_agents_seed_inactive"):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE ai_os_agents SET active = 1 WHERE id = :i"),
                {"i": str(row_id)},
            )


def test_sqlite_tenant_scoped_agent_uniqueness(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    tenant_id, user_id = _seed_parent_rows(engine)
    other_tenant = uuid.uuid4()
    _insert_agent(engine, tenant_id, user_id, "hermes")
    with pytest.raises(IntegrityError):
        _insert_agent(engine, tenant_id, user_id, "hermes")
    # Same logical agent id under a different tenant is permitted.
    _insert_agent(engine, other_tenant, user_id, "hermes")


def test_sqlite_agent_version_and_definition_hash_uniqueness(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path)
    upgrade(engine, AI_OS_ROOT)
    tenant_id, user_id = _seed_parent_rows(engine)
    agent_row = _insert_agent(engine, tenant_id, user_id, "hermes")
    _insert_version(engine, tenant_id, user_id, agent_row, "1.0.0", '{"a":1}')
    with pytest.raises(IntegrityError):  # duplicate (agent, semver)
        _insert_version(engine, tenant_id, user_id, agent_row, "1.0.0", '{"a":2}')
    with pytest.raises(IntegrityError):  # duplicate (agent, definition hash)
        _insert_version(engine, tenant_id, user_id, agent_row, "1.0.1", '{"a":1}')


def test_models_expose_no_hard_delete_or_mutation_helpers() -> None:
    """Retirement is a status change; version rows are immutable."""
    agent_columns = set(AIOSAgent.__table__.columns.keys())
    version_columns = set(AIOSAgentVersion.__table__.columns.keys())
    assert "deleted_at" not in agent_columns
    assert "updated_at" not in agent_columns
    assert "deleted_at" not in version_columns
    assert "updated_at" not in version_columns
    for model in (AIOSAgent, AIOSAgentVersion):
        for forbidden in ("delete", "soft_delete", "purge", "hard_delete"):
            assert not hasattr(model, forbidden)
    status_check = next(
        c
        for c in AIOSAgent.__table__.constraints
        if getattr(c, "name", "") == "ck_ai_os_agents_status"
    )
    assert "retired" in str(status_check.sqltext)


def test_sqlite_divergence_is_declared() -> None:
    """SQLite cannot ALTER TABLE ADD CONSTRAINT, so the deferred FK is absent."""
    neutral = (AI_OS_ROOT / "0001_agents_and_versions" / "up.sql").read_text(encoding="utf-8")
    pg_specific = (AI_OS_ROOT / "0001_agents_and_versions" / "up.postgresql.sql").read_text(
        encoding="utf-8"
    )
    assert "fk_ai_os_agents_current_version" not in neutral
    assert "fk_ai_os_agents_current_version" in pg_specific
    assert "ALTER TABLE ai_os_agents" in pg_specific


# ── PostgreSQL lane (items 4, 5, 6, 9, and repeats of 10-15) ─────────────────


@pytest.mark.postgresql
def test_postgresql_fresh_upgrade() -> None:
    engine = _fresh_postgres_engine()
    try:
        assert upgrade(engine, AI_OS_ROOT) == ["0001_agents_and_versions"]
        assert set(AI_OS_TABLES) <= _tables(engine)
        fks = {fk["name"] for fk in inspect(engine).get_foreign_keys("ai_os_agents")}
        assert "fk_ai_os_agents_current_version" in fks
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_postgresql_fresh_downgrade_leaves_no_residue() -> None:
    engine = _fresh_postgres_engine()
    try:
        upgrade(engine, AI_OS_ROOT)
        assert downgrade(engine, AI_OS_ROOT) == ["0001_agents_and_versions"]
        assert not [t for t in _tables(engine) if t.startswith("ai_os_")]
        assert applied_versions(engine) == {}
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_postgresql_upgrade_downgrade_upgrade_cycle() -> None:
    engine = _fresh_postgres_engine()
    try:
        upgrade(engine, AI_OS_ROOT)
        first = {t: _describe(engine, t) for t in AI_OS_TABLES}
        downgrade(engine, AI_OS_ROOT)
        upgrade(engine, AI_OS_ROOT)
        assert {t: _describe(engine, t) for t in AI_OS_TABLES} == first
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_postgresql_legacy_fk_compatibility_and_schema_parity() -> None:
    """The mandatory K-2 ORM/SQL parity gate plus legacy FK compatibility."""
    legacy_engine = _fresh_postgres_engine()
    try:
        # Authoritative live catalog types for the legacy bootstrap corpus.
        legacy_tenants_id = _catalog_column(legacy_engine, "tenants", "id")
        legacy_users_id = _catalog_column(legacy_engine, "users", "id")

        # AI-OS references to legacy tables must match the bootstrapped catalog exactly.
        assert (
            _compiled_type(AIOSAgent.__table__.c.tenant_id, legacy_engine.dialect)
            == legacy_tenants_id["type"]
        )
        assert (
            _compiled_type(AIOSAgent.__table__.c.created_by, legacy_engine.dialect)
            == legacy_users_id["type"]
        )
        assert (
            _compiled_type(AIOSAgentVersion.__table__.c.tenant_id, legacy_engine.dialect)
            == legacy_tenants_id["type"]
        )
        assert (
            _compiled_type(AIOSAgentVersion.__table__.c.created_by, legacy_engine.dialect)
            == legacy_users_id["type"]
        )
        assert legacy_tenants_id["length"] is None
        assert legacy_users_id["length"] is None
    finally:
        legacy_engine.dispose()

    engine = _fresh_postgres_engine()
    try:
        Base.metadata.create_all(
            engine,
            tables=[AIOSAgent.__table__, AIOSAgentVersion.__table__],
        )
        from_orm = {t: _describe(engine, t) for t in AI_OS_TABLES}
        orm_refs = {
            "ai_os_agents.tenant_id": _catalog_column(engine, "ai_os_agents", "tenant_id"),
            "ai_os_agents.created_by": _catalog_column(engine, "ai_os_agents", "created_by"),
            "ai_os_agent_versions.tenant_id": _catalog_column(
                engine, "ai_os_agent_versions", "tenant_id"
            ),
            "ai_os_agent_versions.created_by": _catalog_column(
                engine, "ai_os_agent_versions", "created_by"
            ),
        }
    finally:
        engine.dispose()

    sql_engine = _fresh_postgres_engine()
    try:
        upgrade(sql_engine, AI_OS_ROOT)
        from_sql = {t: _describe(sql_engine, t) for t in AI_OS_TABLES}
        runtime_refs = {
            "ai_os_agents.tenant_id": _catalog_column(sql_engine, "ai_os_agents", "tenant_id"),
            "ai_os_agents.created_by": _catalog_column(sql_engine, "ai_os_agents", "created_by"),
            "ai_os_agent_versions.tenant_id": _catalog_column(
                sql_engine, "ai_os_agent_versions", "tenant_id"
            ),
            "ai_os_agent_versions.created_by": _catalog_column(
                sql_engine, "ai_os_agent_versions", "created_by"
            ),
        }
    finally:
        sql_engine.dispose()

    for table in AI_OS_TABLES:
        for facet in (
            "columns",
            "primary_key",
            "foreign_keys",
            "unique_constraints",
            "check_constraints",
            "indexes",
        ):
            assert (
                from_orm[table][facet] == from_sql[table][facet]
            ), f"parity mismatch on {table}.{facet}"

    assert orm_refs == runtime_refs
    assert orm_refs["ai_os_agents.tenant_id"]["type"] == "uuid"
    assert orm_refs["ai_os_agents.created_by"]["type"] == "uuid"
    assert runtime_refs["ai_os_agent_versions.created_by"]["type"] == "uuid"


@pytest.mark.postgresql
def test_postgresql_constraints_are_enforced() -> None:
    engine = _fresh_postgres_engine()
    try:
        upgrade(engine, AI_OS_ROOT)
        tenant_id, user_id = _seed_parent_rows(engine)
        agent_row = _insert_agent(engine, tenant_id, user_id, "hermes")
        with engine.connect() as conn:
            status, active = conn.execute(
                text("SELECT status, active FROM ai_os_agents WHERE id = :i"),
                {"i": str(agent_row)},
            ).one()
        assert (status, active) == ("seed", False)

        with pytest.raises(IntegrityError):
            _insert_agent(engine, tenant_id, user_id, "hermes")

        _insert_version(engine, tenant_id, user_id, agent_row, "1.0.0", '{"a":1}')
        with pytest.raises(IntegrityError):
            _insert_version(engine, tenant_id, user_id, agent_row, "1.0.0", '{"a":2}')
        with pytest.raises(IntegrityError):
            _insert_version(engine, tenant_id, user_id, agent_row, "1.0.1", '{"a":1}')

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE ai_os_agents SET active = TRUE WHERE id = :i"),
                    {"i": str(agent_row)},
                )
    finally:
        engine.dispose()
