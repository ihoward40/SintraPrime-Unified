from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from packages.async_job_queue import AsyncJobQueue, JobStatus, RetryPolicy


@pytest.fixture
def webhook_events() -> list[tuple[str, str, dict]]:
    return []


@pytest.fixture
def queue(tmp_path, webhook_events: list[tuple[str, str, dict]]) -> AsyncJobQueue:
    return AsyncJobQueue(
        db_path=tmp_path / "jobs.sqlite",
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=2, max_delay_seconds=10),
        webhook_sender=lambda url, event, payload: webhook_events.append((url, event, payload)),
    )


def test_submit_persists_pending(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    assert job.status is JobStatus.PENDING
    assert queue.get(job.task_id) is not None


def test_claim_next_ready_marks_running_and_increments_attempts(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    claimed = queue.claim_next_ready()
    assert claimed is not None
    assert claimed.task_id == job.task_id
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempts == 1


def test_mark_completed_updates_status(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    queue.claim_next_ready()
    done = queue.mark_completed(job.task_id, result={"ok": True})
    assert done.status is JobStatus.COMPLETED
    assert done.last_error is None


def test_mark_failed_sets_retrying_before_limit(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    queue.claim_next_ready()
    failed = queue.mark_failed(job.task_id, error="timeout")
    assert failed.status is JobStatus.RETRYING
    assert failed.last_error == "timeout"


def test_mark_failed_sets_failed_at_limit(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    queue.claim_next_ready()
    queue.mark_failed(job.task_id, error="e1")
    queue.claim_next_ready(as_of=datetime.now(UTC) + timedelta(seconds=10))
    queue.mark_failed(job.task_id, error="e2")
    queue.claim_next_ready(as_of=datetime.now(UTC) + timedelta(seconds=20))
    failed = queue.mark_failed(job.task_id, error="e3")
    assert failed.status is JobStatus.FAILED


@pytest.mark.parametrize(
    ("attempt", "expected_delay"),
    [(1, 2), (2, 4), (3, 8), (8, 10)],
)
def test_retry_policy_exponential_backoff(attempt: int, expected_delay: int) -> None:
    assert RetryPolicy(max_attempts=5, base_delay_seconds=2, max_delay_seconds=10).delay_for_attempt(
        attempt
    ) == expected_delay


def test_retry_policy_rejects_non_positive_attempt() -> None:
    with pytest.raises(ValueError, match="attempt must be >= 1"):
        RetryPolicy().delay_for_attempt(0)


def test_webhook_on_complete(queue: AsyncJobQueue, webhook_events: list[tuple[str, str, dict]]) -> None:
    job = queue.submit({"kind": "ucc"}, callback_url="https://callback")
    queue.claim_next_ready()
    queue.mark_completed(job.task_id, result={"receipt": "r1"})
    assert webhook_events == [("https://callback", "completed", {"receipt": "r1"})]


def test_webhook_on_final_failure(queue: AsyncJobQueue, webhook_events: list[tuple[str, str, dict]]) -> None:
    job = queue.submit({"kind": "ucc"}, callback_url="https://callback")
    for seconds, error in ((0, "e1"), (10, "e2"), (20, "e3")):
        queue.claim_next_ready(as_of=datetime.now(UTC) + timedelta(seconds=seconds))
        queue.mark_failed(job.task_id, error=error)
    assert webhook_events[-1] == ("https://callback", "failed", {"error": "e3"})


def test_claim_next_ready_respects_run_after(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    queue.claim_next_ready()
    queue.mark_failed(job.task_id, error="retry")
    assert queue.claim_next_ready(as_of=datetime.now(UTC)) is None


def test_submit_generates_unique_ids(queue: AsyncJobQueue) -> None:
    one = queue.submit({"kind": "ucc"})
    two = queue.submit({"kind": "court"})
    assert one.task_id != two.task_id


def test_get_missing_returns_none(queue: AsyncJobQueue) -> None:
    assert queue.get("missing") is None


def test_claim_returns_none_when_empty(queue: AsyncJobQueue) -> None:
    assert queue.claim_next_ready() is None


def test_mark_completed_missing_job_raises(queue: AsyncJobQueue) -> None:
    with pytest.raises(KeyError):
        queue.mark_completed("missing", result={"ok": True})


def test_mark_completed_requires_running_state(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    with pytest.raises(KeyError):
        queue.mark_completed(job.task_id, result={"ok": True})


def test_mark_failed_requires_running_state(queue: AsyncJobQueue) -> None:
    job = queue.submit({"kind": "ucc"})
    with pytest.raises(ValueError, match="job must be running"):
        queue.mark_failed(job.task_id, error="nope")
