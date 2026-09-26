from __future__ import annotations

import asyncio

import pytest

from orchestration.a2a_audit import A2AAuditStore
from orchestration.a2a_governance import ApprovalReceipt, DispatchAudit
from orchestration.approval_store import ApprovalStore
from orchestration.outbox import DurableOutbox
from orchestration.persistence import ShadowMismatchError
from orchestration.shadow_reconciliation import ShadowLifecycleRecorder, ShadowMismatchStore, ShadowMirror, reconcile_records


def test_mirror_success_and_durable_mismatch(tmp_path):
    store = ShadowMismatchStore(str(tmp_path / "mismatch.jsonl"))
    mirror = ShadowMirror(store)
    assert mirror.mirror(tenant_id="t1", lifecycle_area="audit", local_write=lambda: {"key": "k", "status": "ok"}, postgres_write=lambda: {"key": "k", "status": "ok"})["status"] == "ok"
    with pytest.raises(ShadowMismatchError):
        mirror.mirror(tenant_id="t1", lifecycle_area="approval", local_write=lambda: {"key": "k", "status": "issued"}, postgres_write=lambda: {"key": "k", "status": "used"})
    record = store.read()[0]
    assert record["certification_blocked"] is True
    assert record["lifecycle_area"] == "approval"
    assert store.integrity_check()["records"] == 1


@pytest.mark.asyncio
async def test_async_mirror_fail_closed_on_postgres_write_error(tmp_path):
    store = ShadowMismatchStore(str(tmp_path / "mismatch.jsonl"))
    mirror = ShadowMirror(store)
    async def postgres_write():
        raise ConnectionError("database unavailable")
    with pytest.raises(ShadowMismatchError):
        await mirror.mirror_async(tenant_id="t1", lifecycle_area="outbox", local_write=lambda: {"key": "o1", "status": "pending"}, postgres_write=postgres_write)
    assert store.read()[0]["severity"] == "critical"


def test_reconciliation_reports_missing_and_divergent_records():
    report = reconcile_records(
        local=[{"idempotency_key": "a", "status": "issued"}, {"idempotency_key": "b", "status": "pending"}],
        postgres=[{"idempotency_key": "a", "status": "used"}, {"idempotency_key": "c", "status": "pending"}],
    )
    assert report["missing_in_postgres"] == ["b"]
    assert report["missing_in_jsonl"] == ["c"]
    assert report["divergent"] == ["a"]
    assert report["certification_blocked"] is True


def test_concrete_jsonl_stores_emit_lifecycle_observations(tmp_path):
    recorder = ShadowLifecycleRecorder()
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"), shadow_recorder=recorder)
    audit.append(DispatchAudit("m1", "TEST", ("a",), (), (), (), "none", False, "h", "ok"))
    approval = ApprovalStore(str(tmp_path / "approval.jsonl"), shadow_recorder=recorder)
    receipt = ApprovalReceipt("u", "o", "b", "h", sender_agent_id="a", tenant_id="t1", expires_at=9999999999)
    approval.issue(receipt)
    outbox = DurableOutbox(str(tmp_path / "outbox.jsonl"), shadow_recorder=recorder)
    outbox.enqueue(receipt_id=receipt.receipt_id, sender_agent_id="a", tenant_id="t1", recipient="b", payload_hash="h")
    areas = {item["lifecycle_area"] for item in recorder.observations}
    assert {"audit_event", "approval_issued", "outbox_intent"} <= areas


@pytest.mark.parametrize("area,local,postgres", [
    ("audit_event", {"k": "a"}, {"k": "b"}),
    ("approval_issue", {"status": "issued"}, {"status": "revoked"}),
    ("approval_revoke", {"status": "revoked"}, {"status": "issued"}),
    ("approval_expire", {"status": "expired"}, {"status": "issued"}),
    ("approval_consume", {"status": "used"}, {"status": "issued"}),
    ("outbox_intent", {"status": "pending"}, {"status": "missing"}),
    ("outbox_validate", {"status": "validated"}, {"status": "blocked"}),
    ("outbox_claim", {"worker": "w1"}, {"worker": "w2"}),
    ("outbox_block", {"status": "blocked"}, {"status": "pending"}),
    ("outbox_fail", {"status": "failed"}, {"status": "pending"}),
    ("outbox_dlq", {"status": "dlq"}, {"status": "failed"}),
    ("redis_delivery", {"attempt": 1}, {"attempt": 2}),
])
def test_each_lifecycle_mismatch_blocks_certification(tmp_path, area, local, postgres):
    store = ShadowMismatchStore(str(tmp_path / f"{area}.jsonl"))
    with pytest.raises(ShadowMismatchError):
        ShadowMirror(store).mirror(tenant_id="t1", lifecycle_area=area, local_write=lambda: local, postgres_write=lambda: postgres)
    assert store.read()[0]["certification_blocked"] is True
