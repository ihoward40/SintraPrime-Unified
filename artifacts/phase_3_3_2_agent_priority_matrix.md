# Agent Migration Priority Matrix — Phase 3.3.2

**Date:** 2026-07-27
**Scope:** Select the next lowest-risk production agent to migrate onto `GovernedInferenceRouter`.

---

## Candidates

| Agent | Primary LLM Call Path | Test Coverage | External Integrations | Operational Risk | Rollback Difficulty | Architectural Benefit | Recommendation |
|---|---|---|---|---|---|---|---|
| **Chat** | `_get_llm_response()` | 71 existing + 6 new | OpenAI (optional) | Low | Low | High (interactive agent) | ✅ Completed in P3.3.1 |
| **Zero** | `generate_fix_patch()` | ~35 existing (`tests/test_zero_agent.py`) | OpenAI (optional); file writes | Medium | Low | Medium (self-healing path) | ✅ Next target — best risk/benefit balance |
| **Sigma** | `generate_gate_report()` AI review section | ~25 existing (`tests/test_sigma_agent.py`) | OpenAI (optional); GitHub API | Low | Low | Low (peripheral feature) | Defer — not a core inference path |
| **Nova** | `execute_action()` dynamic handler generation | ~30 existing (`tests/test_nova_agent.py`) | OpenAI (optional); `exec()` of generated code | High | Low | High | Defer — high operational risk due to dynamic code execution |

---

## Scoring

Scale: 1 = lowest/favorable, 5 = highest/unfavorable for migration complexity and risk; 1 = lowest, 5 = highest for architectural benefit.

| Agent | Migration Complexity | Test Coverage | Operational Risk | Rollback Difficulty | Architectural Benefit | Weighted Score |
|---|---|---|---|---|---|---|
| Zero | 2 | 3 | 2 | 1 | 3 | **11** |
| Sigma | 1 | 2 | 1 | 1 | 1 | 6 |
| Nova | 3 | 2 | 5 | 1 | 4 | 15 |

Lower weighted score indicates lower overall migration risk. Zero is the clear next target.

---

## Selection Justification

**Zero Agent** is selected for Phase 3.3.2 because:

1. **Single, well-contained LLM call path** in `generate_fix_patch()`.
2. **Existing test coverage** for patch generation and health reporting.
3. **Optional OpenAI integration** — the agent already falls back to rule-based fixes when no key is present.
4. **Low rollback difficulty** — the legacy path can remain as fallback, and patches are already revertible.
5. **Moderate architectural benefit** — it moves a self-healing automation path onto the governed control plane.

**Sigma** is deferred because its LLM usage is a non-critical AI review add-on, not a core inference path. Migrating it would provide minimal architectural value.

**Nova** is deferred because its LLM path generates and `exec()`s dynamic code. The operational and security risk outweighs the benefit at this stage; it should be migrated only after the control plane has proven itself on safer agents.

---

## Next Action

Proceed with Phase 3.3.2 — Zero Agent Call Site Migration.
