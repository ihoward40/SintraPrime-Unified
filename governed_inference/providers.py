from __future__ import annotations

import time
from collections.abc import Iterable, Iterator
from dataclasses import replace

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
    ProviderMetadata,
    QualityFloor,
    RouteTier,
    receipt_hash,
)


class BaseConfiguredProvider:
    def __init__(
        self,
        *,
        name: str,
        model: str,
        route_tier: RouteTier,
        capabilities: Iterable[str],
        cloud: bool,
        paid: bool,
        configured: bool = False,
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
        self.configured = configured
        self.pricing_known = pricing_known
        self.estimated_cost_usd = estimated_cost_usd
        self.context_window = context_window
        self.quality = quality
        self.source_url = source_url
        self.account_entitlement_known = account_entitlement_known
        self.free_allowance_known = free_allowance_known

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
        return ProviderHealth(
            reachable=self.configured,
            healthy=self.configured,
            reason=None if self.configured else "not_configured",
        )

    def estimate_cost(self, request: InferenceRequest) -> CostEstimate:
        return CostEstimate(
            estimated_cost_usd=self.estimated_cost_usd,
            input_tokens=_rough_tokens(request),
            output_tokens=request.max_output_tokens,
            pricing_known=self.pricing_known,
        )

    def invoke(self, _request: InferenceRequest) -> InferenceResult:
        raise InferenceError(f"{self.name} adapter is not configured for network invocation")

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        """Default streaming implementation: delegate to invoke() and yield one result."""
        yield self.invoke(request)

    def current_limits(self) -> ProviderLimits:
        return ProviderLimits(rate_limits_known=self.configured)

    def metadata(self) -> ProviderMetadata:
        evidence = receipt_hash(
            self.name,
            self.model,
            self.configured,
            self.pricing_known,
            self.account_entitlement_known,
        )
        eligible = self.configured and self.pricing_known and self.health().healthy
        return ProviderMetadata(
            configured=self.configured,
            authenticated=self.configured,
            reachable=self.configured,
            model_available=self.configured,
            account_entitlement_known=self.account_entitlement_known,
            rate_limits_known=self.configured,
            pricing_known=self.pricing_known,
            free_allowance_known=self.free_allowance_known,
            healthy=self.configured,
            eligible=eligible,
            source_url=self.source_url,
            verification_method="configuration",
            evidence_hash=evidence,
        )


class MockProvider(BaseConfiguredProvider):
    def __init__(
        self,
        *,
        name: str = "mock-local",
        model: str = "deterministic-local",
        route_tier: RouteTier = RouteTier.LOCAL_PRIVATE,
        capabilities: Iterable[str] = (
            "classification",
            "extraction",
            "summarization",
            "drafting",
            "coding",
            "reasoning",
        ),
        fail_times: int = 0,
        stream_fails: bool = False,
        error_kind: ProviderErrorKind = ProviderErrorKind.TRANSIENT,
        estimated_cost_usd: float | None = 0.0,
        cloud: bool = False,
        paid: bool = False,
        quality: QualityFloor = QualityFloor.STANDARD,
    ) -> None:
        super().__init__(
            name=name,
            model=model,
            route_tier=route_tier,
            capabilities=capabilities,
            cloud=cloud,
            paid=paid,
            configured=True,
            pricing_known=estimated_cost_usd is not None,
            estimated_cost_usd=estimated_cost_usd,
            context_window=64000,
            quality=quality,
            account_entitlement_known=True,
            free_allowance_known=estimated_cost_usd == 0,
        )
        self.fail_times = fail_times
        self.stream_fails = stream_fails
        self.error_kind = error_kind
        self.invoke_count = 0

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        self.invoke_count += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise InferenceError("mock provider failure", self.error_kind)
        started = time.perf_counter()
        content = {
            "provider": self.name,
            "task_type": request.task_type,
            "capability": request.capability,
            "message_count": len(request.messages),
        }
        input_tokens = _rough_tokens(request)
        output_tokens = len(str(content).split())
        return InferenceResult(
            request_id=request.request_id,
            provider=self.name,
            model=self.model,
            route_tier=self.route_tier,
            content=content,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_tokens": 0,
                "total_tokens": input_tokens + output_tokens,
            },
            estimated_cost_usd=self.estimated_cost_usd,
            actual_cost_usd=self.estimated_cost_usd,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cache_status=CacheStatus.MISS,
            attempts=self.invoke_count,
            finish_reason="stop",
            policy_receipt_id="pending",
            provider_request_id=f"mock_{self.invoke_count}",
        )

    def invoke_stream(self, request: InferenceRequest) -> Iterator[InferenceResult]:
        if self.stream_fails:
            raise InferenceError("partial stream failed", ProviderErrorKind.TRANSIENT)
        partial = self.invoke(request)
        yield replace(partial, content=partial.content, is_partial=True)
        yield replace(partial, content=partial.content, is_partial=False)


