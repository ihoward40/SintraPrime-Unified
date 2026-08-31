from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from governed_inference.contracts import (
    AttemptRecord,
    CacheStatus,
    DataClassification,
    InferenceReceipt,
    InferenceRequest,
    InferenceResult,
    ProviderReliability,
    RejectedRoute,
    RouteCandidate,
    receipt_hash,
    stable_hash,
)


class InferenceLedger:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.receipts: dict[str, InferenceReceipt] = {}
        self.reliability: dict[str, ProviderReliability] = {}
        self.daily_total_usd = 0.0
        self.monthly_total_usd = 0.0

    def emit(self, event: str, **payload: object) -> None:
        self.events.append({"event": event, "timestamp": datetime.now(UTC), **payload})

    def provider_reliability(self, provider: str) -> ProviderReliability:
        return self.reliability.get(provider, ProviderReliability(provider=provider))

    def record_provider_success(self, provider: str) -> None:
        current = self.provider_reliability(provider)
        self.reliability[provider] = replace(
            current,
            successes=current.successes + 1,
            recent_failures=0,
        )

    def record_provider_failure(self, provider: str) -> None:
        current = self.provider_reliability(provider)
        self.reliability[provider] = replace(
            current,
            failures=current.failures + 1,
            recent_failures=current.recent_failures + 1,
        )

    def create_receipt(
        self,
        *,
        request: InferenceRequest,
        classification: DataClassification,
        policy_version: str,
        eligible_routes: list[RouteCandidate],
        rejected_routes: list[RejectedRoute],
        selected: RouteCandidate | None,
        attempts: list[AttemptRecord],
        fallback_history: list[RouteCandidate],
        cache_status: CacheStatus,
    ) -> InferenceReceipt:
        receipt_id = receipt_hash(request.request_id, policy_version, len(self.receipts))
        receipt = InferenceReceipt(
            receipt_id=receipt_id,
            request_id=request.request_id,
            request_hash=stable_hash(request),
            prompt_version_hash=stable_hash(request.metadata.get("prompt_version", "default")),
            classification=classification,
            policy_version=policy_version,
            eligible_routes=eligible_routes,
            rejected_routes=rejected_routes,
            selected_provider=selected.provider if selected else None,
            selected_model=selected.model if selected else None,
            retry_history=attempts,
            fallback_history=fallback_history,
            token_usage={},
            estimated_cost_usd=selected.estimated_cost_usd if selected else None,
            actual_cost_usd=None,
            cache_status=cache_status,
            created_at=datetime.now(UTC),
        )
        self.receipts[receipt_id] = receipt
        return receipt

    def finalize_receipt(self, receipt_id: str, result: InferenceResult) -> InferenceReceipt:
        receipt = self.receipts[receipt_id]
        finalized = replace(
            receipt,
            token_usage=dict(result.usage),
            estimated_cost_usd=result.estimated_cost_usd,
            actual_cost_usd=result.actual_cost_usd,
            cache_status=result.cache_status,
            final_output_hash=stable_hash(result.content),
        )
        self.receipts[receipt_id] = finalized
        cost = (
            result.actual_cost_usd
            if result.actual_cost_usd is not None
            else result.estimated_cost_usd
        )
        if cost is not None:
            self.daily_total_usd += cost
            self.monthly_total_usd += cost
        return finalized
