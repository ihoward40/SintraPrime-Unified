"""
Ollama Client — SintraPrime-Unified local_models
Connects to a local Ollama instance and provides generate, chat,
embeddings, model management, and streaming support.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Generator, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model capability registry
# ---------------------------------------------------------------------------

LEGAL_RECOMMENDED_MODELS: List[str] = [
    "llama3",
    "mistral",
    "deepseek-r1",
    "hermes3",
]

MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "llama3": {
        "description": "Meta's LLaMA 3 — strong general-purpose reasoning",
        "legal_tasks": ["chat", "summarisation", "document_review"],
        "context_length": 8192,
        "strengths": ["instruction following", "structured output"],
    },
    "mistral": {
        "description": "Mistral 7B — fast and precise",
        "legal_tasks": ["chat", "clause_extraction", "quick_research"],
        "context_length": 32768,
        "strengths": ["speed", "long context"],
    },
    "deepseek-r1": {
        "description": "DeepSeek-R1 — deep chain-of-thought reasoning model",
        "legal_tasks": ["legal_research", "case_analysis", "contract_review", "argument_construction"],
        "context_length": 65536,
        "strengths": ["complex reasoning", "multi-step analysis", "legal nuance"],
    },
    "hermes3": {
        "description": "Hermes 3 — fine-tuned for instruction and tool-use",
        "legal_tasks": ["chat", "template_filling", "extraction"],
        "context_length": 131072,
        "strengths": ["instruction following", "tool use", "very long context"],
    },
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OllamaConnectionError(Exception):
    """Raised when the client cannot connect to the Ollama daemon."""


class OllamaModelError(Exception):
    """Raised when a requested model is not available or fails."""


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------


class OllamaClient:
    """
    Client for the local Ollama REST API.

    Parameters
    ----------
    base_url:
        URL of the Ollama server. Defaults to ``http://localhost:11434``.
    timeout:
        Request timeout in seconds (default 120 s for generation).
    max_retries:
        Number of automatic retries on transient connection failures.
    default_model:
        Model used when no model is explicitly provided.
    """

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 120,
        max_retries: int = 3,
        default_model: str = "llama3",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_model = default_model
        self._session = self._build_session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _post(self, path: str, payload: Dict[str, Any], stream: bool = False) -> requests.Response:
        try:
            resp = self._session.post(
                self._url(path),
                json=payload,
                timeout=self.timeout,
                stream=stream,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as exc:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is the Ollama daemon running? Try: ollama serve"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise OllamaModelError(f"Ollama API error: {exc}") from exc

    def _get(self, path: str) -> requests.Response:
        try:
            resp = self._session.get(self._url(path), timeout=self.timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as exc:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}."
            ) from exc

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the Ollama daemon is reachable and healthy."""
        try:
            resp = self._session.get(self._url("/"), timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """Return a detailed health report."""
        available = self.is_available()
        result: Dict[str, Any] = {
            "available": available,
            "base_url": self.base_url,
            "timestamp": time.time(),
        }
        if available:
            try:
                models = self.list_models()
                result["loaded_models"] = [m["name"] for m in models]
                result["model_count"] = len(models)
            except Exception as exc:
                result["error"] = str(exc)
        return result

    def wait_until_ready(self, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """Block until Ollama is ready or timeout is reached."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_available():
                return True
            time.sleep(poll_interval)
        return False

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def list_models(self) -> List[Dict[str, Any]]:
        """Return a list of locally available models."""
        resp = self._get("/api/tags")
        data = resp.json()
        return data.get("models", [])

    def model_info(self, model: str) -> Dict[str, Any]:
        """Return detailed information about a specific model."""
        resp = self._post("/api/show", {"name": model})
        return resp.json()

    def pull_model(
        self,
        model: str,
        stream: bool = True,
        progress_callback: Optional[Any] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Pull (download) a model from the Ollama registry.

        Yields status dicts with keys: ``status``, ``completed``, ``total``.
        """
        resp = self._post("/api/pull", {"name": model}, stream=True)
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if progress_callback:
                progress_callback(chunk)
            yield chunk

    def delete_model(self, model: str) -> Dict[str, Any]:
        """Delete a locally stored model."""
        try:
            resp = self._session.delete(
                self._url("/api/delete"),
                json={"name": model},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return {"deleted": model}
        except requests.exceptions.HTTPError as exc:
            raise OllamaModelError(f"Failed to delete model '{model}': {exc}") from exc

    def model_exists(self, model: str) -> bool:
        """Return True if the model is locally available."""
        try:
            models = self.list_models()
            names = [m.get("name", "").split(":")[0] for m in models]
            return model.split(":")[0] in names
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
        """
        Generate a completion for the given prompt.

        Parameters
        ----------
        prompt:
            The user prompt.
        model:
            Model name. Falls back to ``self.default_model``.
        system:
            Optional system prompt.
        temperature:
            Sampling temperature (0–1).
        max_tokens:
            Maximum number of tokens to generate.
        stream:
            If True, returns a generator that yields response chunks.
        options:
            Additional Ollama options dict (e.g. top_p, top_k).

        Returns
        -------
        Non-streaming: a dict with ``response`` and metadata keys.
        Streaming: a generator of chunk dicts.
        """
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                **({"num_predict": max_tokens} if max_tokens else {}),
                **(options or {}),
            },
        }
        if system:
            payload["system"] = system

        if stream:
            return self._stream_generate(payload)

        resp = self._post("/api/generate", payload)
        return resp.json()

    def _stream_generate(self, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        resp = self._post("/api/generate", payload, stream=True)
        for line in resp.iter_lines():
            if line:
                yield json.loads(line)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
        """
        Multi-turn chat completion.

        Parameters
        ----------
        messages:
            List of ``{"role": "user"|"assistant"|"system", "content": "..."}`` dicts.
        """
        all_messages = list(messages)
        if system:
            all_messages = [{"role": "system", "content": system}] + all_messages

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": all_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                **({"num_predict": max_tokens} if max_tokens else {}),
                **(options or {}),
            },
        }

        if stream:
            return self._stream_chat(payload)

        resp = self._post("/api/chat", payload)
        return resp.json()

    def _stream_chat(self, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        resp = self._post("/api/chat", payload, stream=True)
        for line in resp.iter_lines():
            if line:
                yield json.loads(line)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Returns a list of floats.
        """
        payload = {
            "model": model or self.default_model,
            "prompt": text,
        }
        resp = self._post("/api/embeddings", payload)
        data = resp.json()
        return data.get("embedding", [])

    def batch_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return [self.embeddings(text, model=model) for text in texts]

    # ------------------------------------------------------------------
    # Capability helpers
    # ------------------------------------------------------------------

    def recommended_model_for_task(self, task: str) -> str:
        """
        Return the recommended local model name for a given task type.

        Falls back to ``self.default_model`` if no match.
        """
        for model_name, info in MODEL_CAPABILITIES.items():
            if task in info.get("legal_tasks", []):
                if self.model_exists(model_name):
                    return model_name
        return self.default_model

    @staticmethod
    def capability_report() -> Dict[str, Any]:
        """Return the static capability registry for all known models."""
        return {
            "recommended_models": LEGAL_RECOMMENDED_MODELS,
            "capabilities": MODEL_CAPABILITIES,
        }

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"OllamaClient(base_url={self.base_url!r}, default_model={self.default_model!r})"
