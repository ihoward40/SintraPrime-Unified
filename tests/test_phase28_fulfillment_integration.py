from __future__ import annotations

from datetime import UTC, datetime, timedelta

from packages.async_job_queue import AsyncJobQueue, JobStatus
from packages.browser_automation import FilingEngine, FilingRequest
from packages.execution_bridge import ExecutionBridge


def test_end_to_end_ucc_flow(tmp_path) -> None:
    bridge = ExecutionBridge()
    payload = bridge.validate_and_transform(
        document="UCC filing body",
        filing_type="ucc-1",
        metadata={
            "debtor_name": "Debtor LLC",
            "secured_party_name": "Secured Inc",
            "collateral": "All assets",
            "jurisdiction": "CA",
        },
    )

    queue = AsyncJobQueue(db_path=tmp_path / "queue.sqlite")
    job = queue.submit({"filing_type": payload.filing_type, "hash": payload.document_hash})
    queue.claim_next_ready()

    filing_result = FilingEngine().file(
        FilingRequest(
            filing_type=payload.filing_type,
            jurisdiction=payload.jurisdiction,
            payload=payload.transformed_fields,
            signer_name="Alex",
        )
    )
    done = queue.mark_completed(job.task_id, result={"filing_id": filing_result.filing_id})

    assert filing_result.status == "submitted"
    assert done.status is JobStatus.COMPLETED


def test_retry_flow_then_success(tmp_path) -> None:
    queue = AsyncJobQueue(db_path=tmp_path / "queue.sqlite")
    job = queue.submit({"filing_type": "court"})
    queue.claim_next_ready()
    retried = queue.mark_failed(job.task_id, error="timeout")
    assert retried.status is JobStatus.RETRYING

    queue.claim_next_ready(as_of=datetime.now(UTC) + timedelta(seconds=2))
    completed = queue.mark_completed(job.task_id, result={"ok": True})
    assert completed.status is JobStatus.COMPLETED


def test_bridge_and_browser_share_document_hash_context() -> None:
    bridge = ExecutionBridge()
    engine = FilingEngine()
    payload = bridge.validate_and_transform(
        document="petition",
        filing_type="court",
        metadata={"case_number": "1", "court_name": "District", "filing_party": "Alice", "jurisdiction": "TX"},
    )
    filing_payload = {"document_hash": payload.document_hash}
    result = engine.file(
        FilingRequest(
            filing_type="court",
            jurisdiction="TX",
            payload=filing_payload,
            signer_name="Alex",
        )
    )
    expected_signature = engine.capture_signature("Alex", filing_payload)
    assert f"sign:{expected_signature}" in result.browser_log
    assert result.receipt_reference.startswith("receipt-tx-")
