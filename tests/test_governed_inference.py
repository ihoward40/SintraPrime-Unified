from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from governed_inference import (
    CacheStatus,
    DataClassification,
    DeterministicReplayProvider,
    EscalationQueue,
    GovernedInferenceRouter,
    InferencePolicy,
    InferenceRequest,
    LMStudioProvider,
    MockProvider,
    OmniRouteProvider,
    OpenRouterProvider,
    PaidAuthorization,
    PremiumApprovedProvider,
    QualityFloor,
    RouteTier,
    decompose_for_local_models,
)
from governed_inference.contracts import InferenceError, ProviderErrorKind, ProviderReliability
from governed_inference.ledger import InferenceLedger
from governed_inference.policy import merge_policy_strictest
from governed_inference.providers import GroqProvider


def request(**kwargs):
    defaults = {
        "request_id": "req-test",
        "task_type": "summarize_restricted",
        "capability": "summarization",
        "messages": [{"role": "user", "content": "Review this trust evidence for my client."}],
        "max_input_tokens": 100,
        "max_output_tokens": 100,
    }
    defaults.update(kwargs)
    return InferenceRequest(**defaults)


def test_sensitive_request_uses_local_and_blocks_cloud_by_default():
    local = MockProvider(name="local")
    cloud = MockProvider(
        name="cloud",
        route_tier=RouteTier.CLOUD_PROTOTYPE,
        cloud=True,
        estimated_cost_usd=0.0,
    )
    router = GovernedInferenceRouter([cloud, local])

    result = router.invoke(request())

    assert result.provider == "local"
    assert any(
        event["event"] == "inference.classified"
        and event["classification"] == DataClassification.RESTRICTED_LEGAL.value
        for event in router.ledger.events
    )


def test_paid_route_denied_when_global_switch_false_even_with_request_approval():
    premium = PremiumApprovedProvider(configured=True)
    router = GovernedInferenceRouter([premium])
    approval = PaidAuthorization(
        actor="admin",
        scope="global",
        max_amount_usd=10.0,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        purpose="test",
        policy_receipt_id="policy",
    )

    with pytest.raises(InferenceError) as exc:
        router.invoke(
            request(
                data_classification=DataClassification.PUBLIC,
                paid_use_authorized=True,
                capability="coding",
            ),
            authorization=approval,
        )

    assert exc.value.kind == ProviderErrorKind.POLICY_DENIED
    receipt = next(iter(router.ledger.receipts.values()))
    assert receipt.rejected_routes[0].reason == "global_paid_models_disabled"


def test_unknown_cloud_cost_fails_closed_not_zero():
    cloud = GroqProvider(configured=True)
    router = GovernedInferenceRouter([cloud])

    with pytest.raises(InferenceError):
        router.invoke(request(data_classification=DataClassification.PUBLIC))

    receipt = next(iter(router.ledger.receipts.values()))
    assert receipt.rejected_routes[0].reason == "unknown_cloud_cost"


def test_omniroute_and_openrouter_are_ineligible_until_cost_is_known():
    router = GovernedInferenceRouter(
        [OmniRouteProvider(configured=True), OpenRouterProvider(configured=True)]
    )

    with pytest.raises(InferenceError):
        router.invoke(request(data_classification=DataClassification.PUBLIC, capability="coding"))

    receipt = next(iter(router.ledger.receipts.values()))
    assert {route.reason for route in receipt.rejected_routes} == {"unknown_cloud_cost"}


def test_configured_free_gateway_can_handle_public_non_sensitive_work():
    gateway = OmniRouteProvider(configured=True, estimated_cost_usd=0.0)
    policy = InferencePolicy(daily_budget_usd=1.0)
    router = GovernedInferenceRouter([gateway], policy=policy)

    with pytest.raises(InferenceError) as exc:
        router.invoke(request(data_classification=DataClassification.PUBLIC, capability="coding"))

    assert exc.value.kind == ProviderErrorKind.UNKNOWN
    assert router.escalation_queue.items[0].reason == "eligible_routes_failed"


