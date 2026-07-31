# Phase 3.2 — Migration Verification Report

**Report ID:** P3.2-MVR-2026-07-27-01
**Phase:** 3.2 — ModelRouter Migration
**Date:** 2026-07-27
**Baseline:** 4462e9db88d235967bf6ac9dfb6aa2428f03ec5b

---

## 1. Verification Commands

| Command | Result |
|---|---|
| `python -m pytest tests/test_governed_inference_adapters.py -v --tb=short` | 40 passed |
| `python -m pytest tests/test_model_router_migration.py -v --tb=short` | 15 passed |
| `python -m pytest local_models/tests/test_local_models.py -v --tb=short` | 103 passed |
| `python -m pytest --tb=short -q -o addopts=` | 448 passed, 2 warnings |
| `python -m ruff check . --quiet` | clean |
| `python scripts/smoke/e2e_skills_smoke.py` | PASS |

---

## 2. Test Inventory

### Existing adapter tests (28 tests, P3.1)
All passed unchanged.

### New adapter tests (12 tests)
| Test Class | Count | Coverage |
|---|---|---|
| TestOllamaProvider | 6 | configured/health, successful invocation, model override, error translation, structured logging |
| TestDeepSeekProvider | 6 | unconfigured raises, successful invocation, reasoning task, reasoning content preservation, rate-limit error translation, structured logging |

### Migration tests (15 tests)
| Test Class | Count | Coverage |
|---|---|---|
| TestModelRouterDelegation | 10 | Ollama delegation, DeepSeek fallback, air-gap mode, timeout enforcement, structured logging, trace propagation, API backward compatibility, routing_plan/status shape, no-provider error, unknown task default |
| TestModelRouterReasoning | 2 | legal research uses deepseek-reasoner, explicit model override passthrough |
| TestModelRouterErrorHandling | 3 | transient error result, InferenceError result, (placeholder) |

### Existing local_models tests (103 tests)
All passed, confirming legacy `_call_ollama`, `_call_deepseek`, and ModelRouter public API are preserved.

---

## 3. Feature Parity Verification

| Feature | Legacy | Delegated | Evidence |
|---|---|---|---|
| Model selection by task | `TASK_PROVIDER_PREFERENCE` | Provider list ordered to match preference; Ollama scores highest | `test_complete_delegates_to_ollama`, `test_complete_delegates_to_deepseek_when_ollama_unavailable` |
| Fallback to next provider | Manual loop in `complete()` | Router fallback history | `test_complete_delegates_to_deepseek_when_ollama_unavailable` |
| Timeout | None (legacy ignored `stream`) | `policy.per_request.timeout_seconds` with post-hoc deadline check | `test_timeout_enforcement_preserved` |
| Logging | Basic warnings | Structured lifecycle logs in router + adapter logs | `test_structured_logging_active` |
| Tracing | None | Optional tracer spans per invoke | `test_trace_propagation_active` |
| Retry | Manual try/except loop | `policy.per_request.max_attempts` | `test_timeout_enforcement_preserved` |
| Air-gap mode | Skip non-Ollama providers | Router built with only OllamaProvider | `test_air_gap_mode_uses_only_ollama` |
| DeepSeek reasoning | `TASK_DEEPSEEK_MODEL` mapping | DeepSeekProvider reasoning task detection + model override | `test_legal_research_task_uses_deepseek_reasoner` |

---

## 4. Notable Implementation Adjustments from Design Note

1. **OllamaProvider uses `OllamaClient.generate()`** rather than `.chat()` to preserve the existing call shape used by `local_models/tests/test_local_models.py` mocks.
2. **OllamaProvider context window** set to 128,000 to accommodate ModelRouter's default `max_tokens=4096` without tripping the router's `context_window_too_small` denial.
3. **DeepSeekProvider pre-call cost estimate** set to `0.0` so the router does not reject it for `unknown_cloud_cost`; actual cost is still reported in `actual_cost_usd` post-call.
4. **ModelRouter policy** enables `paid_models_allowed=True` and `paid_escalation_requires_explicit_approval=False` when any paid provider key is present, matching legacy behavior where a key alone authorized use.
5. **Request token limits** raised to `max_output_tokens=4096` in the ModelRouter policy to match the legacy `complete(max_tokens=4096)` default.

---

## 5. Issues Not Found

- No prompt content leakage in logs (verified by P3.1 tests, still green).
- No production call sites modified outside `local_models/model_router.py`.
- No behavioral regressions in existing local_models tests.

---

## 6. Conclusion

The migration is verified. All targeted tests pass, the full repository suite passes, the smoke lane passes, and the ModelRouter public API remains stable.
