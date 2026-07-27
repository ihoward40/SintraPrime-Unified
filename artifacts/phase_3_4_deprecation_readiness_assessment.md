# Governed Inference Deprecation Readiness Assessment

**Report ID:** P3.4-DEPRECATION-2026-07-27-01
**Phase:** 3.4 — Governance & Reliability Consolidation
**Date:** 2026-07-27
**Certified by:** Hermes Agent on behalf of Isiah Howard
**Baseline commit:** 86c1ac3eaed9fcecdde877975eddc337d4e29de2

---

## 1. Purpose

Identify duplicate or legacy routing logic that is now a candidate for deprecation, and assess whether each candidate is ready for removal. **No code is removed in this phase.** This assessment informs a future retirement phase.

---

## 2. Deprecation Candidates

### Candidate 1: `local_models/model_router.py` legacy `_call_*` methods

| Attribute | Value |
|---|---|
| Paths | `local_models/model_router.py:_call_ollama`, `_call_deepseek`, `_call_openai`, `_call_anthropic` |
| Status | Internal safety net only |
| Used by `complete()`? | No — `complete()` delegates to `GovernedInferenceRouter` |
| External callers | None identified in current tests or default CI lanes |
| Readiness | **High** |

**Rationale for deprecation:** These methods duplicate provider logic that now lives in `governed_inference/adapters.py`. `complete()` no longer calls them.

**Blockers:**
- No explicit retirement phase has been authorized.
- Need confirmation that no production service calls `_call_*` directly.

**Recommended action:** Add a deprecation warning and schedule removal in a dedicated retirement phase after verifying no direct callers.

---

### Candidate 2: Legacy fallback methods inside migrated agents

| Attribute | Value |
|---|---|
| Paths | `agents/chat/chat_agent.py` legacy branch, `agents/zero/zero_agent.py:_legacy_llm_fix_code`, `agents/sigma/sigma_agent.py:_legacy_ai_review` |
| Status | Fallback paths inside migrated agents |
| Triggered when? | Governed router raises an unexpected exception or is unavailable |
| Readiness | **Medium** |

**Rationale for deprecation:** Once the governed router has proven reliable across all error conditions, these fallback paths can be retired.

**Blockers:**
- Migration rules require keeping legacy code available until certification of a retirement phase.
- Need confidence that `GovernedInferenceRouter` handles the same exceptions the legacy code handled (network errors, authentication, timeouts, malformed responses).

**Recommended action:** Run a retirement phase that removes one fallback at a time, with targeted error-injection tests.

---

### Candidate 3: `local_llm/sintra_llm_bridge.py` cloud chat

| Attribute | Value |
|---|---|
| Paths | `local_llm/sintra_llm_bridge.py:_cloud_chat`, `_openai_chat`, `_claude_chat` |
| Status | Active alternate routing layer |
| Readiness | **Low** |

**Rationale for deprecation:** Implements its own OpenAI/Anthropic routing, overlapping with `GovernedInferenceRouter`.

**Blockers:**
- Not yet migrated onto the governed control plane.
- Async API shape differs from the current sync router; requires either an async adapter or a sync invocation wrapper.
- Used by `sintra_llm_bridge.py` chat paths that may have downstream consumers.

**Recommended action:** Migrate first; deprecate only after migration and consumer verification.

---

### Candidate 4: `phase17/llm_wiring/llm_executor.py`

| Attribute | Value |
|---|---|
| Paths | `phase17/llm_wiring/llm_executor.py` |
| Status | Separate legacy LLM gateway |
| Readiness | **Low** |

**Rationale for deprecation:** A separate gateway with its own provider abstraction, stats, and mock responses duplicates governed inference responsibilities.

**Blockers:**
- Different request/response contract (`LLMRequest`, `LLMResponse`).
- May be used by phase17 modules outside the default CI lane.
- No evidence of current migration effort or tests for this layer.

**Recommended action:** Map `LLMProvider` enum to `InferenceProvider` adapters, or retire phase17 consumers first.

---

### Candidate 5: `developer_experience/model_playground.py` model clients

| Attribute | Value |
|---|---|
| Paths | `developer_experience/model_playground.py:OpenAIClient`, `AnthropicClient`, `DeepSeekClient` |
| Status | Interactive dev tool |
| Readiness | **N/A** |

**Rationale for deprecation:** These clients are intentionally independent so users can compare models side-by-side. They are not production routing paths.

**Blockers:**
- Dev-experience purpose; migration value is low.
- Product decision required if playground should be governed.

**Recommended action:** Keep as-is unless the model playground becomes a production feature.

---

## 3. Deprecation Readiness Summary

| Candidate | Readiness | Blockers | Next Step |
|---|---|---|---|
| ModelRouter legacy `_call_*` | High | Authorization + caller audit | Schedule retirement phase |
| Agent legacy fallbacks | Medium | Program-wide retirement policy | Error-injection retirement phase |
| SintraLLMBridge cloud chat | Low | Not migrated, async mismatch | Migrate first |
| phase17 LLM executor | Low | Different contract, phase17 consumers | Map or retire consumers first |
| Dev model playground | N/A | Dev tool scope | No action unless productized |

---

## 4. Risk Notes

- Removing legacy fallbacks before the router has been exercised against all failure modes would reintroduce ungoverned paths on failure.
- `local_llm/sintra_llm_bridge.py` and `phase17/llm_wiring/llm_executor.py` are not candidates for deprecation until they are first migrated or their consumers retired.
- Nova's dynamic execution path is not a deprecation candidate; it is a deferred migration item requiring new controls.

---

## 5. References

- `artifacts/phase_3_4_migration_coverage_report.md` — coverage report
- `artifacts/nova_agent_migration_deferred_plan.md` — Nova deferral plan
- `governed_inference/AGENTS.md` — package DOX contract
- `local_models/AGENTS.md` — ModelRouter DOX contract
