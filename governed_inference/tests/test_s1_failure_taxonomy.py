from __future__ import annotations

import json

import pytest

from governed_inference.contracts import (
    DataClassification,
    InferenceError,
    InferencePolicy,
    InferenceRequest,
    PerRequestPolicy,
    ProviderErrorKind,
    QualityFloor,
    RouteTier,
)
from governed_inference.ledger import InferenceLedger
from governed_inference.providers import MockProvider
from governed_inference.router import GovernedInferenceRouter


def request() -> InferenceRequest:
    return InferenceRequest.new(
        task_type="summarization",
        capability="summarization",
        messages=[{"role": "user", "content": "bounded evidence"}],
        max_input_tokens=100,
        max_output_tokens=100,
    )


def policy(*, max_attempts: int = 1) -> InferencePolicy:
    return InferencePolicy(
        per_request=PerRequestPolicy(
            max_input_tokens=100,
            max_output_tokens=100,
            max_attempts=max_attempts,
            max_attempts_per_provider=1,
            timeout_seconds=1,
        )
    )


def provider(name: str, *, error_kind: ProviderErrorKind | None = None, quality=QualityFloor.STANDARD) -> MockProvider:
    return MockProvider(
        name=name,
        model="fixture",
        route_tier=RouteTier.LOCAL_PRIVATE,
        capabilities=("summarization",),
        fail_times=1 if error_kind else 0,
        error_kind=error_kind or ProviderErrorKind.TRANSIENT,
        estimated_cost_usd=0,
        quality=quality,
    )


def invoke_or_error(router: GovernedInferenceRouter, req: InferenceRequest):
    try:
        return router.invoke(req), None
    except InferenceError as exc:
        return None, exc


def run(providers: list[MockProvider], *, max_attempts: int = 1):
    ledger = InferenceLedger()
    router = GovernedInferenceRouter(providers, policy=policy(max_attempts=max_attempts), ledger=ledger)
    result, error = invoke_or_error(router, request())
    return result, error, ledger


def test_success_is_one_attempt_and_one_final_result():
    result, _, ledger = run([provider("good")])
    assert result.provider == "good"
    assert result.attempts == 1
    assert len(ledger.receipts) == 1


@pytest.mark.parametrize(
    "kind",
    [
        ProviderErrorKind.TIMEOUT_FIRST_BYTE,
        ProviderErrorKind.TIMEOUT_PROGRESS,
        ProviderErrorKind.RATE_LIMITED,
        ProviderErrorKind.PROVIDER_5XX,
        ProviderErrorKind.MALFORMED_RESPONSE,
        ProviderErrorKind.SCHEMA_INVALID,
        ProviderErrorKind.PROVIDER_UNAVAILABLE,
    ],
)
def test_failover_eligible_provider_failures_select_next_provider(kind):
    result, _, ledger = run([provider("provider-a", error_kind=kind), provider("provider-b")])
    assert result.provider == "provider-b"
    assert result.attempts == 1
    assert ledger.reliability["provider-a"].failures == 1
    events = [e["event"] for e in ledger.events]
    assert "inference.fallback_selected" in events


@pytest.mark.parametrize("kind", [ProviderErrorKind.AUTH_FAILURE, ProviderErrorKind.POLICY_DENIED])
def test_non_failover_failures_do_not_provider_shop(kind):
    failing = provider("provider-a", error_kind=kind)
    result, error, ledger = run([failing, provider("provider-b")])
    assert result is None
    assert error is not None
    assert error.kind is kind
    assert failing.invoke_count == 1
    assert "provider-b" not in [e.get("provider") for e in ledger.events]


def test_provider_exhaustion_is_bounded_and_fails():
    result, error, ledger = run(
        [provider("provider-a", error_kind=ProviderErrorKind.PROVIDER_5XX),
         provider("provider-b", error_kind=ProviderErrorKind.PROVIDER_5XX)]
    )
    assert result is None
    assert error is not None
    assert error.kind is ProviderErrorKind.PROVIDER_5XX
    assert sum(1 for e in ledger.events if e["event"] == "inference.attempt_started") == 2


def test_max_attempts_per_provider_is_one():
    primary = provider(
        "provider-a", error_kind=ProviderErrorKind.PROVIDER_5XX,
        quality=QualityFloor.PREMIUM,
    )
    fallback = provider("provider-b", quality=QualityFloor.STANDARD)
    ledger = InferenceLedger()
    router = GovernedInferenceRouter([primary, fallback], policy=policy(max_attempts=3), ledger=ledger)
    candidates, _ = router._build_candidates(
        request(), DataClassification.INTERNAL, None,
    )
    assert candidates[0].provider == "provider-a"
    assert candidates[1].provider == "provider-b"
    result = router.invoke(request())
    assert result.provider == "provider-b"
    attempts = [e for e in ledger.events if e["event"] == "inference.attempt_started"]
    assert len(attempts) == 2


def test_policy_denial_is_not_converted_to_failover():
    ledger = InferenceLedger()
    denied = MockProvider(
        name="denied", model="fixture", route_tier=RouteTier.LOCAL_PRIVATE,
        capabilities=("summarization",), estimated_cost_usd=0,
        fail_times=1, error_kind=ProviderErrorKind.POLICY_DENIED,
    )
    router = GovernedInferenceRouter([denied, provider("other")], policy=policy(), ledger=ledger)
    result, error = invoke_or_error(router, request())
    assert result is None
    assert error is not None
    assert error.kind is ProviderErrorKind.POLICY_DENIED
    assert denied.invoke_count == 1


def test_attempt_evidence_contains_no_secret_material():
    ledger = InferenceLedger()
    secret = "sk-test-secret-value"
    class SecretProvider(MockProvider):
        def invoke(self, _req):
            raise InferenceError(secret, ProviderErrorKind.PROVIDER_5XX)
    router = GovernedInferenceRouter([SecretProvider(name="secret", model="fixture", route_tier=RouteTier.LOCAL_PRIVATE, capabilities=("summarization",), estimated_cost_usd=0)], policy=policy(), ledger=ledger)
    result, error = invoke_or_error(router, request())
    assert result is None
    assert error is not None
    serialized = json.dumps(ledger.events, default=str)
    assert secret not in serialized
