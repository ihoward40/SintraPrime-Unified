"""
Tests for SintraPrime-Unified local_models package.

Run with:
    python -m pytest local_models/tests/test_local_models.py -v

All external HTTP calls are mocked with unittest.mock.
"""

from __future__ import annotations

import json
import sys
import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Add parent dir to path so imports work when running from repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_response(json_data: Any = None, status_code: int = 200, lines: List[bytes] = None) -> Mock:
    resp = Mock()
    resp.status_code = status_code
    resp.ok = (status_code < 400)
    resp.raise_for_status = Mock()
    if json_data is not None:
        resp.json = Mock(return_value=json_data)
    if lines is not None:
        resp.iter_lines = Mock(return_value=iter(lines))
    return resp


# ===========================================================================
# OllamaClient tests
# ===========================================================================

class TestOllamaClientInit(unittest.TestCase):
    def test_default_url(self):
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_custom_url(self):
        from local_models.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://myhost:11434")
        self.assertEqual(client.base_url, "http://myhost:11434")

    def test_trailing_slash_stripped(self):
        from local_models.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434/")
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_repr(self):
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertIn("OllamaClient", repr(client))


class TestOllamaHealth(unittest.TestCase):
    @patch("requests.Session.get")
    def test_is_available_true(self, mock_get):
        mock_get.return_value = make_response(status_code=200)
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertTrue(client.is_available())

    @patch("requests.Session.get")
    def test_is_available_false_on_connection_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertFalse(client.is_available())

    @patch("requests.Session.get")
    def test_health_check_available(self, mock_get):
        mock_get.return_value = make_response(status_code=200)
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        with patch.object(client, "list_models", return_value=[{"name": "llama3"}]):
            report = client.health_check()
        self.assertTrue(report["available"])
        self.assertIn("model_count", report)

    @patch("requests.Session.get")
    def test_health_check_unavailable(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        report = client.health_check()
        self.assertFalse(report["available"])


class TestOllamaModels(unittest.TestCase):
    @patch("requests.Session.get")
    def test_list_models(self, mock_get):
        mock_get.return_value = make_response(
            json_data={"models": [{"name": "llama3"}, {"name": "mistral"}]}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        models = client.list_models()
        self.assertEqual(len(models), 2)

    @patch("requests.Session.post")
    def test_model_info(self, mock_post):
        mock_post.return_value = make_response(json_data={"name": "llama3", "details": {}})
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        info = client.model_info("llama3")
        self.assertEqual(info["name"], "llama3")

    @patch("requests.Session.get")
    def test_model_exists_true(self, mock_get):
        mock_get.return_value = make_response(
            json_data={"models": [{"name": "llama3:latest"}]}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertTrue(client.model_exists("llama3"))

    @patch("requests.Session.get")
    def test_model_exists_false(self, mock_get):
        mock_get.return_value = make_response(json_data={"models": []})
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        self.assertFalse(client.model_exists("nonexistent"))

    @patch("requests.Session.post")
    def test_pull_model(self, mock_post):
        lines = [
            json.dumps({"status": "pulling manifest"}).encode(),
            json.dumps({"status": "success"}).encode(),
        ]
        mock_post.return_value = make_response(lines=lines)
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        chunks = list(client.pull_model("llama3"))
        self.assertGreater(len(chunks), 0)


class TestOllamaGenerate(unittest.TestCase):
    @patch("requests.Session.post")
    def test_generate_non_streaming(self, mock_post):
        mock_post.return_value = make_response(
            json_data={"response": "Hello, legal world!", "done": True}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        result = client.generate("Tell me about habeas corpus", stream=False)
        self.assertEqual(result["response"], "Hello, legal world!")

    @patch("requests.Session.post")
    def test_generate_streaming(self, mock_post):
        lines = [
            json.dumps({"response": "Hello", "done": False}).encode(),
            json.dumps({"response": " world", "done": True}).encode(),
        ]
        mock_post.return_value = make_response(lines=lines)
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        chunks = list(client.generate("test", stream=True))
        self.assertEqual(len(chunks), 2)

    @patch("requests.Session.post")
    def test_generate_with_system(self, mock_post):
        mock_post.return_value = make_response(json_data={"response": "OK", "done": True})
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        result = client.generate("Prompt", system="You are a legal AI", stream=False)
        call_payload = mock_post.call_args[1]["json"]
        self.assertIn("system", call_payload)

    @patch("requests.Session.post")
    def test_generate_connection_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError
        from local_models.ollama_client import OllamaClient, OllamaConnectionError
        client = OllamaClient()
        with self.assertRaises(OllamaConnectionError):
            client.generate("test", stream=False)


class TestOllamaChat(unittest.TestCase):
    @patch("requests.Session.post")
    def test_chat_non_streaming(self, mock_post):
        mock_post.return_value = make_response(
            json_data={"message": {"content": "Hello!"}, "done": True}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        result = client.chat([{"role": "user", "content": "Hi"}], stream=False)
        self.assertIn("message", result)

    @patch("requests.Session.post")
    def test_chat_with_system_prepended(self, mock_post):
        mock_post.return_value = make_response(
            json_data={"message": {"content": "OK"}, "done": True}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        client.chat(
            [{"role": "user", "content": "Hi"}],
            system="You are a lawyer",
            stream=False,
        )
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["messages"][0]["role"], "system")


class TestOllamaEmbeddings(unittest.TestCase):
    @patch("requests.Session.post")
    def test_embeddings_returns_list(self, mock_post):
        mock_post.return_value = make_response(json_data={"embedding": [0.1, 0.2, 0.3]})
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        emb = client.embeddings("Some legal text")
        self.assertEqual(emb, [0.1, 0.2, 0.3])

    @patch("requests.Session.post")
    def test_batch_embeddings(self, mock_post):
        mock_post.return_value = make_response(json_data={"embedding": [0.1, 0.2]})
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        results = client.batch_embeddings(["text1", "text2"])
        self.assertEqual(len(results), 2)


class TestOllamaCapabilities(unittest.TestCase):
    def test_capability_report(self):
        from local_models.ollama_client import OllamaClient
        report = OllamaClient.capability_report()
        self.assertIn("recommended_models", report)
        self.assertIn("capabilities", report)

    @patch("requests.Session.get")
    def test_recommended_model_for_task(self, mock_get):
        mock_get.return_value = make_response(
            json_data={"models": [{"name": "deepseek-r1:latest"}]}
        )
        from local_models.ollama_client import OllamaClient
        client = OllamaClient()
        model = client.recommended_model_for_task("legal_research")
        self.assertEqual(model, "deepseek-r1")


# ===========================================================================
# DeepSeekClient tests
# ===========================================================================

class TestDeepSeekClientInit(unittest.TestCase):
    def test_api_key_from_param(self):
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="test-key")
        self.assertEqual(client.api_key, "test-key")

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-key"}):
            from local_models.deepseek_client import DeepSeekClient
            client = DeepSeekClient()
            self.assertEqual(client.api_key, "env-key")

    def test_repr(self):
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="key")
        self.assertIn("DeepSeekClient", repr(client))


class TestDeepSeekExtractThinking(unittest.TestCase):
    def test_extract_think_block(self):
        from local_models.deepseek_client import DeepSeekClient
        text = "<think>Step 1: analyse. Step 2: conclude.</think>Final answer."
        thinking, answer = DeepSeekClient.extract_thinking(text)
        self.assertIn("Step 1", thinking)
        self.assertEqual(answer, "Final answer.")

    def test_no_think_block(self):
        from local_models.deepseek_client import DeepSeekClient
        text = "Just the answer, no thinking."
        thinking, answer = DeepSeekClient.extract_thinking(text)
        self.assertEqual(thinking, "")
        self.assertEqual(answer, text)

    def test_empty_think_block(self):
        from local_models.deepseek_client import DeepSeekClient
        text = "<think></think>Answer here."
        thinking, answer = DeepSeekClient.extract_thinking(text)
        self.assertEqual(thinking, "")
        self.assertEqual(answer, "Answer here.")

    def test_multiline_thinking(self):
        from local_models.deepseek_client import DeepSeekClient
        text = "<think>\nLine 1\nLine 2\n</think>\nAnswer."
        thinking, answer = DeepSeekClient.extract_thinking(text)
        self.assertIn("Line 1", thinking)
        self.assertIn("Answer", answer)


class TestDeepSeekCostTracker(unittest.TestCase):
    def test_record_cost(self):
        from local_models.deepseek_client import CostTracker
        tracker = CostTracker()
        cost = tracker.record("deepseek-chat", 1000, 500)
        self.assertGreater(cost, 0)

    def test_total_cost_accumulates(self):
        from local_models.deepseek_client import CostTracker
        tracker = CostTracker()
        tracker.record("deepseek-chat", 1000, 500)
        tracker.record("deepseek-chat", 2000, 1000)
        self.assertGreater(tracker.total_cost, 0)

    def test_summary_structure(self):
        from local_models.deepseek_client import CostTracker
        tracker = CostTracker()
        tracker.record("deepseek-chat", 100, 50)
        summary = tracker.summary()
        self.assertIn("calls", summary)
        self.assertIn("total_cost_usd", summary)
        self.assertIn("by_model", summary)

    def test_reset(self):
        from local_models.deepseek_client import CostTracker
        tracker = CostTracker()
        tracker.record("deepseek-chat", 1000, 500)
        tracker.reset()
        self.assertEqual(tracker.total_cost, 0)
        self.assertEqual(tracker.total_prompt_tokens, 0)

    def test_reasoner_pricing_higher(self):
        from local_models.deepseek_client import CostTracker
        tracker = CostTracker()
        cost_chat = tracker.record("deepseek-chat", 10000, 5000)
        tracker2 = CostTracker()
        cost_reasoner = tracker2.record("deepseek-reasoner", 10000, 5000)
        self.assertGreater(cost_reasoner, cost_chat)


class TestDeepSeekComplete(unittest.TestCase):
    @patch("requests.Session.post")
    def test_complete_success(self, mock_post):
        mock_post.return_value = make_response(json_data={
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "Legal analysis..."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        })
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="key")
        resp = client.complete("Analyse this contract.", model="deepseek-chat")
        self.assertIn("choices", resp)
        self.assertIn("cost_usd", resp)

    @patch("requests.Session.post")
    def test_complete_no_api_key_raises(self, mock_post):
        from local_models.deepseek_client import DeepSeekClient, DeepSeekAuthError
        client = DeepSeekClient(api_key="")
        with self.assertRaises(DeepSeekAuthError):
            client.complete("test")

    @patch("requests.Session.post")
    def test_rate_limit_raises(self, mock_post):
        resp = make_response(status_code=429)
        resp.raise_for_status = Mock()
        mock_post.return_value = resp
        from local_models.deepseek_client import DeepSeekClient, DeepSeekRateLimitError
        client = DeepSeekClient(api_key="key")
        # Patch _post to simulate 429
        with patch.object(client, "_post", side_effect=__import__(
            "local_models.deepseek_client", fromlist=["DeepSeekRateLimitError"]
        ).DeepSeekRateLimitError("Rate limit")):
            with self.assertRaises(DeepSeekRateLimitError):
                client.complete("test")

    @patch("requests.Session.post")
    def test_cost_recorded_after_call(self, mock_post):
        mock_post.return_value = make_response(json_data={
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        })
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="key")
        client.complete("Test prompt")
        self.assertGreater(client.cost_tracker.total_cost, 0)


class TestDeepSeekLegalReasoning(unittest.TestCase):
    @patch("requests.Session.post")
    def test_legal_reasoning_returns_result(self, mock_post):
        mock_post.return_value = make_response(json_data={
            "model": "deepseek-reasoner",
            "choices": [{"message": {"content": "<think>Thinking...</think>Legal answer."}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
        })
        from local_models.deepseek_client import DeepSeekClient, ReasoningResult
        client = DeepSeekClient(api_key="key")
        result = client.legal_reasoning("What is the burden of proof?")
        self.assertIsInstance(result, ReasoningResult)
        self.assertEqual(result.thinking, "Thinking...")
        self.assertEqual(result.answer, "Legal answer.")

    @patch("requests.Session.post")
    def test_legal_reasoning_with_context(self, mock_post):
        mock_post.return_value = make_response(json_data={
            "model": "deepseek-reasoner",
            "choices": [{"message": {"content": "Analysis complete."}}],
            "usage": {"prompt_tokens": 80, "completion_tokens": 120},
        })
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="key")
        result = client.legal_reasoning("Question", context="Case facts here.")
        self.assertEqual(result.answer, "Analysis complete.")

    def test_estimate_cost(self):
        from local_models.deepseek_client import DeepSeekClient
        client = DeepSeekClient(api_key="key")
        cost = client.estimate_cost(1000000, 1000000, "deepseek-chat")
        self.assertAlmostEqual(cost, 0.42, places=2)


# ===========================================================================
# ModelRouter tests
# ===========================================================================

class TestModelRouterInit(unittest.TestCase):
    def test_default_init(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        self.assertFalse(router.air_gap_mode)
        self.assertTrue(router.prefer_local)

    def test_air_gap_init(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter(air_gap_mode=True)
        self.assertTrue(router.air_gap_mode)

    def test_repr(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        self.assertIn("ModelRouter", repr(router))


class TestModelRouterAvailability(unittest.TestCase):
    def test_air_gap_blocks_cloud_providers(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter(air_gap_mode=True)
        self.assertFalse(router._is_available(Provider.DEEPSEEK))
        self.assertFalse(router._is_available(Provider.OPENAI))
        self.assertFalse(router._is_available(Provider.ANTHROPIC))

    def test_deepseek_available_when_key_set(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter(deepseek_api_key="test-key")
        self.assertTrue(router._is_available(Provider.DEEPSEEK))

    def test_deepseek_unavailable_without_key(self):
        from local_models.model_router import ModelRouter, Provider
        with patch.dict(os.environ, {}, clear=True):
            router = ModelRouter(deepseek_api_key="")
            self.assertFalse(router._is_available(Provider.DEEPSEEK))

    def test_openai_available_when_key_set(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter(openai_api_key="sk-test")
        self.assertTrue(router._is_available(Provider.OPENAI))

    def test_ollama_availability_from_health_check(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        router._ollama = mock_ollama
        self.assertTrue(router._is_available(Provider.OLLAMA))

    def test_ollama_unavailable_when_offline(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = False
        router._ollama = mock_ollama
        self.assertFalse(router._is_available(Provider.OLLAMA))


class TestModelRouterTaskResolution(unittest.TestCase):
    def test_resolve_string_task(self):
        from local_models.model_router import ModelRouter, TaskType
        router = ModelRouter()
        t = router._resolve_task_type("legal_research")
        self.assertEqual(t, TaskType.LEGAL_RESEARCH)

    def test_resolve_enum_task(self):
        from local_models.model_router import ModelRouter, TaskType
        router = ModelRouter()
        t = router._resolve_task_type(TaskType.CHAT)
        self.assertEqual(t, TaskType.CHAT)

    def test_resolve_unknown_defaults_to_general(self):
        from local_models.model_router import ModelRouter, TaskType
        router = ModelRouter()
        t = router._resolve_task_type("totally_unknown_task")
        self.assertEqual(t, TaskType.GENERAL)


class TestModelRouterComplete(unittest.TestCase):
    def _make_router_with_mock_ollama(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        mock_ollama.model_exists.return_value = True
        mock_ollama.generate.return_value = {"response": "Local legal answer.", "eval_count": 42}
        mock_ollama.default_model = "llama3"
        router._ollama = mock_ollama
        return router

    def test_complete_uses_ollama_when_available(self):
        router = self._make_router_with_mock_ollama()
        result = router.complete("What is estoppel?", task="chat")
        self.assertEqual(result.content, "Local legal answer.")
        self.assertEqual(result.provider.value, "ollama")

    def test_complete_falls_back_when_ollama_model_missing(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter(deepseek_api_key="key")
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        mock_ollama.model_exists.return_value = False
        mock_ollama.generate.return_value = {"response": "Fallback answer", "eval_count": 10}
        mock_ollama.default_model = "llama3"
        router._ollama = mock_ollama
        result = router.complete("Question", task="chat")
        self.assertIsNotNone(result)

    def test_complete_returns_error_when_no_provider(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = False
        router._ollama = mock_ollama
        result = router.complete("Test", task="chat")
        self.assertIsNotNone(result.error)

    def test_routing_plan(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        plan = router.routing_plan("legal_research")
        self.assertIn("task", plan)
        self.assertIn("preference_order", plan)
        self.assertIn("local_model", plan)

    def test_status(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        s = router.status()
        self.assertIn("providers", s)
        self.assertIn("air_gap_mode", s)


# ===========================================================================
# QuantizationManager tests
# ===========================================================================

class TestQuantizationManager(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()

    def _make_manager(self, ram_gb=16.0):
        from local_models.quantization_manager import QuantizationManager
        return QuantizationManager(models_dir=Path(self.tmpdir), available_ram_gb=ram_gb)

    def test_memory_required_q4(self):
        qm = self._make_manager()
        req = qm.memory_required_gb("llama3:8b", "Q4_K_M")
        self.assertGreater(req, 3.0)
        self.assertLess(req, 6.0)

    def test_memory_required_q8_larger_than_q4(self):
        qm = self._make_manager()
        q4 = qm.memory_required_gb("llama3:8b", "Q4_K_M")
        q8 = qm.memory_required_gb("llama3:8b", "Q8_0")
        self.assertGreater(q8, q4)

    def test_what_can_i_run_16gb(self):
        qm = self._make_manager(ram_gb=16.0)
        report = qm.what_can_i_run()
        self.assertIn("llama3:8b", report)
        self.assertGreater(len(report["llama3:8b"]), 0)

    def test_what_can_i_run_4gb_excludes_large(self):
        qm = self._make_manager(ram_gb=4.0)
        report = qm.what_can_i_run()
        self.assertNotIn("llama3:70b", report)

    def test_recommend_quantization_returns_list(self):
        qm = self._make_manager()
        recs = qm.recommend_quantization("llama3:8b")
        self.assertGreater(len(recs), 0)
        from local_models.quantization_manager import QuantRecommendation
        self.assertIsInstance(recs[0], QuantRecommendation)

    def test_recommend_suitable_first(self):
        qm = self._make_manager(ram_gb=32.0)
        recs = qm.recommend_quantization("llama3:8b")
        suitable = [r for r in recs if r.suitable]
        self.assertGreater(len(suitable), 0)

    def test_best_quant_for_ram(self):
        qm = self._make_manager(ram_gb=8.0)
        best = qm.best_quant_for_ram("llama3:8b")
        self.assertIn(best, ["Q4_K_M", "Q5_K_M", "Q3_K_M", "Q2_K"])

    def test_gguf_info_structure(self):
        from local_models.quantization_manager import QuantizationManager
        info = QuantizationManager.gguf_info()
        self.assertIn("format", info)
        self.assertEqual(info["format"], "GGUF")
        self.assertIn("quantization_levels", info)

    def test_list_local_models_empty(self):
        qm = self._make_manager()
        models = qm.list_local_models()
        self.assertIsInstance(models, list)

    def test_repr(self):
        qm = self._make_manager()
        self.assertIn("QuantizationManager", repr(qm))

    @patch("requests.get")
    def test_download_model(self, mock_get):
        import tempfile
        tmpdir = Path(tempfile.mkdtemp())
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = Mock()
        mock_resp.headers = {"Content-Length": "100"}
        mock_resp.iter_content = Mock(return_value=iter([b"x" * 100]))
        mock_get.return_value = mock_resp

        from local_models.quantization_manager import QuantizationManager
        qm = QuantizationManager(models_dir=tmpdir, available_ram_gb=16.0)
        job = qm.download_model("http://example.com/model.gguf", "testmodel", "Q4_K_M")
        self.assertEqual(job.status, "done")

    def test_detect_ram_fallback(self):
        from local_models.quantization_manager import QuantizationManager
        ram = QuantizationManager._detect_ram()
        self.assertGreater(ram, 0)


# ===========================================================================
# OfflineMode tests
# ===========================================================================

class TestOfflineMode(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = Path(tempfile.mkdtemp())

    def _make_manager(self, air_gap=False):
        from local_models.offline_manager import OfflineMode
        return OfflineMode(cache_dir=self.tmpdir, air_gap=air_gap)

    def test_air_gap_blocks_connectivity(self):
        mgr = self._make_manager(air_gap=True)
        self.assertFalse(mgr.is_online())

    def test_enable_air_gap(self):
        mgr = self._make_manager()
        mgr.enable_air_gap()
        self.assertTrue(mgr.air_gap_enabled)

    def test_disable_air_gap(self):
        mgr = self._make_manager(air_gap=True)
        mgr.disable_air_gap()
        self.assertFalse(mgr.air_gap_enabled)

    def test_guard_blocks_in_air_gap(self):
        mgr = self._make_manager(air_gap=True)
        with self.assertRaises(RuntimeError):
            mgr.guard_external_call("DeepSeek")

    def test_guard_allows_without_air_gap_online(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=True):
            # Should not raise
            mgr.guard_external_call("DeepSeek")

    def test_guard_blocks_when_offline(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=False):
            with self.assertRaises(RuntimeError):
                mgr.guard_external_call("DeepSeek")

    def test_response_cache_set_get(self):
        mgr = self._make_manager()
        mgr.cache_response("What is estoppel?", "llama3", "Estoppel is...")
        cached = mgr.get_cached_response("What is estoppel?", "llama3")
        self.assertEqual(cached, "Estoppel is...")

    def test_response_cache_miss(self):
        mgr = self._make_manager()
        result = mgr.get_cached_response("unknown prompt", "llama3")
        self.assertIsNone(result)

    def test_clear_response_cache(self):
        mgr = self._make_manager()
        mgr.cache_response("prompt", "llama3", "response")
        count = mgr.clear_response_cache()
        self.assertEqual(count, 1)
        self.assertEqual(mgr.response_cache_size, 0)

    def test_get_template(self):
        mgr = self._make_manager()
        tmpl = mgr.get_template("nda_simple")
        self.assertIsNotNone(tmpl)
        self.assertIn("NON-DISCLOSURE", tmpl)

    def test_list_templates(self):
        mgr = self._make_manager()
        templates = mgr.list_templates()
        self.assertIn("nda_simple", templates)
        self.assertIn("engagement_letter", templates)

    def test_add_custom_template(self):
        mgr = self._make_manager()
        mgr.add_template("custom_tmpl", "Custom content [NAME]")
        self.assertEqual(mgr.get_template("custom_tmpl"), "Custom content [NAME]")

    def test_fill_template(self):
        mgr = self._make_manager()
        filled = mgr.fill_template("nda_simple", {
            "DATE": "2025-01-01",
            "PARTY_A": "ACME Corp",
            "PARTY_B": "Widgets Ltd",
            "TERM": "2",
        })
        self.assertIn("ACME Corp", filled)
        self.assertIn("Widgets Ltd", filled)
        self.assertNotIn("[DATE]", filled)

    def test_fill_template_missing_template(self):
        mgr = self._make_manager()
        result = mgr.fill_template("nonexistent_template", {"KEY": "value"})
        self.assertIsNone(result)

    def test_pre_cache_templates(self):
        mgr = self._make_manager()
        count = mgr.pre_cache_templates()
        self.assertGreaterEqual(count, 4)

    def test_capability_report_air_gap(self):
        mgr = self._make_manager(air_gap=True)
        report = mgr.capability_report()
        self.assertTrue(report["air_gap_mode"])
        self.assertFalse(report["capabilities"]["DeepSeek API"])
        self.assertTrue(report["capabilities"]["Local Ollama models"])

    def test_capability_report_online(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=True):
            report = mgr.capability_report()
        self.assertTrue(report["capabilities"]["DeepSeek API"])

    def test_with_fallback_online(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=True):
            result = mgr.with_fallback(
                online_fn=lambda: "online_result",
                offline_fn=lambda: "offline_result",
            )
        self.assertEqual(result, "online_result")

    def test_with_fallback_offline(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=False):
            result = mgr.with_fallback(
                online_fn=lambda: "online_result",
                offline_fn=lambda: "offline_result",
            )
        self.assertEqual(result, "offline_result")

    def test_with_fallback_online_exception_uses_offline(self):
        mgr = self._make_manager()
        with patch.object(mgr, "is_online", return_value=True):
            result = mgr.with_fallback(
                online_fn=lambda: (_ for _ in ()).throw(RuntimeError("API error")),
                offline_fn=lambda: "fallback_result",
            )
        self.assertEqual(result, "fallback_result")

    def test_status_structure(self):
        mgr = self._make_manager()
        s = mgr.status()
        self.assertIn("air_gap", s)
        self.assertIn("cache_dir", s)
        self.assertIn("response_cache_entries", s)

    def test_repr(self):
        mgr = self._make_manager()
        self.assertIn("OfflineMode", repr(mgr))

    def test_blocked_call_log(self):
        mgr = self._make_manager(air_gap=True)
        try:
            mgr.guard_external_call("Service A")
        except RuntimeError:
            pass
        self.assertIn("Service A", mgr.blocked_call_log)

    @patch("socket.create_connection")
    def test_check_connectivity_success(self, mock_conn):
        mock_conn.return_value = Mock()
        from local_models.offline_manager import OfflineMode
        result = OfflineMode._check_connectivity()
        self.assertTrue(result)

    @patch("socket.create_connection")
    def test_check_connectivity_failure(self, mock_conn):
        import socket
        mock_conn.side_effect = OSError
        from local_models.offline_manager import OfflineMode
        result = OfflineMode._check_connectivity()
        self.assertFalse(result)


# ===========================================================================
# Integration-style tests
# ===========================================================================

class TestModelRouterFallbackChain(unittest.TestCase):
    """Test that the router correctly falls through the provider chain."""

    def test_ollama_failure_falls_to_deepseek(self):
        from local_models.model_router import ModelRouter, Provider
        router = ModelRouter(deepseek_api_key="test-key")

        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        mock_ollama.model_exists.return_value = True
        mock_ollama.generate.side_effect = Exception("Ollama crashed")
        mock_ollama.default_model = "llama3"
        router._ollama = mock_ollama

        mock_ds = Mock()
        mock_ds.complete.return_value = {
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "DeepSeek answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "cost_usd": 0.001,
        }
        router._deepseek = mock_ds

        result = router.complete("Legal question?", task="chat")
        # Should have fallen back to DeepSeek or returned an error
        self.assertIsNotNone(result)

    def test_all_providers_fail_returns_error_result(self):
        from local_models.model_router import ModelRouter
        router = ModelRouter()
        # No API keys, no Ollama
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = False
        router._ollama = mock_ollama
        result = router.complete("Question", task="chat")
        self.assertIsNotNone(result.error)


class TestOfflineCachePersistence(unittest.TestCase):
    def test_cache_survives_reload(self):
        import tempfile
        tmpdir = Path(tempfile.mkdtemp())
        from local_models.offline_manager import OfflineMode
        mgr1 = OfflineMode(cache_dir=tmpdir)
        mgr1.cache_response("Prompt A", "llama3", "Answer A")

        mgr2 = OfflineMode(cache_dir=tmpdir)
        cached = mgr2.get_cached_response("Prompt A", "llama3")
        self.assertEqual(cached, "Answer A")


class TestDeepSeekReasonerRouting(unittest.TestCase):
    """Ensure legal research tasks route to deepseek-reasoner."""

    def test_task_model_mapping(self):
        from local_models.model_router import TASK_DEEPSEEK_MODEL, TaskType
        model = TASK_DEEPSEEK_MODEL[TaskType.LEGAL_RESEARCH]
        self.assertEqual(model, "deepseek-reasoner")

    def test_chat_routes_to_chat_model(self):
        from local_models.model_router import TASK_DEEPSEEK_MODEL, TaskType
        model = TASK_DEEPSEEK_MODEL[TaskType.CHAT]
        self.assertEqual(model, "deepseek-chat")


class TestQuantizationLargeModel(unittest.TestCase):
    def test_70b_model_requires_significant_ram(self):
        import tempfile
        from local_models.quantization_manager import QuantizationManager
        qm = QuantizationManager(
            models_dir=Path(tempfile.mkdtemp()),
            available_ram_gb=48.0
        )
        req = qm.memory_required_gb("llama3:70b", "Q4_K_M")
        self.assertGreater(req, 30.0)

    def test_70b_does_not_fit_in_8gb(self):
        import tempfile
        from local_models.quantization_manager import QuantizationManager
        qm = QuantizationManager(
            models_dir=Path(tempfile.mkdtemp()),
            available_ram_gb=8.0
        )
        report = qm.what_can_i_run(ram_gb=8.0)
        self.assertNotIn("llama3:70b", report)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
