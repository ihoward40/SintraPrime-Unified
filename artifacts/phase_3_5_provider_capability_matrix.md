# Provider Capability Matrix — Phase 3.5

**Artifact ID:** P3.5-ARTIFACT-001
**Phase:** 3.5 — Adapter Capability Expansion
**Date:** 2026-07-27
**Ratified under:** Blackstone Governance Library GB-1 (frozen baseline)

---

## 1. Scope

This matrix documents the capabilities declared by each provider adapter in the governed inference control plane after the Phase 3.5 capability expansion. It covers the four concrete provider adapters introduced or hardened during this phase: OpenAI, Anthropic, Ollama, and DeepSeek.

Capabilities are declared via `ProviderCapabilities` in `governed_inference/contracts.py` and surfaced through the `InferenceProvider.capabilities()` protocol method.

---

## 2. Capability Definitions

| Capability | Meaning |
|---|---|
| `supports_streaming` | Provider can yield incremental content. Used by `GovernedInferenceRouter.invoke_stream()` and `route_denial_reason()` when `request.requires_streaming=True`. |
| `supports_vision` | Provider accepts vision/image message content. Used by routing when `request.requires_vision=True`. |
| `supports_structured_output` | Provider honors JSON schema / structured output requests via `InferenceRequest.structured_output_schema`. |
| `paid` | Provider incurs real cost or requires real credentials. Gate for `policy.paid_models_allowed`. |
| `cloud` | Provider routes outside the local network. Gate for `policy.cloud_sensitive_data_allowed`. |
| `route_tier` | Routing preference bucket: `LOCAL_PRIVATE`, `CLOUD_LOW_COST_FAST`, `CLOUD_PROTOTYPE`, `CLOUD_CODING`, `PREMIUM_ESCALATION`, `FAIL_CLOSED`. |
| `quality` | Minimum quality floor the provider satisfies: `basic`, `standard`, `high`, `premium`. |
| `context_window` | Maximum input+output token context the provider advertises. |

---

## 3. Adapter Capability Matrix

| Provider | Default Model | Route Tier | Quality | Context Window | Streaming | Vision | Structured Output | Paid | Cloud |
|---|---|---|---|---|---|---|---|---|---|
| **OpenAIProvider** | `gpt-4o-mini` | `CLOUD_PROTOTYPE` | `standard` | 128,000 | ✅ Native | ❌ | ✅ | ✅ | ✅ |
| **AnthropicProvider** | `claude-3-5-sonnet-20241022` | `CLOUD_CODING` | `high` | 200,000 | ✅ Fallback (`invoke` wrapper) | ❌ | ✅ | ✅ | ✅ |
| **OllamaProvider** | `llama3` | `LOCAL_PRIVATE` | `standard` | 128,000 | ✅ Fallback (`invoke` wrapper) | ❌ | ✅ | ❌ | ❌ |
| **DeepSeekProvider** | `deepseek-chat` | `CLOUD_LOW_COST_FAST` | `standard` | 64,000 | ✅ Fallback (`invoke` wrapper) | ❌ | ✅ | ✅ | ✅ |

Notes:

- **OpenAIProvider** is the only adapter with a native token-by-token streaming implementation (`invoke_stream` parses `chat.completions.create(stream=True)` chunks and yields partial/final `InferenceResult` objects).
- **AnthropicProvider**, **OllamaProvider**, and **DeepSeekProvider** implement `invoke_stream` by yielding the single result from `invoke()`. This satisfies the `InferenceProvider` protocol and makes them routable through `invoke_stream()`, but does not provide true incremental delivery.
- **Vision** is unsupported across all adapters in this phase. Requests with `requires_vision=True` against any Phase 3.5 adapter will be rejected by `route_denial_reason()` with reason `vision_not_supported`.
- **Structured output** is supported in contract and by OpenAI adapter; the other adapters inherit the contract flag but do not translate schemas into provider-specific formats in this phase.

---

## 4. Capability Set Taxonomy

Each adapter advertises a capability set used by `route_denial_reason()` to enforce `unsupported_capability` denials:

| Provider | Capability Set |
|---|---|
| OpenAIProvider | `classification`, `extraction`, `summarization`, `drafting`, `coding`, `reasoning` |
| AnthropicProvider | `classification`, `extraction`, `summarization`, `drafting`, `coding`, `reasoning` |
| OllamaProvider | `classification`, `extraction`, `summarization`, `drafting`, `coding`, `reasoning` |
| DeepSeekProvider | `classification`, `extraction`, `summarization`, `drafting`, `coding`, `reasoning` |

---

## 5. Routing Implications

| Request Flag | Behavior |
|---|---|
| `requires_streaming=True` | OpenAI preferred; Anthropic/Ollama/DeepSeek acceptable via fallback. |
| `requires_vision=True` | No adapter eligible; request escalated with `vision_not_supported`. |
| `structured_output_schema` set | OpenAI emits `response_format={type:"json_schema"...}`; others return content unchanged. |
| `quality_floor=high` | Anthropic satisfies; OpenAI/Ollama/DeepSeek rejected with `quality_floor_not_met`. |
| `quality_floor=premium` | No adapter satisfies in default configuration. |

---

## 6. Deferred Capabilities

The following capabilities were intentionally deferred and are not part of Phase 3.5:

- **Async invocation** (`invoke_async`) — no `async`/`await` plumbing added.
- **True native streaming** for Anthropic, Ollama, DeepSeek.
- **Vision input** — all adapters declare `supports_vision=False`.
- **Multi-modal output** (audio, image generation).
- **Function/tool execution loops** — `tools` are forwarded by OpenAI adapter but not executed by the router.

---

## 7. References

- `governed_inference/contracts.py` — `ProviderCapabilities`, `InferenceProvider`
- `governed_inference/adapters.py` — `OpenAIProvider`, `AnthropicProvider`, `OllamaProvider`, `DeepSeekProvider`
- `governed_inference/policy.py` — `route_denial_reason()`
- `governed_inference/router.py` — `invoke_stream()`, `_build_candidates()`
