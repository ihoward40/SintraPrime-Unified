# agents/zero — SintraPrime Zero Agent

## Purpose

Owns the Zero Agent: an autonomous self-healing maintenance agent that scans the repository for broken imports and failing tests, generates candidate fixes, applies patches with rollback support, and reports repository health.

## Ownership

- `agents/zero/zero_agent.py` — core self-healing agent
- `agents/zero/health_monitor.py` — health monitoring primitives
- `agents/zero/__init__.py` — public exports
- `agents/zero/tests/test_zero_agent_governed.py` — governed inference routing regression tests
- `tests/test_zero_agent_governed.py` — CI-visible wrapper for the governed tests

## Local Contracts

- All auto-applied patches must be revertible via `rollback_patch()`.
- No real external API calls are made in tests.
- The LLM-based fix path in `generate_fix_patch()` routes through `GovernedInferenceRouter` when an OpenAI API key is present or when a router is injected.
- The legacy direct OpenAI SDK path remains as a fallback until an explicit retirement phase.
- Rule-based fallback (e.g., placeholder fixture generation) is preserved.

## Work Guidance

- When modifying patch generation, update both the governed route and the legacy fallback.
- Keep `InferenceRequest` mapping consistent with other agents:
  - `task_type="code_repair"`
  - `capability="coding"`
  - `data_classification=DataClassification.PUBLIC`
  - `quality_floor=QualityFloor.STANDARD`
- Markdown stripping of LLM output must remain identical to the legacy behavior.
- Add regression tests for routing changes; keep existing `tests/test_zero_agent.py` green.

## Verification

- Run `python -m pytest tests/test_zero_agent.py -q` after any change to Zero Agent behavior.
- Run `python -m pytest tests/test_zero_agent_governed.py -q` after changing governed inference routing.
- Run `python -m pytest agents/zero/tests/test_zero_agent_governed.py -q` for local development.
- Run the full suite (`python -m pytest --tb=short -q -o addopts=`) before certification.
- Run the smoke lane (`python scripts/smoke/e2e_skills_smoke.py`) before certification.

## Child DOX Index

*(None — modules are leaf modules.)*
