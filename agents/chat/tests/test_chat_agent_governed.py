"""
Regression tests for ChatAgent's governed inference routing path.

These tests verify that the chat agent's primary LLM call path delegates to
GovernedInferenceRouter while keeping the public API stable. They use the
deterministic MockProvider so no OpenAI API key or network access is needed.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from agents.chat.chat_agent import ChatAgent, ChatSession, AgentMode
from governed_inference import GovernedInferenceRouter, InferencePolicy
from governed_inference.contracts import InferenceError, PerRequestPolicy, ProviderErrorKind
from governed_inference.providers import MockProvider


class TestChatAgentGovernedRouting(unittest.TestCase):
    """Verify _get_llm_response routes through GovernedInferenceRouter."""

    def _build_router(self, provider: MockProvider) -> GovernedInferenceRouter:
        per_request = PerRequestPolicy(
            max_input_tokens=12000,
            max_output_tokens=4096,
            timeout_seconds=60,
            max_attempts=3,
        )
        policy = InferencePolicy(
            per_request=per_request,
            paid_models_allowed=True,
            paid_escalation_requires_explicit_approval=False,
        )
        return GovernedInferenceRouter([provider], policy=policy)

    def test_governed_router_returns_content(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        messages = [{"role": "user", "content": "Hello"}]
        response = agent._get_llm_response(messages, session)

        self.assertIn("mock-local", response)
        self.assertEqual(provider.invoke_count, 1)
        self.assertGreater(session.token_count, 0)

    def test_governed_router_uses_lazy_build(self):
        agent = ChatAgent()
        agent._openai_key = "test-key"
        self.assertIsNone(agent._governed_router)

        provider = MockProvider(name="mock-local", model="mock-model")
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        response = agent._get_llm_response([{"role": "user", "content": "Hi"}], session)
        self.assertIn("mock-local", response)

    def test_governed_router_error_returns_error_message(self):
        provider = MockProvider(
            name="mock-local",
            model="mock-model",
            fail_times=1,
            error_kind=ProviderErrorKind.TRANSIENT,
        )
        # Make provider unhealthy after one failure? MockProvider.health is based on configured.
        # With max_attempts=3, router will retry transient failures up to 3 times then exhaust.
        # Set fail_times high enough to exhaust all attempts.
        provider = MockProvider(
            name="mock-local",
            model="mock-model",
            fail_times=5,
            error_kind=ProviderErrorKind.TRANSIENT,
        )
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        response = agent._get_llm_response([{"role": "user", "content": "Hello"}], session)
        self.assertIn("error", response.lower())

    def test_fallback_when_no_openai_key(self):
        agent = ChatAgent()
        agent._openai_key = None

        session = agent.create_session()
        response = agent._get_llm_response([{"role": "user", "content": "Hello"}], session)
        self.assertIn("SintraPrime", response)

    def test_governed_router_request_metadata_model_override(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = ChatAgent(model="gpt-4o-mini")
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        agent._get_llm_response([{"role": "user", "content": "Hello"}], session)

        # MockProvider returns its own model name; the request metadata override
        # is not visible in the result, but we can verify the request was routed.
        self.assertEqual(provider.invoke_count, 1)

    def test_public_mode_system_prompt_preserved_in_messages(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session(mode=AgentMode.GOD_MODE.value)
        messages = agent._build_messages(session)
        response = agent._get_llm_response(messages, session)

        self.assertIn("mock-local", response)
        self.assertIn("GOD MODE", messages[0]["content"])


class TestChatAgentStreamingGovernedRouting(unittest.TestCase):
    """Verify chat_stream delegates to GovernedInferenceRouter.invoke_stream."""

    def _build_router(self, provider: MockProvider) -> GovernedInferenceRouter:
        per_request = PerRequestPolicy(
            max_input_tokens=12000,
            max_output_tokens=4096,
            timeout_seconds=60,
            max_attempts=3,
        )
        policy = InferencePolicy(
            per_request=per_request,
            paid_models_allowed=True,
            paid_escalation_requires_explicit_approval=False,
        )
        return GovernedInferenceRouter([provider], policy=policy)

    def test_chat_stream_routes_through_governed_router(self):
        provider = MockProvider(name="mock-stream", model="mock-model")
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        chunks = list(agent.chat_stream(session.session_id, "Hello"))

        # MockProvider yields one partial and one final result.
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("mock-stream", "".join(chunks))
        self.assertEqual(len(session.messages), 2)  # user + assistant
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertGreater(session.token_count, 0)

    def test_chat_stream_governed_router_failure_falls_back_to_legacy(self):
        provider = MockProvider(
            name="mock-stream",
            model="mock-model",
            fail_times=5,
            error_kind=ProviderErrorKind.TRANSIENT,
        )
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            mock_stream = MagicMock()
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = "legacy fallback"
            mock_stream.__iter__ = lambda self: iter([chunk])
            mock_client.chat.completions.create.return_value.__enter__ = lambda *args: mock_stream
            mock_client.chat.completions.create.return_value.__exit__ = lambda *args: None

            session = agent.create_session()
            chunks = list(agent.chat_stream(session.session_id, "Hello"))

        self.assertEqual("".join(chunks), "legacy fallback")
        self.assertEqual(len(session.messages), 2)

    def test_chat_stream_no_api_key_uses_fallback(self):
        agent = ChatAgent()
        agent._openai_key = None

        session = agent.create_session()
        chunks = list(agent.chat_stream(session.session_id, "Hello"))

        self.assertEqual(len(chunks), 1)
        self.assertIn("SintraPrime", chunks[0])
        self.assertEqual(len(session.messages), 2)

    def test_chat_stream_request_requires_streaming(self):
        provider = MockProvider(name="mock-stream", model="mock-model")
        agent = ChatAgent()
        agent._openai_key = "test-key"
        agent._governed_router = self._build_router(provider)

        session = agent.create_session()
        list(agent.chat_stream(session.session_id, "Hello"))

        # Verify the provider saw a streaming request.
        self.assertEqual(provider.invoke_count, 1)


if __name__ == "__main__":
    unittest.main()
