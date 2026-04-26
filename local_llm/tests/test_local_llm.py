"""
SintraPrime Local LLM — Full Test Suite (30+ tests)
All tests use mocked HTTP responses — no real Ollama instance required.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from local_llm.provider import LLMConfig, LLMResponse, LocalLLMProvider, ProviderRegistry
from local_llm.ollama_adapter import OllamaAdapter
from local_llm.hermes_adapter import (
    HermesAdapter,
    HERMES_MODELS,
    HERMES_LEGAL_SYSTEM,
    HERMES_TRUST_SYSTEM,
    build_chatml_prompt,
    build_function_call_prompt,
    build_cot_prompt,
)
from local_llm.model_manager import ModelManager, TASK_RECOMMENDATIONS
from local_llm.sintra_llm_bridge import SintraLLMBridge, _FALLBACK_MSG


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

def make_config(**kwargs) -> LLMConfig:
    return LLMConfig(**kwargs)


def make_ollama_adapter(**kwargs) -> OllamaAdapter:
    return OllamaAdapter(make_config(**kwargs))


def make_hermes_adapter(**kwargs) -> HermesAdapter:
    return HermesAdapter(make_config(**kwargs))


async def _async_gen(*items):
    """Helper: yield items from an async generator."""
    for item in items:
        yield item


# ===========================================================================
# 1. LLMConfig Tests
# ===========================================================================

class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.model == "hermes3"
        assert cfg.base_url == "http://localhost:11434"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096
        assert cfg.context_window == 8192
        assert cfg.stream is True
        assert cfg.system_prompt == ""
        assert cfg.timeout == 120

    def test_custom_values(self):
        cfg = LLMConfig(model="llama3.2", temperature=0.2, max_tokens=1024)
        assert cfg.model == "llama3.2"
        assert cfg.temperature == 0.2
        assert cfg.max_tokens == 1024

    def test_to_ollama_options(self):
        cfg = LLMConfig(temperature=0.5, max_tokens=512, context_window=4096)
        opts = cfg.to_ollama_options()
        assert opts["temperature"] == 0.5
        assert opts["num_predict"] == 512
        assert opts["num_ctx"] == 4096

    def test_to_ollama_options_with_seed(self):
        cfg = LLMConfig(seed=42)
        opts = cfg.to_ollama_options()
        assert opts["seed"] == 42

    def test_to_ollama_options_without_seed(self):
        cfg = LLMConfig()
        opts = cfg.to_ollama_options()
        assert "seed" not in opts


# ===========================================================================
# 2. LLMResponse Tests
# ===========================================================================

class TestLLMResponse:
    def test_basic(self):
        r = LLMResponse(content="Hello", model="hermes3")
        assert r.content == "Hello"
        assert r.model == "hermes3"
        assert r.tokens_used == 0
        assert r.finish_reason == "stop"
        assert r.metadata == {}

    def test_is_complete_stop(self):
        r = LLMResponse(content="x", model="m", finish_reason="stop")
        assert r.is_complete is True

    def test_is_complete_length(self):
        r = LLMResponse(content="x", model="m", finish_reason="length")
        assert r.is_complete is True

    def test_is_complete_eos(self):
        r = LLMResponse(content="x", model="m", finish_reason="eos")
        assert r.is_complete is True

    def test_str(self):
        r = LLMResponse(content="output", model="m")
        assert str(r) == "output"


# ===========================================================================
# 3. ProviderRegistry Tests
# ===========================================================================

class TestProviderRegistry:
    def test_register_and_get(self):
        @ProviderRegistry.register("_test_provider")
        class _TestProvider(LocalLLMProvider):
            async def generate(self, prompt, system=""): ...
            async def stream(self, prompt, system=""): ...
            async def health_check(self): return True

        assert ProviderRegistry.is_registered("_test_provider")
        p = ProviderRegistry.get("_test_provider", LLMConfig())
        assert isinstance(p, _TestProvider)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.get("__nonexistent__", LLMConfig())

    def test_list_providers(self):
        providers = ProviderRegistry.list_providers()
        assert "ollama" in providers
        assert "hermes" in providers

    def test_is_registered_false(self):
        assert ProviderRegistry.is_registered("__fake__") is False


# ===========================================================================
# 4. OllamaAdapter — Initialisation
# ===========================================================================

class TestOllamaAdapterInit:
    def test_base_url_stripped(self):
        adapter = make_ollama_adapter(base_url="http://localhost:11434/")
        assert adapter._base_url == "http://localhost:11434"

    def test_custom_model(self):
        adapter = make_ollama_adapter(model="mistral")
        assert adapter.config.model == "mistral"


# ===========================================================================
# 5. OllamaAdapter — health_check
# ===========================================================================

class TestOllamaAdapterHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(adapter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_get_client.return_value = mock_client
            result = await adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        adapter = make_ollama_adapter()
        with patch.object(adapter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("refused"))
            mock_get_client.return_value = mock_client
            result = await adapter.health_check()
        assert result is False


# ===========================================================================
# 6. OllamaAdapter — generate
# ===========================================================================

class TestOllamaAdapterGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "response": "Trust is a fiduciary relationship.",
            "model": "hermes3",
            "done": True,
            "eval_count": 8,
        }
        with patch.object(adapter, "_post_with_retry", AsyncMock(return_value=mock_resp)):
            result = await adapter.generate("What is trust?")
        assert "fiduciary" in result.content
        assert result.tokens_used == 8
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_not_done(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "...", "model": "hermes3", "done": False}
        with patch.object(adapter, "_post_with_retry", AsyncMock(return_value=mock_resp)):
            result = await adapter.generate("x")
        assert result.finish_reason == "length"

    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        adapter = make_ollama_adapter()
        with patch.object(adapter, "_post_with_retry", AsyncMock(side_effect=Exception("connect failed"))):
            with pytest.raises(ConnectionError):
                await adapter.generate("x")


# ===========================================================================
# 7. OllamaAdapter — list_models
# ===========================================================================

class TestOllamaAdapterListModels:
    @pytest.mark.asyncio
    async def test_list_models_success(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "hermes3"}, {"name": "llama3.2"}]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(adapter, "_get_client") as mock_gc:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_gc.return_value = mock_client
            models = await adapter.list_models()
        assert len(models) == 2
        assert models[0]["name"] == "hermes3"

    @pytest.mark.asyncio
    async def test_list_models_error_returns_empty(self):
        adapter = make_ollama_adapter()
        with patch.object(adapter, "_get_client") as mock_gc:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("fail"))
            mock_gc.return_value = mock_client
            models = await adapter.list_models()
        assert models == []


# ===========================================================================
# 8. OllamaAdapter — embed
# ===========================================================================

class TestOllamaAdapterEmbed:
    @pytest.mark.asyncio
    async def test_embed_success(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        with patch.object(adapter, "_post_with_retry", AsyncMock(return_value=mock_resp)):
            vec = await adapter.embed("hello")
        assert vec == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_empty_raises(self):
        adapter = make_ollama_adapter()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": []}
        with patch.object(adapter, "_post_with_retry", AsyncMock(return_value=mock_resp)):
            with pytest.raises(RuntimeError, match="empty embedding"):
                await adapter.embed("hello")


# ===========================================================================
# 9. HermesAdapter — ChatML formatting
# ===========================================================================

class TestBuildChatMLPrompt:
    def test_system_and_user(self):
        p = build_chatml_prompt("Hello?", system_message="You are helpful.")
        assert "<|im_start|>system" in p
        assert "You are helpful." in p
        assert "<|im_start|>user" in p
        assert "Hello?" in p
        assert "<|im_start|>assistant" in p

    def test_no_system(self):
        p = build_chatml_prompt("Hi")
        assert "<|im_start|>system" not in p
        assert "Hi" in p

    def test_with_history(self):
        history = [{"role": "user", "content": "prev q"}, {"role": "assistant", "content": "prev a"}]
        p = build_chatml_prompt("new q", history=history)
        assert "prev q" in p
        assert "prev a" in p
        assert "new q" in p

    def test_ends_with_assistant_tag(self):
        p = build_chatml_prompt("q")
        assert p.strip().endswith("<|im_start|>assistant")


class TestBuildFunctionCallPrompt:
    def test_contains_tool_json(self):
        tools = [{"name": "search", "description": "Search the web", "parameters": {}}]
        p = build_function_call_prompt("Find something", tools)
        assert "search" in p
        assert "Search the web" in p

    def test_contains_user_message(self):
        tools = [{"name": "t", "description": "d", "parameters": {}}]
        p = build_function_call_prompt("my question", tools)
        assert "my question" in p


class TestBuildCotPrompt:
    def test_contains_question(self):
        p = build_cot_prompt("What is a trust?")
        assert "What is a trust?" in p
        assert "step by step" in p.lower()

    def test_includes_context(self):
        p = build_cot_prompt("Q?", context="Some context here")
        assert "Some context here" in p


# ===========================================================================
# 10. HermesAdapter — legal methods
# ===========================================================================

class TestHermesAdapterLegalMethods:
    @pytest.mark.asyncio
    async def test_legal_analysis(self):
        adapter = make_hermes_adapter()
        mock_resp = LLMResponse(content="Legal analysis result", model="hermes3")
        with patch.object(OllamaAdapter, "generate", AsyncMock(return_value=mock_resp)):
            result = await adapter.legal_analysis("Explain fiduciary duty")
        assert result.content == "Legal analysis result"

    @pytest.mark.asyncio
    async def test_trust_law_expert(self):
        adapter = make_hermes_adapter()
        mock_resp = LLMResponse(content="Trust law answer", model="hermes3")
        with patch.object(OllamaAdapter, "generate", AsyncMock(return_value=mock_resp)):
            result = await adapter.trust_law_expert("What is a revocable trust?")
        assert result.content == "Trust law answer"

    @pytest.mark.asyncio
    async def test_function_call_valid_json(self):
        adapter = make_hermes_adapter()
        tool_resp = LLMResponse(
            content='{"tool": "search", "arguments": {"query": "trust law"}}',
            model="hermes3",
        )
        with patch.object(OllamaAdapter, "generate", AsyncMock(return_value=tool_resp)):
            result = await adapter.function_call("Find trust law info", tools=[])
        assert result["tool"] == "search"
        assert result["arguments"]["query"] == "trust law"

    @pytest.mark.asyncio
    async def test_function_call_invalid_json(self):
        adapter = make_hermes_adapter()
        bad_resp = LLMResponse(content="not json at all", model="hermes3")
        with patch.object(OllamaAdapter, "generate", AsyncMock(return_value=bad_resp)):
            result = await adapter.function_call("q", tools=[])
        assert "error" in result

    def test_list_hermes_models(self):
        models = HermesAdapter.list_hermes_models()
        assert len(models) >= 3
        names = [m["id"] for m in models]
        assert "hermes3" in names
        assert "nous-hermes2" in names


# ===========================================================================
# 11. ModelManager Tests
# ===========================================================================

class TestModelManager:
    @pytest.mark.asyncio
    async def test_list_available(self):
        mm = ModelManager()
        mock_models = [{"name": "hermes3"}, {"name": "llama3.2"}]
        with patch.object(OllamaAdapter, "list_models", AsyncMock(return_value=mock_models)):
            result = await mm.list_available()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_is_available_true(self):
        mm = ModelManager()
        with patch.object(mm, "list_available", AsyncMock(return_value=[{"name": "hermes3"}])):
            assert await mm.is_available("hermes3") is True

    @pytest.mark.asyncio
    async def test_is_available_false(self):
        mm = ModelManager()
        with patch.object(mm, "list_available", AsyncMock(return_value=[])):
            assert await mm.is_available("hermes3") is False

    @pytest.mark.asyncio
    async def test_recommend_legal_task(self):
        mm = ModelManager()
        with patch.object(mm, "list_available", AsyncMock(return_value=[{"name": "hermes3"}])):
            rec = await mm.recommend_for_task("legal analysis")
        assert "hermes" in rec.lower()

    @pytest.mark.asyncio
    async def test_recommend_fallback_when_no_preferred(self):
        mm = ModelManager()
        with patch.object(mm, "list_available", AsyncMock(return_value=[{"name": "somemodel"}])):
            rec = await mm.recommend_for_task("legal analysis")
        assert rec == "somemodel"

    @pytest.mark.asyncio
    async def test_recommend_last_resort(self):
        mm = ModelManager()
        with patch.object(mm, "list_available", AsyncMock(return_value=[])):
            rec = await mm.recommend_for_task("legal analysis")
        assert rec == "hermes3"

    @pytest.mark.asyncio
    async def test_pull_model_success(self):
        mm = ModelManager()
        with patch.object(OllamaAdapter, "pull_model", AsyncMock(return_value=True)):
            result = await mm.pull_model("hermes3")
        assert result is True

    @pytest.mark.asyncio
    async def test_pull_model_failure(self):
        mm = ModelManager()
        with patch.object(OllamaAdapter, "pull_model", AsyncMock(return_value=False)):
            result = await mm.pull_model("bad-model")
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_delegates(self):
        mm = ModelManager()
        with patch.object(OllamaAdapter, "health_check", AsyncMock(return_value=True)):
            assert await mm.health_check() is True


# ===========================================================================
# 12. SintraLLMBridge Tests
# ===========================================================================

class TestSintraLLMBridge:
    @pytest.mark.asyncio
    async def test_is_local_available_true(self, monkeypatch):
        monkeypatch.setenv("SINTRA_LOCAL_LLM", "true")
        bridge = SintraLLMBridge(force_local=True)
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        bridge._local_llm = mock_provider
        assert await bridge.is_local_available() is True

    @pytest.mark.asyncio
    async def test_is_local_available_false_when_disabled(self):
        bridge = SintraLLMBridge(force_local=False)
        assert await bridge.is_local_available() is False

    @pytest.mark.asyncio
    async def test_chat_uses_local_when_available(self):
        bridge = SintraLLMBridge(force_local=True)
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_provider.chat = AsyncMock(
            return_value=LLMResponse(content="Local answer", model="hermes3")
        )
        bridge._local_llm = mock_provider
        result = await bridge.chat([{"role": "user", "content": "Hello"}])
        assert result == "Local answer"

    @pytest.mark.asyncio
    async def test_chat_fallback_message_when_no_backend(self):
        bridge = SintraLLMBridge(force_local=False)
        result = await bridge.chat([{"role": "user", "content": "Hello"}])
        assert result == _FALLBACK_MSG

    @pytest.mark.asyncio
    async def test_legal_analysis_with_hermes(self):
        bridge = SintraLLMBridge(force_local=True)
        mock_hermes = AsyncMock(spec=HermesAdapter)
        mock_hermes.health_check = AsyncMock(return_value=True)
        mock_hermes.legal_analysis = AsyncMock(
            return_value=LLMResponse(content="Legal analysis", model="hermes3")
        )
        bridge._local_llm = mock_hermes
        result = await bridge.legal_analysis("Explain fiduciary duty")
        assert result == "Legal analysis"

    @pytest.mark.asyncio
    async def test_trust_law_expert_with_hermes(self):
        bridge = SintraLLMBridge(force_local=True)
        mock_hermes = AsyncMock(spec=HermesAdapter)
        mock_hermes.health_check = AsyncMock(return_value=True)
        mock_hermes.trust_law_expert = AsyncMock(
            return_value=LLMResponse(content="Trust law answer", model="hermes3")
        )
        bridge._local_llm = mock_hermes
        result = await bridge.trust_law_expert("What is a spendthrift trust?")
        assert result == "Trust law answer"

    @pytest.mark.asyncio
    async def test_chat_local_error_uses_fallback_msg(self):
        bridge = SintraLLMBridge(force_local=True)
        bridge._local_fallback = False
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_provider.chat = AsyncMock(side_effect=Exception("oops"))
        bridge._local_llm = mock_provider
        result = await bridge.chat([{"role": "user", "content": "Hi"}])
        assert "Local LLM error" in result

    @pytest.mark.asyncio
    async def test_summarise(self):
        bridge = SintraLLMBridge(force_local=False)
        with patch.object(bridge, "chat", AsyncMock(return_value="Summary here")):
            result = await bridge.summarise("Long text...")
        assert result == "Summary here"

    @pytest.mark.asyncio
    async def test_chain_of_thought_delegates(self):
        bridge = SintraLLMBridge(force_local=False)
        with patch.object(bridge, "chat", AsyncMock(return_value="Step 1... Conclusion.")):
            result = await bridge.chain_of_thought("Hard question")
        assert "Step 1" in result

    def test_model_manager_property(self):
        bridge = SintraLLMBridge()
        mm = bridge.model_manager
        assert isinstance(mm, ModelManager)
        # Second access returns same instance
        assert bridge.model_manager is mm


# ===========================================================================
# 13. Integration — chat() messages conversion
# ===========================================================================

class TestChatMessagesConversion:
    @pytest.mark.asyncio
    async def test_system_message_extracted(self):
        bridge = SintraLLMBridge(force_local=True)
        captured_calls = []

        async def fake_chat(messages):
            captured_calls.append(messages)
            return LLMResponse(content="ok", model="hermes3")

        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_provider.chat = fake_chat
        bridge._local_llm = mock_provider

        await bridge.chat([
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ])
        assert len(captured_calls) == 1

    @pytest.mark.asyncio
    async def test_stream_chat_yields_tokens(self):
        bridge = SintraLLMBridge(force_local=True)
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)

        async def fake_stream(prompt, system=""):
            for token in ["Hello", " ", "world"]:
                yield token

        mock_provider.stream = fake_stream
        bridge._local_llm = mock_provider

        tokens = []
        async for token in bridge.stream_chat([{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert "".join(tokens) == "Hello world"
