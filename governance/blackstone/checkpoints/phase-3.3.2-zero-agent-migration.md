# Governance Checkpoint — Phase 3.3.2 Zero Agent Migration

**Ratified under:** Blackstone Governance Library GB-1 (frozen baseline)
**Checkpoint ID:** GC-2026-07-27-06
**Status:** Phase 3.3.2 CLOSED
**Closed by:** Hermes Agent on behalf of Isiah Howard
**Date:** 2026-07-27
**Baseline commit:** 15c1cf8359b7dca5a033af965749baad27814329
**Closure commit:** b9dffc5a8c22450fb754be11f78d655411f58f67

---

## Phase 3.3.2 Closure Evidence

| Criterion | Evidence | Result |
|---|---|---|
| Ruff | `.venv/Scripts/python -m ruff check . --quiet` | Clean |
| Full test suite | `.venv/Scripts/python -m pytest --tb=short -q -o addopts=` | 459 passed, 2 warnings |
| Existing Zero Agent tests | `.venv/Scripts/python -m pytest tests/test_zero_agent.py -q` | 32/32 PASS |
| New governed routing tests (CI-visible) | `.venv/Scripts/python -m pytest tests/test_zero_agent_governed.py -q` | 5/5 PASS |
| New governed routing tests (agent-local) | `.venv/Scripts/python -m pytest agents/zero/tests/test_zero_agent_governed.py -q` | 5/5 PASS |
| Existing Chat Agent tests | `.venv/Scripts/python -m pytest agents/chat/tests/test_chat_agent.py -q` | 71/71 PASS |
| Chat governed routing tests (CI-visible) | `.venv/Scripts/python -m pytest tests/test_chat_agent_governed.py -q` | 6/6 PASS |
| Smoke lane | `.venv/Scripts/python scripts/smoke/e2e_skills_smoke.py` | PASS |
| Agent Migration Priority Matrix | `artifacts/phase_3_3_2_agent_priority_matrix.md` | COMPLETE |
| Exactly one production call path migrated | git diff verification | CONFIRMED (`generate_fix_patch` LLM path only) |
| Public API preserved | `tests/test_zero_agent.py` | PASS |
| Legacy fallback preserved | `agents/zero/zero_agent.py` | PASS |
| Working tree | `git status --porcelain=v1` | Clean after commit |

---

## Phase 3.3.2 Deliverables

| Deliverable | Path |
|---|---|
| Agent Migration Priority Matrix | `artifacts/phase_3_3_2_agent_priority_matrix.md` |
| Zero Agent migration | `agents/zero/zero_agent.py` |
| Regression tests (agent-local) | `agents/zero/tests/test_zero_agent_governed.py` |
| CI-visible test wrapper | `tests/test_zero_agent_governed.py` |
| Zero Agent DOX contract | `agents/zero/AGENTS.md` |
| Agents parent DOX update | `agents/AGENTS.md` |
| Chat CI-visible test wrapper | `tests/test_chat_agent_governed.py` |
| Phase 3.3.2 Certification Report | `artifacts/phase_3_3_2_zero_agent_certification.md` |
| Governance Checkpoint | This document |

---

## Architecture Summary

Phase 3.3.2 migrated the second production agent call site onto the governed inference control plane:

- **Zero Agent (`ZeroAgent`)**: The LLM-based code-fix path `generate_fix_patch()` now delegates to `GovernedInferenceRouter.invoke()`. The router is constructed lazily and contains an `OpenAIProvider` using `gpt-4o-mini` and the `OPENAI_API_KEY` environment variable.
- **Policy alignment**: The governed policy permits paid cloud routes when the OpenAI key is present and does not require per-request paid approval, matching legacy behavior.
- **Result mapping**: `InferenceResult.content` is converted back to a code string and passed through the same markdown-stripping logic as the legacy path.
- **Fallback behavior**: Rule-based placeholder fixture generation remains the default fallback. The legacy direct OpenAI SDK path is retained for unexpected router failures.

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
| 9 | Phase 3.3.2: Zero Agent call site migration — CLOSED | 2026-07-27 |

---

## Next Action

Phase 3.3.3 — Next Agent Call Site Migration: Select the next lowest-risk agent from the remaining candidates (`sigma`, `nova`, and any newly discovered production consumers) based on the priority matrix criteria. Sigma is recommended next because its LLM call path is peripheral and low risk; Nova should remain deferred until the control plane has proven itself on safer agents.

---

## References

- `artifacts/phase_3_3_2_zero_agent_certification.md` — full certification report
- `artifacts/phase_3_3_2_agent_priority_matrix.md` — priority matrix
- `governance/blackstone/checkpoints/phase-3.3.1-chat-agent-migration.md` — prior checkpoint
- `agents/zero/AGENTS.md` — agent DOX contract
- `agents/chat/AGENTS.md` — Chat Agent DOX contract
- `governed_inference/AGENTS.md` — package DOX contract