def test_strict_policy_merge_cannot_weaken_parent():
    parent = InferencePolicy(paid_models_allowed=False, cloud_sensitive_data_allowed=False)
    child = InferencePolicy(
        paid_models_allowed=True,
        cloud_sensitive_data_allowed=True,
        daily_budget_usd=100.0,
    )

    merged = merge_policy_strictest(parent, child)

    assert merged.paid_models_allowed is False
    assert merged.cloud_sensitive_data_allowed is False
    assert merged.daily_budget_usd == 0.0


def test_local_inference_remains_available_when_cloud_disabled_or_unconfigured():
    local = LMStudioProvider(configured=True)
    cloud = GroqProvider(configured=False)
    router = GovernedInferenceRouter([cloud, local])

    result = router.invoke(request(data_classification=DataClassification.PUBLIC))

    assert result.provider == "lmstudio"
    assert result.route_tier == RouteTier.LOCAL_PRIVATE


def test_stream_failure_retries_same_adapter_non_stream_without_partial_concat():
    provider = MockProvider(name="streamy", stream_fails=True)
    router = GovernedInferenceRouter([provider])

    result = router.invoke(request(), stream=True)

    assert result.provider == "streamy"
    assert provider.invoke_count == 1
    assert any(
        event["event"] == "inference.attempt_failed"
        and event.get("stream_partial_preserved") is True
        for event in router.ledger.events
    )


def test_streaming_router_yields_partials_for_stream_supported_provider():
    provider = MockProvider(name="streamy")
    router = GovernedInferenceRouter([provider])

    results = list(router.invoke_stream(
        request(task_type="test", capability="drafting", data_classification=DataClassification.PUBLIC)
    ))

    assert len(results) == 2
    assert results[0].provider == "streamy"
    assert results[0].content == {
        "provider": "streamy",
        "task_type": "test",
        "capability": "drafting",
        "message_count": 1,
    }
    assert getattr(results[0], "is_partial", False) is True
    assert results[-1].provider == "streamy"
    assert not getattr(results[-1], "is_partial", False)
    assert results[-1].policy_receipt_id != "pending"


def test_streaming_router_falls_back_to_invoke_when_provider_does_not_support_streaming():
    class NonStreamingProvider(MockProvider):
        def capabilities(self):
            caps = super().capabilities()
            from dataclasses import replace
            return replace(caps, supports_streaming=False)

    provider = NonStreamingProvider(name="no-stream")
    router = GovernedInferenceRouter([provider])

    results = list(router.invoke_stream(
        request(task_type="test", capability="drafting", data_classification=DataClassification.PUBLIC)
    ))

    assert len(results) == 1
    assert results[0].provider == "no-stream"
    assert results[-1].policy_receipt_id != "pending"
    assert any(event["event"] == "inference.route_selected" for event in router.ledger.events)


def test_transient_retry_is_bounded_and_recorded():
    provider = MockProvider(name="flaky", fail_times=2)
    base = InferencePolicy()
    policy = replace(base, per_request=replace(base.per_request, max_attempts=2))
    router = GovernedInferenceRouter([provider], policy=policy)

    with pytest.raises(InferenceError):
        router.invoke(request())

    failed_events = [
        event for event in router.ledger.events if event["event"] == "inference.attempt_failed"
    ]
    assert len(failed_events) == 2
    assert router.escalation_queue.items[0].reason == "eligible_routes_failed"


def test_exact_cache_hit_is_auditable_and_skips_provider_call():
    provider = MockProvider(name="cache-local")
    router = GovernedInferenceRouter([provider])
    first = router.invoke(request(request_id="first"))
    second = router.invoke(request(request_id="second"))

    assert first.cache_status == CacheStatus.MISS
    assert second.cache_status == CacheStatus.HIT
    assert provider.invoke_count == 1


