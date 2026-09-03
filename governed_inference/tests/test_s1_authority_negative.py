from __future__ import annotations

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


def _request() -> InferenceRequest:
    return InferenceRequest(
        request_id="authority-negative",
        messages=[{"role": "user", "content": "bounded"}],
        task_type="summarization",
        capability="summarization",
        data_classification=DataClassification.INTERNAL,
    )


def _provider(name: str, *, fail_times: int = 0, error_kind: ProviderErrorKind = ProviderErrorKind.PROVIDER_5XX) -> MockProvider:
    return MockProvider(
        name=name,
        model=f"model-{name}",
        route_tier=RouteTier.LOCAL_PRIVATE,
        capabilities=("summarization",),
        quality=QualityFloor.STANDARD,
        estimated_cost_usd=0,
        fail_times=fail_times,
        error_kind=error_kind,
    )


def _attempted(ledger: InferenceLedger) -> list[str]:
    return [event["provider"] for event in ledger.events if event["event"] == "inference.attempt_started"]


def test_task_cannot_rank_providers() -> None:
    task = {"preferred_provider_order": ["fallback", "primary"], "provider_order": ["fallback", "primary"]}
    ledger = InferenceLedger()
    router = GovernedInferenceRouter([_provider("primary", fail_times=1), _provider("fallback")], ledger=ledger, policy=InferencePolicy(provider_priority={"primary": 0, "fallback": 1}))
    result = router.invoke(_request())
    assert task["preferred_provider_order"] == ["fallback", "primary"]
    assert _attempted(ledger) == ["primary", "fallback"]
    assert result.provider == "fallback"


def test_worker_cannot_rank_providers() -> None:
    from swarm_runtime.tool_workers import ModelReasoningWorker

    assert not hasattr(ModelReasoningWorker, "set_provider_order")
    assert not hasattr(ModelReasoningWorker, "set_primary_provider")
    assert not hasattr(ModelReasoningWorker, "set_fallback_provider")
    names = ModelReasoningWorker.execute.__code__.co_names
    assert "preferred_provider_order" not in names
    assert "provider_order" not in names
    assert "primary_provider" not in names
    assert "fallback_provider" not in names


def test_auth_failure_no_failover_normalized() -> None:
    ledger = InferenceLedger()
    router = GovernedInferenceRouter(
        [_provider("primary", fail_times=1, error_kind=ProviderErrorKind.AUTH_FAILURE), _provider("fallback", fail_times=1, error_kind=ProviderErrorKind.AUTH_FAILURE)],
        policy=InferencePolicy(provider_priority={"primary": 0, "fallback": 1}),
        ledger=ledger,
    )
    with pytest.raises(InferenceError) as caught:
        router.invoke(_request())
    assert caught.value.kind == ProviderErrorKind.AUTH_FAILURE
    assert _attempted(ledger) == ["primary"]
    assert not any(event["event"] == "inference.fallback_selected" for event in ledger.events)
