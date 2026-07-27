# Phase 3.0 — LLM Reliability Discovery Report

**Report ID:** P3.0-2026-07-27-01
**Generated:** 2026-07-27
**Scope:** LLM provider integration inventory, gap analysis, and bounded implementation plan
**Authorization:** Isiah Howard — P3.0 Discovery authorized, no production code modified
**Status:** COMPLETE

---

## 1. Executive Summary

The SintraPrime-Unified repository contains **four parallel, uncoordinated LLM integration layers**, none of which is wired to the others. The `governed_inference/` package is the most architecturally complete — it defines a provider-agnostic control plane with routing, policy enforcement, redaction receipts, retry/fallback, circuit-breaker scoring, cost accounting, and an inference ledger — but it has **zero production consumers**. All actual LLM calls in the agent system, RAG pipeline, multimodal layer, CRM integration, and code generation bypass it entirely, instantiating SDK clients directly with `openai.OpenAI()` or `anthropic.Anthropic()` inside each call site.

This creates five critical gaps: no unified retry/timeout, no structured logging around LLM requests, no redaction enforcement on ungoverned paths, no correlation/trace ID propagation, and no cost accounting for actual API usage. The good news is that the `governed_inference/` layer already provides the correct abstraction surface — the work is to wire it in, not to design it.

---

## 2. Repository Inventory

### 2.1 LLM Provider SDKs in Use

| Provider | SDK | Import Pattern | Files Using It |
|---|---|---|---|
| OpenAI | `openai` (Python SDK) | `import openai` / `from openai import OpenAI/AsyncOpenAI` | 9 Python files |
| Anthropic | `anthropic` (Python SDK) | `import anthropic` / `from anthropic import Anthropic` | 4 Python files |
| Ollama | Custom `OllamaClient` (local_models/ollama_client.py) | `from local_models.ollama_client import OllamaClient` | 3 Python files |
| DeepSeek | Custom `DeepSeekClient` (local_models/deepseek_client.py) | `from local_models.deepseek_client import DeepSeekClient` | 1 file (model_router.py) |

No LiteLLM, Groq SDK, Google GenAI, Cohere, Mistral, or Together SDK imports were found. Groq, Gemini, and Mistral exist as **shell adapters** in `governed_inference/providers.py` but are not configured for network invocation.

### 2.2 LLM Integration Layers (Four Parallel Systems)

#### Layer A: Governed Inference Control Plane (governed_inference/)

**Status:** Architected, tested, **not wired to any production consumer.**

| Module | Path | Purpose |
|---|---|---|
| contracts.py | governed_inference/contracts.py | InferenceRequest/Result, Provider Protocol, policy dataclasses, enums |
| providers.py | governed_inference/providers.py | BaseConfiguredProvider, MockProvider, shell adapters (LMStudio, OmniRoute, OpenRouter, Groq, Gemini, Mistral, Premium) |
| router.py | governed_inference/router.py | GovernedInferenceRouter — routing, retry, fallback, circuit-breaker scoring |
| policy.py | governed_inference/policy.py | Route denial logic, strictest-policy merge, data classification gates |
| classification.py | governed_inference/classification.py | Data classification (legal/financial/identity), redaction receipts |
| ledger.py | governed_inference/ledger.py | In-memory event ledger, provider reliability tracking, inference receipts |
| cache.py | governed_inference/cache.py | Exact-match inference cache |
| decomposition.py | governed_inference/decomposition.py | Task decomposition for local models |
| escalation.py | governed_inference/escalation.py | Escalation queue for denied/failed requests |

Key contracts:
- `InferenceProvider` Protocol: `capabilities()`, `health()`, `estimate_cost()`, `invoke()`, `invoke_stream()`, `current_limits()`
- `InferenceRequest`: request_id, task_type, capability, messages, data_classification, quality_floor, max_input/output_tokens, temperature, structured_output_schema, tools, paid_use_authorized, cache_policy, metadata
- `InferenceResult`: request_id, provider, model, route_tier, content, usage, estimated/actual_cost_usd, latency_ms, cache_status, attempts, finish_reason, policy_receipt_id, provider_request_id
- `InferencePolicy`: mode, paid_models_allowed, budgets, per_request limits, cache policy, min_success_rate
- `InferenceReceipt`: full audit record with eligible/rejected routes, retry/fallback history, token usage, cost, hashes

