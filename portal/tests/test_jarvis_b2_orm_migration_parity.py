"""P3 ORM/migration parity certification against real PostgreSQL.

Opt-in: runs only when JARVIS_B2_POSTGRES_URL is supplied (postgresql marker).
Compares portal/models/jarvis_b2_durability.py metadata against the live schema
created by portal/migrations/jarvis_b2_durability_2026_09_05.sql.

Contract:
- Portable parity (columns, types, nullability, PKs, uniques, enum CHECKs,
  non-unique indexes, server defaults) must match exactly.
- The migration-only receipt-payload secret regex CHECK is migration-owned
  PostgreSQL hardening; it is verified present in the database.
"""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import pytest
from sqlalchemy.dialects import postgresql

from portal.models import jarvis_b2_durability as models

pytestmark = pytest.mark.postgresql

EXPECTED_TABLES = (
    "jarvis_authority_leases",
    "jarvis_operations",
    "jarvis_action_receipts",
    "jarvis_operational_memory",
    "jarvis_credential_state",
)

MIGRATION_OWNED_CHECKS = {"ck_jarvis_receipt_payload_no_secret"}


@pytest.fixture
def pg_conn_params():
    value = os.getenv("JARVIS_B2_POSTGRES_URL")
    if not value:
        pytest.skip("JARVIS_B2_POSTGRES_URL is required; parity not certified")
    parsed = urlparse(value.replace("postgresql+asyncpg://", "postgresql://"))
    return {
        "user": parsed.username,
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "ssl": False,
    }


def _orm_facts() -> dict:
    tables = {
        "jarvis_authority_leases": models.JarvisAuthorityLeaseRecord.__table__,
        "jarvis_operations": models.JarvisOperationRecord.__table__,
        "jarvis_action_receipts": models.JarvisActionReceiptRecord.__table__,
        "jarvis_operational_memory": models.JarvisOperationalMemoryRecord.__table__,
        "jarvis_credential_state": models.JarvisCredentialStateRecord.__table__,
    }
    facts: dict = {}
    for name, table in tables.items():
        columns = {}
        for col in table.columns:
            compiled = col.type.compile(dialect=postgresql.dialect()).upper()
            columns[col.name] = {
                "type": compiled,
                "nullable": bool(col.nullable),
                "default": _default_token(col.server_default),
            }
        checks = sorted(
            c.name for c in table.constraints if c.__class__.__name__ == "CheckConstraint"
        )
        uniques = set()
        for constraint in table.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint":
                uniques.add(tuple(c.name for c in constraint.columns))
        for col in table.columns:
            if col.unique:
                uniques.add((col.name,))
        indexes = set()
        for index in table.indexes:
            indexes.add((index.name, tuple(c.name for c in index.columns)))
        pk = tuple(c.name for c in sorted(table.primary_key.columns, key=lambda c: c.name))
        facts[name] = {
            "columns": columns,
            "checks": set(checks),
            "uniques": uniques,
            "indexes": indexes,
            "pk": pk,
        }
    return facts


def _default_token(server_default) -> str | None:
    if server_default is None:
        return None
    text = str(server_default.arg).strip().lower()
    if text in {"0"}:
        return "0"
    if "current_timestamp" in text or "now()" in text:
        return "NOW"
    if text in {"'open'", "open"}:
        return "OPEN"
    if text in {"'issued'", "issued"}:
        return "ISSUED"
    return text


