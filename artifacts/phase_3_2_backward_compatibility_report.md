# Phase 3.2 — Backward Compatibility Report

**Report ID:** P3.2-BC-2026-07-27-01
**Phase:** 3.2 — ModelRouter Migration
**Date:** 2026-07-27

---

## 1. Public API Inventory

`local_models/model_router.py` exposes the following public surface. All signatures are unchanged.

| Symbol | Type | Status |
|---|---|---|
| `TaskType` | Enum | Unchanged |
| `Provider` | Enum | Unchanged |
| `RouterResult` | Dataclass | Unchanged |
| `TASK_PROVIDER_PREFERENCE` | Dict | Unchanged |
| `TASK_LOCAL_MODEL` | Dict | Unchanged |
| `TASK_DEEPSEEK_MODEL` | Dict | Unchanged |
| `ModelRouter.__init__` | Constructor | Signature unchanged |
| `ModelRouter.complete` | Method | Signature unchanged |
| `ModelRouter.status` | Method | Signature unchanged |
| `ModelRouter.routing_plan` | Method | Signature unchanged |
| `ModelRouter.available_providers` | Method | Signature unchanged |
| `ModelRouter.__repr__` | Method | Unchanged |

---

## 2. `ModelRouter.complete()` Signature

```python
def complete(
    self,
    prompt: str,
    model: str = "auto",
    task: Union[str, TaskType] = TaskType.GENERAL,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
) -> RouterResult:
```

No parameter was added, removed, or had its default changed.

---

## 3. `RouterResult` Shape

```python
@dataclass
class RouterResult:
    content: str
    provider: Provider
    model: str
    task_type: TaskType
    latency_s: float
    usage: Dict[str, Any]
    cost_usd: float
    thinking: Optional[str]
    error: Optional[str]
```

All fields are populated by the new delegated path:
- `content` from `InferenceResult.content`
- `provider` mapped from `InferenceResult.provider`
- `model` from `InferenceResult.model`
- `task_type` preserved from the original request
- `latency_s` measured around the governed router call
- `usage` copied from `InferenceResult.usage`
- `cost_usd` from `actual_cost_usd` or `estimated_cost_usd`
- `thinking` reserved for future reasoning-content plumbing
- `error` populated when the governed router raises `InferenceError`

---

## 4. Legacy Methods Preserved

The following internal methods remain in `ModelRouter` and are still importable/callable, though `complete()` no longer exercises them:

- `_call_ollama`
- `_call_deepseek`
- `_call_openai`
- `_call_anthropic`
- `_call_provider`
- `_select_provider`
- `_is_available`
- `_check_provider`
- `_get_ollama`
- `_get_deepseek`

They are retained as a safety net per the phase's explicit non-goals.

---

## 5. Behavioral Compatibility Evidence

| Test | File | Result |
|---|---|---|
| test_complete_uses_ollama_when_available | local_models/tests/test_local_models.py | PASS |
| test_complete_falls_back_when_ollama_model_missing | local_models/tests/test_local_models.py | PASS |
| test_complete_returns_error_when_no_provider | local_models/tests/test_local_models.py | PASS |
| test_ollama_failure_falls_to_deepseek | local_models/tests/test_local_models.py | PASS |
| test_all_providers_fail_returns_error_result | local_models/tests/test_local_models.py | PASS |
| test_routing_plan | local_models/tests/test_local_models.py | PASS |
| test_status | local_models/tests/test_local_models.py | PASS |
| test_air_gap_blocks_cloud_providers | local_models/tests/test_local_models.py | PASS |
| test_deepseek_available_when_key_set | local_models/tests/test_local_models.py | PASS |
| test_model_router_api_backward_compatible | tests/test_model_router_migration.py | PASS |
| test_routing_plan_shape_unchanged | tests/test_model_router_migration.py | PASS |
| test_status_shape_unchanged | tests/test_model_router_migration.py | PASS |

---

## 6. Call Site Impact

Search of the repository shows `ModelRouter` is used by:
- `local_models/__init__.py` (re-export)
- `local_models/local_models_api.py` (FastAPI router)
- `local_models/tests/test_local_models.py` (tests)

No call site required modification. The `local_models_api.py` import and usage remain valid because the public API is unchanged.

---

## 7. Conclusion

Backward compatibility is preserved. The `ModelRouter` public contract, method signatures, and return shape are unchanged. Existing tests that exercise the public API pass without modification. Legacy provider call paths remain in the file but are no longer exercised by `complete()`.
