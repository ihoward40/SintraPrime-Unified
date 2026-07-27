# Governance Checkpoint — Phase 3.3.1 Chat Agent Migration

**Ratified under:** Blackstone Governance Library GB-1 (frozen baseline)
**Checkpoint ID:** GC-2026-07-27-05
**Status:** Phase 3.3.1 CLOSED
**Closed by:** Hermes Agent on behalf of Isiah Howard
**Date:** 2026-07-27
**Baseline commit:** 8f8dbcadb1b50ed3f0b3bbe7cef54abebb882c67
**Closure commit:** 44d5afc43d0344586f849825ffdf909eb6932a96

---

## Phase 3.3.1 Closure Evidence

| Criterion | Evidence | Result |
|---|---|---|
| Ruff | `.venv/Scripts/python -m ruff check . --quiet` | Clean |
| Full test suite | `.venv/Scripts/python -m pytest --tb=short -q -o addopts=` | 448 passed, 2 warnings |
| Existing chat agent tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent.py -q` | 71/71 PASS |
| New governed routing tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent_governed.py -q` | 6/6 PASS |
| Smoke lane | `.venv/Scripts/python scripts/smoke/e2e_skills_smoke.py` | PASS |
| Public API preserved | `agents/chat/tests/test_chat_agent.py` | PASS |
| Legacy fallback preserved | `agents/chat/chat_agent.py` | PASS |
| Exactly one production call path migrated | git diff verification | CONFIRMED (`_get_llm_response` only) |
| Working tree | `git status --porcelain=v1` | Clean after commit |

---

## Phase 3.3.1 Deliverables

| Deliverable | Path |
|---|---|
| Chat Agent migration | `agents/chat/chat_agent.py` |
| Regression tests | `agents/chat/tests/test_chat_agent_governed.py` |
| Agent DOX contract | `agents/chat/AGENTS.md` |
| Phase 3.3.1 Certification Report | `artifacts/phase_3_3_1_chat_agent_certification.md` |
| Governance Checkpoint | This document |

---

## Architecture Summary

Phase 3.3.1 migrated the first production agent call site onto the governed inference control plane:

- **Chat Agent (`ChatAgent`)**: The primary conversational response path `_get_llm_response()` now delegates to `GovernedInferenceRouter.invoke()`. The router is constructed lazily and contains an `OpenAIProvider` using the agent's configured model and API key.
- **Policy alignment**: The governed policy permits paid cloud routes when the OpenAI key is present and does not require per-request paid approval, matching legacy behavior.
- **Result mapping**: `InferenceResult.content` is returned to the caller, and `InferenceResult.usage["total_tokens"]` is accumulated into the session token count.
- **Legacy fallback**: Direct OpenAI SDK invocation remains in `_get_llm_response` for unexpected router failures. The no-key fallback and rule-based responses are unchanged.

---

## Progression Log

| Step | Action | Date |
|---|---|---|
| 1 | Phase Zero: Repository discovery and preservation | 2026-07-27 |
| 2 | Phase One: Verification and smoke infrastructure | 2026-07-27 |
| 3 | Phase 1.5: CI production certification | 2026-07-27 |
| 4 | Phase Two: Database stabilization (Option C) | 2026-07-27 |
| 5 | Phase 3.0: LLM reliability inventory and gap analysis | 2026-07-27 |
| 6 | Phase 3.1: Provider adapter implementation — CLOSED | 2026-07-27 |
| 7 | Phase 3.2: ModelRouter migration — CLOSED | 2026-07-27 |
| 8 | Phase 3.3.1: Chat Agent call site migration — CLOSED | 2026-07-27 |

---

## Next Action

Phase 3.3.2 — Next Agent Call Site Migration: Select the next lowest-risk agent (`sigma`, `zero`, or `nova`) based on dependency analysis and migrate exactly one production LLM call path.

---

## References

- `artifacts/phase_3_3_1_chat_agent_certification.md` — full certification report
- `governance/blackstone/checkpoints/phase-3.2-modelrouter-migration.md` — prior checkpoint
- `agents/chat/AGENTS.md` — agent DOX contract
- `governed_inference/AGENTS.md` — package DOX contract
- `local_models/AGENTS.md` — local_models DOX contract
