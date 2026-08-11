"""
Phase 3.1 — Real provider adapters for the governed inference control plane.

These adapters wrap the OpenAI and Anthropic SDKs into the InferenceProvider
protocol defined in contracts.py. They are disabled by default and must be
explicitly configured with credentials before they can make network calls.

No production call sites are modified. These adapters exist in isolation and
are exercised only through tests and future migration phases.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Iterator
from dataclasses import replace
from typing import Any

from governed_inference.contracts import (
    CacheStatus,
    CostEstimate,
    InferenceError,
    InferenceRequest,
    InferenceResult,
    ProviderCapabilities,
    ProviderErrorKind,
    ProviderHealth,
    ProviderLimits,
    QualityFloor,
    RouteTier,
)

logger = logging.getLogger("governed_inference.adapters")

# ---------------------------------------------------------------------------
# Ollama error translation
# ---------------------------------------------------------------------------


def _translate_ollama_error(exc: Exception) -> InferenceError:
    """Translate an Ollama/local client exception into an InferenceError."""
    exc_name = type(exc).__name__
    if exc_name in {"OllamaConnectionError", "ConnectionError"}:
        return InferenceError(str(exc), ProviderErrorKind.TRANSIENT)
    if exc_name in {"OllamaModelError", "ValueError"}:
        return InferenceError(str(exc), ProviderErrorKind.INVALID_REQUEST)
    return InferenceError(str(exc), ProviderErrorKind.UNKNOWN)


# ---------------------------------------------------------------------------
# Error translation helpers
# ---------------------------------------------------------------------------

# Map SDK exception types to ProviderErrorKind values.
# These mappings are intentionally conservative — unknown errors map to UNKNOWN,
# which the router treats as non-transient (no retry).

_OPENAI_ERROR_MAP: dict[type, ProviderErrorKind] = {}

_ANTHROPIC_ERROR_MAP: dict[type, ProviderErrorKind] = {}


def _translate_openai_error(exc: Exception) -> InferenceError:
    """Translate an OpenAI SDK exception into an InferenceError with kind."""
    kind = ProviderErrorKind.UNKNOWN
    exc_type = type(exc)
    # Match by class name first (avoids hard dependency on openai SDK at import time)
    exc_name = exc_type.__name__
    if exc_name == "APITimeoutError" or exc_name == "RateLimitError":
        kind = ProviderErrorKind.TRANSIENT
    elif exc_name == "AuthenticationError":
        kind = ProviderErrorKind.AUTHENTICATION
    elif exc_name == "PaymentRequiredError":
        kind = ProviderErrorKind.PAYMENT_REQUIRED
    elif exc_name == "BadRequestError":
        kind = ProviderErrorKind.INVALID_REQUEST
    elif exc_name == "APIConnectionError" or exc_name == "InternalServerError":
        kind = ProviderErrorKind.TRANSIENT
    elif exc_name == "ContextWindowExceededError":
        kind = ProviderErrorKind.CONTEXT_OVERFLOW
    return InferenceError(str(exc), kind)


def _translate_anthropic_error(exc: Exception) -> InferenceError:
    """Translate an Anthropic SDK exception into an InferenceError with kind."""
    exc_name = type(exc).__name__
    if exc_name == "APITimeoutError" or exc_name == "RateLimitError":
        kind = ProviderErrorKind.TRANSIENT
    elif exc_name == "AuthenticationError":
        kind = ProviderErrorKind.AUTHENTICATION
    elif exc_name == "PaymentRequiredError":
        kind = ProviderErrorKind.PAYMENT_REQUIRED
    elif exc_name == "BadRequestError":
        kind = ProviderErrorKind.INVALID_REQUEST
    elif exc_name == "APIConnectionError" or exc_name == "InternalServerError":
        kind = ProviderErrorKind.TRANSIENT
    else:
        kind = ProviderErrorKind.UNKNOWN
    return InferenceError(str(exc), kind)


# ---------------------------------------------------------------------------
# Base real provider
# ---------------------------------------------------------------------------


class _BaseRealProvider:
    """
    Shared logic for real SDK-backed providers.

    Subclasses must implement ``_build_client_kwargs`` and ``_call_sdk``.
    """

    def __init__(
        self,
        *,
        name: str,
        model: str,
        route_tier: RouteTier,
        capabilities: Iterable[str],
        cloud: bool,
        paid: bool,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout_seconds: float | None = None,
        pricing_known: bool = False,
        estimated_cost_usd: float | None = None,
        context_window: int = 8192,
        quality: QualityFloor = QualityFloor.STANDARD,
        source_url: str | None = None,
        account_entitlement_known: bool = False,
        free_allowance_known: bool = False,
    ) -> None:
        self.name = name
        self.model = model
        self._capabilities = frozenset(capabilities)
        self.route_tier = route_tier
        self.cloud = cloud
        self.paid = paid
        self._api_key = api_key
        self._api_base = api_base
        self._timeout_seconds = timeout_seconds
        self.configured = bool(api_key)
        self.pricing_known = pricing_known
        self.estimated_cost_usd = estimated_cost_usd
        self.context_window = context_window
        self.quality = quality
        self.source_url = source_url
        self.account_entitlement_known = account_entitlement_known
        self.free_allowance_known = free_allowance_known
        self._client: Any = None

    def _ensure_client(self) -> Any:
        """Lazily build the SDK client.  Raises if not configured."""
        if not self.configured:
            raise InferenceError(
                f"{self.name} adapter is not configured (missing API key)",
                ProviderErrorKind.AUTHENTICATION,
            )
        if self._client is None:
            kwargs = self._build_client_kwargs()
            self._client = self._create_client(**kwargs)
        return self._client

    def _build_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._api_base:
            kwargs["base_url"] = self._api_base
        if self._timeout_seconds is not None:
            kwargs["timeout"] = self._timeout_seconds
        return kwargs

    def _create_client(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            route_tier=self.route_tier,
            model=self.model,
            capabilities=self._capabilities,
            quality=self.quality,
            context_window=self.context_window,
            supports_streaming=True,
            supports_vision=False,
            supports_structured_output=True,
            paid=self.paid,
            cloud=self.cloud,
        )

    def health(self) -> ProviderHealth:
        if not self.configured:
            return ProviderHealth(
                reachable=False,
                healthy=False,
                reason="not_configured",
            )
        return ProviderHealth(reachable=True, healthy=True)

    def estimate_cost(self, request: InferenceRequest) -> CostEstimate:
        return CostEstimate(
            estimated_cost_usd=self.estimated_cost_usd,
            input_tokens=_rough_tokens(request),
            output_tokens=request.max_output_tokens,
            pricing_known=self.pricing_known,
        )

    def current_limits(self) -> ProviderLimits:
        return ProviderLimits(rate_limits_known=self.configured)

    def _result(
        self,
        request: InferenceRequest,
        content: str,
        usage: dict[str, int],
        provider_request_id: str | None = None,
        latency_ms: int = 0,
        is_partial: bool = False,
    ) -> InferenceResult:
        return InferenceResult(
            request_id=request.request_id,
            provider=self.name,
            model=self.model,
            route_tier=self.route_tier,
            content=content,
            usage=usage,
            estimated_cost_usd=self.estimated_cost_usd,
            actual_cost_usd=self.estimated_cost_usd,
            latency_ms=latency_ms,
            cache_status=CacheStatus.MISS,
            attempts=1,
            finish_reason="stop",
            policy_receipt_id="pending",
            provider_request_id=provider_request_id,
            is_partial=is_partial,
        )


# ---------------------------------------------------------------------------
# OpenAI adapter
# ---------------------------------------------------------------------------


class OpenAIProvider(_BaseRealProvider):
    """
    Production OpenAI provider adapter.

    Wraps ``openai.OpenAI`` (sync) into the InferenceProvider protocol.
    Disabled by default; pass ``api_key`` to configure.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
        timeout_seconds: float | None = 60.0,
        route_tier: RouteTier = RouteTier.CLOUD_PROTOTYPE,
        capabilities: Iterable[str] = (
            "classification",
            "extraction",
            "summarization",
            "drafting",
            "coding",
            "reasoning",
        ),
        pricing_known: bool = False,
        estimated_cost_usd: float | None = None,
        context_window: int = 128000,
        quality: QualityFloor = QualityFloor.STANDARD,
        account_entitlement_known: bool = False,
        free_allowance_known: bool = False,
    ) -> None:
        super().__init__(
            name="openai",
            model=model,
            route_tier=route_tier,
            capabilities=capabilities,
            cloud=True,
            paid=True,
            api_key=api_key,
            api_base=api_base,
            timeout_seconds=timeout_seconds,
            pricing_known=pricing_known,
            estimated_cost_usd=estimated_cost_usd,
            context_window=context_window,
            quality=quality,
            source_url="https://platform.openai.com/docs/api-reference",
            account_entitlement_known=account_entitlement_known,
            free_allowance_known=free_allowance_known,
        )

    def _create_client(self, **kwargs: Any) -> Any:
        import openai

        return openai.OpenAI(**kwargs)

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        client = self._ensure_client()
        started = time.perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "model": request.metadata.get("model_override", self.model),
                "messages": list(request.messages),
                "temperature": request.temperature,
                "max_tokens": request.max_output_tokens,
            }
            if request.structured_output_schema is not None:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "schema": request.structured_output_schema,
                    },
                }
            if request.tools:
                kwargs["tools"] = request.tools

            resp = client.chat.completions.create(**kwargs)
            latency_ms = int((time.perf_counter() - started) * 1000)

            content = resp.choices[0].message.content or ""
            usage_obj = getattr(resp, "usage", None)
            usage = {
                "input_tokens": getattr(usage_obj, "prompt_tokens", 0) if usage_obj else 0,
                "output_tokens": getattr(usage_obj, "completion_tokens", 0) if usage_obj else 0,
                "total_tokens": getattr(usage_obj, "total_tokens", 0) if usage_obj else 0,
                "cached_tokens": 0,
            }
            provider_request_id = getattr(resp, "id", None)

            logger.info(
                "openai.invoke.success",
                extra={
                    "provider": self.name,
                    "model": kwargs["model"],
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "provider_request_id": provider_request_id,
                },
            )
            return self._result(request, content, usage, provider_request_id, latency_ms)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            inf_error = _translate_openai_error(exc)
            logger.warning(
                "openai.invoke.error",
                extra={
                    "provider": self.name,
                    "model": self.model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "error_kind": inf_error.kind.value,
                    "error_type": type(exc).__name__,
                },
            )
            raise inf_error from exc

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        client = self._ensure_client()
        started = time.perf_counter()
        model = request.metadata.get("model_override", self.model)
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": list(request.messages),
                "temperature": request.temperature,
                "max_tokens": request.max_output_tokens,
                "stream": True,
            }
            stream = client.chat.completions.create(**kwargs)
            full_content = ""
            chunk_count = 0
            for chunk in stream:
                delta = ""
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_content += delta
                    chunk_count += 1
                    usage = {
                        "input_tokens": _rough_tokens(request),
                        "output_tokens": chunk_count,
                        "total_tokens": _rough_tokens(request) + chunk_count,
                        "cached_tokens": 0,
                    }
                    yield self._result(
                        request=request,
                        content=delta,
                        usage=usage,
                        provider_request_id=None,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        is_partial=True,
                    )

            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = {
                "input_tokens": _rough_tokens(request),
                "output_tokens": chunk_count,
                "total_tokens": _rough_tokens(request) + chunk_count,
                "cached_tokens": 0,
            }

            logger.info(
                "openai.invoke_stream.success",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "chunk_count": chunk_count,
                },
            )
            yield self._result(
                request=request,
                content=full_content,
                usage=usage,
                provider_request_id=None,
                latency_ms=latency_ms,
                is_partial=False,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            inf_error = _translate_openai_error(exc)
            logger.warning(
                "openai.invoke_stream.error",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "error_kind": inf_error.kind.value,
                    "error_type": type(exc).__name__,
                },
            )
            raise inf_error from exc