Features present:
- Data classification with legal/financial/identity term detection
- Redaction receipts (hash-based, not content transformation)
- Route scoring: local-first, cost-aware, reliability-aware
- Retry with transient error detection and bounded backoff (max_attempts from policy)
- Fallback across providers in preference order
- Circuit-breaker: provider reliability tracking with success_rate floor
- Exact-match cache with policy-aware bypass
- Inference receipts with prompt/output hashing
- Paid-use governance with authorization scope/expiry validation
- Escalation queue for denied requests
- Policy merge (strictest-wins) for hierarchical enforcement
- Environment-driven policy override (SINTRAPRIME_PAID_MODELS_ALLOWED, etc.)

Features absent:
- No real network-capable provider adapters (all `invoke()` raise InferenceError)
- No timeout enforcement on `invoke()` / `invoke_stream()`
- No structured logging (uses in-memory ledger events, not stdlib logging)
- No correlation/trace ID propagation to provider calls
- No async support (router.invoke is synchronous)

#### Layer B: Local Model Router (local_models/model_router.py)

**Status:** Production-active, standalone, **not connected to governed_inference/.**

`ModelRouter` class provides task-based routing across Ollama, DeepSeek, OpenAI, and Anthropic. Key characteristics:
- Task type enum with 12 legal-domain categories
- Static provider preference order per task type
- Availability-cached provider selection (30s TTL)
- Fallback through preference list on provider failure
- Direct SDK instantiation: `openai.OpenAI(api_key=self._openai_key)`, `anthropic.Anthropic(api_key=self._anthropic_key)`
- No retry logic (single attempt per provider, fall through on failure)
- No timeout enforcement
- No structured logging (uses `logging.getLogger` with `logger.warning` for failures only)
- No redaction or data classification
- No cost accounting
- No correlation/trace ID propagation
- Stream parameter declared but not implemented for cloud providers

#### Layer C: SintraLLMBridge (local_llm/sintra_llm_bridge.py)

**Status:** Production-active, standalone, **not connected to governed_inference/.**

Priority chain: Ollama/Hermes → OpenAI → Anthropic → static fallback. Key characteristics:
- Async-first design (async def methods)
- Environment-driven configuration (SINTRA_LOCAL_LLM, SINTRA_LOCAL_MODEL, etc.)
- Custom adapter pattern: HermesAdapter, OllamaAdapter
- No retry logic
- No timeout enforcement
- No structured logging (uses `logging.getLogger`)
- No redaction or data classification
- No cost accounting
- No correlation/trace ID propagation

#### Layer D: Direct SDK Calls (agents/, claude_code/, rag/, multimodal/, integrations/, phase17/)

**Status:** Production-active, **no abstraction layer at all.**

Every file that calls an LLM does so by directly importing the SDK and instantiating a client. No shared gateway, no policy enforcement, no redaction.

Files with direct `openai.OpenAI()` or `openai.AsyncOpenAI()`:

| File | Call Pattern | Purpose |
|---|---|---|
| agents/chat/chat_agent.py | `openai.OpenAI()` ×4 call sites | Chat responses, streaming, task execution |
| agents/nova/nova_agent.py | `openai.OpenAI()` ×1 | Nova agent LLM calls |
| agents/sigma/sigma_agent.py | `openai.OpenAI()` ×1 | Sigma agent LLM calls |
| agents/zero/zero_agent.py | `openai.OpenAI()` ×1 | Zero agent LLM calls |
| local_models/model_router.py | `openai.OpenAI()` ×1 | Model router OpenAI path |
| integrations/airtable_crm/crm_manager.py | `openai.OpenAI()` ×2 | CRM enrichment |
| multimodal/document_vision.py | `OpenAI()` ×1 | Document vision analysis |
| multimodal/audio_transcription.py | `OpenAI()` ×1 | Audio transcription |
| rag/rag_pipeline.py | `AsyncOpenAI()` ×1 | RAG pipeline |
| rag/embedder.py | `AsyncOpenAI()` ×1 | Embedding generation |
| phase17/llm_wiring/llm_executor.py | `openai.OpenAI()` ×1 | LLM Gateway (phase 17C) |
| developer_experience/model_playground.py | `openai.OpenAI()` ×2 | Model playground |

