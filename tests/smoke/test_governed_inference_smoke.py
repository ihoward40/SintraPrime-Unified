import pytest

from governed_inference import (
    GovernedInferenceRouter,
    InferencePolicy,
    InferenceRequest,
    MockProvider,
    RouteTier,
)

pytestmark = pytest.mark.smoke


def test_mock_provider_invokes_locally():
    provider = MockProvider(name="smoke-local")
    request = InferenceRequest.new(
        task_type="smoke",
        capability="classification",
        messages=[{"role": "user", "content": "hello"}],
    )
    result = provider.invoke(request)
    assert result.provider == "smoke-local"
    assert result.route_tier == RouteTier.LOCAL_PRIVATE
    assert result.content["task_type"] == "smoke"


def test_router_selects_local_provider_by_default():
    policy = InferencePolicy.from_environment()
    router = GovernedInferenceRouter(policy=policy, providers=[MockProvider()])
    request = InferenceRequest.new(
        task_type="smoke",
        capability="classification",
        messages=[{"role": "user", "content": "classify this"}],
    )
    result = router.invoke(request)
    assert result.route_tier == RouteTier.LOCAL_PRIVATE
    assert result.attempts >= 1


def test_router_produces_receipt():
    router = GovernedInferenceRouter(policy=InferencePolicy(), providers=[MockProvider()])
    request = InferenceRequest.new(
        task_type="smoke",
        capability="classification",
        messages=[{"role": "user", "content": "classify this"}],
    )
    result = router.invoke(request)
    receipt = next(
        (r for r in router.ledger.receipts.values() if r.request_id == request.request_id),
        None,
    )
    assert receipt is not None
    assert receipt.selected_provider == "mock-local"
    assert receipt.final_output_hash is not None
