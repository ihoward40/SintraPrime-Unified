"""
Ollama Adapter — SintraPrime Local LLM
Communicates with a running Ollama daemon to serve Hermes, Llama, Mistral, etc.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Callable, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from .provider import LLMConfig, LLMResponse, LocalLLMProvider, ProviderRegistry

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1.0, 2.0, 4.0]  # exponential backoff delays (seconds)


@ProviderRegistry.register("ollama")
class OllamaAdapter(LocalLLMProvider):
    """
    Async adapter for the Ollama REST API.

    Endpoints used:
      POST /api/generate   — text generation (streaming & non-streaming)
      POST /api/embeddings — embedding generation
      GET  /api/tags       — list local models
      POST /api/pull       — download a model
      GET  /               — health / version check
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if httpx is None:
            raise RuntimeError(
                "httpx is required for OllamaAdapter. Install it with: pip install httpx"
            )
        self._base_url = config.base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self.config.timeout, connect=10.0),
            )
        return self._client

    async def _post_with_retry(self, endpoint: str, payload: dict) -> httpx.Response:
        """POST request with 3-attempt exponential backoff."""
        client = self._get_client()
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt, delay in enumerate([0.0] + _RETRY_DELAYS, start=1):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                return response
            except httpx.ConnectError as exc:
                last_exc = exc
                self.logger.warning(
                    "Ollama connection error (attempt %d/4): %s", attempt, exc
                )
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                self.logger.warning(
                    "Ollama HTTP error (attempt %d/4): %s", attempt, exc
                )
                if exc.response.status_code < 500:
                    # 4xx errors won't improve with retries
                    break
        raise last_exc

    async def _stream_request(self, endpoint: str, payload: dict) -> AsyncGenerator[dict, None]:
        """Stream NDJSON lines from Ollama, yielding parsed dicts."""
        client = self._get_client()
        try:
            async with client.stream("POST", endpoint, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        self.logger.warning("Failed to parse stream line: %r", line)
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(self, prompt: str, system: str = "") -> LLMResponse:
        """Generate a complete (non-streaming) response."""
        system_text = system or self.config.system_prompt
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_text,
            "stream": False,
            "options": self.config.to_ollama_options(),
        }
        self.logger.debug("Ollama generate | model=%s | prompt_len=%d", self.config.model, len(prompt))
        try:
            response = await self._post_with_retry("/api/generate", payload)
        except Exception as exc:
            raise ConnectionError(
                f"Ollama generate failed: {exc}. "
                "Ensure Ollama is running and the model is pulled."
            ) from exc

        data = response.json()
        return LLMResponse(
            content=data.get("response", ""),
            model=data.get("model", self.config.model),
            tokens_used=data.get("eval_count", 0),
            finish_reason="stop" if data.get("done") else "length",
            metadata={
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_duration_ns": data.get("eval_duration", 0),
                "total_duration_ns": data.get("total_duration", 0),
                "load_duration_ns": data.get("load_duration", 0),
            },
        )

    async def stream(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive from Ollama."""
        system_text = system or self.config.system_prompt
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_text,
            "stream": True,
            "options": self.config.to_ollama_options(),
        }
        self.logger.debug(
            "Ollama stream | model=%s | prompt_len=%d", self.config.model, len(prompt)
        )
        async for chunk in self._stream_request("/api/generate", payload):
            token = chunk.get("response", "")
            if token:
                yield token
            if chunk.get("done"):
                break

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector using Ollama's embedding endpoint."""
        payload = {"model": self.config.model, "prompt": text}
        try:
            response = await self._post_with_retry("/api/embeddings", payload)
        except Exception as exc:
            raise RuntimeError(f"Ollama embedding failed: {exc}") from exc
        data = response.json()
        embedding = data.get("embedding", [])
        if not embedding:
            raise RuntimeError(
                f"Ollama returned empty embedding. "
                f"Ensure the model '{self.config.model}' supports embeddings."
            )
        return embedding

    async def health_check(self) -> bool:
        """Return True if Ollama daemon is reachable."""
        client = self._get_client()
        try:
            response = await client.get("/")
            return response.status_code == 200
        except Exception as exc:
            self.logger.warning("Ollama health check failed: %s", exc)
            return False

    async def list_models(self) -> list[dict]:
        """
        Return a list of locally available models.
        Each dict has keys: name, size, modified_at, digest.
        """
        client = self._get_client()
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as exc:
            self.logger.error("Failed to list Ollama models: %s", exc)
            return []

    async def pull_model(
        self,
        model: str,
        progress_cb: Optional[Callable[[str, float], None]] = None,
    ) -> bool:
        """
        Pull (download) a model from the Ollama hub.
        Calls progress_cb(status, progress_pct) as download progresses.
        Returns True on success.
        """
        payload = {"name": model, "stream": True}
        self.logger.info("Pulling model: %s", model)
        try:
            async for chunk in self._stream_request("/api/pull", payload):
                status = chunk.get("status", "")
                total = chunk.get("total", 0)
                completed = chunk.get("completed", 0)
                pct = (completed / total * 100) if total else 0.0
                if progress_cb:
                    progress_cb(status, pct)
                if "success" in status.lower() or chunk.get("status") == "success":
                    self.logger.info("Model '%s' pulled successfully.", model)
                    return True
        except Exception as exc:
            self.logger.error("Failed to pull model '%s': %s", model, exc)
            return False
        return True

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "OllamaAdapter":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