Files with direct `anthropic.Anthropic()`:

| File | Call Pattern | Purpose |
|---|---|---|
| claude_code/legal_code_assistant.py | `anthropic.Anthropic()` ×1 | Legal code assistant |
| claude_code/engine.py | `anthropic.Anthropic()` ×1 | Claude code engine |
| claude_code/code_generator.py | `anthropic.Anthropic()` ×1 | Code generation |
| local_models/model_router.py | `anthropic.Anthropic()` ×1 | Model router Anthropic path |
| developer_experience/model_playground.py | `anthropic.Anthropic()` ×1 | Model playground |

### 2.3 Prompt Construction and Invocation Patterns

Three distinct patterns exist:

**Pattern 1: Raw message list (agents/)**
```python
messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}]
resp = client.chat.completions.create(model=..., messages=messages, ...)
```
No structured output schema, no tool definitions, no temperature governance.

**Pattern 2: Single prompt string (local_models/model_router.py, phase17/)**
```python
resp = client.chat.completions.create(model=..., messages=[{"role": "user", "content": prompt}])
```
System prompt optional. No structured output. No tools.

**Pattern 3: Governed request contract (governed_inference/ — unused)**
```python
request = InferenceRequest.new(task_type="legal_research", capability="extraction",
                                messages=[...], structured_output_schema={...}, tools=[...])
result = router.invoke(request)
```
Full structured output, tools, data classification, quality floor, cache policy, paid-use authorization.

### 2.4 Retry Logic

