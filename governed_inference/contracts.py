from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any, Protocol


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED_LEGAL = "RESTRICTED_LEGAL"
    RESTRICTED_FINANCIAL = "RESTRICTED_FINANCIAL"
    RESTRICTED_IDENTITY = "RESTRICTED_IDENTITY"
    UNKNOWN = "UNKNOWN"


class RouteTier(StrEnum):
    LOCAL_PRIVATE = "LOCAL_PRIVATE"
    CLOUD_LOW_COST_FAST = "CLOUD_LOW_COST_FAST"
    CLOUD_PROTOTYPE = "CLOUD_PROTOTYPE"
    CLOUD_CODING = "CLOUD_CODING"
    PREMIUM_ESCALATION = "PREMIUM_ESCALATION"
    FAIL_CLOSED = "FAIL_CLOSED"


class QualityFloor(StrEnum):
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    PREMIUM = "premium"


class CacheStatus(StrEnum):
    MISS = "miss"
    HIT = "hit"
    BYPASS = "bypass"


class ProviderErrorKind(StrEnum):
    TRANSIENT = "transient"
    TIMEOUT_FIRST_BYTE = "timeout_first_byte"
    TIMEOUT_PROGRESS = "timeout_progress"
    RATE_LIMITED = "rate_limited"
    PROVIDER_5XX = "provider_5xx"
    MALFORMED_RESPONSE = "malformed_response"
    SCHEMA_INVALID = "schema_invalid"
    AUTH_FAILURE = "auth_failure"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION = "authentication"
    PAYMENT_REQUIRED = "payment_required"
    POLICY_DENIED = "policy_denied"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    CONTEXT_OVERFLOW = "context_overflow"
    QUALITY_FLOOR = "quality_floor"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class InferenceError(Exception):
    def __init__(self, message: str, kind: ProviderErrorKind = ProviderErrorKind.UNKNOWN):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class PerRequestPolicy:
    max_input_tokens: int = 12000
    max_output_tokens: int = 2000
    max_estimated_cost_usd: float = 0.0
    timeout_seconds: int = 60
    max_attempts: int = 3
    max_attempts_per_provider: int = 1


@dataclass(frozen=True)
class CachePolicy:
    enabled: bool = True
    semantic_cache_enabled: bool = False
    sensitive_content_cache: str = "local_encrypted_only"


@dataclass(frozen=True)
class InferencePolicy:
    mode: str = "local_first"
    paid_models_allowed: bool = False
    paid_escalation_requires_explicit_approval: bool = True
    cloud_sensitive_data_allowed: bool = False
    fail_closed_on_unknown_cost: bool = True
    fail_closed_on_unknown_data_policy: bool = True
    daily_budget_usd: float = 0.0
    monthly_budget_usd: float = 0.0
    per_request: PerRequestPolicy = field(default_factory=PerRequestPolicy)
    cache: CachePolicy = field(default_factory=CachePolicy)
    provider_metadata_ttl_days: int = 14
    pricing_metadata_ttl_days: int = 7
    promotion_metadata_ttl_days: int = 3
    min_success_rate: float = 0.50
    version: str = "2026-07-21.local-first.v2"
    provider_priority: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def from_environment(cls, base: InferencePolicy | None = None) -> InferencePolicy:
        policy = base or cls()
        paid_allowed = _env_bool("SINTRAPRIME_PAID_MODELS_ALLOWED", policy.paid_models_allowed)
        require_approval = _env_bool(
            "SINTRAPRIME_REQUIRE_PAID_APPROVAL",
            policy.paid_escalation_requires_explicit_approval,
        )
        daily_budget = float(
            os.environ.get("SINTRAPRIME_PAID_DAILY_BUDGET_USD", policy.daily_budget_usd)
        )
        return replace(
            policy,
            paid_models_allowed=paid_allowed,
            paid_escalation_requires_explicit_approval=require_approval,
            daily_budget_usd=min(policy.daily_budget_usd, daily_budget),
        )


@dataclass(frozen=True)
class PaidAuthorization:
    actor: str
    scope: str
    max_amount_usd: float
    expires_at: datetime
    purpose: str
    policy_receipt_id: str
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_valid_for(self, request: InferenceRequest, estimated_cost_usd: float | None) -> bool:
        if datetime.now(UTC) >= self.expires_at:
            return False
        if self.scope not in {"global", request.task_type, request.request_id}:
            return False
        if estimated_cost_usd is None:
            return False
        return estimated_cost_usd <= self.max_amount_usd


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    task_type: str
    capability: str
    messages: list[dict[str, Any]]
    data_classification: DataClassification = DataClassification.UNKNOWN
    quality_floor: QualityFloor = QualityFloor.STANDARD
    latency_target_ms: int | None = None
    max_input_tokens: int = 12000
    max_output_tokens: int = 2000
    temperature: float = 0.2
    structured_output_schema: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    paid_use_authorized: bool = False
    cache_policy: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        *,
        task_type: str,
        capability: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> InferenceRequest:
        return cls(
            request_id=f"inf_{uuid.uuid4().hex[:12]}",
            task_type=task_type,
            capability=capability,
            messages=messages,
            **kwargs,
        )


