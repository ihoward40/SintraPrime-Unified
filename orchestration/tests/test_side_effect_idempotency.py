"""Durable workflow side-effect idempotency acceptance tests."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from orchestration.durable_execution import (
    DurableWorkflowEngine,
    ProviderExecutionResult,
    SideEffectConflictError,
    SideEffectProvider,
    WorkflowRecord,
    WorkflowStatus,
)


class AcceptedButTimedOut(TimeoutError):
    def __init__(self, provider_request_id: str):
        super().__init__("provider accepted mutation before timeout")
        self.provider_request_id = provider_request_id


class DeterministicProvider(SideEffectProvider):
    name = "deterministic"

    def __init__(
        self,
        *,
        accepted_timeout_once: bool = False,
        supports_native_idempotency: bool = True,
        fail_receipt_once: bool = False,
    ) -> None:
        self.accepted_timeout_once = accepted_timeout_once
        self.supports_native_idempotency = supports_native_idempotency
        self.fail_receipt_once = fail_receipt_once
        self.mutation_count = 0
        self._results: Dict[str, ProviderExecutionResult] = {}

    async def execute(
        self,
        request: Dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ProviderExecutionResult:
        existing = self._results.get(idempotency_key)
        if existing is not None:
            return existing
        self.mutation_count += 1
        result = ProviderExecutionResult(
            provider_request_id=f"provider-{self.mutation_count}",
            result_reference={"remote_id": f"remote-{self.mutation_count}"},
        )
        self._results[idempotency_key] = result
        await asyncio.sleep(0.05)
        if self.accepted_timeout_once:
            self.accepted_timeout_once = False
            raise AcceptedButTimedOut(result.provider_request_id)
        return result

    async def verify_or_reconcile(
        self,
        *,
        idempotency_key: str,
        provider_request_id: Optional[str],
    ) -> Optional[ProviderExecutionResult]:
        result = self._results.get(idempotency_key)
        if result is None:
            return None
        if provider_request_id is None or provider_request_id == result.provider_request_id:
            return result
        return None


def _engine(path: Path) -> DurableWorkflowEngine:
    engine = DurableWorkflowEngine(db_path=str(path))
    engine._store.claim_workflow(
        WorkflowRecord(
            workflow_id="wf-1",
            workflow_type="side-effect-test",
            status=WorkflowStatus.CLAIMED,
            state={},
        )
    )
    return engine


@pytest.mark.asyncio
async def test_same_logical_mutation_replay_calls_provider_once(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")
    provider = DeterministicProvider()
    kwargs = dict(
        tenant_id="tenant-1",
        workflow_id="wf-1",
        activity_id="send-message",
        target_type="message",
        target_identifier="recipient-1",
        request={"body": "hello"},
        provider=provider,
    )
    try:
        first = await engine.execute_idempotent_side_effect(**kwargs)
        second = await engine.execute_idempotent_side_effect(**kwargs)
        assert first == second
        assert provider.mutation_count == 1
    finally:
        engine.close()


@pytest.mark.asyncio
async def test_same_key_changed_payload_is_conflict(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")
    provider = DeterministicProvider()
    try:
        await engine.execute_idempotent_side_effect(
            tenant_id="tenant-1", workflow_id="wf-1", activity_id="write",
            target_type="record", target_identifier="target-1",
            request={"value": 1}, provider=provider,
            idempotency_key="stable-external-key",
        )
        with pytest.raises(SideEffectConflictError):
            await engine.execute_idempotent_side_effect(
                tenant_id="tenant-1", workflow_id="wf-1", activity_id="write",
                target_type="record", target_identifier="target-1",
                request={"value": 2}, provider=provider,
                idempotency_key="stable-external-key",
            )
    finally:
        engine.close()


@pytest.mark.asyncio
async def test_provider_accepts_then_times_out_reconciles_without_retry(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")
    provider = DeterministicProvider(accepted_timeout_once=True)
    try:
        result = await engine.execute_idempotent_side_effect(
            tenant_id="tenant-1", workflow_id="wf-1", activity_id="submit",
            target_type="filing", target_identifier="court-1",
            request={"filing": "A"}, provider=provider,
        )
        assert result == {"remote_id": "remote-1"}
        assert provider.mutation_count == 1
    finally:
        engine.close()


@pytest.mark.asyncio
async def test_local_receipt_loss_reconciles_prior_provider_success(tmp_path: Path) -> None:
    db_path = tmp_path / "durable.db"
    engine = _engine(db_path)
    provider = DeterministicProvider(fail_receipt_once=True)
    kwargs = dict(
        tenant_id="tenant-1", workflow_id="wf-1", activity_id="connector-write",
        target_type="connector", target_identifier="crm-1",
        request={"record": "A"}, provider=provider,
    )
    try:
        with pytest.raises(RuntimeError, match="simulated local receipt loss"):
            await engine.execute_idempotent_side_effect(**kwargs)
    finally:
        engine.close()

    replay = DurableWorkflowEngine(db_path=str(db_path))
    try:
        result = await replay.execute_idempotent_side_effect(**kwargs)
        assert result == {"remote_id": "remote-1"}
        assert provider.mutation_count == 1
    finally:
        replay.close()


@pytest.mark.asyncio
async def test_timeout_with_unverifiable_remote_outcome_stays_unknown(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")

    class UnverifiableProvider(DeterministicProvider):
        async def verify_or_reconcile(
            self,
            *,
            idempotency_key: str,
            provider_request_id: Optional[str],
        ) -> Optional[ProviderExecutionResult]:
            return None

    provider = UnverifiableProvider(accepted_timeout_once=True)
    kwargs = dict(
        tenant_id="tenant-1", workflow_id="wf-1", activity_id="submit-unknown",
        target_type="filing", target_identifier="court-unknown",
        request={"filing": "unknown"}, provider=provider,
    )
    try:
        with pytest.raises(AcceptedButTimedOut):
            await engine.execute_idempotent_side_effect(**kwargs)
        record = engine._store.get_side_effect(
            engine.derive_side_effect_identity(
                workflow_id="wf-1",
                activity_id="submit-unknown",
                target_type="filing",
                target_identifier="court-unknown",
                request={"filing": "unknown"},
            )[0]
        )
        assert record is not None
        assert record.status.value == "unknown"
        assert provider.mutation_count == 1
    finally:
        engine.close()


@pytest.mark.asyncio
async def test_two_workers_race_same_side_effect_key_one_provider_mutation(tmp_path: Path) -> None:
    db_path = tmp_path / "durable.db"
    engine_a = _engine(db_path)
    engine_b = DurableWorkflowEngine(db_path=str(db_path))
    provider = DeterministicProvider(supports_native_idempotency=False)
    kwargs = dict(
        tenant_id="tenant-1", workflow_id="wf-1", activity_id="external-write",
        target_type="external", target_identifier="target-1",
        request={"value": "same"}, provider=provider,
    )
    try:
        results = await asyncio.gather(
            engine_a.execute_idempotent_side_effect(**kwargs),
            engine_b.execute_idempotent_side_effect(**kwargs),
        )
        assert results[0] == results[1]
        assert provider.mutation_count == 1
    finally:
        engine_a.close()
        engine_b.close()


@pytest.mark.asyncio
async def test_workflow_replay_does_not_duplicate_completed_external_mutation(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")
    provider = DeterministicProvider()
    kwargs = dict(
        tenant_id="tenant-1", workflow_id="wf-1", activity_id="notify",
        target_type="notification", target_identifier="recipient-1",
        request={"message": "approved"}, provider=provider,
    )
    try:
        await engine.execute_idempotent_side_effect(**kwargs)
        await engine.execute_idempotent_side_effect(**kwargs)
        assert provider.mutation_count == 1
    finally:
        engine.close()


@pytest.mark.asyncio
async def test_different_workflow_or_activity_allows_distinct_side_effect(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "durable.db")
    provider = DeterministicProvider()
    try:
        await engine.execute_idempotent_side_effect(
            tenant_id="tenant-1", workflow_id="wf-1", activity_id="step-a",
            target_type="record", target_identifier="target-1",
            request={"value": 1}, provider=provider,
        )
        engine._store.claim_workflow(
            WorkflowRecord(
                workflow_id="wf-2",
                workflow_type="side-effect-test",
                status=WorkflowStatus.CLAIMED,
                state={},
            )
        )
        await engine.execute_idempotent_side_effect(
            tenant_id="tenant-1", workflow_id="wf-2", activity_id="step-a",
            target_type="record", target_identifier="target-1",
            request={"value": 1}, provider=provider,
        )
        await engine.execute_idempotent_side_effect(
            tenant_id="tenant-1", workflow_id="wf-1", activity_id="step-b",
            target_type="record", target_identifier="target-1",
            request={"value": 1}, provider=provider,
        )
        assert provider.mutation_count == 3
    finally:
        engine.close()
