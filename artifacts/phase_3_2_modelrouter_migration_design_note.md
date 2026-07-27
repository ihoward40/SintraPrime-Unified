# Phase 3.2 — ModelRouter Migration Design Note

**Design Note ID:** P3.2-DN-2026-07-27-01
**Date:** 2026-07-27
**Scope:** OllamaProvider adapter, DeepSeekProvider adapter, ModelRouter delegation to GovernedInferenceRouter
**Baseline:** Phase 3.1 CLOSED (commit 4462e9db88d235967bf6ac9dfb6aa2428f03ec5b)

---

## 1. Objective

Make `local_models/model_router.py` the first production consumer of the governed inference control plane while preserving its external behavior. Add real provider adapters for Ollama and DeepSeek so the `GovernedInferenceRouter` can route local and DeepSeek traffic, not only OpenAI and Anthropic.

---

## 2. Architecture

### 2.1 Design Principle

Preserve the existing `ModelRouter` public API exactly. Change only the internal execution path so `complete()`, `status()`, and `routing_plan()` delegate to `GovernedInferenceRouter` for inference decisions while continuing to expose the same data shapes.

### 2.2 Module Layout

| Module | Path | Responsibility |
|---|---|---|
| adapters.py | governed_inference/adapters.py | Add OllamaProvider and DeepSeekProvider |
| model_router.py | local_models/model_router.py | Delegate `complete()` to `GovernedInferenceRouter` via the new providers |
| __init__.py | governed_inference/__init__.py | Export new adapters |
| test_governed_inference_adapters.py | tests/test_governed_inference_adapters.py | Add adapter tests for Ollama and DeepSeek |
| test_model_router_migration.py | tests/test_model_router_migration.py | New migration verification tests |

### 2.3 Adapter Class Hierarchy

```
BaseConfiguredProvider (providers.py — existing)
    └── _BaseRealProvider (adapters.py — new in P3.1)
            ├── OpenAIProvider (adapters.py)
            ├── AnthropicProvider (adapters.py)
            ├── OllamaProvider (adapters.py)      ← new
            └── DeepSeekProvider (adapters.py)    ← new
```

### 2.4 ModelRouter Delegation Flow

```
ModelRouter.complete(prompt, task, model, system, temperature, max_tokens)
        │
        ▼
[build InferenceRequest from ModelRouter arguments]
        │
        ▼
[GovernedInferenceRouter.invoke(request)]
        │
        ▼
[convert InferenceResult → RouterResult]
        │
        ▼
return RouterResult
```

`ModelRouter` remains the public surface. Existing call sites in `local_models_api.py`, tests, and any agents continue to work unchanged. Legacy provider-specific methods (`_call_ollama`, `_call_deepseek`, etc.) are kept as fallback paths and are only removed in a later phase.

### 2.5 Availability Mapping

| ModelRouter Flag | GovernedInferenceRouter Behavior |
|---|---|
| `air_gap_mode=True` | Construct router with only `OllamaProvider`; paid/remote providers excluded |
| `prefer_local=True` | `OllamaProvider` scores highest via LOCAL_PRIVATE tier |
| DeepSeek key present | Add `DeepSeekProvider` as a cloud candidate |
| OpenAI key present | Add `OpenAIProvider` as a cloud candidate |
| Anthropic key present | Add `AnthropicProvider` as a cloud candidate |

---

## 3. OllamaProvider (P3.2.1)

### 3.1 Responsibilities

- Chat completion via the existing `OllamaClient`
- Timeout support via `timeout_seconds` passed to `OllamaClient`
- Structured logging matching OpenAI/Anthropic adapter conventions
- Trace propagation via the router (no provider-side tracer dependency)
- Retry compatibility via `InferenceError` translation
- Token accounting where available (`eval_count`, `prompt_eval_count`, `load_duration` from Ollama response)
- Provider metadata via `capabilities()`, `health()`, `current_limits()`

### 3.2 Configuration

```python
OllamaProvider(
    base_url="http://localhost:11434",
    model="llama3",
    timeout_seconds=120.0,
)
```

An Ollama provider is always `configured=True` for routing purposes because the local daemon is the only runtime dependency; actual reachability is checked in `health()`.

### 3.3 Model Selection