@dataclass(frozen=True)
class InferenceResult:
    request_id: str
    provider: str
    model: str
    route_tier: RouteTier
    content: str | dict[str, Any]
    usage: dict[str, int]
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    latency_ms: int
    cache_status: CacheStatus
    attempts: int
    finish_reason: str
    policy_receipt_id: str
    provider_request_id: str | None = None


@dataclass(frozen=True)
class CostEstimate:
    estimated_cost_usd: float | None
    input_tokens: int
    output_tokens: int
    pricing_known: bool
    free_allowance_consumed: int = 0


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: str
    route_tier: RouteTier
    model: str
    capabilities: frozenset[str]
    quality: QualityFloor = QualityFloor.STANDARD
    context_window: int = 8192
    supports_streaming: bool = True
    supports_structured_output: bool = False
    paid: bool = False
    cloud: bool = False


@dataclass(frozen=True)
class ProviderHealth:
    reachable: bool
    healthy: bool
    circuit_open: bool = False
    reason: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ProviderLimits:
    requests_remaining: int | None = None
    tokens_remaining: int | None = None
    rate_limits_known: bool = False


@dataclass(frozen=True)
class ProviderMetadata:
    configured: bool
    authenticated: bool
    reachable: bool
    model_available: bool
    account_entitlement_known: bool
    rate_limits_known: bool
    pricing_known: bool
    free_allowance_known: bool
    healthy: bool
    eligible: bool
    source_url: str | None = None
    administrative_source: str | None = None
    verification_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    verification_method: str = "configuration"
    expiration_or_review_date: datetime | None = None
    verification_actor: str = "system"
    evidence_hash: str = ""


@dataclass(frozen=True)
class RouteCandidate:
    provider: str
    model: str
    route_tier: RouteTier
    score: float
    estimated_cost_usd: float | None
    success_rate: float


@dataclass(frozen=True)
class RejectedRoute:
    provider: str
    model: str
    route_tier: RouteTier
    reason: str


@dataclass(frozen=True)
class AttemptRecord:
    provider: str
    model: str
    route_tier: RouteTier
    attempt: int
    event: str
    error_kind: ProviderErrorKind | None = None
    message: str | None = None


@dataclass(frozen=True)
class InferenceReceipt:
    receipt_id: str
    request_id: str
    request_hash: str
    prompt_version_hash: str
    classification: DataClassification
    policy_version: str
    eligible_routes: list[RouteCandidate]
    rejected_routes: list[RejectedRoute]
    selected_provider: str | None
    selected_model: str | None
    retry_history: list[AttemptRecord]
    fallback_history: list[RouteCandidate]
    token_usage: dict[str, int]
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    cache_status: CacheStatus
    created_at: datetime
    final_output_hash: str | None = None


@dataclass(frozen=True)
class ProviderReliability:
    provider: str
    successes: int = 0
    failures: int = 0
    recent_failures: int = 0

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.successes / self.total


@dataclass(frozen=True)
class DecomposedTask:
    task_id: str
    parent_request_id: str
    task_type: str
    capability: str
    route_tier: RouteTier
    max_input_tokens: int
    max_output_tokens: int
    instruction: str


@dataclass(frozen=True)
class EscalationRequest:
    escalation_id: str
    request_id: str
    reason: str
    denied_routes: list[RejectedRoute]
    required_capability: str
    data_classification: DataClassification
    estimated_cost_usd: float | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InferenceProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...
    def health(self) -> ProviderHealth: ...
    def estimate_cost(self, request: InferenceRequest) -> CostEstimate: ...
    def invoke(self, request: InferenceRequest) -> InferenceResult: ...
    def invoke_stream(self, request: InferenceRequest) -> InferenceResult: ...
    def current_limits(self) -> ProviderLimits: ...


def stable_hash(value: Any) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def receipt_hash(*values: Any) -> str:
    return stable_hash(values)


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    return _jsonable(asdict(value))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, frozenset | set):
        return sorted(_jsonable(item) for item in value)
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
