# Phase 3.3.1 — Chat Agent Call Site Migration

**Report ID:** P3.3.1-CERT-2026-07-27-01
**Phase:** 3.3.1 — Agent Call Site Migration (Chat Agent)
**Status:** CLOSED
**Certified by:** Hermes Agent on behalf of Isiah Howard
**Date:** 2026-07-27
**Baseline commit:** 8f8dbcadb1b50ed3f0b3bbe7cef54abebb882c67
**Closure commit:** 44d5afc43d0344586f849825ffdf909eb6932a96

---

## 1. Authorization

Phase 3.3 was formally authorized after Phase 3.2 closure. Scope for P3.3.1:

- Migrate the Chat Agent's primary LLM call path (`ChatAgent._get_llm_response`) to route through `GovernedInferenceRouter`.
- Preserve the legacy direct OpenAI SDK fallback path until certification.
- Preserve all existing public interfaces (`chat()`, `chat_stream()`, session management, tools, statistics, persistence).
- Add regression tests that verify delegation without requiring network calls.

Non-goals respected: streaming path, tool handlers, and other agent call sites were not modified.

---

## 2. Verification Summary

| Verification | Command | Result |
|---|---|---|
| Ruff lint | `.venv/Scripts/python -m ruff check . --quiet` | Clean |
| Full test suite | `.venv/Scripts/python -m pytest --tb=short -q -o addopts=` | **448 passed, 2 warnings** |
| Existing chat agent tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent.py -q` | 71/71 PASS |
| New governed routing tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent_governed.py -q` | 6/6 PASS |
| Smoke lane | `.venv/Scripts/python scripts/smoke/e2e_skills_smoke.py` | PASS |
| Working tree | `git status --porcelain=v1` | Clean after commit |

---

## 3. Deliverables

| Deliverable | Path | Status |
|---|---|---|
| Chat Agent migration | `agents/chat/chat_agent.py` | COMPLETE |
| Regression tests | `agents/chat/tests/test_chat_agent_governed.py` | COMPLETE |
| Agent DOX update | `agents/chat/AGENTS.md` | COMPLETE |
| Phase 3.3.1 Certification Report | This document | COMPLETE |
| Updated Governance Checkpoint | `governance/blackstone/checkpoints/phase-3.3.1-chat-agent-migration.md` | COMPLETE |

---

## 4. Migration Details

### Call Path Migrated

- `ChatAgent._get_llm_response(messages, session)` now delegates to `GovernedInferenceRouter.invoke()` when an OpenAI API key is present.
- The router is built lazily in `_ensure_governed_router()` and contains an `OpenAIProvider` configured with the same model and API key used by the legacy path.
- `InferenceRequest` is constructed with:
  - `task_type="chat"`
  - `capability="drafting"`
  - `data_classification=DataClassification.PUBLIC`
  - `quality_floor=QualityFloor.STANDARD`
  - `max_output_tokens=2000`, `temperature=0.7`
  - `model_override` set to `self.model` when not `"auto"`

### Result Mapping

- `InferenceResult.content` is returned as the response string.
- `InferenceResult.usage["total_tokens"]` is added to the session token count, preserving the existing accounting behavior.

### Fallback Behavior

- If no OpenAI API key is set, the existing rule-based fallback is used.
- If the governed router raises `InferenceError`, the agent returns an error message in the same shape as the legacy error path.
- If the governed router raises an unexpected exception, the legacy direct OpenAI SDK path is attempted as a safety net.

---

## 5. Feature Parity

| Criterion | Status |
|---|---|
| Public `chat()` interface stable | PASS |
| Session message history preserved | PASS |
| Token counting preserved | PASS |
| System prompt customization preserved | PASS |
| Autonomous mode prompt injection preserved | PASS |
| God mode prompt injection preserved | PASS |
| Error message shape preserved | PASS |
| Fallback when no API key | PASS |
| Legacy OpenAI SDK path still available | PASS |
| Governed router logs emitted | PASS |

---

## 6. Files Changed

| File | Change |
|---|---|
| `agents/chat/chat_agent.py` | Added governed inference imports, `_build_governed_router`, `_ensure_governed_router`, `_build_inference_request`, and routed `_get_llm_response` through `GovernedInferenceRouter` with legacy fallback |
| `agents/chat/tests/test_chat_agent_governed.py` | New regression tests verifying delegation, lazy router construction, error handling, fallback, and message preservation |
| `agents/chat/AGENTS.md` | New DOX contract documenting purpose, ownership, local contracts, work guidance, verification, and child index |
| `governance/blackstone/checkpoints/phase-3.3.1-chat-agent-migration.md` | New governance checkpoint |
| `artifacts/last_smoke_*` | Smoke lane artifacts refreshed |

---

## 7. Strategic Observation

With the Chat Agent migrated, the governed inference control plane now serves an interactive production agent in addition to `ModelRouter`. The legacy path remains available as a safety net. The incremental cadence (one agent per certification cycle) is maintained.

---

## 8. Final Certification Verdict

**Phase 3.3.1: CLOSED**

All success criteria satisfied. The Chat Agent's primary LLM call path routes through `GovernedInferenceRouter`. Public behavior is preserved. The full regression suite (448 tests), existing chat agent tests (71 tests), new governed routing tests (6 tests), and smoke lane all pass. Governance checkpoint and agent DOX are updated.