`ModelRouter` maps `task` → recommended model (`TASK_LOCAL_MODEL`) and stores it in `request.metadata["model_override"]` so the provider uses the task-appropriate local model. If the model does not exist locally, the Ollama provider falls back to `model_exists`/`default_model` logic inside `OllamaClient` or returns a `TRANSIENT` error that triggers router fallback.

### 3.4 Logging

| Event | Level | Key Extra Fields |
|---|---|---|
| ollama.invoke.success | INFO | provider, model, request_id, latency_ms, input_tokens, output_tokens |
| ollama.invoke.error | WARNING | provider, model, request_id, latency_ms, error_kind, error_type |

---

## 4. DeepSeekProvider (P3.2.2)

### 4.1 Responsibilities

- Chat completion via the existing `DeepSeekClient`
- Timeout support via `timeout_seconds` passed to `DeepSeekClient`
- Structured logging matching OpenAI/Anthropic adapter conventions
- Trace propagation via the router
- Retry compatibility via `InferenceError` translation of DeepSeek SDK/request errors
- Token accounting (`prompt_tokens`, `completion_tokens`, `total_tokens`)
- Cost tracking via `CostTracker` on the underlying client or local estimate
- Provider metadata

### 4.2 Configuration

```python
DeepSeekProvider(
    api_key="...",               # required for network calls
    model="deepseek-chat",
    timeout_seconds=120.0,
)
```

`configured` is `True` only when an API key is present.

### 4.3 Reasoning Mode

`ModelRouter` maps reasoning tasks (`legal_research`, `case_analysis`, `argument_construction`) to `deepseek-reasoner`. The provider calls `DeepSeekClient.complete()` with the reasoning model and extracts chain-of-thought if present. The raw reasoning text is preserved in `request.metadata` or returned in the result content; `RouterResult.thinking` is populated for backward compatibility.

### 4.4 Logging

| Event | Level | Key Extra Fields |
|---|---|---|
| deepseek.invoke.success | INFO | provider, model, request_id, latency_ms, input_tokens, output_tokens, cost_usd |
| deepseek.invoke.error | WARNING | provider, model, request_id, latency_ms, error_kind, error_type |

---

## 5. ModelRouter Delegation (P3.2.3)

### 5.1 Internal Router Construction

`ModelRouter.__init__` builds a `GovernedInferenceRouter` using:

- `OllamaProvider` always (local-first default)
- `DeepSeekProvider` if key is present
- `OpenAIProvider` if key is present
- `AnthropicProvider` if key is present

The order of providers in the list matches `TASK_PROVIDER_PREFERENCE` so equivalent routing is produced when all are healthy.

### 5.2 Policy

Use the default `InferencePolicy.local_first()`. Because Ollama is a `LOCAL_PRIVATE` provider, it is selected first under the default scoring. DeepSeek, OpenAI, and Anthropic are cloud/paid providers and are only selected when:

1. local fails, and
2. the provider is configured, and
3. the data classification permits cloud routing.

`air_gap_mode=True` constructs the router with only the Ollama provider, which is identical to the legacy behavior.

### 5.3 Request Mapping

| ModelRouter.complete() arg | InferenceRequest field |
|---|---|
| prompt | messages = `[{"role":"user","content":prompt}]` |
| task | task_type, capability (mapped from task) |
| system | messages prepend `"system"` message |
| temperature | temperature |
| max_tokens | max_output_tokens |
| model != "auto" | metadata["model_override"] |

Capability mapping:

| TaskType | capability |
|---|---|
| LEGAL_RESEARCH | reasoning |
| CASE_ANALYSIS | reasoning |
| ARGUMENT_CONSTRUCTION | reasoning |
| CONTRACT_REVIEW | extraction |
| DOCUMENT_REVIEW | summarization |
| CLAUSE_EXTRACTION | extraction |
| SUMMARISATION | summarization |
| TEMPLATE_FILLING | drafting |
| QUICK_RESEARCH | summarization |
| CHAT | drafting |
| EMBEDDINGS | extraction |
| GENERAL | drafting |

### 5.4 Result Mapping

`InferenceResult` → `RouterResult`:

