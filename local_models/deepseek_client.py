"""
DeepSeek Client — SintraPrime-Unified local_models
API client for DeepSeek-V3 and DeepSeek-R1 (reasoning model).
Handles chain-of-thought extraction, legal reasoning mode, and cost tracking.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"

# Pricing in USD per 1 M tokens (approximate, as of early 2025)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "deepseek-chat": {        # DeepSeek-V3
        "input": 0.14,
        "output": 0.28,
    },
    "deepseek-reasoner": {    # DeepSeek-R1
        "input": 0.55,
        "output": 2.19,
    },
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    task_type: Optional[str] = None


@dataclass
class ReasoningResult:
    """Result from a DeepSeek-R1 call including chain-of-thought."""

    thinking: str          # Content inside <think>…</think>
    answer: str            # Final answer (after <think> block)
    full_response: str     # Raw combined text
    model: str
    usage: Dict[str, int]
    cost_usd: float


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DeepSeekAuthError(Exception):
    """API key missing or invalid."""


class DeepSeekRateLimitError(Exception):
    """Rate limit exceeded."""


class DeepSeekAPIError(Exception):
    """Generic DeepSeek API error."""


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class CostTracker:
    """Tracks DeepSeek API usage and cost across the session."""

    def __init__(self) -> None:
        self._records: List[UsageRecord] = []

    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task_type: Optional[str] = None,
    ) -> float:
        """Record a call and return the cost in USD."""
        pricing = MODEL_PRICING.get(model, {"input": 0.5, "output": 1.5})
        cost = (
            prompt_tokens / 1_000_000 * pricing["input"]
            + completion_tokens / 1_000_000 * pricing["output"]
        )
        rec = UsageRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            task_type=task_type,
        )
        self._records.append(rec)
        logger.debug(
            "DeepSeek usage — model=%s prompt=%d completion=%d cost=$%.6f",
            model, prompt_tokens, completion_tokens, cost,
        )
        return cost

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self._records)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self._records)

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self._records)

    def summary(self) -> Dict[str, Any]:
        return {
            "calls": len(self._records),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "by_model": self._by_model(),
        }

    def _by_model(self) -> Dict[str, Any]:
        agg: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            if r.model not in agg:
                agg[r.model] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
            agg[r.model]["calls"] += 1
            agg[r.model]["cost_usd"] += r.cost_usd
            agg[r.model]["tokens"] += r.prompt_tokens + r.completion_tokens
        return agg

    def reset(self) -> None:
        self._records.clear()


# ---------------------------------------------------------------------------
# DeepSeekClient
# ---------------------------------------------------------------------------


class DeepSeekClient:
    """
    Client for the DeepSeek API supporting V3 (deepseek-chat) and
    R1 (deepseek-reasoner) models.

    Parameters
    ----------
    api_key:
        DeepSeek API key. Falls back to DEEPSEEK_API_KEY env var if not set.
    base_url:
        Override the API base URL.
    timeout:
        Request timeout in seconds.
    max_retries:
        Retry count for transient failures.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEEPSEEK_API_BASE,
        timeout: int = 120,
        max_retries: int = 3,
    ) -> None:
        import os
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cost_tracker = CostTracker()
        self._session = self._build_session(max_retries)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise DeepSeekAuthError(
                "DeepSeek API key not set. "
                "Pass api_key= or set DEEPSEEK_API_KEY env var."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: Dict[str, Any], stream: bool = False) -> requests.Response:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
                stream=stream,
            )
        except requests.exceptions.ConnectionError as exc:
            raise DeepSeekAPIError(f"Connection error: {exc}") from exc

        if resp.status_code == 401:
            raise DeepSeekAuthError("Invalid or missing DeepSeek API key.")
        if resp.status_code == 429:
            raise DeepSeekRateLimitError("DeepSeek rate limit reached. Retry later.")
        if not resp.ok:
            raise DeepSeekAPIError(f"DeepSeek API error {resp.status_code}: {resp.text[:500]}")
        return resp

    def _record_usage(
        self, data: Dict[str, Any], task_type: Optional[str] = None
    ) -> float:
        usage = data.get("usage", {})
        model = data.get("model", "unknown")
        return self.cost_tracker.record(
            model=model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            task_type=task_type,
        )

    # ------------------------------------------------------------------
    # Chain-of-thought extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_thinking(text: str) -> Tuple[str, str]:
        """
        Extract content from DeepSeek-R1's <think>…</think> block.

        Returns (thinking, answer) where thinking is the CoT and answer
        is the remainder of the text.
        """
        pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        match = pattern.search(text)
        if match:
            thinking = match.group(1).strip()
            answer = pattern.sub("", text).strip()
        else:
            thinking = ""
            answer = text.strip()
        return thinking, answer

    # ------------------------------------------------------------------
    # Core completion
    # ------------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        model: str = "deepseek-chat",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        task_type: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a completion with the given model.

        Parameters
        ----------
        prompt:
            User message.
        model:
            ``"deepseek-chat"`` (V3) or ``"deepseek-reasoner"`` (R1).
        system:
            Optional system prompt.
        temperature:
            Sampling temperature.
        max_tokens:
            Max tokens to generate.
        task_type:
            Optional label for cost tracking (e.g. "legal_research").
        stream:
            Stream response (returns generator if True).
        """
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_complete(payload, task_type=task_type)  # type: ignore[return-value]

        resp = self._post("/chat/completions", payload)
        data = resp.json()
        cost = self._record_usage(data, task_type=task_type)
        data["cost_usd"] = cost
        return data

    def _stream_complete(
        self, payload: Dict[str, Any], task_type: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        resp = self._post("/chat/completions", payload, stream=True)
        for line in resp.iter_lines():
            if not line:
                continue
            raw = line.decode("utf-8") if isinstance(line, bytes) else line
            if raw.startswith("data: "):
                raw = raw[6:]
            if raw == "[DONE]":
                break
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                continue

    # ------------------------------------------------------------------
    # Chat (multi-turn)
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Multi-turn chat with DeepSeek."""
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        resp = self._post("/chat/completions", payload)
        data = resp.json()
        cost = self._record_usage(data, task_type=task_type)
        data["cost_usd"] = cost
        return data

    # ------------------------------------------------------------------
    # Legal reasoning (DeepSeek-R1)
    # ------------------------------------------------------------------

    def legal_reasoning(
        self,
        question: str,
        context: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        max_tokens: int = 8192,
    ) -> ReasoningResult:
        """
        Run deep legal reasoning using DeepSeek-R1.

        Enables extended chain-of-thought and returns a ReasoningResult
        with the thinking trace separated from the final answer.

        Parameters
        ----------
        question:
            The legal question or research task.
        context:
            Optional legal context, case facts, or document excerpt.
        jurisdiction:
            Optional jurisdiction string (e.g. "California", "UK").
        max_tokens:
            Max tokens. Defaults to 8192 for comprehensive analysis.
        """
        system_parts = [
            "You are an expert legal AI assistant with deep knowledge of case law, "
            "statutes, and legal reasoning. Provide thorough, accurate analysis.",
        ]
        if jurisdiction:
            system_parts.append(f"Focus on {jurisdiction} law unless otherwise specified.")
        system_prompt = " ".join(system_parts)

        user_parts = []
        if context:
            user_parts.append(f"CONTEXT:\n{context}\n")
        user_parts.append(f"LEGAL QUESTION:\n{question}")
        user_prompt = "\n".join(user_parts)

        resp = self.complete(
            prompt=user_prompt,
            model="deepseek-reasoner",
            system=system_prompt,
            temperature=0.1,   # low temperature for deterministic legal reasoning
            max_tokens=max_tokens,
            task_type="legal_research",
        )

        # Extract content from response
        choice = resp.get("choices", [{}])[0]
        message = choice.get("message", {})
        full_text = message.get("content", "")

        # R1 may also put thinking in a separate field
        reasoning_content = message.get("reasoning_content", "")
        if reasoning_content:
            thinking = reasoning_content.strip()
            answer = full_text.strip()
        else:
            thinking, answer = self.extract_thinking(full_text)

        return ReasoningResult(
            thinking=thinking,
            answer=answer,
            full_response=full_text,
            model=resp.get("model", "deepseek-reasoner"),
            usage=resp.get("usage", {}),
            cost_usd=resp.get("cost_usd", 0.0),
        )

    # ------------------------------------------------------------------
    # Cost / usage
    # ------------------------------------------------------------------

    def cost_summary(self) -> Dict[str, Any]:
        """Return the current session cost summary."""
        return self.cost_tracker.summary()

    def reset_cost_tracker(self) -> None:
        """Reset the cost tracker."""
        self.cost_tracker.reset()

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "deepseek-chat",
    ) -> float:
        """Estimate cost in USD without making an API call."""
        pricing = MODEL_PRICING.get(model, {"input": 0.5, "output": 1.5})
        return (
            prompt_tokens / 1_000_000 * pricing["input"]
            + completion_tokens / 1_000_000 * pricing["output"]
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        has_key = bool(self.api_key)
        return f"DeepSeekClient(has_key={has_key}, base_url={self.base_url!r})"