| System | Retry? | Strategy |
|---|---|---|
| governed_inference/router.py | Yes | max_attempts from policy (default 3), transient error detection, 0.01*attempt backoff (capped at 0.05s), fallback to next provider |
| local_models/model_router.py | No | Single attempt per provider, fall through to next in preference list |
| local_llm/sintra_llm_bridge.py | No | Single attempt per provider in priority chain |
| agents/chat/chat_agent.py | No | Single attempt, try/except with fallback response string |
| agents/nova/sigma/zero | No | Single attempt |
| claude_code/* | No | Single attempt |
| rag/* | No | Single attempt |
| multimodal/* | No | Single attempt |
| phase17/llm_executor.py | No | Single attempt, catch-all exception handler |
| integrations/airtable_crm | No | Single attempt |

Only `governed_inference/router.py` has retry logic. No file in the repository uses `tenacity`, `backoff`, or any retry library.

### 2.5 Timeout Handling

| System | Timeout? | Mechanism |
|---|---|---|
| governed_inference/contracts.py | Defined in policy (default 60s) | `PerRequestPolicy.timeout_seconds` — but **not enforced** in router.invoke() |
| agents/sigma/sigma_agent.py | Yes (subprocess) | `subprocess.run(..., timeout=600)` — for shell commands, not LLM calls |
| agents/zero/zero_agent.py | Yes (subprocess) | `subprocess.run(..., timeout=300)` — for shell commands, not LLM calls |
| All other LLM call sites | No | No timeout parameter passed to any SDK call |

No LLM call in the repository passes a `timeout` parameter to the SDK. The `openai` and `anthropic` SDKs use their own defaults (typically 60-120s), which are not configurable per-request in the current code.

### 2.6 Streaming Support

| System | Streaming? | Implementation |
|---|---|---|
| agents/chat/chat_agent.py | Yes | `stream=True` with `client.chat.completions.create(...)`, yields `chunk.choices[0].delta.content` |
| governed_inference/router.py | Yes (contract) | `invoke_stream()` on provider, falls back to `invoke()` on transient error |
| local_models/model_router.py | Declared, not implemented | `stream` parameter accepted but not passed to OpenAI/Anthropic calls |
| All other call sites | No | No streaming |

Only `chat_agent.py` implements real streaming. The governed inference router declares streaming in the provider protocol but no real provider implements it.

### 2.7 Structured Logging Around LLM Requests

| System | Logging? | What is Logged |
|---|---|---|
| governed_inference/ledger.py | In-memory event ledger | `inference.requested`, `inference.classified`, `inference.redacted`, `inference.route_candidates_built`, `inference.route_selected`, `inference.attempt_started`, `inference.attempt_failed`, `inference.completed`, `inference.cost_recorded`, `inference.cache_hit`, `inference.fallback_selected`, `inference.denied` |
| local_models/model_router.py | `logging.getLogger` | `logger.warning("Provider %s failed: %s")` — failures only |
| local_llm/sintra_llm_bridge.py | `logging.getLogger` | `logger.error` / `logger.warning` — failures only |
| agents/chat/chat_agent.py | `logging.getLogger` | `logger.error("Streaming failed: %s")` — failures only |
| All other call sites | None or minimal | No logging around LLM request/response |

No file uses structured logging (JSON, key-value) around LLM requests. No file logs request input, response output, token usage, latency, or cost in a machine-parseable format.

### 2.8 Redaction and Secret-Handling

| System | Redaction? | Mechanism |
|---|---|---|
| governed_inference/classification.py | Yes | Data classification by keyword matching (legal/financial/identity terms), redaction receipts with hash-based audit. Does NOT transform content — classifies and gates routing. |
| All other call sites | No | API keys read from environment. Prompt content sent directly to providers with no classification, redaction, or gating. |

No file in the repository performs content-level redaction (PII masking, SSN removal, etc.) on prompts before sending to LLM providers. The governed inference layer classifies and gates (local-only for restricted) but does not transform content.

### 2.9 Request IDs, Correlation IDs, and Execution IDs

| System | ID Propagation? | Mechanism |
|---|---|---|
| governed_inference/contracts.py | Yes (defined) | `InferenceRequest.request_id` (auto-generated `inf_*`), `InferenceResult.provider_request_id`, `InferenceReceipt.receipt_id` |
| observability/tracer.py | Yes (defined) | `TraceContext` with `trace_id`, `span_id`, `x-trace-id` / `x-parent-span-id` headers |
| governed_inference/router.py | Partial | Emits ledger events with `request_id` but does not propagate to provider calls |
| agents/chat/chat_agent.py | No | No request IDs |
| All other call sites | No | No request IDs, no correlation IDs, no trace IDs |

The observability tracer (`observability/tracer.py`) provides a complete tracing model with `TraceContext`, `Span`, `Trace`, and `Tracer` classes. It supports:
- `x-trace-id` / `x-parent-span-id` HTTP header propagation
- Chrome DevTools flame graph export
- Span tags and logs
- But it is **not wired to any LLM call site**

The governed inference router emits `request_id` in its ledger events but does not inject trace context into provider calls.

---

## 3. Current Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │          PRODUCTION CALLERS             │
                    │  (agents/, rag/, multimodal/,          │
                    │   claude_code/, integrations/,          │
                    │   phase17/, developer_experience/)     │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │     DIRECT SDK INSTANTIATION            │
                    │  openai.OpenAI(api_key=...)             │
                    │  anthropic.Anthropic(api_key=...)       │
                    │  OllamaClient(base_url=...)            │
                    │  DeepSeekClient(api_key=...)            │
                    │                                         │
                    │  NO retry  NO timeout  NO redaction    │
                    │  NO logging  NO trace IDs  NO cost      │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │       CLOUD / LOCAL PROVIDERS           │
                    │  OpenAI API  Anthropic API  Ollama       │
                    └─────────────────────────────────────────┘

    ┌─────────────────────────────────────────┐
    │     GOVERNED INFERENCE CONTROL PLANE     │
    │  (governed_inference/)                   │
    │                                          │
    │  Routing  Policy  Redaction  Retry        │
    │  Fallback  Cache  Ledger  Cost           │
    │  Escalation  Classification               │
    │                                          │
    │  *** NOT WIRED TO ANY CALLER ***          │
    └─────────────────────────────────────────┘

    ┌──────────────────┐  ┌──────────────────┐
    │  MODEL ROUTER    │  │  SINTRA LLM      │
    │  (local_models/) │  │  BRIDGE          │
    │                  │  │  (local_llm/)    │
    │  Separate        │  │  Separate        │
    │  routing logic   │  │  routing logic   │
    │  NO governance   │  │  NO governance   │
    └──────────────────┘  └──────────────────┘
```

---

## 4. Gap Analysis

### 4.1 Critical Gaps

| # | Gap | Impact | Affected Call Sites |
|---|---|---|---|
| G1 | No unified retry/timeout | Transient failures cause silent degradation; no recovery from rate limits | All 12+ direct SDK call sites |
| G2 | No redaction on ungoverned paths | Restricted data (SSNs, financial, legal) sent to cloud providers without classification | All direct SDK call sites |
| G3 | No structured logging | LLM failures invisible; no observability into latency, cost, token usage | All direct SDK call sites |
| G4 | No correlation/trace ID propagation | Cannot trace LLM calls across agent workflows; no end-to-end request visibility | All direct SDK call sites |
| G5 | No cost accounting | Cloud API spend untracked; no budget enforcement | All direct SDK call sites |
| G6 | Four parallel routing layers | Maintenance burden; inconsistent behavior; no single source of truth | All systems |
| G7 | Governed inference has no real providers | Control plane is architected but cannot make actual API calls | governed_inference/providers.py |
| G8 | Timeout defined in policy but not enforced | PerRequestPolicy.timeout_seconds=60 exists but router.invoke() does not apply it | governed_inference/router.py |

### 4.2 Existing Capabilities (Ready to Use)

| Capability | Location | Status |
|---|---|---|
| Provider-agnostic request/result contracts | governed_inference/contracts.py | Ready — frozen dataclasses |
| Policy framework with strictest-merge | governed_inference/policy.py | Ready |
| Data classification | governed_inference/classification.py | Ready — keyword-based, extendable |
| Redaction receipts | governed_inference/classification.py | Ready — hash-based audit |
| Route scoring (cost/reliability/health) | governed_inference/router.py | Ready |
| Retry with transient detection | governed_inference/router.py | Ready — bounded backoff |
| Fallback across providers | governed_inference/router.py | Ready |
| Circuit-breaker (reliability floor) | governed_inference/router.py | Ready |
| Exact-match cache | governed_inference/cache.py | Ready |
| Inference ledger + receipts | governed_inference/ledger.py | Ready — in-memory |
| Cost tracking | governed_inference/ledger.py | Ready |
| Escalation queue | governed_inference/escalation.py | Ready |
| Tracing model | observability/tracer.py | Ready — not wired |
| Provider shells | governed_inference/providers.py | Shells only — need real implementations |

---

## 5. Recommended Insertion Points

### 5.1 Primary Insertion Point: Governed Inference Router

The `GovernedInferenceRouter.invoke()` method is the correct single entry point for all LLM calls. It already handles routing, retry, fallback, redaction, cost accounting, and receipt generation.

**Strategy:** Implement real provider adapters that wrap the existing SDK calls, then replace direct SDK instantiation at each call site with a `router.invoke(InferenceRequest)` call.

### 5.2 Adapter Implementation Order (Highest Impact First)

| Priority | Adapter | Wraps | Call Sites Enabled |
|---|---|---|---|
| 1 | OpenAIProvider | `openai.OpenAI()` / `openai.AsyncOpenAI()` | 9 Python files |
| 2 | AnthropicProvider | `anthropic.Anthropic()` | 4 Python files |
| 3 | OllamaProvider | `local_models/ollama_client.py` | 3 Python files |
| 4 | DeepSeekProvider | `local_models/deepseek_client.py` | 1 file |

### 5.3 Trace Context Wiring Point

The `observability/tracer.py` Tracer should be injected into `GovernedInferenceRouter.invoke()` to create spans for:
- `inference.requested` → span start
- `inference.route_selected` → span tag
- `inference.attempt_started/failed` → span logs
- `inference.completed` → span finish

Trace context should propagate `request_id` as `trace_id` (or child span) and emit `x-trace-id` headers for any HTTP-based provider calls.

### 5.4 Least Disruptive Migration Path

The `local_models/model_router.py` `ModelRouter` class is the closest production consumer to the governed inference pattern. It already:
- Routes across multiple providers
- Falls back on failure
- Has task-type-based selection

The migration path is:
1. Implement real provider adapters in `governed_inference/providers.py`
2. Replace `ModelRouter._call_openai/anthropic/ollama/deepseek` with `GovernedInferenceRouter.invoke()`
3. Map `ModelRouter.TaskType` → `InferenceRequest.task_type`
4. Map `ModelRouter.RouterResult` → `InferenceResult`
5. Deprecate `ModelRouter` as a thin compatibility wrapper

This approach preserves the `ModelRouter` public API while routing all calls through the governed inference control plane.

---

## 6. Bounded Implementation Plan

### Phase 3.1 — Provider Adapter Implementation

**Scope:** Implement real network-capable provider adapters for OpenAI and Anthropic in `governed_inference/providers.py`.

| Step | Description | Files |
|---|---|---|
| 3.1.1 | Implement `OpenAIProvider` with real `invoke()` and `invoke_stream()` | governed_inference/providers.py |
| 3.1.2 | Implement `AnthropicProvider` with real `invoke()` | governed_inference/providers.py |
| 3.1.3 | Add timeout enforcement to `GovernedInferenceRouter._invoke_provider()` | governed_inference/router.py |
| 3.1.4 | Add structured logging (stdlib `logging`) alongside ledger events | governed_inference/router.py |
| 3.1.5 | Add trace context injection (create span per invoke, propagate request_id) | governed_inference/router.py |
| 3.1.6 | Add regression tests for real provider adapters (mock SDK, verify call shape) | tests/test_governed_inference.py |
| 3.1.7 | Verify full test suite remains green (393+ tests) | — |

**Constraints:**
- Adapters must be disabled by default (configured=False) unless credentials are present
- No external API calls in CI/tests
- Preserve all existing governed_inference test contracts
- Adapter `invoke()` must map SDK responses to InferenceResult exactly

### Phase 3.2 — ModelRouter Migration

**Scope:** Route `local_models/model_router.py` through `GovernedInferenceRouter`.

| Step | Description | Files |
|---|---|---|
| 3.2.1 | Implement `OllamaProvider` adapter wrapping `OllamaClient` | governed_inference/providers.py |
| 3.2.2 | Implement `DeepSeekProvider` adapter wrapping `DeepSeekClient` | governed_inference/providers.py |
| 3.2.3 | Refactor `ModelRouter.complete()` to delegate to `GovernedInferenceRouter.invoke()` | local_models/model_router.py |
| 3.2.4 | Map `RouterResult` → `InferenceResult` compatibility wrapper | local_models/model_router.py |
| 3.2.5 | Add integration test: ModelRouter routes through governed inference | local_models/tests/test_local_models.py |
| 3.2.6 | Verify full test suite remains green | — |

### Phase 3.3 — Agent Call Site Migration

**Scope:** Replace direct SDK calls in agent files with `GovernedInferenceRouter.invoke()`.

| Step | Description | Files |
|---|---|---|
| 3.3.1 | Migrate `agents/chat/chat_agent.py` (4 call sites, includes streaming) | agents/chat/chat_agent.py |
| 3.3.2 | Migrate `agents/nova/nova_agent.py` (1 call site) | agents/nova/nova_agent.py |
| 3.3.3 | Migrate `agents/sigma/sigma_agent.py` (1 call site) | agents/sigma/sigma_agent.py |
| 3.3.4 | Migrate `agents/zero/zero_agent.py` (1 call site) | agents/zero/zero_agent.py |
| 3.3.5 | Add agent-level tests verifying governance (classification, policy, retry) | agents/*/tests/ |
| 3.3.6 | Verify full test suite remains green | — |

