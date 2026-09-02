from __future__ import annotations

import pytest
from test_s1_failure_taxonomy import invoke_or_error, policy, provider, request

from governed_inference.contracts import InferenceError, ProviderErrorKind
from governed_inference.providers import MockProvider
from governed_inference.router import GovernedInferenceRouter


class BadSchemaProvider(MockProvider):
    def invoke(self, _req):
        raise InferenceError("response schema invalid", ProviderErrorKind.SCHEMA_INVALID)


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        (ProviderErrorKind.TIMEOUT_FIRST_BYTE, "TIMEOUT_FIRST_BYTE"),
        (ProviderErrorKind.TIMEOUT_PROGRESS, "TIMEOUT_PROGRESS"),
        (ProviderErrorKind.RATE_LIMITED, "RATE_LIMITED"),
        (ProviderErrorKind.PROVIDER_5XX, "PROVIDER_5XX"),
        (ProviderErrorKind.MALFORMED_RESPONSE, "MALFORMED_RESPONSE"),
        (ProviderErrorKind.SCHEMA_INVALID, "SCHEMA_INVALID"),
        (ProviderErrorKind.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_failure_classification_and_different_provider_failover(kind, label):
    ledger = __import__("governed_inference.ledger", fromlist=["InferenceLedger"]).InferenceLedger()
    router = GovernedInferenceRouter(
        [provider("provider-a", error_kind=kind), provider("provider-b")],
        policy=policy(), ledger=ledger,
    )
    result = router.invoke(request())
    assert result.provider == "provider-b", label
    failure = next(e for e in ledger.events if e["event"] == "inference.attempt_failed")
    assert failure["error_kind"] == kind.value
    assert [e["provider"] for e in ledger.events if e["event"] == "inference.attempt_started"] == ["provider-a", "provider-b"]


@pytest.mark.parametrize("kind", [ProviderErrorKind.AUTH_FAILURE, ProviderErrorKind.POLICY_DENIED])
def test_authority_and_auth_failures_stop_without_provider_shopping(kind):
    ledger = __import__("governed_inference.ledger", fromlist=["InferenceLedger"]).InferenceLedger()
    router = GovernedInferenceRouter(
        [provider("provider-a", error_kind=kind), provider("provider-b")],
        policy=policy(), ledger=ledger,
    )
    _, error = invoke_or_error(router, request())
    assert error is not None
    assert error.kind is kind
    assert [e["provider"] for e in ledger.events if e["event"] == "inference.attempt_started"] == ["provider-a"]
    assert not any(e["event"] == "inference.fallback_selected" for e in ledger.events)


def test_schema_invalid_is_provider_response_failure_and_fails_over():
    ledger = __import__("governed_inference.ledger", fromlist=["InferenceLedger"]).InferenceLedger()
    router = GovernedInferenceRouter(
        [BadSchemaProvider(name="provider-a", model="fixture", route_tier=provider("x").route_tier, capabilities=("summarization",), estimated_cost_usd=0), provider("provider-b")],
        policy=policy(), ledger=ledger,
    )
    result = router.invoke(request())
    assert result.provider == "provider-b"


def test_attempt_policy_is_explicit_and_bounded():
    assert policy().per_request.max_attempts_per_provider == 1
    ledger = __import__("governed_inference.ledger", fromlist=["InferenceLedger"]).InferenceLedger()
    router = GovernedInferenceRouter(
        [provider("provider-a", error_kind=ProviderErrorKind.PROVIDER_5XX), provider("provider-b")],
        policy=policy(max_attempts=3), ledger=ledger,
    )
    router.invoke(request())
    attempts = [e for e in ledger.events if e["event"] == "inference.attempt_started"]
    assert len(attempts) == 2
    assert attempts[0]["provider"] != attempts[1]["provider"]
