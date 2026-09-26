from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orchestration.a2a_governance import ApprovalReceipt, DispatchAudit
from orchestration.persistence import ShadowComparator, ShadowMismatchError, select_backend
from orchestration.postgres_approval_store import PostgresApprovalStore
from orchestration.postgres_audit_store import PostgresAuditStore
from orchestration.postgres_outbox import PostgresOutboxStore


class Result:
    def __init__(self, rows=(), rowcount=1):
        self.rows = list(rows)
        self.rowcount = rowcount

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class Session:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.used = False

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        if "SELECT * FROM a2a_approval_current_state" in sql:
            row = dict(self.rows[0]) if self.rows and not self.used else None
            if self.used and self.rows:
                row = dict(self.rows[0]); row["status"] = "used"
            return Result([row] if row else [])
        if sql.strip().startswith("UPDATE a2a_approval_current_state"):
            self.used = True
        if "SELECT * FROM a2a_outbox_current_state" in sql:
            return Result(self.rows)
        return Result()


@pytest.fixture
def receipt(monkeypatch):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "test-secret")
    return ApprovalReceipt(
        approved_by="principal", approved_output_id="output-1", recipient="worker",
        final_content_hash="hash", sender_agent_id="orchestrator", tenant_id="tenant-a",
        expires_at=datetime.now(timezone.utc).timestamp() + 3600, signature="sig",
    )


def test_backend_defaults_to_jsonl(monkeypatch):
    monkeypatch.delenv("A2A_PERSISTENCE_BACKEND", raising=False)
    monkeypatch.delenv("A2A_PERSISTENCE_SHADOW", raising=False)
    config = select_backend()
    assert config.backend == "jsonl" and not config.shadow


def test_backend_rejects_invalid_or_inconsistent_shadow(monkeypatch):
    monkeypatch.setenv("A2A_PERSISTENCE_BACKEND", "invalid")
    with pytest.raises(ValueError):
        select_backend()
    monkeypatch.setenv("A2A_PERSISTENCE_BACKEND", "jsonl")
    monkeypatch.setenv("A2A_PERSISTENCE_SHADOW", "true")
    with pytest.raises(ValueError):
        select_backend()


def test_shadow_mismatch_is_fail_closed():
    seen = []
    comparator = ShadowComparator(seen.append)
    with pytest.raises(ShadowMismatchError):
        comparator.compare(entity="approval", local={"status": "issued"}, postgres={"status": "revoked"})
    assert seen[0]["entity"] == "approval"


@pytest.mark.parametrize(
    "entity,local,postgres",
    [
        ("audit_missing", {"event_id": "e1", "status": "blocked"}, None),
        ("approval_state", {"receipt_id": "r1", "status": "issued"}, {"receipt_id": "r1", "status": "used"}),
        ("outbox_state", {"outbox_id": "o1", "status": "pending"}, {"outbox_id": "o1", "status": "dispatched"}),
        ("payload_hash", {"payload_hash": "hash-a"}, {"payload_hash": "hash-b"}),
        ("tenant_scope", {"tenant_id": "tenant-a"}, {"tenant_id": "tenant-b"}),
    ],
)
def test_shadow_mismatch_cases_block_certification(entity, local, postgres):
    with pytest.raises(ShadowMismatchError):
        ShadowComparator().compare(entity=entity, local=local, postgres=postgres)


@pytest.mark.asyncio
async def test_postgres_approval_consumption_is_one_time(receipt):
    row = {"status": "issued", "expires_at": datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1), "sender_agent_id": "orchestrator", "recipient": "worker", "final_content_hash": "hash"}
    session = Session([row])
    store = PostgresApprovalStore(session)
    await store.verify_and_consume(receipt, tenant_id="tenant-a", consumer_id="worker-1")
    with pytest.raises(PermissionError, match="used"):
        await store.verify_and_consume(receipt, tenant_id="tenant-a", consumer_id="worker-2")
    assert any("FOR UPDATE" in call[0] for call in session.calls)


@pytest.mark.asyncio
async def test_postgres_approval_rejects_cross_tenant(receipt):
    store = PostgresApprovalStore(Session())
    with pytest.raises(PermissionError, match="tenant"):
        await store.verify_and_consume(receipt, tenant_id="tenant-b", consumer_id="worker")


@pytest.mark.asyncio
async def test_postgres_outbox_claim_uses_skip_locked():
    session = Session([{"outbox_id": "o1", "status": "pending", "created_at": 1}])
    rows = await PostgresOutboxStore(session).claim(tenant_id="tenant-a", worker_id="w1")
    assert rows[0]["outbox_id"] == "o1"
    assert any("SKIP LOCKED" in call[0] for call in session.calls)


@pytest.mark.asyncio
async def test_postgres_outbox_rejects_invalid_terminal_status():
    with pytest.raises(ValueError):
        await PostgresOutboxStore(Session()).transition(tenant_id="tenant-a", outbox_id="o1", worker_id="w1", claim_version=1, status="pending")


@pytest.mark.asyncio
async def test_postgres_audit_requires_tenant_and_writes_immutable_event():
    audit = DispatchAudit(mission_id="m1", objective="TEST", agents_used=("a",), sources_used=(), claims_verified=(), risks_flagged=(), user_approval="none", external_action_taken=False, final_output_hash="h", status="blocked")
    session = Session()
    store = PostgresAuditStore(session)
    with pytest.raises(ValueError):
        await store.append(audit, tenant_id="")
    await store.append(audit, tenant_id="tenant-a")
    assert any("INSERT INTO a2a_audit_events" in call[0] and "FALSE" in call[0] for call in session.calls)
