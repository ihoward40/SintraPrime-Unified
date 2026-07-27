# Phase 3.3.2 — Zero Agent Call Site Migration

**Report ID:** P3.3.2-CERT-2026-07-27-01
**Phase:** 3.3.2 — Agent Call Site Migration (Zero Agent)
**Status:** CLOSED
**Certified by:** Hermes Agent on behalf of Isiah Howard
**Date:** 2026-07-27
**Baseline commit:** 15c1cf8359b7dca5a033af965749baad27814329
**Closure commit:** b9dffc5a8c22450fb754be11f78d655411f58f67

---

## 1. Authorization

Phase 3.3.2 was formally authorized after Phase 3.3.1 closure. Scope:

- Migrate the Zero Agent's LLM-based patch generation path (`ZeroAgent.generate_fix_patch`) to route through `GovernedInferenceRouter`.
- Preserve the legacy direct OpenAI SDK fallback path until certification.
- Preserve the rule-based fallback (placeholder fixture generation).
- Preserve all existing public interfaces (`scan_import_errors`, `auto_fix_imports`, `generate_fix_patch`, `apply_patch`, `rollback_patch`, `health_report`, `run_maintenance_cycle`, scheduler lifecycle).
- Add regression tests that verify delegation without requiring network calls.

Non-goals respected: other agent call sites (`sigma`, `nova`) were not modified.

---

## 2. Selection Justification

The Agent Migration Priority Matrix ranked the remaining candidates by migration complexity, test coverage, external integrations, operational risk, rollback difficulty, and architectural benefit. **Zero Agent** was selected because it offers the best balance of low risk and meaningful architectural value:

- Single, well-contained LLM call path in `generate_fix_patch()`.
- Existing test coverage (`tests/test_zero_agent.py`: 32 tests).
- Optional OpenAI integration with existing rule-based fallback.
- Low rollback difficulty because patches are already revertible.
- Moderate architectural benefit: moves self-healing automation onto the governed control plane.

Sigma was deferred because its LLM usage is a peripheral PR review add-on. Nova was deferred because its LLM path generates and executes dynamic code, creating high operational risk.

---

## 3. Verification Summary

