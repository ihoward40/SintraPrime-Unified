# Phase 3.1 — Provider Adapter Design Note

**Design Note ID:** P3.1-DN-2026-07-27-01
**Date:** 2026-07-27
**Scope:** OpenAI and Anthropic provider adapters, timeout enforcement, structured logging, trace integration

---

## 1. Architecture

### 1.1 Design Principle

Do not build a fifth LLM layer. Complete the one that already exists.

The `governed_inference/` package already defines the correct provider abstraction via the `InferenceProvider` protocol and `BaseConfiguredProvider` base class. Phase 3.1 adds real network-capable adapters that conform to this existing interface, plus wiring for timeout, logging, and tracing in the router.

### 1.2 Module Layout

| Module | Path | Responsibility |
|---|---|---|
| adapters.py | governed_inference/adapters.py | OpenAIProvider, AnthropicProvider, error translation |
| router.py (patched) | governed_inference/router.py | Timeout enforcement, structured logging, trace span lifecycle |
| __init__.py (patched) | governed_inference/__init__.py | Export new adapters |
| test_governed_inference_adapters.py | tests/ | 28 targeted adapter tests |

### 1.3 Adapter Class Hierarchy

```
BaseConfiguredProvider (providers.py — existing)
    └── _BaseRealProvider (adapters.py — new shared base)
            ├── OpenAIProvider (adapters.py)
            └── AnthropicProvider (adapters.py)
```

`_BaseRealProvider` provides shared logic: lazy client construction, capabilities/health/estimate_cost/current_limits, and result assembly. Subclasses implement `_create_client()`, `invoke()`, and `invoke_stream()`.

### 1.4 Error Translation

SDK exceptions are translated to `InferenceError` with `ProviderErrorKind` by class-name matching (avoids hard SDK import dependency at module load time):

| SDK Exception Class | ProviderErrorKind | Router Behavior |
|---|---|---|
| APITimeoutError | TRANSIENT | Retry |
| RateLimitError | TRANSIENT | Retry |
| APIConnectionError | TRANSIENT | Retry |
| InternalServerError | TRANSIENT | Retry |
| AuthenticationError | AUTHENTICATION | No retry, fallback |
| PaymentRequiredError | PAYMENT_REQUIRED | No retry, fallback |
| BadRequestError | INVALID_REQUEST | No retry, fallback |
| ContextWindowExceededError | CONTEXT_OVERFLOW | No retry, fallback |
| (other) | UNKNOWN | No retry, fallback |

### 1.5 Timeout Enforcement

The router now reads `policy.per_request.timeout_seconds` (default: 60s), computes a `time.monotonic()` deadline before each provider invocation, and checks the deadline after the call returns. If exceeded, it raises `InferenceError(TRANSIENT)` which triggers the existing retry/fallback logic.

This is a post-hoc deadline check, not a pre-emptive timeout signal. The OpenAI and Anthropic SDKs receive `timeout=` at client construction (passed through `_timeout_seconds` on the adapter), so they enforce their own network-level timeout. The router deadline catches any case where the SDK timeout fails or is longer than the policy allows.

### 1.6 Structured Logging

The router emits structured log records at these lifecycle points:

| Event | Level | Logger | Key Extra Fields |
|---|---|---|---|
| inference.requested | INFO | governed_inference.router | request_id, task_type, capability |
| inference.classified | INFO | governed_inference.router | request_id, classification, redaction_decision |
| inference.cache_hit | INFO | governed_inference.router | request_id, provider |
| inference.denied | WARNING | governed_inference.router | request_id, rejected_count, reasons |
| inference.attempt_failed | WARNING | governed_inference.router | request_id, provider, model, attempt, error_kind |
| inference.fallback_selected | INFO | governed_inference.router | request_id, failed_provider |
| inference.stream_fallback | WARNING | governed_inference.router | request_id, provider, error_kind, stream_partial_preserved |
| inference.timeout_exceeded | WARNING | governed_inference.router | request_id, provider, timeout_seconds, latency_ms |
| inference.completed | INFO | governed_inference.router | request_id, provider, model, route_tier, latency_ms, attempts, input_tokens, output_tokens, cache_status, estimated_cost_usd, provider_request_id |

Adapters emit their own logs:
| Event | Level | Logger | Key Extra Fields |
|---|---|---|---|
| openai.invoke.success | INFO | governed_inference.adapters | provider, model, request_id, latency_ms, input_tokens, output_tokens, provider_request_id |
| openai.invoke.error | WARNING | governed_inference.adapters | provider, model, request_id, latency_ms, error_kind, error_type |
| openai.invoke_stream.success | INFO | governed_inference.adapters | provider, model, request_id, latency_ms, chunk_count |
| openai.invoke_stream.error | WARNING | governed_inference.adapters | provider, model, request_id, latency_ms, error_kind, error_type |
| anthropic.invoke.success | INFO | governed_inference.adapters | provider, model, request_id, latency_ms, input_tokens, output_tokens, provider_request_id |
| anthropic.invoke.error | WARNING | governed_inference.adapters | provider, model, request_id, latency_ms, error_kind, error_type |

No prompt content or secrets are logged. Only metadata: request_id, provider, model, token counts, latency, error kinds.

### 1.7 Trace Integration

The router accepts an optional `tracer` parameter (defaults to None for backward compatibility). When a tracer is provided:

1. A new trace is created per `invoke()` call with name `inference.{task_type}`.
2. A root span `inference.invoke` is created with tags: request_id, task_type, capability, classification.
3. On success: span tags get provider, model, latency_ms, attempts; span finishes with OK.
4. On cache hit: span gets outcome=cache_hit, provider; finishes OK.
5. On denial: span gets outcome=denied; finishes with error.
6. On all-routes-failed: span gets outcome=all_routes_failed; finishes with error.

The tracer uses the existing `observability/tracer.py` Tracer class — no new tracing framework introduced.

### 1.8 Backward Compatibility

- `GovernedInferenceRouter.__init__` `tracer` parameter is optional (default None)
- All existing tests pass without modification (16/16)
- No production call sites are modified
- No existing provider shells are modified
- The `__init__.py` exports are additive (new names only)

---

## 2. Verification Evidence

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Existing governed_inference tests | 16/16 PASS |
| New adapter tests | 28/28 PASS |
| Full test suite | 421 passed (393 existing + 28 new), 2 pre-existing warnings |
| Smoke lane | PASS — 3/3 smoke tests, repo_truth PASS |
| Production code modified | router.py (additive), __init__.py (additive exports), 0 call sites |
| New files | adapters.py, test_governed_inference_adapters.py |

---

## 3. Out of Scope (Confirmed)

- No migration of existing call sites
- No replacement of ModelRouter or SintraLLMBridge
- No new providers beyond OpenAI and Anthropic
- No architectural consolidation
- No async support in the router (sync-only)
- No content-level PII redaction (classification gates routing, content transformation is separate)
- No semantic cache