# ---------------------------------------------------------------------------
# Anthropic adapter
# ---------------------------------------------------------------------------


class AnthropicProvider(_BaseRealProvider):
    """
    Production Anthropic provider adapter.

    Wraps ``anthropic.Anthropic`` (sync) into the InferenceProvider protocol.
    Disabled by default; pass ``api_key`` to configure.
    """

    def __init__(
        self,
        *,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        api_base: str | None = None,
        timeout_seconds: float | None = 60.0,
        route_tier: RouteTier = RouteTier.CLOUD_CODING,
        capabilities: Iterable[str] = (
            "classification",
            "extraction",
            "summarization",
            "drafting",
            "coding",
            "reasoning",
        ),
        pricing_known: bool = False,
        estimated_cost_usd: float | None = None,
        context_window: int = 200000,
        quality: QualityFloor = QualityFloor.HIGH,
        account_entitlement_known: bool = False,
        free_allowance_known: bool = False,
    ) -> None:
        super().__init__(
            name="anthropic",
            model=model,
            route_tier=route_tier,
            capabilities=capabilities,
            cloud=True,
            paid=True,
            api_key=api_key,
            api_base=api_base,
            timeout_seconds=timeout_seconds,
            pricing_known=pricing_known,
            estimated_cost_usd=estimated_cost_usd,
            context_window=context_window,
            quality=quality,
            source_url="https://docs.anthropic.com/en/api/reference",
            account_entitlement_known=account_entitlement_known,
            free_allowance_known=free_allowance_known,
        )

    def _create_client(self, **kwargs: Any) -> Any:
        import anthropic

        return anthropic.Anthropic(**kwargs)

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        client = self._ensure_client()
        started = time.perf_counter()
        try:
            model = request.metadata.get("model_override", self.model)
            # Extract system message if present
            messages = list(request.messages)
            system_text: str | None = None
            filtered_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_text = msg.get("content", "")
                else:
                    filtered_messages.append(msg)

            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": request.max_output_tokens,
                "messages": filtered_messages,
                "temperature": request.temperature,
            }
            if system_text:
                kwargs["system"] = system_text

            resp = client.messages.create(**kwargs)
            latency_ms = int((time.perf_counter() - started) * 1000)

            content = ""
            if resp.content:
                content = resp.content[0].text
            usage_obj = getattr(resp, "usage", None)
            usage = {
                "input_tokens": getattr(usage_obj, "input_tokens", 0) if usage_obj else 0,
                "output_tokens": getattr(usage_obj, "output_tokens", 0) if usage_obj else 0,
                "total_tokens": (
                    getattr(usage_obj, "input_tokens", 0) + getattr(usage_obj, "output_tokens", 0)
                )
                if usage_obj
                else 0,
                "cached_tokens": 0,
            }
            provider_request_id = getattr(resp, "id", None)

            logger.info(
                "anthropic.invoke.success",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "provider_request_id": provider_request_id,
                },
            )
            return self._result(request, content, usage, provider_request_id, latency_ms)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            inf_error = _translate_anthropic_error(exc)
            logger.warning(
                "anthropic.invoke.error",
                extra={
                    "provider": self.name,
                    "model": self.model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "error_kind": inf_error.kind.value,
                    "error_type": type(exc).__name__,
                },
            )
            raise inf_error from exc

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        """Default streaming implementation: delegate to invoke() and yield one result."""
        yield self.invoke(request)

    def current_limits(self) -> ProviderLimits:
        return ProviderLimits(rate_limits_known=self.configured)