| Verification | Command | Result |
|---|---|---|
| Ruff lint | `.venv/Scripts/python -m ruff check . --quiet` | Clean |
| Full test suite | `.venv/Scripts/python -m pytest --tb=short -q -o addopts=` | **459 passed, 2 warnings** |
| Existing Zero Agent tests | `.venv/Scripts/python -m pytest tests/test_zero_agent.py -q` | 32/32 PASS |
| New governed routing tests (CI-visible) | `.venv/Scripts/python -m pytest tests/test_zero_agent_governed.py -q` | 5/5 PASS |
| New governed routing tests (agent-local) | `.venv/Scripts/python -m pytest agents/zero/tests/test_zero_agent_governed.py -q` | 5/5 PASS |
| Existing Chat Agent tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent.py -q` | 71/71 PASS |
| Chat governed routing tests (CI-visible) | `.venv/Scripts/python -m pytest tests/test_chat_agent_governed.py -q` | 6/6 PASS |
| Smoke lane | `.venv/Scripts/python scripts/smoke/e2e_skills_smoke.py` | PASS |
| Working tree | `git status --porcelain=v1` | Clean after commit |

---

## 4. Deliverables

| Deliverable | Path | Status |
|---|---|---|
| Agent Migration Priority Matrix | `artifacts/phase_3_3_2_agent_priority_matrix.md` | COMPLETE |
| Zero Agent migration | `agents/zero/zero_agent.py` | COMPLETE |
| Regression tests (agent-local) | `agents/zero/tests/test_zero_agent_governed.py` | COMPLETE |
| CI-visible test wrapper | `tests/test_zero_agent_governed.py` | COMPLETE |
| Zero Agent DOX update | `agents/zero/AGENTS.md` | COMPLETE |
| Agents parent DOX update | `agents/AGENTS.md` | COMPLETE |
| Chat CI-visible test wrapper | `tests/test_chat_agent_governed.py` | COMPLETE |
| Phase 3.3.2 Certification Report | This document | COMPLETE |
| Updated Governance Checkpoint | `governance/blackstone/checkpoints/phase-3.3.2-zero-agent-migration.md` | COMPLETE |

---

## 5. Migration Details

### Call Path Migrated

- `ZeroAgent.generate_fix_patch(failure)` now delegates the LLM code-fix request to `ZeroAgent._llm_fix_code()`, which uses `GovernedInferenceRouter.invoke()` when an OpenAI API key is present or when a router is injected.
- The router is built lazily in `_ensure_governed_router()` and contains an `OpenAIProvider` configured with `gpt-4o-mini`.
- `InferenceRequest` is constructed with:
  - `task_type="code_repair"`
  - `capability="coding"`
  - `data_classification=DataClassification.PUBLIC`
  - `quality_floor=QualityFloor.STANDARD`
  - `max_output_tokens=4000`, `temperature=0.1`
  - system + user messages matching the legacy prompt

### Result Mapping

- `InferenceResult.content` is converted to a string and passed through the same markdown-stripping logic (````python`, ` ``` `) that the legacy path used.
- The resulting code is returned to `generate_fix_patch`, which creates a `Patch` with the LLM-generated description.

### Fallback Behavior

- If the governed router raises `InferenceError`, the agent logs the error and falls back to rule-based fixture generation.
- If the governed router raises an unexpected exception, the legacy direct OpenAI SDK path is attempted as a safety net.
- If no OpenAI API key is set and no router is injected, `_llm_fix_code` returns `None`, and the rule-based fallback runs.

---

## 6. Feature Parity

| Criterion | Status |
|---|---|
| Public `generate_fix_patch()` interface stable | PASS |
| Patch object shape preserved | PASS |
| Rule-based fixture fallback preserved | PASS |
| Markdown stripping preserved | PASS |
| Patch rollback behavior preserved | PASS |
| Health report unaffected | PASS |
| Maintenance cycle flow unaffected | PASS |
| Legacy OpenAI SDK path still available | PASS |
| Governed router logs emitted | PASS |

---

## 7. Files Changed

| File | Change |
|---|---|
| `agents/zero/zero_agent.py` | Added governed inference imports, `_build_governed_router`, `_ensure_governed_router`, `_build_fix_patch_prompt`, `_build_fix_patch_request`, `_llm_fix_code`, `_legacy_llm_fix_code`, and routed `generate_fix_patch` through the governed router with legacy fallback |
| `agents/zero/tests/test_zero_agent_governed.py` | New regression tests verifying delegation, lazy router construction, error handling, fallback, and missing-file behavior |
| `tests/test_zero_agent_governed.py` | CI-visible wrapper re-exporting the governed tests so they run in the default lane |
| `agents/zero/AGENTS.md` | New DOX contract |
| `agents/AGENTS.md` | Updated child index |
| `tests/test_chat_agent_governed.py` | CI-visible wrapper for the Chat Agent governed tests |
| `artifacts/phase_3_3_2_agent_priority_matrix.md` | New priority matrix artifact |
| `artifacts/phase_3_3_2_zero_agent_certification.md` | This certification report |
| `governance/blackstone/checkpoints/phase-3.3.2-zero-agent-migration.md` | New governance checkpoint |
| `artifacts/last_smoke_*` | Smoke lane artifacts refreshed |

---

## 8. Strategic Observation

With the Zero Agent migrated, the governed inference control plane now serves both an interactive agent (Chat) and an autonomous maintenance agent (Zero). Both migrations preserved legacy fallbacks, public APIs, and existing tests. The incremental cadence remains intact.

---

## 9. Final Certification Verdict

**Phase 3.3.2: CLOSED**

All success criteria satisfied. The Zero Agent's LLM-based patch generation path routes through `GovernedInferenceRouter`. Public behavior is preserved. The full regression suite (459 tests), existing Zero Agent tests (32 tests), new governed routing tests (5 tests), Chat Agent tests (71 + 6 tests), and smoke lane all pass. Governance checkpoint and agent DOX are updated.
