from __future__ import annotations

import threading

import pytest

from governed_inference.contracts import (
    DataClassification,
    InferenceError,
    InferencePolicy,
    InferenceRequest,
    ProviderErrorKind,
    QualityFloor,
    RouteTier,
)
from governed_inference.ledger import InferenceLedger
from governed_inference.providers import MockProvider
from governed_inference.router import GovernedInferenceRouter
from swarm_runtime.inference_adapter import SwarmInferenceAdapter, WorkerInferenceRequest


def request() -> InferenceRequest:
    return InferenceRequest(
        request_id="cancelled-request",
        task_type="summarization",
        capability="summarization",
        messages=[{"role": "user", "content": "bounded"}],
        data_classification=DataClassification.INTERNAL,
    )


def provider(name: str, kind: ProviderErrorKind = ProviderErrorKind.CANCELLED) -> MockProvider:
    return MockProvider(name=name, model=f"model-{name}", route_tier=RouteTier.LOCAL_PRIVATE, capabilities=("summarization",), quality=QualityFloor.PREMIUM if name == "primary" else QualityFloor.STANDARD, estimated_cost_usd=0, fail_times=1, error_kind=kind)


def attempted(ledger: InferenceLedger) -> list[str]:
    return [event["provider"] for event in ledger.events if event["event"] == "inference.attempt_started"]


def test_router_cancellation_is_terminal_without_failover() -> None:
    ledger = InferenceLedger()
    router = GovernedInferenceRouter([provider("primary"), provider("fallback")], ledger=ledger, policy=InferencePolicy(provider_priority={"primary": 0, "fallback": 1}))
    with pytest.raises(InferenceError) as caught:
        router.invoke(request())
    assert caught.value.kind == ProviderErrorKind.CANCELLED
    assert attempted(ledger) == ["primary"]
    assert not any(event["event"] == "inference.fallback_selected" for event in ledger.events)


def test_adapter_pre_inference_cancellation_is_terminal() -> None:
    ledger = InferenceLedger()
    router = GovernedInferenceRouter([provider("primary"), provider("fallback")], ledger=ledger)
    adapter = SwarmInferenceAdapter(router)
    cancelled = threading.Event()
    cancelled.set()
    result = adapter.invoke(WorkerInferenceRequest(worker_id="w", task_id="t", task_type="summarization", capability="summarization", messages=[]), cancel_event=cancelled)
    assert result.error == ProviderErrorKind.CANCELLED.value
    assert result.attempts == 0
    assert attempted(ledger) == []