### Phase 3.4 — Remaining Call Site Migration

**Scope:** Migrate RAG, multimodal, claude_code, integrations, and phase17 call sites.

| Step | Description | Files |
|---|---|---|
| 3.4.1 | Migrate `rag/rag_pipeline.py` and `rag/embedder.py` (AsyncOpenAI) | rag/ |
| 3.4.2 | Migrate `multimodal/document_vision.py` and `multimodal/audio_transcription.py` | multimodal/ |
| 3.4.3 | Migrate `claude_code/legal_code_assistant.py`, `engine.py`, `code_generator.py` | claude_code/ |
| 3.4.4 | Migrate `integrations/airtable_crm/crm_manager.py` | integrations/ |
| 3.4.5 | Migrate `phase17/llm_wiring/llm_executor.py` | phase17/ |
| 3.4.6 | Migrate `developer_experience/model_playground.py` | developer_experience/ |
| 3.4.7 | Verify full test suite remains green | — |

### Phase 3.5 — Deprecation and Consolidation

**Scope:** Deprecate parallel routing layers, consolidate to single governed inference path.

| Step | Description | Files |
|---|---|---|
| 3.5.1 | Deprecate `SintraLLMBridge` as thin wrapper over `GovernedInferenceRouter` | local_llm/sintra_llm_bridge.py |
| 3.5.2 | Deprecate `LLMGateway` (phase17) as thin wrapper | phase17/llm_wiring/llm_executor.py |
| 3.5.3 | Document migration guide for future call sites | docs/ |
| 3.5.4 | Final certification: verify no direct SDK calls remain (except in provider adapters) | — |