# ---------------------------------------------------------------------------
# Ollama adapter
# ---------------------------------------------------------------------------


class OllamaProvider(_BaseRealProvider):
    """
    Production Ollama provider adapter.

    Wraps ``local_models.ollama_client.OllamaClient`` into the InferenceProvider
    protocol. Always considered configured because the local daemon is the only
    runtime dependency; reachability is reported by ``health()``.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout_seconds: float | None = 120.0,
        route_tier: RouteTier = RouteTier.LOCAL_PRIVATE,
        capabilities: Iterable[str] = (
            "classification",
            "extraction",
            "summarization",
            "drafting",
            "coding",
            "reasoning",
        ),
        context_window: int = 128000,
        quality: QualityFloor = QualityFloor.STANDARD,
        source_url: str | None = "https://github.com/ollama/ollama/blob/main/docs/api.md",
    ) -> None:
        super().__init__(
            name="ollama",
            model=model,
            route_tier=route_tier,
            capabilities=capabilities,
            cloud=False,
            paid=False,
            api_key="local",  # always configured for local-first routing
            api_base=base_url,
            timeout_seconds=timeout_seconds,
            pricing_known=True,
            estimated_cost_usd=0.0,
            context_window=context_window,
            quality=quality,
            source_url=source_url,
            account_entitlement_known=True,
            free_allowance_known=True,
        )
        self._ollama_client_cls: Any = None

    def _create_client(self, **kwargs: Any) -> Any:
        from local_models.ollama_client import OllamaClient

        self._ollama_client_cls = OllamaClient
        base_url = kwargs.get("base_url", "http://localhost:11434")
        timeout = kwargs.get("timeout", 120)
        return OllamaClient(base_url=base_url, timeout=int(timeout))

    def health(self) -> ProviderHealth:
        try:
            client = self._ensure_client()
            available = client.is_available()
            return ProviderHealth(
                reachable=available,
                healthy=available,
                reason=None if available else "ollama_unreachable",
            )
        except Exception as exc:
            return ProviderHealth(reachable=False, healthy=False, reason=str(exc))

    def current_limits(self) -> ProviderLimits:
        return ProviderLimits(rate_limits_known=True)

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        client = self._ensure_client()
        started = time.perf_counter()
        try:
            model = request.metadata.get("model_override", self.model)
            # Backward-compatible path: legacy ModelRouter used OllamaClient.generate,
            # and existing tests mock that method. Build a prompt from messages.
            messages = list(request.messages)
            system_text: str | None = None
            prompt_parts = []
            for msg in messages:
                role = msg.get("role")
                if role == "system":
                    system_text = msg.get("content", "")
                elif role == "user":
                    prompt_parts.append(msg.get("content", ""))
                else:
                    prompt_parts.append(f"[{role}]: {msg.get('content', '')}")
            prompt = "\n\n".join(prompt_parts) or " "

            if not client.model_exists(model):
                model = getattr(client, "default_model", self.model)

            resp = client.generate(
                prompt=prompt,
                model=model,
                system=system_text,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                stream=False,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)

            content = resp.get("response", "") or ""
            usage = {
                "input_tokens": resp.get("prompt_eval_count", 0) or 0,
                "output_tokens": resp.get("eval_count", 0) or 0,
                "total_tokens": (resp.get("prompt_eval_count", 0) or 0)
                + (resp.get("eval_count", 0) or 0),
                "cached_tokens": 0,
            }

            logger.info(
                "ollama.invoke.success",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                },
            )
            return self._result(request, content, usage, None, latency_ms)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            inf_error = _translate_ollama_error(exc)
            logger.warning(
                "ollama.invoke.error",
                extra={
                    "provider": self.name,
                    "model": self.model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "error_kind": inf_error.kind.value,
                    "error_type": type(exc).__name__,
                },
            )
            raise inf_error from exc

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        """Default streaming implementation: delegate to invoke() and yield one result."""
        yield self.invoke(request)


# ---------------------------------------------------------------------------
# DeepSeek adapter
# ---------------------------------------------------------------------------


class DeepSeekProvider(_BaseRealProvider):
    """
    Production DeepSeek provider adapter.

    Wraps ``local_models.deepseek_client.DeepSeekClient`` into the
    InferenceProvider protocol. Requires an API key to invoke.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "deepseek-chat",
        timeout_seconds: float | None = 120.0,
        route_tier: RouteTier = RouteTier.CLOUD_LOW_COST_FAST,
        capabilities: Iterable[str] = (
            "classification",
            "extraction",
            "summarization",
            "drafting",
            "coding",
            "reasoning",
        ),
        context_window: int = 64000,
        quality: QualityFloor = QualityFloor.STANDARD,
        pricing_known: bool = True,
        source_url: str | None = "https://platform.deepseek.com/api-docs",
    ) -> None:
        super().__init__(
            name="deepseek",
            model=model,
            route_tier=route_tier,
            capabilities=capabilities,
            cloud=True,
            paid=True,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            pricing_known=pricing_known,
            estimated_cost_usd=0.0,  # conservative pre-call estimate; actual cost reported post-call
            context_window=context_window,
            quality=quality,
            source_url=source_url,
            account_entitlement_known=bool(api_key),
            free_allowance_known=False,
        )
        self._deepseek_client_cls: Any = None

    def _create_client(self, **kwargs: Any) -> Any:
        from local_models.deepseek_client import DeepSeekClient

        self._deepseek_client_cls = DeepSeekClient
        api_key = kwargs.get("api_key")
        timeout = kwargs.get("timeout", 120)
        return DeepSeekClient(api_key=api_key, timeout=int(timeout))

    def _is_reasoning_task(self, request: InferenceRequest) -> bool:
        override = request.metadata.get("model_override")
        if override == "deepseek-reasoner":
            return True
        return request.task_type in {"legal_research", "case_analysis", "argument_construction"}

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        client = self._ensure_client()
        started = time.perf_counter()
        try:
            model = request.metadata.get("model_override", self.model)
            if self._is_reasoning_task(request) and model in {"deepseek-chat", "deepseek-r1"}:
                model = "deepseek-reasoner"

            messages = list(request.messages)
            system_text: str | None = None
            chat_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_text = msg.get("content", "")
                else:
                    chat_messages.append(msg)
            if not chat_messages:
                chat_messages.append({"role": "user", "content": ""})

            resp = client.chat(
                messages=chat_messages,
                model=model,
                system=system_text,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                task_type=request.task_type,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)

            choice = resp.get("choices", [{}])[0]
            message = choice.get("message", {}) or {}
            content = message.get("content", "") or ""
            usage_obj = resp.get("usage", {}) or {}
            usage = {
                "input_tokens": usage_obj.get("prompt_tokens", 0) or 0,
                "output_tokens": usage_obj.get("completion_tokens", 0) or 0,
                "total_tokens": usage_obj.get("total_tokens", 0) or 0,
                "cached_tokens": 0,
            }
            actual_cost = resp.get("cost_usd", 0.0)
            reasoning_content = message.get("reasoning_content", "") or ""
            if reasoning_content:
                # Preserve thinking without changing the public content string shape.
                # Callers that need chain-of-thought can inspect result.metadata.
                request.metadata.setdefault("reasoning_content", reasoning_content)

            logger.info(
                "deepseek.invoke.success",
                extra={
                    "provider": self.name,
                    "model": model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "cost_usd": actual_cost,
                },
            )
            result = self._result(request, content, usage, None, latency_ms)
            return replace(result, actual_cost_usd=actual_cost)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            inf_error = _translate_deepseek_error(exc)
            logger.warning(
                "deepseek.invoke.error",
                extra={
                    "provider": self.name,
                    "model": self.model,
                    "request_id": request.request_id,
                    "latency_ms": latency_ms,
                    "error_kind": inf_error.kind.value,
                    "error_type": type(exc).__name__,
                },
            )
            raise inf_error from exc

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        """Default streaming implementation: delegate to invoke() and yield one result."""
        yield self.invoke(request)

    def current_limits(self) -> ProviderLimits:
        return ProviderLimits(rate_limits_known=self.configured)


