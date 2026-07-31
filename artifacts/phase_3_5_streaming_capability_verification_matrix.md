# Streaming Capability Verification Matrix — Phase 3.5

**Artifact ID:** P3.5-ARTIFACT-002
**Phase:** 3.5 — Adapter Capability Expansion
**Date:** 2026-07-27
**Ratified under:** Blackstone Governance Library GB-1 (frozen baseline)

---

## 1. Scope

This matrix documents the streaming behavior of the governed inference control plane after Phase 3.5. It maps the three streaming entry points to their implementation status, partial/final semantics, and test coverage.

---

## 2. Streaming Entry Points

| Entry Point | Location | Status | Notes |
|---|---|---|---|
| `GovernedInferenceRouter.invoke_stream()` | `governed_inference/router.py` | ✅ Implemented | Classification, routing, policy enforcement, and provider streaming in one path. |
| `GovernedInferenceRouter.invoke(..., stream=True)` | `governed_inference/router.py` | ✅ Implemented | Transparently delegates to `provider.invoke_stream()` and materializes the final result for retry/fallback logic. |
| `ChatAgent.chat_stream()` | `agents/chat/chat_agent.py` | ✅ Migrated | Primary streaming consumer path now routes through `GovernedInferenceRouter.invoke_stream()`. Legacy OpenAI SDK fallback preserved. |

---

## 3. Partial / Final Semantics

`InferenceResult.is_partial` is the canonical signal introduced in Phase 3.5.

| Producer | Partial Result (`is_partial=True`) | Final Result (`is_partial=False`) |
|---|---|---|
| `OpenAIProvider.invoke_stream()` | Each token/text chunk yielded individually. | Last result contains the full aggregated content. |
| `MockProvider.invoke_stream()` | One partial mirroring the full content. | One final mirroring the full content. |
| `AnthropicProvider.invoke_stream()` | None (single final only). | One result from `invoke()`. |
| `OllamaProvider.invoke_stream()` | None (single final only). | One result from `invoke()`. |
| `DeepSeekProvider.invoke_stream()` | None (single final only). | One result from `invoke()`. |

---

## 4. Streaming Consumer Handling

| Consumer | Partial Handling | Final Handling | Fallback on Failure |
|---|---|---|---|
| `ChatAgent.chat_stream()` | Yields each `result.content` delta while `is_partial=True`. | Uses final `result.content` as the assistant message; adds `usage["total_tokens"]` to session token count. | Falls back to legacy direct OpenAI SDK streaming call. |

---

## 5. Test Coverage

| Test | Location | What It Verifies |
|---|---|---|
| `test_streaming_invocation_accumulates_content` | `tests/test_governed_inference_adapters.py` | OpenAI adapter yields partials + final with correct `is_partial` flags and aggregated content. |
| `test_streaming_router_yields_partials_for_stream_supported_provider` | `tests/test_governed_inference.py` | Router `invoke_stream()` yields partial and final results for a streaming provider. |
| `test_streaming_router_falls_back_to_invoke_when_provider_does_not_support_streaming` | `tests/test_governed_inference.py` | Router falls back to `invoke()` when `supports_streaming=False`. |
| `test_stream_failure_retries_same_adapter_non_stream_without_partial_concat` | `tests/test_governed_inference.py` | Router `invoke(stream=True)` retries a failed stream through non-stream `invoke()` without concatenating partials. |
| `test_chat_stream_routes_through_governed_router` | `agents/chat/tests/test_chat_agent_governed.py` | Chat streaming path routes through governed router and updates session state. |
| `test_chat_stream_governed_router_failure_falls_back_to_legacy` | `agents/chat/tests/test_chat_agent_governed.py` | Chat streaming falls back to legacy OpenAI SDK streaming on governed router failure. |
| `test_chat_stream_no_api_key_uses_fallback` | `agents/chat/tests/test_chat_agent_governed.py` | No API key yields rule-based fallback, not an error. |
| `test_chat_stream_request_requires_streaming` | `agents/chat/tests/test_chat_agent_governed.py` | Streaming request flag is propagated to the provider. |

---

## 6. Verification Results

| Verification | Command | Result |
|---|---|---|
| Streaming adapter tests | `.venv/Scripts/python -m pytest tests/test_governed_inference_adapters.py -q` | ✅ PASS |
| Streaming router tests | `.venv/Scripts/python -m pytest tests/test_governed_inference.py -q` | ✅ PASS |
| Chat agent governed tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent_governed.py -q` | ✅ PASS |
| CI-visible chat wrapper | `.venv/Scripts/python -m pytest tests/test_chat_agent_governed.py -q` | ✅ PASS |
| Full suite | `.venv/Scripts/python -m pytest --tb=short -q -o addopts=` | ✅ 470 passed, 2 warnings |

---

## 7. Streaming Limitations

- Only `OpenAIProvider` implements true token-by-token streaming.
- Anthropic, Ollama, and DeepSeek streaming is contract-compliant but yields a single aggregated result.
- Streaming requests bypass the exact-match cache; partial results are not cacheable.
- Vision streaming is not supported; `requires_vision=True` requests are denied before reaching streaming logic.
- Async streaming is not introduced in this phase.

---

## 8. References

- `governed_inference/contracts.py` — `InferenceResult.is_partial`, `InferenceRequest.requires_streaming`
- `governed_inference/router.py` — `invoke_stream()`, `invoke(..., stream=True)`
- `governed_inference/adapters.py` — `OpenAIProvider.invoke_stream()`, fallback streaming implementations
- `governed_inference/providers.py` — `MockProvider.invoke_stream()`
- `agents/chat/chat_agent.py` — `chat_stream()`
- `agents/chat/tests/test_chat_agent_governed.py` — chat streaming regression tests
- `tests/test_governed_inference.py` — router streaming tests
- `tests/test_governed_inference_adapters.py` — adapter streaming tests
