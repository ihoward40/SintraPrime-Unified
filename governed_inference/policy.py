from __future__ import annotations

from dataclasses import replace

from governed_inference.contracts import (
    DataClassification,
    InferencePolicy,
    InferenceRequest,
    PaidAuthorization,
    PerRequestPolicy,
    ProviderCapabilities,
    QualityFloor,
    RouteTier,
)

SENSITIVE_CLASSIFICATIONS = {
    DataClassification.CONFIDENTIAL,
    DataClassification.RESTRICTED_LEGAL,
    DataClassification.RESTRICTED_FINANCIAL,
    DataClassification.RESTRICTED_IDENTITY,
    DataClassification.UNKNOWN,
}
QUALITY_ORDER = {
    QualityFloor.BASIC: 1,
    QualityFloor.STANDARD: 2,
    QualityFloor.HIGH: 3,
    QualityFloor.PREMIUM: 4,
}


def merge_policy_strictest(base: InferencePolicy, override: InferencePolicy) -> InferencePolicy:
    return replace(
        base,
        paid_models_allowed=base.paid_models_allowed and override.paid_models_allowed,
        paid_escalation_requires_explicit_approval=(
            base.paid_escalation_requires_explicit_approval
            or override.paid_escalation_requires_explicit_approval
        ),
        cloud_sensitive_data_allowed=(
            base.cloud_sensitive_data_allowed and override.cloud_sensitive_data_allowed
        ),
        fail_closed_on_unknown_cost=(
            base.fail_closed_on_unknown_cost or override.fail_closed_on_unknown_cost
        ),
        fail_closed_on_unknown_data_policy=(
            base.fail_closed_on_unknown_data_policy or override.fail_closed_on_unknown_data_policy
        ),
        daily_budget_usd=min(base.daily_budget_usd, override.daily_budget_usd),
        monthly_budget_usd=min(base.monthly_budget_usd, override.monthly_budget_usd),
        min_success_rate=max(base.min_success_rate, override.min_success_rate),
        per_request=PerRequestPolicy(
            max_input_tokens=min(
                base.per_request.max_input_tokens, override.per_request.max_input_tokens
            ),
            max_output_tokens=min(
                base.per_request.max_output_tokens, override.per_request.max_output_tokens
            ),
            max_estimated_cost_usd=min(
                base.per_request.max_estimated_cost_usd,
                override.per_request.max_estimated_cost_usd,
            ),
            timeout_seconds=min(
                base.per_request.timeout_seconds, override.per_request.timeout_seconds
            ),
            max_attempts=min(base.per_request.max_attempts, override.per_request.max_attempts),
        ),
    )


def route_denial_reason(
    *,
    request: InferenceRequest,
    classification: DataClassification,
    policy: InferencePolicy,
    capabilities: ProviderCapabilities,
    estimated_cost_usd: float | None,
    authorization: PaidAuthorization | None,
) -> str | None:
    if request.capability not in capabilities.capabilities:
        return "unsupported_capability"
    if QUALITY_ORDER[capabilities.quality] < QUALITY_ORDER[request.quality_floor]:
        return "quality_floor_not_met"
    if request.max_input_tokens > policy.per_request.max_input_tokens:
        return "input_token_cap_exceeded"
    if request.max_output_tokens > policy.per_request.max_output_tokens:
        return "output_token_cap_exceeded"
    if capabilities.context_window < request.max_input_tokens + request.max_output_tokens:
        return "context_window_too_small"
    if capabilities.cloud and classification in SENSITIVE_CLASSIFICATIONS:
        if not policy.cloud_sensitive_data_allowed:
            return "data_classification_cloud_blocked"
    if capabilities.paid or capabilities.route_tier == RouteTier.PREMIUM_ESCALATION:
        if not policy.paid_models_allowed:
            return "global_paid_models_disabled"
        if policy.paid_escalation_requires_explicit_approval:
            if not request.paid_use_authorized or authorization is None:
                return "paid_approval_missing"
            if not authorization.is_valid_for(request, estimated_cost_usd):
                return "paid_approval_invalid_or_stale"
    if estimated_cost_usd is None and capabilities.cloud and policy.fail_closed_on_unknown_cost:
        return "unknown_cloud_cost"
    if estimated_cost_usd is not None:
        if estimated_cost_usd > policy.per_request.max_estimated_cost_usd:
            return "per_request_budget_exceeded"
        if policy.daily_budget_usd <= 0 and estimated_cost_usd > 0:
            return "daily_budget_exhausted"
    return None