# ---------------------------------------------------------------------------
# DeepSeek error translation
# ---------------------------------------------------------------------------


def _translate_deepseek_error(exc: Exception) -> InferenceError:
    """Translate a DeepSeek client exception into an InferenceError."""
    exc_name = type(exc).__name__
    if exc_name == "DeepSeekAuthError":
        return InferenceError(str(exc), ProviderErrorKind.AUTHENTICATION)
    if exc_name == "DeepSeekRateLimitError":
        return InferenceError(str(exc), ProviderErrorKind.TRANSIENT)
    if exc_name == "DeepSeekAPIError":
        text = str(exc).lower()
        if "rate limit" in text or "429" in text:
            return InferenceError(str(exc), ProviderErrorKind.TRANSIENT)
        if "timeout" in text or "connection" in text:
            return InferenceError(str(exc), ProviderErrorKind.TRANSIENT)
        if "invalid" in text or "bad request" in text:
            return InferenceError(str(exc), ProviderErrorKind.INVALID_REQUEST)
        return InferenceError(str(exc), ProviderErrorKind.UNKNOWN)
    if exc_name == "ConnectionError":
        return InferenceError(str(exc), ProviderErrorKind.TRANSIENT)
    return InferenceError(str(exc), ProviderErrorKind.UNKNOWN)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rough_tokens(request: InferenceRequest) -> int:
    text = " ".join(str(message.get("content", "")) for message in request.messages)
    return max(1, len(text.split()))