def test_deterministic_replay_provider_for_ci_without_external_calls():
    source = MockProvider(name="recorded")
    recorded = source.invoke(request(request_id="recorded-id"))
    replay = DeterministicReplayProvider({"recorded-id": recorded})
    router = GovernedInferenceRouter([replay])

    result = router.invoke(request(request_id="recorded-id"))

    assert result.provider == "recorded"
    assert result.content == recorded.content


def test_reliability_floor_blocks_bad_free_provider():
    ledger = InferenceLedger()
    ledger.reliability["bad-free"] = ProviderReliability(
        provider="bad-free",
        successes=1,
        failures=4,
        recent_failures=3,
    )
    provider = MockProvider(
        name="bad-free",
        route_tier=RouteTier.CLOUD_LOW_COST_FAST,
        cloud=True,
        estimated_cost_usd=0.0,
    )
    router = GovernedInferenceRouter(
        [provider], policy=InferencePolicy(daily_budget_usd=1.0), ledger=ledger
    )

    with pytest.raises(InferenceError):
        router.invoke(request(data_classification=DataClassification.PUBLIC))

    receipt = next(iter(router.ledger.receipts.values()))
    assert receipt.rejected_routes[0].reason == "provider_reliability_floor_not_met"


def test_reliability_score_prefers_healthier_free_provider():
    ledger = InferenceLedger()
    ledger.reliability["shaky-free"] = ProviderReliability(
        provider="shaky-free",
        successes=2,
        failures=2,
        recent_failures=2,
    )
    ledger.reliability["steady-free"] = ProviderReliability(provider="steady-free", successes=5)
    shaky = MockProvider(
        name="shaky-free",
        route_tier=RouteTier.CLOUD_LOW_COST_FAST,
        cloud=True,
        estimated_cost_usd=0.0,
    )
    steady = MockProvider(
        name="steady-free",
        route_tier=RouteTier.CLOUD_LOW_COST_FAST,
        cloud=True,
        estimated_cost_usd=0.0,
    )
    router = GovernedInferenceRouter(
        [shaky, steady],
        policy=InferencePolicy(daily_budget_usd=1.0, min_success_rate=0.0),
        ledger=ledger,
    )

    result = router.invoke(request(data_classification=DataClassification.PUBLIC))

    assert result.provider == "steady-free"


def test_complex_work_can_be_decomposed_for_smaller_local_models():
    parts = decompose_for_local_models(
        request(
            request_id="complex-1",
            task_type="code_complex",
            capability="coding",
            max_input_tokens=12000,
            max_output_tokens=5000,
        )
    )

    assert [part.task_type for part in parts] == ["inspect", "plan", "patch", "test"]
    assert all(part.route_tier == RouteTier.LOCAL_PRIVATE for part in parts)
    assert all(part.max_input_tokens <= 6000 for part in parts)


def test_quality_floor_blocks_small_model_for_premium_reasoning():
    local = MockProvider(name="small-local", quality=QualityFloor.BASIC)
    router = GovernedInferenceRouter([local])

    with pytest.raises(InferenceError):
        router.invoke(
            request(
                data_classification=DataClassification.PUBLIC,
                capability="reasoning",
                quality_floor=QualityFloor.HIGH,
            )
        )

    receipt = next(iter(router.ledger.receipts.values()))
    assert receipt.rejected_routes[0].reason == "quality_floor_not_met"


def test_escalation_queue_records_why_no_route_can_run():
    queue = EscalationQueue()
    premium = PremiumApprovedProvider(configured=True)
    router = GovernedInferenceRouter([premium], escalation_queue=queue)

    with pytest.raises(InferenceError):
        router.invoke(request(data_classification=DataClassification.PUBLIC, capability="coding"))

    assert queue.items[0].request_id == "req-test"
    assert queue.items[0].reason == "no_eligible_route"
    assert queue.items[0].denied_routes[0].reason == "global_paid_models_disabled"