| RouterResult field | Source |
|---|---|
| content | `str(result.content)` |
| provider | `Provider(result.provider)` or best-effort mapping |
| model | `result.model` |
| task_type | original `task_type` |
| latency_s | `result.latency_ms / 1000.0` |
| usage | `result.usage` |
| cost_usd | `result.actual_cost_usd or result.estimated_cost_usd or 0.0` |
| thinking | from DeepSeek reasoning or metadata |
| error | None on success |

If the router raises `InferenceError`, `ModelRouter.complete()` catches it and returns a `RouterResult` with `error` set, preserving the legacy error-return contract.

### 5.5 status() and routing_plan()

- `status()` delegates to provider `health()` and `capabilities()` from the internal `GovernedInferenceRouter` providers, converting back to the existing `dict` shape.
- `routing_plan()` keeps its existing shape but uses `GovernedInferenceRouter` candidate scoring when providers are healthy.

---

## 6. Feature Parity (P3.2.4)

| Legacy Behavior | Delegated Equivalent |
|---|---|
| Task-based provider preference | Provider list ordered by `TASK_PROVIDER_PREFERENCE` and default scoring |
| Fallback to next provider | Router fallback history |
| Timeout | `policy.per_request.timeout_seconds` + adapter timeout |
| Logging | Router lifecycle logs + adapter logs |
| Tracing | Router tracer spans |
| Retry | `policy.per_request.max_attempts` |
| Air-gap mode | Router built with only OllamaProvider |
| DeepSeek reasoning extraction | DeepSeekProvider with reasoning model override |

---

## 7. Explicit Non-Goals

Per authorization, this phase does NOT:

- Migrate `SintraLLMBridge`
- Modify agent call sites
- Remove legacy routing classes
- Delete `_call_ollama`, `_call_deepseek`, `_call_openai`, `_call_anthropic`
- Consolidate all LLM layers

Legacy methods remain untouched and available as a safety net.

---

## 8. Verification Plan

### 8.1 New Tests

Add tests in `tests/test_governed_inference_adapters.py`:

| Test Class | Count | Focus |
|---|---|---|
| TestOllamaProvider | 6 | unconfigured→always configured, successful invocation, model override fallback, error translation, structured logging, capabilities |
| TestDeepSeekProvider | 6 | unconfigured raises, successful invocation, reasoning mode, error translation, structured logging, capabilities |

Add new file `tests/test_model_router_migration.py`:

| Test | Focus |
|---|---|
| test_complete_delegates_to_ollama | ModelRouter returns content from OllamaProvider via router |
| test_air_gap_mode_uses_only_ollama | DeepSeek/OpenAI keys ignored when air_gap=True |
| test_deepseek_fallback_when_ollama_fails | Router fallback to DeepSeekProvider |
| test_timeout_enforcement_preserved | Slow provider triggers timeout error via router |
| test_structured_logging_active | Router emits lifecycle logs |
| test_trace_propagation_active | Tracer spans created |
| test_model_router_api_backward_compatible | `complete()` signature unchanged, returns RouterResult |
| test_routing_plan_shape_unchanged | `routing_plan()` returns same keys |
| test_status_shape_unchanged | `status()` returns same keys |

### 8.2 Required Evidence

- Full suite: `python -m pytest --tb=short` must report 421 existing + new tests passed
- Smoke lane: `scripts/smoke/e2e_skills_smoke.py` must PASS
- `git status --porcelain=v1` must be empty before certification

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| ModelRouter behavior drift | Keep legacy methods, add backward-compatibility tests |
| Ollama health check in tests | Mock `OllamaClient.is_available()` |
| DeepSeek key leak in tests | Use fake keys, never real credentials |
| Provider list ordering changes routing | Match `TASK_PROVIDER_PREFERENCE` exactly |
| Policy denies cloud routes unexpectedly | Use PUBLIC data classification in tests |

---

## 10. Deliverables

1. ModelRouter Migration Design Note — this document
2. OllamaProvider — `governed_inference/adapters.py`
3. DeepSeekProvider — `governed_inference/adapters.py`
4. Migration Verification Report — to be produced after tests
5. Backward Compatibility Report — to be produced after tests
6. Phase 3.2 Certification Report — to be produced after tests
7. Updated governance checkpoint — `governance/blackstone/checkpoints/phase-3.2-modelrouter-migration.md`
