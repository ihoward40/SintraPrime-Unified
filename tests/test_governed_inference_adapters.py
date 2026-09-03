"""
Phase 3.1 — Targeted adapter tests for OpenAIProvider, AnthropicProvider,
timeout enforcement, structured logging, and trace integration.

These tests use mock SDK clients (no external API calls) to verify the
adapter contract, error mapping, timeout enforcement, and trace propagation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from governed_inference import (
    DataClassification,
    GovernedInferenceRouter,
    InferencePolicy,
    InferenceRequest,
    MockProvider,
)
from governed_inference.adapters import AnthropicProvider, OpenAIProvider
from governed_inference.contracts import (
    InferenceError,
    PerRequestPolicy,
    ProviderErrorKind,
    RouteTier,
)
from observability.tracer import Tracer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(**kwargs: Any) -> InferenceRequest:
    defaults = {
        "request_id": "adapter-test",
        "task_type": "general",
        "capability": "summarization",
        "messages": [{"role": "user", "content": "Summarize this document."}],
        "max_input_tokens": 1000,
        "max_output_tokens": 500,
        "data_classification": DataClassification.PUBLIC,
    }
    defaults.update(kwargs)
    return InferenceRequest(**defaults)


# ---------------------------------------------------------------------------
# Mock OpenAI response objects
# ---------------------------------------------------------------------------


@dataclass
class _MockUsage:
    prompt_tokens: int = 50
    completion_tokens: int = 30
    total_tokens: int = 80


@dataclass
class _MockMessage:
    content: str = "This is a summary."


@dataclass
class _MockChoice:
    message: _MockMessage = None
    delta: Any = None


@dataclass
class _MockResponse:
    id: str = "chatcmpl-test-123"
    choices: list = None
    usage: _MockUsage = None

    def __post_init__(self):
        if self.choices is None:
            self.choices = [_MockChoice(message=_MockMessage())]
        if self.usage is None:
            self.usage = _MockUsage()


class _MockStreamChunk:
    def __init__(self, content: str):
        self.choices = [_MockChoice(delta=MagicMock(content=content))]


# ---------------------------------------------------------------------------
# OpenAI adapter tests
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def test_unconfigured_provider_raises_on_invoke(self):
        provider = OpenAIProvider()  # no api_key
        assert provider.configured is False
        with pytest.raises(InferenceError) as exc:
            provider.invoke(_req())
        assert exc.value.kind == ProviderErrorKind.AUTHENTICATION

    def test_unconfigured_provider_health_reports_not_configured(self):
        provider = OpenAIProvider()
        health = provider.health()
        assert health.healthy is False
        assert health.reason == "not_configured"

    def test_successful_invocation_returns_correct_result(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_response = _MockResponse()
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        result = provider.invoke(_req())

        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.content == "This is a summary."
        assert result.usage["input_tokens"] == 50
        assert result.usage["output_tokens"] == 30
        assert result.usage["total_tokens"] == 80
        assert result.provider_request_id == "chatcmpl-test-123"
        assert result.latency_ms >= 0
        assert result.finish_reason == "stop"

    def test_error_translation_rate_limit(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        # Create a fake RateLimitError
        exc = type("RateLimitError", (Exception,), {})("Rate limited")
        mock_client.chat.completions.create.side_effect = exc
        provider._client = mock_client

        with pytest.raises(InferenceError) as result:
            provider.invoke(_req())
        assert result.value.kind == ProviderErrorKind.TRANSIENT

    def test_error_translation_auth_error(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        exc = type("AuthenticationError", (Exception,), {})("Bad key")
        mock_client.chat.completions.create.side_effect = exc
        provider._client = mock_client

        with pytest.raises(InferenceError) as result:
            provider.invoke(_req())
        assert result.value.kind == ProviderErrorKind.AUTHENTICATION

    def test_error_translation_bad_request(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        exc = type("BadRequestError", (Exception,), {})("Bad request")
        mock_client.chat.completions.create.side_effect = exc
        provider._client = mock_client

        with pytest.raises(InferenceError) as result:
            provider.invoke(_req())
        assert result.value.kind == ProviderErrorKind.INVALID_REQUEST

    def test_streaming_invocation_accumulates_content(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        chunks = [_MockStreamChunk("Hello "), _MockStreamChunk("world"), _MockStreamChunk("!")]
        mock_client.chat.completions.create.return_value = iter(chunks)
        provider._client = mock_client

        result = provider.invoke_stream(_req())
        assert "Hello world!" in result.content

    def test_structured_logging_on_success(self, caplog):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _MockResponse()
        provider._client = mock_client

        with caplog.at_level(logging.INFO, logger="governed_inference.adapters"):
            provider.invoke(_req())

        assert any("openai.invoke.success" in r.message for r in caplog.records)

    def test_structured_logging_on_error(self, caplog):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()
        exc = type("RateLimitError", (Exception,), {})("Rate limited")
        mock_client.chat.completions.create.side_effect = exc
        provider._client = mock_client

        with (
            caplog.at_level(logging.WARNING, logger="governed_inference.adapters"),
            pytest.raises(InferenceError),
        ):
            provider.invoke(_req())

        assert any("openai.invoke.error" in r.message for r in caplog.records)

    def test_capabilities_report_correct_metadata(self):
        provider = OpenAIProvider(api_key="test-key")
        caps = provider.capabilities()
        assert caps.provider == "openai"
        assert caps.cloud is True
        assert caps.paid is True
        assert caps.supports_streaming is True
        assert caps.context_window == 128000


# ---------------------------------------------------------------------------
# Anthropic adapter tests
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def test_unconfigured_provider_raises_on_invoke(self):
        provider = AnthropicProvider()
        assert provider.configured is False
        with pytest.raises(InferenceError) as exc:
            provider.invoke(_req())
        assert exc.value.kind == ProviderErrorKind.AUTHENTICATION

    def test_successful_invocation_returns_correct_result(self):
        provider = AnthropicProvider(api_key="test-key")

        # Build mock Anthropic response
        mock_content_block = MagicMock()
        mock_content_block.text = "Claude analysis complete."
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_response.usage = mock_usage
        mock_response.id = "msg_test_456"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        result = provider.invoke(_req())

        assert result.provider == "anthropic"
        assert result.content == "Claude analysis complete."
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.provider_request_id == "msg_test_456"

    def test_system_message_extraction(self):
        provider = AnthropicProvider(api_key="test-key")

        mock_content = MagicMock()
        mock_content.text = "Response"
        mock_usage = MagicMock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage = mock_usage
        mock_response.id = "msg_789"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        req = _req(
            messages=[
                {"role": "system", "content": "You are a legal assistant."},
                {"role": "user", "content": "Analyze this case."},
            ]
        )
        provider.invoke(req)

        # Verify system was extracted and passed separately
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are a legal assistant."
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_error_translation_rate_limit(self):
        provider = AnthropicProvider(api_key="test-key")
        mock_client = MagicMock()
        exc = type("RateLimitError", (Exception,), {})("Rate limited")
        mock_client.messages.create.side_effect = exc
        provider._client = mock_client

        with pytest.raises(InferenceError) as result:
            provider.invoke(_req())
        assert result.value.kind == ProviderErrorKind.TRANSIENT

    def test_capabilities_report_correct_metadata(self):
        provider = AnthropicProvider(api_key="test-key")
        caps = provider.capabilities()
        assert caps.provider == "anthropic"
        assert caps.cloud is True
        assert caps.paid is True
        assert caps.context_window == 200000

    def test_structured_logging_on_success(self, caplog):
        provider = AnthropicProvider(api_key="test-key")

        mock_content = MagicMock()
        mock_content.text = "Result"
        mock_usage = MagicMock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage = mock_usage
        mock_response.id = "msg_log"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        with caplog.at_level(logging.INFO, logger="governed_inference.adapters"):
            provider.invoke(_req())

        assert any("anthropic.invoke.success" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Timeout enforcement tests
# ---------------------------------------------------------------------------


class TestTimeoutEnforcement:
    def test_timeout_policy_value_is_read_from_config(self):
        policy = InferencePolicy(per_request=PerRequestPolicy(timeout_seconds=30))
        assert policy.per_request.timeout_seconds == 30

    def test_router_emits_timeout_on_slow_provider(self):
        """A provider that takes longer than the timeout should trigger a timeout error."""
        # We can't actually sleep in tests, but we can verify the deadline check
        # by mocking time.monotonic to simulate elapsed time.
        provider = MockProvider(name="slow")
        policy = InferencePolicy(per_request=PerRequestPolicy(timeout_seconds=5, max_attempts=1))
        router = GovernedInferenceRouter([provider], policy=policy)

        # Mock time.monotonic to simulate provider taking longer than timeout
        call_count = [0]
        original_monotonic = time.monotonic

        def fake_monotonic():
            call_count[0] += 1
            # Before invoke: t=0, after invoke: t=10 (exceeds 5s timeout)
            if call_count[0] == 1:
                return 0.0  # deadline calculation
            if call_count[0] == 2:
                return 10.0  # remaining check
            return original_monotonic()

        with patch("governed_inference.router.time.monotonic", side_effect=fake_monotonic):
            with pytest.raises(InferenceError) as exc:
                router.invoke(_req())
            assert exc.value.kind == ProviderErrorKind.TIMEOUT_PROGRESS

    def test_router_completes_within_timeout(self):
        """A fast provider should complete without timeout errors."""
        provider = MockProvider(name="fast")
        policy = InferencePolicy(per_request=PerRequestPolicy(timeout_seconds=60))
        router = GovernedInferenceRouter([provider], policy=policy)

        result = router.invoke(_req())
        assert result.provider == "fast"


#
#
# Structured logging tests


class TestStructuredLogging:
    def test_router_logs_request_lifecycle(self, caplog):
        provider = MockProvider(name="logged")
        router = GovernedInferenceRouter([provider])

        with caplog.at_level(logging.INFO, logger="governed_inference.router"):
            router.invoke(_req())

        messages = [r.message for r in caplog.records]
        assert any("inference.requested" in m for m in messages)
        assert any("inference.classified" in m for m in messages)
        assert any("inference.completed" in m for m in messages)

    def test_router_logs_denied_request(self, caplog):
        # Use a provider that will be rejected (not configured, no cost)
        from governed_inference import GroqProvider

        provider = GroqProvider(configured=True)  # no estimated_cost_usd -> unknown_cloud_cost
        router = GovernedInferenceRouter([provider])

        with (
            caplog.at_level(logging.WARNING, logger="governed_inference.router"),
            pytest.raises(InferenceError),
        ):
            router.invoke(_req())

        assert any("inference.denied" in r.message for r in caplog.records)

    def test_router_logs_attempt_failure(self, caplog):
        provider = MockProvider(name="flaky", fail_times=1)
        policy = InferencePolicy(per_request=PerRequestPolicy(max_attempts=2))
        router = GovernedInferenceRouter([provider], policy=policy)

        with (
            caplog.at_level(logging.WARNING, logger="governed_inference.router"),
            pytest.raises(InferenceError) as exc,
        ):
            router.invoke(_req())

        attempt_failures = [
            record for record in caplog.records if "inference.attempt_failed" in record.message
        ]
        assert len(attempt_failures) == 1
        assert provider.invoke_count == 1
        assert attempt_failures[0].provider == "flaky"
        assert getattr(attempt_failures[0], "failure_class", None) is None
        assert exc.value.kind == ProviderErrorKind.TRANSIENT

    def test_no_prompt_content_in_logs(self, caplog):
        """Verify that prompt content is never present in log records."""
        provider = MockProvider(name="safe")
        router = GovernedInferenceRouter([provider])
        sensitive_prompt = "My SSN is 123-45-6789"

        with caplog.at_level(logging.DEBUG):
            router.invoke(
                _req(
                    messages=[{"role": "user", "content": sensitive_prompt}],
                )
            )

        for record in caplog.records:
            assert "123-45-6789" not in record.getMessage()
            # Also check extra fields
            for extra_val in vars(record).values():
                if isinstance(extra_val, str):
                    assert "123-45-6789" not in extra_val


# ---------------------------------------------------------------------------
# Trace integration tests
# ---------------------------------------------------------------------------


class TestTraceIntegration:
    def test_tracer_creates_span_on_invoke(self):
        tracer = Tracer(service_name="test")
        provider = MockProvider(name="traced")
        router = GovernedInferenceRouter([provider], tracer=tracer)

        result = router.invoke(_req())

        assert result.provider == "traced"
        traces = tracer.all_traces()
        assert len(traces) == 1
        trace = traces[0]
        spans = trace.all_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "inference.invoke"
        assert span.tags.get("request_id") == "adapter-test"
        assert span.tags.get("provider") == "traced"
        assert span.is_finished
        assert span.status.value == "ok"

    def test_tracer_records_error_on_denied_request(self):
        tracer = Tracer(service_name="test")
        from governed_inference import GroqProvider

        provider = GroqProvider(configured=True)
        router = GovernedInferenceRouter([provider], tracer=tracer)

        with pytest.raises(InferenceError):
            router.invoke(_req())

        trace = tracer.all_traces()[0]
        span = trace.all_spans()[0]
        assert span.status.value == "error"
        assert span.tags.get("outcome") == "denied"

    def test_tracer_records_cache_hit(self):
        tracer = Tracer(service_name="test")
        provider = MockProvider(name="cached")
        router = GovernedInferenceRouter([provider], tracer=tracer)

        # First call: MISS
        router.invoke(_req(request_id="first"))
        # Second call: HIT (same request hash)
        router.invoke(_req(request_id="second"))

        traces = tracer.all_traces()
        assert len(traces) == 2
        # Second trace should have cache_hit outcome
        second_span = traces[1].all_spans()[0]
        assert second_span.tags.get("outcome") == "cache_hit"

    def test_no_tracer_backward_compatible(self):
        """Router works normally when no tracer is provided."""
        provider = MockProvider(name="no-trace")
        router = GovernedInferenceRouter([provider])

        result = router.invoke(_req())
        assert result.provider == "no-trace"

    def test_tracer_span_has_latency_tag(self):
        tracer = Tracer(service_name="test")
        provider = MockProvider(name="timed")
        router = GovernedInferenceRouter([provider], tracer=tracer)

        router.invoke(_req())

        span = tracer.all_traces()[0].all_spans()[0]
        assert "latency_ms" in span.tags
        assert span.tags["latency_ms"] >= 0


# ---------------------------------------------------------------------------
# Ollama adapter tests
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    def test_provider_is_configured_and_local(self):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        assert provider.configured is True
        assert provider.cloud is False
        assert provider.paid is False
        caps = provider.capabilities()
        assert caps.route_tier == RouteTier.LOCAL_PRIVATE
        assert caps.provider == "ollama"

    def test_health_reflects_client_availability(self):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        provider._client = mock_client

        health = provider.health()
        assert health.healthy is True
        assert health.reachable is True

    def test_successful_invocation_returns_correct_result(self):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "response": "Local legal answer.",
            "prompt_eval_count": 12,
            "eval_count": 7,
        }
        mock_client.model_exists.return_value = True
        provider._client = mock_client

        result = provider.invoke(_req())

        assert result.provider == "ollama"
        assert result.model == "llama3"
        assert result.content == "Local legal answer."
        assert result.usage["input_tokens"] == 12
        assert result.usage["output_tokens"] == 7
        assert result.usage["total_tokens"] == 19

    def test_model_override_is_used(self):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "response": "Reasoning output.",
            "prompt_eval_count": 5,
            "eval_count": 5,
        }
        mock_client.model_exists.return_value = True
        provider._client = mock_client

        provider.invoke(_req(metadata={"model_override": "deepseek-r1"}))

        call_kwargs = mock_client.generate.call_args[1]
        assert call_kwargs["model"] == "deepseek-r1"

    def test_error_translation_for_connection_error(self):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        mock_client = MagicMock()
        from local_models.ollama_client import OllamaConnectionError

        mock_client.generate.side_effect = OllamaConnectionError("Ollama offline")
        mock_client.model_exists.return_value = True
        provider._client = mock_client

        with pytest.raises(InferenceError) as exc:
            provider.invoke(_req())
        assert exc.value.kind == ProviderErrorKind.TRANSIENT

    def test_structured_logging_on_success(self, caplog):
        from governed_inference.adapters import OllamaProvider

        provider = OllamaProvider()
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "response": "Answer.",
            "prompt_eval_count": 3,
            "eval_count": 2,
        }
        mock_client.model_exists.return_value = True
        provider._client = mock_client

        with caplog.at_level(logging.INFO, logger="governed_inference.adapters"):
            provider.invoke(_req())

        assert any("ollama.invoke.success" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# DeepSeek adapter tests
# ---------------------------------------------------------------------------


class TestDeepSeekProvider:
    def test_unconfigured_provider_raises_on_invoke(self):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider()  # no api_key
        assert provider.configured is False
        with pytest.raises(InferenceError) as exc:
            provider.invoke(_req())
        assert exc.value.kind == ProviderErrorKind.AUTHENTICATION

    def test_successful_invocation_returns_correct_result(self):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "DeepSeek answer."}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            "cost_usd": 0.0001,
        }
        provider._client = mock_client

        result = provider.invoke(_req())

        assert result.provider == "deepseek"
        assert result.model == "deepseek-chat"
        assert result.content == "DeepSeek answer."
        assert result.usage["input_tokens"] == 20
        assert result.usage["output_tokens"] == 10
        assert result.actual_cost_usd == 0.0001

    def test_reasoning_task_selects_reasoner_model(self):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "choices": [{"message": {"content": "Reasoning answer."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "cost_usd": 0.0002,
        }
        provider._client = mock_client

        provider.invoke(_req(task_type="legal_research"))

        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["model"] == "deepseek-reasoner"

    def test_reasoning_content_preserved_in_metadata(self):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "choices": [{"message": {"content": "Answer.", "reasoning_content": "Think step 1."}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            "cost_usd": 0.0,
        }
        provider._client = mock_client

        request = _req(task_type="legal_research")
        result = provider.invoke(request)

        assert result.content == "Answer."
        assert request.metadata.get("reasoning_content") == "Think step 1."

    def test_error_translation_rate_limit(self):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()
        from local_models.deepseek_client import DeepSeekRateLimitError

        mock_client.chat.side_effect = DeepSeekRateLimitError("Rate limited")
        provider._client = mock_client

        with pytest.raises(InferenceError) as exc:
            provider.invoke(_req())
        assert exc.value.kind == ProviderErrorKind.TRANSIENT

    def test_structured_logging_on_success(self, caplog):
        from governed_inference.adapters import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "choices": [{"message": {"content": "Logged."}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            "cost_usd": 0.0,
        }
        provider._client = mock_client

        with caplog.at_level(logging.INFO, logger="governed_inference.adapters"):
            provider.invoke(_req())

        assert any("deepseek.invoke.success" in r.message for r in caplog.records)