class DeterministicReplayProvider(MockProvider):
    def __init__(self, results: dict[str, InferenceResult]) -> None:
        super().__init__(name="deterministic-replay", model="recorded-response")
        self.results = results

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        if request.request_id not in self.results:
            raise InferenceError("replay fixture missing", ProviderErrorKind.INVALID_REQUEST)
        return replace(self.results[request.request_id], cache_status=CacheStatus.MISS)


class LMStudioProvider(BaseConfiguredProvider):
    def __init__(self, model: str = "google/gemma-3-4b", configured: bool = False) -> None:
        super().__init__(
            name="lmstudio",
            model=model,
            route_tier=RouteTier.LOCAL_PRIVATE,
            capabilities=("classification", "extraction", "summarization", "drafting", "coding"),
            cloud=False,
            paid=False,
            configured=configured,
            pricing_known=True,
            estimated_cost_usd=0.0,
            context_window=64000,
            account_entitlement_known=True,
            free_allowance_known=True,
        )

    def invoke(self, request: InferenceRequest) -> InferenceResult:
        return MockProvider(name=self.name, model=self.model).invoke(request)


class OmniRouteProvider(BaseConfiguredProvider):
    def __init__(
        self,
        model: str = "configured-free-route",
        configured: bool = False,
        estimated_cost_usd: float | None = None,
    ) -> None:
        super().__init__(
            name="omniroute",
            model=model,
            route_tier=RouteTier.CLOUD_LOW_COST_FAST,
            capabilities=("classification", "extraction", "summarization", "drafting", "coding"),
            cloud=True,
            paid=False,
            configured=configured,
            pricing_known=estimated_cost_usd is not None,
            estimated_cost_usd=estimated_cost_usd,
            context_window=128000,
            quality=QualityFloor.STANDARD,
            source_url="https://www.npmjs.com/package/omniroute",
            account_entitlement_known=configured and estimated_cost_usd is not None,
            free_allowance_known=estimated_cost_usd == 0,
        )


class OpenRouterProvider(BaseConfiguredProvider):
    def __init__(
        self,
        model: str = "configured-openrouter-model",
        configured: bool = False,
        estimated_cost_usd: float | None = None,
    ) -> None:
        super().__init__(
            name="openrouter",
            model=model,
            route_tier=RouteTier.CLOUD_LOW_COST_FAST,
            capabilities=("classification", "extraction", "summarization", "drafting", "coding"),
            cloud=True,
            paid=False,
            configured=configured,
            pricing_known=estimated_cost_usd is not None,
            estimated_cost_usd=estimated_cost_usd,
            context_window=128000,
            quality=QualityFloor.STANDARD,
            source_url="https://openrouter.ai/docs/guides/coding-agents/claude-code-integration",
            account_entitlement_known=configured and estimated_cost_usd is not None,
            free_allowance_known=estimated_cost_usd == 0,
        )


class GroqProvider(BaseConfiguredProvider):
    def __init__(self, model: str = "configured-groq-model", configured: bool = False) -> None:
        super().__init__(
            name="groq",
            model=model,
            route_tier=RouteTier.CLOUD_LOW_COST_FAST,
            capabilities=("classification", "extraction", "summarization", "drafting"),
            cloud=True,
            paid=False,
            configured=configured,
        )


class GeminiProvider(BaseConfiguredProvider):
    def __init__(self, model: str = "configured-gemini-model", configured: bool = False) -> None:
        super().__init__(
            name="gemini",
            model=model,
            route_tier=RouteTier.CLOUD_PROTOTYPE,
            capabilities=("summarization", "drafting", "coding", "extraction"),
            cloud=True,
            paid=False,
            configured=configured,
        )


class MistralProvider(BaseConfiguredProvider):
    def __init__(self, model: str = "configured-mistral-coder", configured: bool = False) -> None:
        super().__init__(
            name="mistral",
            model=model,
            route_tier=RouteTier.CLOUD_CODING,
            capabilities=("coding", "summarization", "drafting"),
            cloud=True,
            paid=False,
            configured=configured,
        )


class PremiumApprovedProvider(BaseConfiguredProvider):
    def __init__(self, model: str = "approved-premium-model", configured: bool = False) -> None:
        super().__init__(
            name="premium-approved",
            model=model,
            route_tier=RouteTier.PREMIUM_ESCALATION,
            capabilities=("coding", "reasoning", "summarization", "drafting"),
            cloud=True,
            paid=True,
            configured=configured,
            quality=QualityFloor.PREMIUM,
        )


def _rough_tokens(request: InferenceRequest) -> int:
    text = " ".join(str(message.get("content", "")) for message in request.messages)
    return max(1, len(text.split()))
