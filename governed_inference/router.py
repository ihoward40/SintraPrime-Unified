from __future__ import annotations

import time
from dataclasses import replace

from governed_inference.cache import ExactInferenceCache
from governed_inference.classification import classify_request_data, redact_for_policy
from governed_inference.contracts import (
    AttemptRecord,
    CacheStatus,
    DataClassification,
    InferenceError,
    InferencePolicy,
    InferenceProvider,
    InferenceRequest,
    InferenceResult,
    PaidAuthorization,
    ProviderErrorKind,
    RejectedRoute,
    RouteCandidate,
    RouteTier,
)
from governed_inference.escalation import EscalationQueue
from governed_inference.ledger import InferenceLedger
from governed_inference.policy import route_denial_reason

TRANSIENT_ERRORS = {ProviderErrorKind.TRANSIENT}


class GovernedInferenceRouter:
    def __init__(
        self,
        providers: list[InferenceProvider],
        *,
        policy: InferencePolicy | None = None,
        ledger: InferenceLedger | None = None,
        cache: ExactInferenceCache | None = None,
        escalation_queue: EscalationQueue | None = None,
    ) -> None:
        self.providers = providers
        self.policy = InferencePolicy.from_environment(policy)
        self.ledger = ledger or InferenceLedger()
        self.cache = cache or ExactInferenceCache()
        self.escalation_queue = escalation_queue or EscalationQueue()

    def invoke(
        self,
        request: InferenceRequest,
        *,
        authorization: PaidAuthorization | None = None,
        stream: bool = False,
    ) -> InferenceResult:
        self._validate(request)
        classification = classify_request_data(request)
        request = replace(
            request,
            data_classification=classification,
            max_input_tokens=min(request.max_input_tokens, self.policy.per_request.max_input_tokens),
            max_output_tokens=min(request.max_output_tokens, self.policy.per_request.max_output_tokens),
        )
        self.ledger.emit("inference.requested", request_id=request.request_id)
        redaction_receipt = redact_for_policy(request)
        self.ledger.emit(
            "inference.classified",
            request_id=request.request_id,
            classification=classification.value,
        )
        self.ledger.emit(
            "inference.redacted",
            request_id=request.request_id,
            redaction_receipt_hash=redaction_receipt.redaction_receipt_hash,
        )

        if self.policy.cache.enabled and request.cache_policy != "bypass":
            cached = self.cache.get(request)
            if cached is not None:
                self.ledger.emit("inference.cache_hit", request_id=request.request_id)
                return cached

        eligible, rejected = self._build_candidates(request, classification, authorization)
        self.ledger.emit(
            "inference.route_candidates_built",
            request_id=request.request_id,
            eligible=len(eligible),
            rejected=len(rejected),
        )
        if not eligible:
            self.ledger.emit("inference.denied", request_id=request.request_id)
            self.ledger.create_receipt(
                request=request,
                classification=classification,
                policy_version=self.policy.version,
                eligible_routes=[],
                rejected_routes=rejected,
                selected=None,
                attempts=[],
                fallback_history=[],
                cache_status=CacheStatus.BYPASS,
            )
            self.escalation_queue.enqueue(
                request=request,
                classification=classification,
                reason="no_eligible_route",
                denied_routes=rejected,
                estimated_cost_usd=None,
            )
            raise InferenceError("no eligible inference route", ProviderErrorKind.POLICY_DENIED)

        attempts: list[AttemptRecord] = []
        fallback_history: list[RouteCandidate] = []
        last_error: InferenceError | None = None
        for candidate in eligible:
            receipt = self.ledger.create_receipt(
                request=request,
                classification=classification,
                policy_version=self.policy.version,
                eligible_routes=eligible,
                rejected_routes=rejected,
                selected=candidate,
                attempts=attempts,
                fallback_history=fallback_history,
                cache_status=CacheStatus.MISS,
            )
            self.ledger.emit(
                "inference.route_selected",
                request_id=request.request_id,
                provider=candidate.provider,
                model=candidate.model,
            )
            provider = self._provider_by_name(candidate.provider)
            for attempt in range(1, self.policy.per_request.max_attempts + 1):
                attempts.append(
                    AttemptRecord(
                        provider=candidate.provider,
                        model=candidate.model,
                        route_tier=candidate.route_tier,
                        attempt=attempt,
                        event="started",
                    )
                )
                self.ledger.emit(
                    "inference.attempt_started",
                    request_id=request.request_id,
                    provider=candidate.provider,
                    attempt=attempt,
                )
                try:
                    result = self._invoke_provider(provider, request, stream=stream and attempt == 1)
                    result = replace(result, attempts=attempt, policy_receipt_id=receipt.receipt_id)
                    self._enforce_post_caps(result, request)
                    self.cache.set(request, result)
                    self.ledger.record_provider_success(candidate.provider)
                    self.ledger.finalize_receipt(receipt.receipt_id, result)
                    self.ledger.emit("inference.completed", request_id=request.request_id, provider=result.provider)
                    self.ledger.emit("inference.cost_recorded", request_id=request.request_id)
                    return result
                except InferenceError as exc:
                    last_error = exc
                    self.ledger.record_provider_failure(candidate.provider)
                    attempts.append(
                        AttemptRecord(
                            provider=candidate.provider,
                            model=candidate.model,
                            route_tier=candidate.route_tier,
                            attempt=attempt,
                            event="failed",
                            error_kind=exc.kind,
                            message=str(exc),
                        )
                    )
                    self.ledger.emit(
                        "inference.attempt_failed",
                        request_id=request.request_id,
                        provider=candidate.provider,
                        error_kind=exc.kind.value,
                    )
                    if exc.kind not in TRANSIENT_ERRORS:
                        break
                    time.sleep(min(0.01 * attempt, 0.05))
            fallback_history.append(candidate)
            self.ledger.emit(
                "inference.fallback_selected",
                request_id=request.request_id,
                failed_provider=candidate.provider,
            )
        self.escalation_queue.enqueue(
            request=request,
            classification=classification,
            reason="eligible_routes_failed",
            denied_routes=rejected,
            estimated_cost_usd=eligible[-1].estimated_cost_usd,
        )
        raise last_error or InferenceError("all inference routes failed", ProviderErrorKind.UNKNOWN)

    def _build_candidates(
        self,
        request: InferenceRequest,
        classification: DataClassification,
        authorization: PaidAuthorization | None,
    ) -> tuple[list[RouteCandidate], list[RejectedRoute]]:
        eligible: list[RouteCandidate] = []
        rejected: list[RejectedRoute] = []
        for provider in self.providers:
            caps = provider.capabilities()
            estimate = provider.estimate_cost(request)
            health = provider.health()
            limits = provider.current_limits()
            reliability = self.ledger.provider_reliability(caps.provider)
            reason = route_denial_reason(
                request=request,
                classification=classification,
                policy=self.policy,
                capabilities=caps,
                estimated_cost_usd=estimate.estimated_cost_usd,
                authorization=authorization,
            )
            if reason is None and reliability.total >= 3:
                if reliability.success_rate < self.policy.min_success_rate:
                    reason = "provider_reliability_floor_not_met"
            if reason is None and (not health.healthy or health.circuit_open):
                reason = "provider_unhealthy_or_circuit_open"
            if reason is None and limits.requests_remaining == 0:
                reason = "rate_limit_blocked"
            if reason is not None:
                rejected.append(
                    RejectedRoute(
                        provider=caps.provider,
                        model=caps.model,
                        route_tier=caps.route_tier,
                        reason=reason,
                    )
                )
                continue
            eligible.append(
                RouteCandidate(
                    provider=caps.provider,
                    model=caps.model,
                    route_tier=caps.route_tier,
                    score=self._score(
                        caps.route_tier,
                        health.healthy,
                        estimate.estimated_cost_usd,
                        reliability.success_rate,
                        reliability.recent_failures,
                    ),
                    estimated_cost_usd=estimate.estimated_cost_usd,
                    success_rate=reliability.success_rate,
                )
            )
        eligible.sort(key=lambda candidate: candidate.score, reverse=True)
        return eligible, rejected

    def _invoke_provider(
        self,
        provider: InferenceProvider,
        request: InferenceRequest,
        *,
        stream: bool,
    ) -> InferenceResult:
        if not stream:
            return provider.invoke(request)
        try:
            return provider.invoke_stream(request)
        except InferenceError as exc:
            if exc.kind != ProviderErrorKind.TRANSIENT:
                raise
            self.ledger.emit(
                "inference.attempt_failed",
                request_id=request.request_id,
                provider=provider.capabilities().provider,
                error_kind=exc.kind.value,
                stream_partial_preserved=True,
            )
            return provider.invoke(request)

    def _provider_by_name(self, name: str) -> InferenceProvider:
        for provider in self.providers:
            if provider.capabilities().provider == name:
                return provider
        raise InferenceError(f"provider disappeared during route selection: {name}")

    def _score(
        self,
        route_tier: RouteTier,
        healthy: bool,
        estimated_cost_usd: float | None,
        success_rate: float,
        recent_failures: int,
    ) -> float:
        score = 100.0 if healthy else 0.0
        if route_tier == RouteTier.LOCAL_PRIVATE:
            score += 50.0
        if estimated_cost_usd == 0:
            score += 10.0
        if estimated_cost_usd is not None:
            score -= estimated_cost_usd * 100.0
        score += success_rate * 25.0
        score -= recent_failures * 15.0
        return score

    def _validate(self, request: InferenceRequest) -> None:
        if not request.request_id:
            raise InferenceError("request_id is required", ProviderErrorKind.INVALID_REQUEST)
        if not request.messages:
            raise InferenceError("messages are required", ProviderErrorKind.INVALID_REQUEST)
        if request.max_input_tokens <= 0 or request.max_output_tokens <= 0:
            raise InferenceError("token limits must be positive", ProviderErrorKind.INVALID_REQUEST)

    def _enforce_post_caps(self, result: InferenceResult, request: InferenceRequest) -> None:
        if result.usage.get("input_tokens", 0) > request.max_input_tokens:
            raise InferenceError("provider exceeded input token cap", ProviderErrorKind.CONTEXT_OVERFLOW)
        if result.usage.get("output_tokens", 0) > request.max_output_tokens:
            raise InferenceError("provider exceeded output token cap", ProviderErrorKind.CONTEXT_OVERFLOW)
