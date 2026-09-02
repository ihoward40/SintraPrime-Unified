from __future__ import annotations

from governed_inference.contracts import (
    DataClassification,
    InferencePolicy,
    InferenceRequest,
    PerRequestPolicy,
    QualityFloor,
    RouteTier,
)
from governed_inference.ledger import InferenceLedger
from governed_inference.providers import MockProvider
from governed_inference.router import GovernedInferenceRouter


def request(request_id: str) -> InferenceRequest:
    return InferenceRequest(
        request_id=request_id,
        task_type="summarization",
        capability="summarization",
        messages=[{"role": "user", "content": "tie"}],
        data_classification=DataClassification.INTERNAL,
    )


def run(names: list[str]) -> str:
    ledger = InferenceLedger()
    providers = [
        MockProvider(
            name=name,
            model=f"model-{name}",
            route_tier=RouteTier.LOCAL_PRIVATE,
            capabilities=("summarization",),
            quality=QualityFloor.STANDARD,
            estimated_cost_usd=0,
        )
        for name in names
    ]
    router = GovernedInferenceRouter(
        providers,
        policy=InferencePolicy(per_request=PerRequestPolicy(max_attempts=1, max_attempts_per_provider=1)),
        ledger=ledger,
    )
    router.invoke(request("-".join(names)))
    return next(event["provider"] for event in ledger.events if event["event"] == "inference.attempt_started")


def run_with_priority(names: list[str], priority: dict[str, int]) -> str:
    ledger = InferenceLedger()
    providers = [
        MockProvider(name=name, model=f"model-{name}", route_tier=RouteTier.LOCAL_PRIVATE,
                     capabilities=("summarization",), quality=QualityFloor.STANDARD,
                     estimated_cost_usd=0)
        for name in names
    ]
    router = GovernedInferenceRouter(
        providers,
        policy=InferencePolicy(
            provider_priority=priority,
            per_request=PerRequestPolicy(max_attempts=1, max_attempts_per_provider=1),
        ),
        ledger=ledger,
    )
    router.invoke(request("priority-" + "-".join(names)))
    return next(event["provider"] for event in ledger.events if event["event"] == "inference.attempt_started")


def test_equal_score_provider_input_order_cannot_select_first_provider() -> None:
    first_ab = run(["A", "B"])
    first_ba = run(["B", "A"])
    assert first_ab == first_ba == "A"


def test_governed_priority_overrides_fixture_order() -> None:
    assert run_with_priority(["A", "B"], {"A": 20, "B": 10}) == "B"
    assert run_with_priority(["B", "A"], {"A": 20, "B": 10}) == "B"
    assert run_with_priority(["A", "B"], {"A": 10, "B": 20}) == "A"
    assert run_with_priority(["B", "A"], {"A": 10, "B": 20}) == "A"


def test_explicit_priority_beats_unspecified() -> None:
    assert run_with_priority(["A", "B"], {"A": 10}) == "A"
    assert run_with_priority(["B", "A"], {"A": 10}) == "A"


def test_unspecified_providers_use_identity_deterministically() -> None:
    assert run(["A", "B"]) == run(["B", "A"]) == "A"


def test_unspecified_provider_does_not_outrank_explicit_provider() -> None:
    assert run_with_priority(["A", "B", "C"], {"A": 20, "B": 10}) == "B"