---

## 7. Risk Assessment

| Risk | Mitigation |
|---|---|
| Provider adapter bugs break existing agent behavior | Phase 3.3 migrates one agent at a time with full test suite verification |
| Timeout enforcement changes behavior | Default timeout matches existing SDK defaults (60s); configurable via policy |
| Classification false positives block legitimate requests | Classification currently classifies as UNKNOWN (most permissive); tuning is a separate workstream |
| Migration introduces latency from router overhead | Router is in-process; overhead is negligible (microseconds for policy check) |
| Streaming support gap | Phase 3.3.1 addresses chat_agent streaming via `invoke_stream()` |

---

## 8. Out of Scope for Phase Three

- Semantic cache (requires embedding model; deferred)
- Content-level PII redaction (classification gates routing; content transformation is a separate concern)
- Alembic or migration tooling changes
- Portal schema reconciliation (DAI-2026-07-27-01)
- Agent Zero Docker container changes
- New provider integrations (Groq, Gemini, Mistral shells exist; configuration is operational, not engineering)
- Prompt engineering or template standardization

---

## 9. Dependencies

| Dependency | Status |
|---|---|
| `openai` Python SDK | Already in pyproject.toml |
| `anthropic` Python SDK | Already in pyproject.toml |
| `governed_inference/` package | Already committed, tested, frozen contracts |
| `observability/tracer.py` | Already committed, tested, ready to wire |
| Full test suite (393 tests) | Green — must remain green throughout |

