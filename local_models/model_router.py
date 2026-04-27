"""
Universal Model Router — SintraPrime-Unified local_models
Single interface for model completion with automatic selection,
task-based routing, and fallback chains.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task categories
# ---------------------------------------------------------------------------


class TaskType(str, Enum):
    LEGAL_RESEARCH = "legal_research"
    CONTRACT_REVIEW = "contract_review"
    CASE_ANALYSIS = "case_analysis"
    DOCUMENT_REVIEW = "document_review"
    CLAUSE_EXTRACTION = "clause_extraction"
    SUMMARISATION = "summarisation"
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    TEMPLATE_FILLING = "template_filling"
    ARGUMENT_CONSTRUCTION = "argument_construction"
    QUICK_RESEARCH = "quick_research"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------


class Provider(str, Enum):
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# Task → preferred provider (in order)
TASK_PROVIDER_PREFERENCE: Dict[TaskType, List[Provider]] = {
    TaskType.LEGAL_RESEARCH:       [Provider.OLLAMA, Provider.DEEPSEEK, Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.CASE_ANALYSIS:        [Provider.OLLAMA, Provider.DEEPSEEK, Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.ARGUMENT_CONSTRUCTION:[Provider.OLLAMA, Provider.DEEPSEEK, Provider.ANTHROPIC, Provider.OPENAI],
    TaskType.CONTRACT_REVIEW:      [Provider.OLLAMA, Provider.DEEPSEEK, Provider.OPENAI, Provider.ANTHROPIC],
    TaskType.DOCUMENT_REVIEW:      [Provider.OLLAMA, Provider.DEEPSEEK, Provider.OPENAI, Provider.ANTHROPIC],
    TaskType.CLAUSE_EXTRACTION:    [Provider.OLLAMA, Provider.DEEPSEEK, Provider.OPENAI, Provider.ANTHROPIC],
    TaskType.SUMMARISATION:        [Provider.OLLAMA, Provider.OPENAI, Provider.DEEPSEEK, Provider.ANTHROPIC],
    TaskType.TEMPLATE_FILLING:     [Provider.OLLAMA, Provider.OPENAI, Provider.DEEPSEEK, Provider.ANTHROPIC],
    TaskType.QUICK_RESEARCH:       [Provider.OLLAMA, Provider.DEEPSEEK, Provider.OPENAI, Provider.ANTHROPIC],
    TaskType.CHAT:                 [Provider.OLLAMA, Provider.OPENAI, Provider.ANTHROPIC, Provider.DEEPSEEK],
    TaskType.EMBEDDINGS:           [Provider.OLLAMA, Provider.OPENAI, Provider.DEEPSEEK, Provider.ANTHROPIC],
    TaskType.GENERAL:              [Provider.OLLAMA, Provider.DEEPSEEK, Provider.OPENAI, Provider.ANTHROPIC],
}

# Task → recommended local model
TASK_LOCAL_MODEL: Dict[TaskType, str] = {
    TaskType.LEGAL_RESEARCH:       "deepseek-r1",
    TaskType.CASE_ANALYSIS:        "deepseek-r1",
    TaskType.ARGUMENT_CONSTRUCTION:"deepseek-r1",
    TaskType.CONTRACT_REVIEW:      "mistral",
    TaskType.DOCUMENT_REVIEW:      "mistral",
    TaskType.CLAUSE_EXTRACTION:    "mistral",
    TaskType.SUMMARISATION:        "llama3",
    TaskType.TEMPLATE_FILLING:     "hermes3",
    TaskType.QUICK_RESEARCH:       "mistral",
    TaskType.CHAT:                 "llama3",
    TaskType.EMBEDDINGS:           "llama3",
    TaskType.GENERAL:              "llama3",
}

# Task → recommended DeepSeek model
TASK_DEEPSEEK_MODEL: Dict[TaskType, str] = {
    TaskType.LEGAL_RESEARCH:       "deepseek-reasoner",
    TaskType.CASE_ANALYSIS:        "deepseek-reasoner",
    TaskType.ARGUMENT_CONSTRUCTION:"deepseek-reasoner",
    TaskType.CONTRACT_REVIEW:      "deepseek-chat",
    TaskType.DOCUMENT_REVIEW:      "deepseek-chat",
    TaskType.CLAUSE_EXTRACTION:    "deepseek-chat",
    TaskType.SUMMARISATION:        "deepseek-chat",
    TaskType.TEMPLATE_FILLING:     "deepseek-chat",
    TaskType.QUICK_RESEARCH:       "deepseek-chat",
    TaskType.CHAT:                 "deepseek-chat",
    TaskType.EMBEDDINGS:           "deepseek-chat",
    TaskType.GENERAL:              "deepseek-chat",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class RouterResult:
    content: str
    provider: Provider
    model: str
    task_type: TaskType
    latency_s: float
    usage: Dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    thinking: Optional[str] = None   # CoT from DeepSeek-R1
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------


class ModelRouter:
    """
    Single interface for model completions.

    Automatically selects the best available provider and model based on:
    - Task type
    - Provider availability (Ollama running? DeepSeek key set? etc.)
    - User-configured preferences

    Parameters
    ----------
    ollama_url:
        Ollama base URL. Defaults to http://localhost:11434.
    deepseek_api_key:
        DeepSeek API key. Falls back to DEEPSEEK_API_KEY env var.
    openai_api_key:
        OpenAI API key. Falls back to OPENAI_API_KEY env var.
    anthropic_api_key:
        Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    prefer_local:
        Always prefer local (Ollama) over cloud providers when available.
    air_gap_mode:
        If True, disable all external API calls (use only Ollama).
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        deepseek_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        prefer_local: bool = True,
        air_gap_mode: bool = False,
    ) -> None:
        self.prefer_local = prefer_local
        self.air_gap_mode = air_gap_mode

        # Lazy-init clients
        self._ollama_url = ollama_url
        self._deepseek_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self._anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")

        self._ollama: Optional[Any] = None
        self._deepseek: Optional[Any] = None

        self._availability_cache: Dict[Provider, bool] = {}
        self._cache_expiry: float = 0.0
        self._cache_ttl: float = 30.0   # re-check every 30 s

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _is_available(self, provider: Provider) -> bool:
        """Check if a provider is currently usable."""
        if self.air_gap_mode and provider != Provider.OLLAMA:
            return False

        now = time.time()
        if now < self._cache_expiry and provider in self._availability_cache:
            return self._availability_cache[provider]

        available = self._check_provider(provider)
        self._availability_cache[provider] = available
        self._cache_expiry = now + self._cache_ttl
        return available

    def _check_provider(self, provider: Provider) -> bool:
        if provider == Provider.OLLAMA:
            try:
                client = self._get_ollama()
                return client.is_available()
            except Exception:
                return False

        if provider == Provider.DEEPSEEK:
            return bool(self._deepseek_key)

        if provider == Provider.OPENAI:
            return bool(self._openai_key)

        if provider == Provider.ANTHROPIC:
            return bool(self._anthropic_key)

        return False

    def available_providers(self) -> List[Provider]:
        """Return list of currently available providers."""
        return [p for p in Provider if self._is_available(p)]

    # ------------------------------------------------------------------
    # Client factory (lazy)
    # ------------------------------------------------------------------

    def _get_ollama(self):
        if self._ollama is None:
            from local_models.ollama_client import OllamaClient
            self._ollama = OllamaClient(base_url=self._ollama_url)
        return self._ollama

    def _get_deepseek(self):
        if self._deepseek is None:
            from local_models.deepseek_client import DeepSeekClient
            self._deepseek = DeepSeekClient(api_key=self._deepseek_key)
        return self._deepseek

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------

    def _select_provider(self, task_type: TaskType) -> Optional[Provider]:
        """Return the best available provider for the task."""
        preference = TASK_PROVIDER_PREFERENCE.get(task_type, list(Provider))
        for provider in preference:
            if self._is_available(provider):
                return provider
        return None

    def _resolve_task_type(self, task: Union[str, TaskType]) -> TaskType:
        if isinstance(task, TaskType):
            return task
        try:
            return TaskType(task)
        except ValueError:
            logger.warning("Unknown task type %r — defaulting to GENERAL", task)
            return TaskType.GENERAL

    # ------------------------------------------------------------------
    # Completions
    # ------------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        model: str = "auto",
        task: Union[str, TaskType] = TaskType.GENERAL,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> RouterResult:
        """
        Generate a completion using the best available model.

        Parameters
        ----------
        prompt:
            The user prompt.
        model:
            ``"auto"`` for automatic selection, or a specific model name.
        task:
            Task type string or ``TaskType`` enum value.
        system:
            Optional system prompt.
        temperature:
            Sampling temperature.
        max_tokens:
            Maximum tokens.
        stream:
            Stream the response (only supported on some providers).
        """
        task_type = self._resolve_task_type(task)
        provider = self._select_provider(task_type)

        if provider is None:
            return RouterResult(
                content="",
                provider=Provider.OLLAMA,
                model="none",
                task_type=task_type,
                latency_s=0.0,
                error="No provider available. Is Ollama running or an API key set?",
            )

        # Try providers in preference order with fallback
        errors: List[str] = []
        for p in TASK_PROVIDER_PREFERENCE.get(task_type, list(Provider)):
            if not self._is_available(p):
                continue
            try:
                return self._call_provider(
                    provider=p,
                    prompt=prompt,
                    model=model,
                    task_type=task_type,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning("Provider %s failed: %s — trying next", p.value, exc)
                errors.append(f"{p.value}: {exc}")
                continue

        return RouterResult(
            content="",
            provider=provider,
            model="none",
            task_type=task_type,
            latency_s=0.0,
            error="; ".join(errors) or "All providers failed",
        )

    def _call_provider(
        self,
        provider: Provider,
        prompt: str,
        model: str,
        task_type: TaskType,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> RouterResult:
        start = time.time()

        if provider == Provider.OLLAMA:
            return self._call_ollama(prompt, model, task_type, system, temperature, max_tokens, start)

        if provider == Provider.DEEPSEEK:
            return self._call_deepseek(prompt, model, task_type, system, temperature, max_tokens, start)

        if provider == Provider.OPENAI:
            return self._call_openai(prompt, model, task_type, system, temperature, max_tokens, start)

        if provider == Provider.ANTHROPIC:
            return self._call_anthropic(prompt, model, task_type, system, temperature, max_tokens, start)

        raise ValueError(f"Unknown provider: {provider}")

    def _call_ollama(self, prompt, model, task_type, system, temperature, max_tokens, start) -> RouterResult:
        client = self._get_ollama()
        local_model = TASK_LOCAL_MODEL.get(task_type, "llama3") if model == "auto" else model

        # Ensure model exists locally
        if not client.model_exists(local_model):
            # Try default
            local_model = client.default_model

        resp = client.generate(
            prompt=prompt,
            model=local_model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return RouterResult(
            content=resp.get("response", ""),
            provider=Provider.OLLAMA,
            model=local_model,
            task_type=task_type,
            latency_s=time.time() - start,
            usage={"eval_count": resp.get("eval_count", 0)},
        )

    def _call_deepseek(self, prompt, model, task_type, system, temperature, max_tokens, start) -> RouterResult:
        client = self._get_deepseek()
        ds_model = TASK_DEEPSEEK_MODEL.get(task_type, "deepseek-chat") if model == "auto" else model

        if ds_model == "deepseek-reasoner" or task_type in (
            TaskType.LEGAL_RESEARCH, TaskType.CASE_ANALYSIS, TaskType.ARGUMENT_CONSTRUCTION
        ):
            result = client.legal_reasoning(prompt, context=None, jurisdiction=None, max_tokens=max_tokens)
            return RouterResult(
                content=result.answer,
                provider=Provider.DEEPSEEK,
                model=result.model,
                task_type=task_type,
                latency_s=time.time() - start,
                usage=result.usage,
                cost_usd=result.cost_usd,
                thinking=result.thinking,
            )

        resp = client.complete(
            prompt=prompt,
            model=ds_model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            task_type=task_type.value,
        )
        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        return RouterResult(
            content=content,
            provider=Provider.DEEPSEEK,
            model=resp.get("model", ds_model),
            task_type=task_type,
            latency_s=time.time() - start,
            usage=resp.get("usage", {}),
            cost_usd=resp.get("cost_usd", 0.0),
        )

    def _call_openai(self, prompt, model, task_type, system, temperature, max_tokens, start) -> RouterResult:
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            oai_model = "gpt-4o" if model == "auto" else model
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=oai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content or ""
            return RouterResult(
                content=content,
                provider=Provider.OPENAI,
                model=oai_model,
                task_type=task_type,
                latency_s=time.time() - start,
                usage={"total_tokens": resp.usage.total_tokens if resp.usage else 0},
            )
        except ImportError:
            raise RuntimeError("openai package not installed. pip install openai")

    def _call_anthropic(self, prompt, model, task_type, system, temperature, max_tokens, start) -> RouterResult:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._anthropic_key)
            ant_model = "claude-3-5-sonnet-20241022" if model == "auto" else model
            kwargs: Dict[str, Any] = {
                "model": ant_model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            resp = client.messages.create(**kwargs)
            content = resp.content[0].text if resp.content else ""
            return RouterResult(
                content=content,
                provider=Provider.ANTHROPIC,
                model=ant_model,
                task_type=task_type,
                latency_s=time.time() - start,
                usage={"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
            )
        except ImportError:
            raise RuntimeError("anthropic package not installed. pip install anthropic")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return router status including provider availability."""
        return {
            "prefer_local": self.prefer_local,
            "air_gap_mode": self.air_gap_mode,
            "providers": {
                p.value: self._is_available(p) for p in Provider
            },
            "available_providers": [p.value for p in self.available_providers()],
        }

    def routing_plan(self, task: Union[str, TaskType]) -> Dict[str, Any]:
        """Return the routing plan for a given task without executing it."""
        task_type = self._resolve_task_type(task)
        preference = TASK_PROVIDER_PREFERENCE.get(task_type, list(Provider))
        available = [p for p in preference if self._is_available(p)]
        selected = available[0] if available else None
        return {
            "task": task_type.value,
            "preference_order": [p.value for p in preference],
            "available": [p.value for p in available],
            "selected_provider": selected.value if selected else None,
            "local_model": TASK_LOCAL_MODEL.get(task_type, "llama3"),
            "deepseek_model": TASK_DEEPSEEK_MODEL.get(task_type, "deepseek-chat"),
        }

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        avail = self.available_providers()
        return f"ModelRouter(available={[p.value for p in avail]}, air_gap={self.air_gap_mode})"
