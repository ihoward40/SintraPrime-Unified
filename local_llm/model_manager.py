"""
Model Manager — Download, switch, and benchmark local models for SintraPrime.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from .ollama_adapter import OllamaAdapter
from .provider import LLMConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task → model recommendation map
# ---------------------------------------------------------------------------
TASK_RECOMMENDATIONS: dict[str, list[str]] = {
    "legal":     ["hermes3", "nous-hermes2", "hermes-2-pro-mistral"],
    "trust":     ["hermes3", "hermes-2-pro-mistral", "nous-hermes2"],
    "code":      ["codellama", "deepseek-coder", "qwen2.5-coder"],
    "reasoning": ["hermes-2-pro-mistral", "mixtral", "hermes3"],
    "creative":  ["llama3.2", "mistral", "nous-hermes2"],
    "fast":      ["llama3.2", "phi3", "mistral"],
    "large":     ["mixtral", "llama3.1:70b", "nous-hermes2:34b"],
    "default":   ["hermes3", "llama3.2", "mistral"],
}

# Models known to support embeddings
EMBEDDING_CAPABLE = {"nomic-embed-text", "mxbai-embed-large", "all-minilm"}

DEFAULT_BENCHMARK_PROMPT = "Explain trust law in one paragraph."


class ModelManager:
    """
    Manage local models served by Ollama.

    Responsibilities:
      - List which models are locally available.
      - Pull (download) new models.
      - Benchmark a model for speed and responsiveness.
      - Recommend the best model for a given task.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._adapter_cache: dict[str, OllamaAdapter] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_adapter(self, model: str) -> OllamaAdapter:
        if model not in self._adapter_cache:
            config = LLMConfig(model=model, base_url=self.base_url)
            self._adapter_cache[model] = OllamaAdapter(config)
        return self._adapter_cache[model]

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def list_available(self) -> list[dict]:
        """
        Return a list of all locally available models.

        Each entry:
          {"name": str, "size": int, "modified_at": str, "digest": str}
        """
        adapter = self._get_adapter("__list__")
        try:
            models = await adapter.list_models()
            self.logger.info("Found %d local models.", len(models))
            return models
        except Exception as exc:
            self.logger.error("Failed to list models: %s", exc)
            return []

    async def pull_model(
        self,
        model: str,
        progress_cb: Optional[Callable[[str, float], None]] = None,
    ) -> bool:
        """
        Download a model from the Ollama hub.

        Args:
            model: Model name, e.g. "hermes3", "llama3.2:3b"
            progress_cb: Optional callback(status: str, pct: float)

        Returns:
            True on success, False on failure.
        """
        adapter = self._get_adapter(model)
        self.logger.info("Pulling model '%s' …", model)
        success = await adapter.pull_model(model, progress_cb=progress_cb)
        if success:
            self.logger.info("Model '%s' pulled successfully.", model)
        else:
            self.logger.error("Failed to pull model '%s'.", model)
        return success

    async def is_available(self, model: str) -> bool:
        """Return True if the model is already downloaded locally."""
        available = await self.list_available()
        names = {m.get("name", "").split(":")[0] for m in available}
        return model.split(":")[0] in names

    async def benchmark(
        self,
        model: str,
        prompt: str = DEFAULT_BENCHMARK_PROMPT,
        warmup: bool = True,
    ) -> dict:
        """
        Benchmark a local model.

        Returns:
          {
            "model": str,
            "first_token_ms": float,
            "total_ms": float,
            "tokens": int,
            "tokens_per_sec": float,
            "prompt": str,
            "error": str | None,
          }
        """
        result: dict = {
            "model": model,
            "first_token_ms": 0.0,
            "total_ms": 0.0,
            "tokens": 0,
            "tokens_per_sec": 0.0,
            "prompt": prompt,
            "error": None,
        }

        adapter = self._get_adapter(model)

        # Optional warmup generation (first generation loads model into VRAM)
        if warmup:
            try:
                self.logger.debug("Warming up model '%s' …", model)
                await adapter.generate("Say: ready", system="")
            except Exception:
                pass  # warmup failure is non-fatal

        # Timed benchmark
        t0 = time.perf_counter()
        first_token_t: Optional[float] = None
        token_count = 0

        try:
            async for token in adapter.stream(prompt, system=""):
                if first_token_t is None:
                    first_token_t = time.perf_counter()
                token_count += len(token.split())  # approximate word count
        except Exception as exc:
            result["error"] = str(exc)
            self.logger.error("Benchmark failed for '%s': %s", model, exc)
            return result

        t1 = time.perf_counter()
        total_ms = (t1 - t0) * 1000
        first_ms = ((first_token_t or t1) - t0) * 1000
        tps = token_count / (t1 - t0) if (t1 - t0) > 0 else 0.0

        result.update(
            first_token_ms=round(first_ms, 2),
            total_ms=round(total_ms, 2),
            tokens=token_count,
            tokens_per_sec=round(tps, 2),
        )
        self.logger.info(
            "Benchmark '%s': %.0f ms total, %.1f tok/s", model, total_ms, tps
        )
        return result

    async def recommend_for_task(self, task: str) -> str:
        """
        Recommend the best locally available model for a given task.

        Task keywords: legal, trust, code, reasoning, creative, fast, large.
        Falls back to any available model if nothing matches.
        """
        task_lower = task.lower()
        for key, candidates in TASK_RECOMMENDATIONS.items():
            if key in task_lower:
                preferred = candidates
                break
        else:
            preferred = TASK_RECOMMENDATIONS["default"]

        available = await self.list_available()
        available_names = {m.get("name", "").split(":")[0] for m in available}

        for candidate in preferred:
            base = candidate.split(":")[0]
            if base in available_names:
                self.logger.info(
                    "Recommended model for task '%s': %s", task, candidate
                )
                return candidate

        # Fallback: return first available
        if available:
            fallback = available[0].get("name", "hermes3")
            self.logger.warning(
                "No preferred model available for task '%s'. Using: %s", task, fallback
            )
            return fallback

        # Last resort
        self.logger.warning("No local models found. Defaulting to hermes3.")
        return "hermes3"

    async def benchmark_all(self, prompt: str = DEFAULT_BENCHMARK_PROMPT) -> list[dict]:
        """Benchmark all locally available models and return sorted results."""
        models = await self.list_available()
        results = []
        for m in models:
            name = m.get("name", "")
            if not name:
                continue
            result = await self.benchmark(name, prompt=prompt, warmup=False)
            results.append(result)
        # Sort by tokens_per_sec descending
        results.sort(key=lambda r: r.get("tokens_per_sec", 0), reverse=True)
        return results

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        adapter = self._get_adapter("health")
        return await adapter.health_check()

    async def close(self) -> None:
        """Close all cached adapters."""
        for adapter in self._adapter_cache.values():
            await adapter.close()
        self._adapter_cache.clear()

    async def __aenter__(self) -> "ModelManager":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