---

## 10. Discovery Verdict

The repository has a well-architected but **unwired** inference control plane. The primary work is not architectural design but **implementation and wiring**: build real provider adapters, enforce timeout, add structured logging and trace context, then migrate call sites one at a time with full test suite verification at each step.

The recommended approach mirrors Phase Two's Option C: bounded scope, additive changes, reversibility at each step, and certification before progression.

**Recommended next step:** Authorize Phase 3.1 — Provider Adapter Implementation, starting with the OpenAI provider adapter and timeout enforcement in the router.

---

## References

- `governed_inference/AGENTS.md` — package DOX contract
- `governed_inference/contracts.py` — frozen inference contracts
- `governed_inference/providers.py` — provider adapter shells
- `governed_inference/router.py` — GovernedInferenceRouter
- `governed_inference/policy.py` — route denial and policy merge
- `governed_inference/classification.py` — data classification and redaction receipts
- `governed_inference/ledger.py` — inference ledger and receipts
- `observability/tracer.py` — distributed tracing model
- `local_models/model_router.py` — ModelRouter (production routing layer)
- `local_llm/sintra_llm_bridge.py` — SintraLLMBridge (production LLM bridge)
- `phase17/llm_wiring/llm_executor.py` — LLMGateway (phase 17C)
- `governance/blackstone/checkpoints/phase-two-database-stabilization.md` — Phase Two closure checkpoint