async def _db_facts(params) -> dict:
    import asyncpg

    conn = await asyncpg.connect(**params)
    try:
        facts: dict = {}
        for table in EXPECTED_TABLES:
            rows = await conn.fetch(
                """
                SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=$1
                ORDER BY ordinal_position
                """,
                table,
            )
            columns = {}
            for row in rows:
                columns[row["column_name"]] = {
                    "type": _normalize_db_type(row),
                    "nullable": row["is_nullable"] == "YES",
                    "default": _normalize_db_default(row["column_default"]),
                }
            conrows = await conn.fetch(
                """
                SELECT conname, contype,
                       (SELECT array_agg(a.attname ORDER BY k.ord)
                        FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ord)
                        JOIN pg_attribute a
                          ON a.attrelid = c.conrelid AND a.attnum = k.attnum) AS cols
                FROM pg_constraint c
                WHERE c.conrelid = $1::regclass
                """,
                f"public.{table}",
            )
            checks, uniques, pk = set(), set(), ()
            for row in conrows:
                contype = row["contype"].decode() if isinstance(row["contype"], bytes) else str(row["contype"])
                if contype == "c" and row["conname"].startswith("ck_"):
                    checks.add(row["conname"])
                elif contype == "u":
                    uniques.add(tuple(row["cols"]))
                elif contype == "p":
                    pk = tuple(row["cols"])
            idxrows = await conn.fetch(
                """
                SELECT i.relname AS index_name,
                       array_agg(a.attname ORDER BY a.attnum) AS cols
                FROM pg_class t
                JOIN pg_index ix ON ix.indrelid = t.oid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relname = $1 AND ix.indisunique = FALSE
                GROUP BY i.relname
                """,
                table,
            )
            indexes = {(r["index_name"], tuple(r["cols"])) for r in idxrows}
            facts[table] = {
                "columns": columns,
                "checks": checks,
                "uniques": uniques,
                "indexes": indexes,
                "pk": pk,
            }
        return facts
    finally:
        await conn.close()


def _normalize_db_type(row) -> str:
    data_type = row["data_type"]
    if data_type == "character varying":
        return "VARCHAR({})".format(row["character_maximum_length"])
    if data_type == "jsonb":
        return "JSONB"
    if data_type == "json":
        return "JSON"
    if data_type in {"timestamp with time zone", "timestamp(6) with time zone"}:
        return "TIMESTAMP WITH TIME ZONE"
    if data_type == "integer":
        return "INTEGER"
    if data_type == "text":
        return "TEXT"
    return data_type.upper()


def _normalize_db_default(default) -> str | None:
    if default is None:
        return None
    text = str(default).strip().lower()
    if text in {"0"}:
        return "0"
    if "now()" in text or "current_timestamp" in text:
        return "NOW"
    if text in {"'open'::character varying", "'open'"}:
        return "OPEN"
    if text in {"'issued'::character varying", "'issued'"}:
        return "ISSUED"
    return text


async def test_orm_migration_parity(pg_conn_params):
    orm_facts = _orm_facts()
    db_facts = await _db_facts(pg_conn_params)
    defects: list[str] = []
    for table in EXPECTED_TABLES:
        orm, db = orm_facts[table], db_facts[table]
        if set(orm["columns"]) != set(db["columns"]):
            defects.append(
                "{} columns: orm_only={} db_only={}".format(
                    table,
                    sorted(set(orm["columns"]) - set(db["columns"])),
                    sorted(set(db["columns"]) - set(orm["columns"])),
                )
            )
            continue
        for column, spec in orm["columns"].items():
            actual = db["columns"][column]
            if actual["type"] != spec["type"]:
                defects.append("{}.{} type: orm={} db={}".format(table, column, spec["type"], actual["type"]))
            if actual["nullable"] != spec["nullable"]:
                defects.append("{}.{} nullable: orm={} db={}".format(table, column, spec["nullable"], actual["nullable"]))
            if actual["default"] != spec["default"]:
                defects.append("{}.{} default: orm={} db={}".format(table, column, spec["default"], actual["default"]))
        if orm["pk"] != db["pk"]:
            defects.append("{} pk: orm={} db={}".format(table, orm["pk"], db["pk"]))
        for check in orm["checks"] - db["checks"]:
            defects.append(f"{table} missing CHECK in migration: {check}")
        for unique in orm["uniques"] - db["uniques"]:
            defects.append(f"{table} missing UNIQUE in migration: {unique}")
        for index in orm["indexes"] - db["indexes"]:
            defects.append(f"{table} missing INDEX in migration: {index}")
    for check in sorted(MIGRATION_OWNED_CHECKS):
        if not any(check in db_facts[t]["checks"] for t in db_facts):
            defects.append(f"migration-owned CHECK absent from database: {check}")
    assert not defects, "MIGRATION_PARITY_DEFECTS: " + "; ".join(defects)
