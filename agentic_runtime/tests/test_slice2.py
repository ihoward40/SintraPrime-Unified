import pytest

from agentic_runtime.comfyui_adapter import GovernedComfyUIAdapter
from agentic_runtime.context_pack import ContextItem, ContextPackBuilder
from agentic_runtime.controls import (
    BenchmarkResult,
    CircuitBreaker,
    ExecutionBudget,
    ModelPromotionGate,
    TestDeltaReceipt,
)
from agentic_runtime.media_workflows import MediaJob, MediaKind, MediaWorkflowPolicy


def test_context_pack_is_bounded_and_relevance_ordered():
    pack = ContextPackBuilder(100).build([
        ContextItem("required", "r", 50, required=True),
        ContextItem("low", "l", 40, relevance=.1),
        ContextItem("high", "h", 40, relevance=.9),
    ])
    assert [i.source_id for i in pack.items] == ["required", "high"]
    assert pack.tokens == 90


def test_required_context_fails_closed():
    with pytest.raises(ValueError, match="REQUIRED_CONTEXT_EXCEEDS_BUDGET"):
        ContextPackBuilder(10).build([ContextItem("x", "x", 11, required=True)])


def test_budget_refuses_overspend():
    budget = ExecutionBudget(max_input_tokens=10, max_output_tokens=10, max_cost_usd=1)
    budget.charge(input_tokens=5, output_tokens=2, cost_usd=.25)
    with pytest.raises(RuntimeError, match="COST_BUDGET_EXCEEDED"):
        budget.charge(cost_usd=.76)


def test_budget_refuses_negative_and_token_overruns():
    budget = ExecutionBudget(max_input_tokens=10, max_output_tokens=10, max_cost_usd=1)

    with pytest.raises(ValueError, match="budget charges cannot be negative"):
        budget.charge(input_tokens=-1)

    with pytest.raises(RuntimeError, match="INPUT_TOKEN_BUDGET_EXCEEDED"):
        budget.charge(input_tokens=11)

    with pytest.raises(RuntimeError, match="OUTPUT_TOKEN_BUDGET_EXCEEDED"):
        budget.charge(output_tokens=11)


def test_circuit_breaker_opens():
    breaker = CircuitBreaker(2)
    breaker.record(False); breaker.record(False)
    with pytest.raises(RuntimeError, match="REPAIR_CIRCUIT_OPEN"):
        breaker.assert_closed()


def test_test_delta_detects_regression():
    assert TestDeltaReceipt(10, 0, 9, 1).regression is True


def test_promotion_requires_evidence_and_floor():
    gate = ModelPromotionGate(.8)
    ok, reason = gate.admit([BenchmarkResult("m", "reasoning", .9, "receipt-1")], required_suites=["reasoning"])
    assert ok
    assert reason == "PROMOTED"
    assert gate.admit([], required_suites=["reasoning"])[0] is False


def test_promotion_rejects_mixed_model_evidence():
    gate = ModelPromotionGate(.8)
    ok, reason = gate.admit(
        [
            BenchmarkResult("model-a", "reasoning", .9, "receipt-1"),
            BenchmarkResult("model-b", "coding", .95, "receipt-2"),
        ],
        required_suites=["reasoning", "coding"],
    )
    assert not ok
    assert reason == "MIXED_MODEL_EVIDENCE"


def test_comfyui_policy_cannot_be_bypassed():
    called = []
    adapter = GovernedComfyUIAdapter(MediaWorkflowPolicy(), lambda payload: called.append(payload) or {"ok": True})
    job = MediaJob(MediaKind.IMAGE, "wf", {}, local_only=False, external_provider="cloud")
    with pytest.raises(PermissionError):
        adapter.run(job)
    assert called == []
