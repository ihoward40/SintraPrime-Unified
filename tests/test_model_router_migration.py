"""
Phase 3.2 — ModelRouter migration verification tests.

Verifies that local_models.model_router.ModelRouter delegates inference
decisions to GovernedInferenceRouter while preserving its public API.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, Mock, patch

import pytest

from governed_inference import GovernedInferenceRouter
from governed_inference.contracts import InferenceError, ProviderErrorKind
from local_models.model_router import ModelRouter, Provider, TaskType
from observability.tracer import Tracer


def _mock_ollama_client(response: str = "Local legal answer.") -> MagicMock:
    client = MagicMock()
    client.is_available.return_value = True
    client.model_exists.return_value = True
    client.generate.return_value = {"response": response, "eval_count": 42}
    client.default_model = "llama3"
    return client


def _mock_deepseek_client(response: str = "DeepSeek answer") -> MagicMock:
    client = MagicMock()
    client.chat.return_value = {
        "model": "deepseek-chat",
        "choices": [{"message": {"content": response}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "cost_usd": 0.001,
    }
    return client


class TestModelRouterDelegation:
    def test_complete_delegates_to_ollama(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client("Local legal answer.")

        result = router.complete("What is estoppel?", task="chat")

        assert result.content == "Local legal answer."
        assert result.provider == Provider.OLLAMA
        assert result.model == "llama3"
        assert result.error is None

    def test_complete_delegates_to_deepseek_when_ollama_unavailable(self):
        router = ModelRouter(deepseek_api_key="test-key")
        router._ollama = _mock_ollama_client()
        router._ollama.is_available.return_value = False
        router._deepseek = _mock_deepseek_client("DeepSeek fallback")

        result = router.complete("What is estoppel?", task="chat")

        assert result.content == "DeepSeek fallback"
        assert result.provider == Provider.DEEPSEEK
        assert result.error is None

    def test_air_gap_mode_uses_only_ollama(self):
        router = ModelRouter(deepseek_api_key="test-key", air_gap_mode=True)
        router._ollama = _mock_ollama_client("Air-gap answer")

        result = router.complete("Question", task="chat")

        assert result.content == "Air-gap answer"
        assert result.provider == Provider.OLLAMA
        assert router._deepseek is None

    def test_timeout_enforcement_preserved(self, caplog):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        # Simulate provider taking longer than the 60s policy timeout on every
        # attempt. Each attempt calls monotonic twice: once for the deadline and
        # once for the remaining check; make the second call exceed the deadline.
        call_count = [0]

        def fake_monotonic():
            call_count[0] += 1
            # Attempt N: call 1 -> 0, call 2 -> 120 (exceeds 0 + 60)
            # Attempt N+1: call 1 -> 200, call 2 -> 320 (exceeds 200 + 60)
            base = (call_count[0] - 1) // 2 * 200
            offset = 0 if call_count[0] % 2 == 1 else 120
            return base + offset

        with (
            patch("governed_inference.router.time.monotonic", side_effect=fake_monotonic),
            caplog.at_level(logging.WARNING, logger="governed_inference.router"),
        ):
            result = router.complete("Test", task="chat")

        messages = [r.message for r in caplog.records]
        assert any("inference.timeout_exceeded" in m for m in messages)
        assert result.error is not None

    def test_structured_logging_active(self, caplog):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        with caplog.at_level(logging.INFO, logger="governed_inference.router"):
            router.complete("Hello", task="chat")

        messages = [r.message for r in caplog.records]
        assert any("inference.requested" in m for m in messages)
        assert any("inference.completed" in m for m in messages)

    def test_trace_propagation_active(self):
        tracer = Tracer(service_name="test")
        router = ModelRouter()
        router._ollama = _mock_ollama_client()
        router._governed_router = GovernedInferenceRouter(
            router._ensure_governed_router().providers,
            tracer=tracer,
        )

        router.complete("Hello", task="chat")

        traces = tracer.all_traces()
        assert len(traces) == 1
        span = traces[0].all_spans()[0]
        assert span.name == "inference.invoke"
        assert span.tags.get("provider") == "ollama"
        assert span.is_finished

    def test_model_router_api_backward_compatible(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        # Same signature as before migration.
        result = router.complete(
            prompt="Explain promissory estoppel.",
            model="auto",
            task=TaskType.LEGAL_RESEARCH,
            system="You are a legal assistant.",
            temperature=0.5,
            max_tokens=2048,
            stream=False,
        )

        assert result.content == "Local legal answer."
        assert isinstance(result.provider, Provider)
        assert result.task_type == TaskType.LEGAL_RESEARCH

    def test_routing_plan_shape_unchanged(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        plan = router.routing_plan("legal_research")

        assert "task" in plan
        assert "preference_order" in plan
        assert "available" in plan
        assert "selected_provider" in plan
        assert "local_model" in plan
        assert "deepseek_model" in plan

    def test_status_shape_unchanged(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        status = router.status()

        assert "providers" in status
        assert "air_gap_mode" in status
        assert "available_providers" in status

    def test_no_provider_returns_error_result(self):
        router = ModelRouter()
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        router._ollama = mock_ollama

        result = router.complete("Test", task="chat")

        assert result.error is not None
        assert result.content == ""

    def test_unknown_task_defaults_to_general_and_succeeds(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        result = router.complete("Hello", task="not_a_real_task")

        assert result.content == "Local legal answer."
        assert result.task_type == TaskType.GENERAL


class TestModelRouterReasoning:
    def test_legal_research_task_uses_deepseek_reasoner(self):
        router = ModelRouter(deepseek_api_key="test-key")
        router._ollama = _mock_ollama_client()
        router._ollama.is_available.return_value = False
        router._deepseek = _mock_deepseek_client("Reasoning answer")

        result = router.complete(
            "Analyse good faith.",
            task=TaskType.LEGAL_RESEARCH,
        )

        assert result.content == "Reasoning answer"
        call_kwargs = router._deepseek.chat.call_args[1]
        assert call_kwargs["model"] == "deepseek-reasoner"

    def test_model_override_passthrough(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        router.complete("Hello", model="mistral", task="chat")

        call_kwargs = router._ollama.generate.call_args[1]
        assert call_kwargs["model"] == "mistral"


class TestModelRouterErrorHandling:
    def test_transient_error_returns_error_result(self):
        router = ModelRouter()
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.model_exists.return_value = True
        mock_ollama.generate.side_effect = Exception("Ollama crashed")
        mock_ollama.default_model = "llama3"
        router._ollama = mock_ollama

        result = router.complete("Question", task="chat")

        assert result.error is not None
        assert "ollama" in result.error.lower() or "unknown" in result.error.lower()

    def test_inference_error_returns_error_result(self):
        router = ModelRouter()
        router._ollama = _mock_ollama_client()

        with patch.object(
            router._governed_router or router._ensure_governed_router(),
            "invoke",
            side_effect=InferenceError("policy denied", ProviderErrorKind.POLICY_DENIED),
        ):
            result = router.complete("Question", task="chat")

        assert result.error is not None
        assert "policy_denied" in result.error
