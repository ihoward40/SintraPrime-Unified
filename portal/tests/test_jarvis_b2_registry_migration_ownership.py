"""JARVIS_B2_REGISTRY_MIGRATION_OWNERSHIP_REPAIR — SQL-only certification.

Contract:
  REGISTRY_SQL_BOOTSTRAP: genuinely fresh database (created via SQL on the
    disposable instance) provisioned from the canonical SQL sequence
    (portal_schema.sql baseline + B2 durability migration + the new registry
    migration) with ZERO Base.metadata.create_all()/init_db() assistance.
  REGISTRY_MIGRATION_UPGRADE: pre-registry schema (baseline + durability SQL
    only, registry tables PROVEN absent) accepts the new migration; unrelated
    tables unchanged; re-apply idempotent.
  REGISTRY_ORM_MIGRATION_PARITY: capability-registry models equal the
    migration-created PostgreSQL schema (columns/types/nullability/lengths/
    PK/FKs/uniques/indexes) — permanent coverage.
  SQL_ONLY_REGISTRY_LIFECYCLE: register -> REVIEWED -> admission -> APPROVED ->
    SANDBOXED -> TRUSTED -> execution eligibility on migration-created tables
    via the normal registry service.
  SQL_ONLY_B2_CHAIN: durable lease -> credential -> operation -> receipt ->
    memory against the SQL-provisioned database.

Each test provisions its own disposable database and drops it afterwards.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.models import jarvis_capability_registry as registry_models

pytestmark = pytest.mark.postgresql

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_DIR = os.path.join(REPO_ROOT, "portal", "migrations")
BASELINE_SQL = os.path.join(SQL_DIR, "portal_schema.sql")
DURABILITY_SQL = os.path.join(SQL_DIR, "jarvis_b2_durability_2026_09_05.sql")
REGISTRY_SQL = os.path.join(SQL_DIR, "jarvis_b2_registry_2026_09_05.sql")


def _base_connect_kwargs() -> tuple[dict, str, str]:
    """Returns (admin_kwargs, admin_sa_url, runner_sa_url)."""
    spec = importlib.util.spec_from_file_location(
        "envmod", r"C:\Users\admin\.sintraprime-secrets\jarvis_b2\jarvis_b2_cert_env.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from urllib.parse import unquote, urlparse

    def _parse(url: str) -> dict:
        p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
        return {
            "user": p.username,
            "password": unquote(p.password or ""),
            "host": p.hostname,
            "port": p.port or 5432,
            "ssl": False,
        }

    return _parse(m.ADMIN_URL), m.ADMIN_URL, m.JARVIS_B2_POSTGRES_URL


async def _connect_with_retry(**kwargs):
    import asyncpg

    last = None
    for _ in range(3):
        try:
            return await asyncpg.connect(**kwargs)
        except (ConnectionRefusedError, OSError) as exc:  # transient Docker engine flap
            last = exc
            await asyncio.sleep(2)
    raise last


def _sql_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


async def _apply_sql(kwargs: dict, *paths: str) -> None:
    conn = await _connect_with_retry(database=kwargs["database"], user=kwargs["user"],
                                     password=kwargs["password"], host=kwargs["host"],
                                     port=kwargs["port"], ssl=False)
    try:
        for path in paths:
            await conn.execute(_sql_file(path))
    finally:
        await conn.close()


async def _create_fresh_db():
    """CREATE DATABASE via the admin identity; returns (kwargs, sa_url, dbname)."""
    admin_kwargs, admin_url, _ = _base_connect_kwargs()
    dbname = "b2reg_" + uuid.uuid4().hex[:10]
    conn = await _connect_with_retry(database="postgres", **admin_kwargs)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()
    kwargs = {**admin_kwargs, "database": dbname}
    sa_url = admin_url.rsplit("/", 1)[0] + f"/{dbname}"
    return kwargs, sa_url, dbname


async def _drop_fresh_db(dbname: str) -> None:
    admin_kwargs, _, _ = _base_connect_kwargs()
    conn = await _connect_with_retry(database="postgres", **admin_kwargs)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
    finally:
        await conn.close()


@pytest.fixture
async def fresh_sql_db():
    """Fresh database with the full canonical SQL sequence applied (no create_all)."""
    kwargs, sa_url, dbname = await _create_fresh_db()
    try:
        await _apply_sql(kwargs, BASELINE_SQL, DURABILITY_SQL, REGISTRY_SQL)
        yield kwargs, sa_url
    finally:
        await _drop_fresh_db(dbname)


@pytest.fixture
async def fresh_pre_registry_db():
    """Fresh database with only the pre-registry sequence (baseline + durability)."""
    kwargs, sa_url, dbname = await _create_fresh_db()
    try:
        await _apply_sql(kwargs, BASELINE_SQL, DURABILITY_SQL)
        yield kwargs, sa_url
    finally:
        await _drop_fresh_db(dbname)


async def _table_columns(kwargs: dict, table: str) -> dict:
    conn = await _connect_with_retry(database=kwargs["database"], user=kwargs["user"],
                                     password=kwargs["password"], host=kwargs["host"],
                                     port=kwargs["port"], ssl=False)
    try:
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1)", table)
        if not exists:
            return {}
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position", table)
        return {r["column_name"]: True for r in rows}
    finally:
        await conn.close()


def _orm_facts() -> dict:
    from sqlalchemy.dialects import postgresql

    tables = {
        "capability_registrations": registry_models.CapabilityRegistration.__table__,
        "capability_transitions": registry_models.CapabilityTransition.__table__,
    }
    facts: dict = {}
    for name, table in tables.items():
        columns = {}
        varchar_lengths = {}
        for col in table.columns:
            compiled = col.type.compile(dialect=postgresql.dialect()).upper()
            if compiled.startswith("VARCHAR("):
                # length compared separately via varchar_lengths (same as DB side)
                columns[col.name] = {"type": "VARCHAR", "nullable": bool(col.nullable)}
            else:
                columns[col.name] = {"type": compiled, "nullable": bool(col.nullable)}
            if compiled.startswith("VARCHAR("):
                varchar_lengths[col.name] = int(compiled.split("(")[1].rstrip(")"))
        uniques = set()
        for constraint in table.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint":
                uniques.add(tuple(c.name for c in constraint.columns))
        indexes = set()
        for index in table.indexes:
            indexes.add((index.name, tuple(c.name for c in index.columns)))
        pk = tuple(c.name for c in sorted(table.primary_key.columns, key=lambda c: c.name))
        fks = set()
        for fk in table.foreign_keys:
            fks.add((fk.parent.name, fk.column.table.name, fk.column.name))
        facts[name] = {
            "columns": columns,
            "uniques": uniques,
            "indexes": indexes,
            "pk": pk,
            "fks": fks,
            "varchar_lengths": varchar_lengths,
        }
    return facts


async def _db_facts(kwargs: dict) -> dict:
    conn = await _connect_with_retry(database=kwargs["database"], user=kwargs["user"],
                                     password=kwargs["password"], host=kwargs["host"],
                                     port=kwargs["port"], ssl=False)
    facts: dict = {}
    try:
        for table in ("capability_registrations", "capability_transitions"):
            colrows = await conn.fetch(
                "SELECT column_name, data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position", table)
            columns, varchar_lengths = {}, {}
            for r in colrows:
                dtype = r["data_type"].upper()
                if dtype == "CHARACTER VARYING":
                    dtype = "VARCHAR"
                    if r["character_maximum_length"]:
                        varchar_lengths[r["column_name"]] = r["character_maximum_length"]
                columns[r["column_name"]] = {"type": dtype, "nullable": r["is_nullable"] == "YES"}
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
            uniques, pk, fks = set(), (), set()
            for row in conrows:
                contype = row["contype"].decode() if isinstance(row["contype"], bytes) else str(row["contype"])
                cols = tuple(row["cols"] or ())
                if contype == "p":
                    pk = tuple(sorted(cols))
                elif contype == "u":
                    uniques.add(cols)
                elif contype == "f":
                    fks.add(cols[0])
            idxrows = await conn.fetch(
                """
                SELECT ipx.indexname,
                       (SELECT array_agg(a.attname ORDER BY k.ordinality)
                        FROM unnest(ix.indkey) WITH ORDINALITY k(attnum, ordinality)
                        JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = k.attnum) AS cols
                FROM pg_index ix
                JOIN pg_class c ON c.oid = ix.indexrelid
                JOIN pg_indexes ipx ON ipx.indexname = c.relname AND ipx.schemaname = 'public'
                WHERE ix.indrelid = $1::regclass
                """,
                f"public.{table}",
            )
            indexes = {(r["indexname"], tuple(r["cols"] or ())) for r in idxrows}
            facts[table] = {
                "columns": columns,
                "uniques": uniques,
                "pk": pk,
                "fks": fks,
                "indexes": indexes,
                "varchar_lengths": varchar_lengths,
            }
    finally:
        await conn.close()
    return facts


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap / upgrade / idempotency
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_registry_sql_bootstrap_creates_authority_tables(fresh_sql_db):
    """REGISTRY_SQL_BOOTSTRAP — fresh DB from SQL only (no create_all)."""
    kwargs, _ = fresh_sql_db
    reg_cols = await _table_columns(kwargs, "capability_registrations")
    tr_cols = await _table_columns(kwargs, "capability_transitions")
    assert {"id", "tenant_id", "capability_id", "capability_version", "contract_hash",
            "owner_principal", "lifecycle_state", "effective_state", "effective_executable",
            "registry_revision", "dependency_ids", "executor_id", "adapter_id"} <= set(reg_cols)
    assert {"id", "tenant_id", "capability_id", "capability_version", "contract_hash",
            "from_status", "to_status", "actor_id", "authority", "transition_hash",
            "previous_transition_hash"} <= set(tr_cols)


@pytest.mark.asyncio
async def test_registry_migration_upgrade_and_idempotency(fresh_pre_registry_db):
    """REGISTRY_MIGRATION_UPGRADE + REGISTRY_MIGRATION_IDEMPOTENCY."""
    kwargs, _ = fresh_pre_registry_db
    # True pre-state: registry tables ABSENT before the migration.
    assert await _table_columns(kwargs, "capability_registrations") == {}
    assert await _table_columns(kwargs, "capability_transitions") == {}
    unrelated_before = await _table_columns(kwargs, "jarvis_action_receipts")
    # Apply the new migration (upgrade).
    await _apply_sql(kwargs, REGISTRY_SQL)
    assert await _table_columns(kwargs, "capability_registrations")
    # Unrelated durable tables untouched by the upgrade.
    unrelated_after = await _table_columns(kwargs, "jarvis_action_receipts")
    assert unrelated_before.keys() == unrelated_after.keys()
    # Re-apply the full canonical sequence, then the registry migration again.
    await _apply_sql(kwargs, BASELINE_SQL, DURABILITY_SQL, REGISTRY_SQL)
    await _apply_sql(kwargs, REGISTRY_SQL)
    assert await _table_columns(kwargs, "capability_registrations")
    assert await _table_columns(kwargs, "capability_transitions")


# ═══════════════════════════════════════════════════════════════════════
# Parity (permanent)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_registry_orm_migration_parity(fresh_sql_db):
    """REGISTRY_ORM_MIGRATION_PARITY — permanent PG coverage, no create_all."""
    kwargs, _ = fresh_sql_db
    orm = _orm_facts()
    db = await _db_facts(kwargs)
    for table in ("capability_registrations", "capability_transitions"):
        o, d = orm[table], db[table]
        assert set(o["columns"]) == set(d["columns"]), (table, "column set")
        for col, ofacts in o["columns"].items():
            dfacts = d["columns"][col]
            assert ofacts["nullable"] == dfacts["nullable"], (table, col, "nullability")
            assert ofacts["type"] == dfacts["type"], (table, col, ofacts["type"], dfacts["type"])
        assert o["pk"] == d["pk"], (table, "pk")
        assert o["uniques"] == d["uniques"], (table, "uniques")
        assert {name for name, _, _ in o["fks"]} == d["fks"], (table, "fk columns")
        assert o["varchar_lengths"] == d["varchar_lengths"], (table, "varchar lengths")
        assert o["indexes"], (table, "orm indexes missing from model")
        assert o["indexes"] <= d["indexes"], (table, "orm indexes present in db")


# ═══════════════════════════════════════════════════════════════════════
# SQL-only lifecycle + B2 chain
# ═══════════════════════════════════════════════════════════════════════


def _contract():
    from portal.services.jarvis_capability_contract import CapabilityContract

    return CapabilityContract(
        capability_id="github.issue.add_label", capability_version="1.0.0",
        allowed_operations=("github.issue.add_label",),
        allowed_targets=("github.issue:owner/repo#1",),
        risk="low", consequence="reversible", authority="tenant_principal",
        credential="github_token", executor_id="jarvis_action_executor",
        adapter_id="github_label_adapter", verification="independent_refetch",
        idempotency="label_already_present", reconciliation="refetch_on_timeout",
        rollback="remove_label", lease="single_request", revocation="approval_consumed",
        receipt="hash_chain_append", memory="bounded_writeback", brief="governed action",
    )


async def _seed_tenant_and_user(session, tenant_id, actor_id):
    await session.execute(text(
        "INSERT INTO tenants (id, name, slug) VALUES (:i, :n, :s) ON CONFLICT DO NOTHING"),
        {"i": str(tenant_id), "n": "SQL Boot Tenant", "s": "sqlboot-" + str(tenant_id)[:8]})
    role_id = (await session.execute(text(
        "SELECT id FROM roles WHERE name='FIRM_ADMIN' LIMIT 1"))).scalar_one()
    await session.execute(text(
        "INSERT INTO users (id, tenant_id, role_id, email, first_name, last_name, hashed_password) "
        "VALUES (:id, :tenant_id, :role_id, :email, :fn, :ln, :hp) ON CONFLICT DO NOTHING"),
        {"id": str(actor_id), "tenant_id": str(tenant_id), "role_id": str(role_id),
         "email": f"sqlboot-{actor_id}@example.invalid", "fn": "SQL", "ln": "Boot",
         "hp": "sqlboot-not-a-real-hash"})


@pytest.mark.asyncio
async def test_sql_only_registry_lifecycle_and_admission(fresh_sql_db):
    """SQL_ONLY_REGISTRY_LIFECYCLE — registry service on migration-created tables."""
    from portal.models.jarvis_capability_registry import LifecycleStatus
    from portal.services.jarvis_capability_admission import admit_for_approval
    from portal.services.jarvis_capability_registry import CapabilityRegistryService

    _, sa_url = fresh_sql_db
    engine = create_async_engine(sa_url)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_id, actor_id = uuid.uuid4(), uuid.uuid4()
    contract = _contract()
    service = CapabilityRegistryService()
    async with factory() as session:
        await _seed_tenant_and_user(session, tenant_id, actor_id)
        await session.commit()

        await service.register_capability(
            session=session, tenant_id=tenant_id, contract=contract,
            owner_principal=actor_id, actor_id=actor_id)
        await session.commit()
        await service.transition_to_reviewed(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash, actor_id=actor_id)
        await session.commit()
        admission = await admit_for_approval(session=session, tenant_id=tenant_id, contract=contract)
        await session.commit()
        assert admission.approved is True
        assert admission.reason_code == "ADMISSION_ELIGIBLE"

        await service.transition_to_approved(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash, actor_id=actor_id,
            approval_policy_ref="approval_policy_v1", credential_policy_ref="credential_policy_v1",
            verification_policy_ref="verification_policy_v1")
        await session.commit()
        await service.transition_to_sandboxed(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash, actor_id=actor_id)
        await session.commit()
        await service.transition_to_trusted(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            contract_hash=contract.contract_hash, actor_id=actor_id, certifier_id=actor_id)
        await session.commit()
        final = await service.get_current_registration(
            session, tenant_id, contract.capability_id, contract.capability_version)
        assert final.lifecycle_state == LifecycleStatus.TRUSTED.value
        assert final.effective_executable is True
        assert await service.check_execution_eligibility(
            session, tenant_id, contract.capability_id, contract.capability_version,
            contract.contract_hash) is True
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_only_b2_chain(fresh_sql_db):
    """SQL_ONLY_B2_CHAIN — durable chain on the SQL-provisioned database."""
    from portal.services.jarvis_action_receipt_b2 import ActionReceipt
    from portal.services.jarvis_authority_lease import AuthorityLease
    from portal.services.jarvis_credential_broker import CredentialRequest
    from portal.services.jarvis_durable_credentials import DurableCredentialBroker
    from portal.services.jarvis_durable_lease import DurableAuthorityLeaseStore
    from portal.services.jarvis_durable_memory import DurableOperationalMemory
    from portal.services.jarvis_durable_operations import DurableReconciler
    from portal.services.jarvis_durable_receipts import DurableReceiptRepository
    from portal.services.jarvis_operational_memory import MemoryClass
    from portal.services.jarvis_verification_reconciliation import VerificationStatus

    _, sa_url = fresh_sql_db
    engine = create_async_engine(sa_url)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant = "sqlchain-" + uuid.uuid4().hex[:10]
    now = datetime.now(UTC)
    lease = AuthorityLease.issue(
        tenant_id=tenant, principal_id="sqlchain-principal", capability_id="github.issue.add_label",
        capability_version="1.0.0", capability_contract_hash="sqlchain-hash",
        registry_revision=1, action_id="sqlchain-action", approval_id="sqlchain-approval",
        operation="github.issue.add_label", target="github.issue:owner/repo#1",
        params_hash="sqlchain-params", ttl=timedelta(minutes=5), now=now)
    ctx = {"tenant_id": tenant, "principal_id": "sqlchain-principal",
           "capability_id": "github.issue.add_label", "capability_version": "1.0.0",
           "capability_contract_hash": "sqlchain-hash", "registry_revision": 1,
           "action_id": "sqlchain-action", "approval_id": "sqlchain-approval",
           "operation": "github.issue.add_label", "target": "github.issue:owner/repo#1",
           "params_hash": "sqlchain-params", "now": now}
    request = CredentialRequest(
        broker_request_id="sqlreq-" + uuid.uuid4().hex[:8], tenant_id=tenant,
        principal_id="sqlchain-principal", capability_id="github.issue.add_label",
        capability_version="1.0.0", capability_contract_hash="sqlchain-hash",
        action_id="sqlchain-action", approval_id="sqlchain-approval",
        lease_id="pending-claim-binding", lease_revision=1, provider_id="github",
        resource_scope="github.issue:owner/repo#1", operation="github.issue.add_label",
        target="github.issue:owner/repo#1", issued_at=now,
        expires_at=now + timedelta(minutes=5), nonce="sqlchain-nonce-" + uuid.uuid4().hex)
    async with factory() as session:
        store = DurableAuthorityLeaseStore(session)
        await store.persist(lease, now=now)
        await session.commit()
        claimed = await store.claim(lease, **ctx)
        await session.commit()
        request = CredentialRequest(**{**request.__dict__, "lease_id": claimed.lease_id,
                                       "lease_revision": claimed.revision})
        broker = DurableCredentialBroker(session)
        grant = await broker.issue_scoped_grant_durable(request=request, lease=claimed, now=now)
        await session.commit()
        ops = DurableReconciler(session)
        record = await ops.create_or_get(
            action_id="sqlchain-action", attempt_id="sqlchain-attempt", tenant_id=tenant,
            capability_contract_hash="sqlchain-hash", lease_id=claimed.lease_id,
            credential_grant_id=grant.grant_id, operation="github.issue.add_label",
            target="github.issue:owner/repo#1", params_hash="sqlchain-params", now=now)
        outcome, status = await ops.attempt_once(
            record, tenant_id=tenant, mutate=lambda: None, read_state=lambda: True)
        assert outcome == "COMPLETED"
        assert status == VerificationStatus.VERIFIED_SUCCESS
        await session.commit()
        receipt = ActionReceipt.create(
            tenant_id=tenant, mission_id="sqlchain-mission",
            action_id="sqlchain-action", operation_id=record.operation_id,
            attempt_id="sqlchain-attempt", principal_id="sqlchain-principal",
            approval_id="sqlchain-approval", capability_id="github.issue.add_label",
            capability_version="1.0.0", capability_contract_hash="sqlchain-hash",
            approved_contract_hash="sqlchain-hash", runtime_contract_hash="sqlchain-hash",
            operation_contract_hash="sqlchain-hash", registry_revision=1,
            lease_id=claimed.lease_id, lease_revision=claimed.revision,
            credential_grant_id=grant.grant_id, executor_id="jarvis_action_executor",
            executor_version="1", executor_artifact_hash="sqlchain-exec",
            adapter_id="github_label_adapter", adapter_version="1",
            adapter_artifact_hash="sqlchain-adapter", operation="github.issue.add_label",
            target="github.issue:owner/repo#1", params_hash="sqlchain-params",
            pre_state_hash="sqlchain-pre", provider_result_hash="sqlchain-provider",
            post_state_hash="sqlchain-post", verification_status="VERIFIED_SUCCESS",
            verification_reason="POST_STATE_CONFIRMED",
            execution_started_at="2026-09-05T00:00:00+00:00",
            execution_completed_at="2026-09-05T00:00:01+00:00",
            verified_at="2026-09-05T00:00:02+00:00")
        repo = DurableReceiptRepository(session)
        await repo.persist(receipt)
        await session.commit()
        memory = DurableOperationalMemory(session)
        event = await memory.record_operational_event(
            tenant_id=tenant, mission_id="sqlchain-mission", action_id="sqlchain-action",
            operation_id=record.operation_id, receipt_id=receipt.receipt_id,
            receipt_hash=receipt.receipt_hash, capability_id="github.issue.add_label",
            capability_version="1.0.0", capability_contract_hash="sqlchain-hash",
            event_class=MemoryClass.GOVERNED_ACTION_COMPLETED,
            reason_code="SQL_CHAIN_OK", summary="SQL-only B2 chain completed",
            dedup_key="sqlchain-dedup-" + uuid.uuid4().hex[:8])
        await session.commit()
    # Restart-style verification from a fresh session.
    async with factory() as session:
        assert (await DurableAuthorityLeaseStore(session).load(lease.lease_id, tenant_id=tenant)) is not None
        assert (await DurableReceiptRepository(session).load(receipt.receipt_id, tenant_id=tenant)) is not None
        events = await DurableOperationalMemory(session).get_for_tenant(tenant_id=tenant)
        assert any(e.memory_event_id == event.memory_event_id for e in events)
    await engine.dispose()
