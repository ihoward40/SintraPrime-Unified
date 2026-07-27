# agents/sigma — SintraPrime Sigma Agent

## Purpose

Owns the Sigma Agent: a mandatory CI/CD gate guardian that runs test suites, enforces coverage thresholds, performs security scans, runs type checks, and produces gate reports for pull requests.

## Ownership

- `agents/sigma/sigma_agent.py` — core gate agent
- `agents/sigma/ci_enforcer.py` — CI hook and workflow templates
- `agents/sigma/__init__.py` — package docstring
- `agents/sigma/tests/test_sigma_agent_governed.py` — governed inference routing regression tests
- `tests/test_sigma_agent_governed.py` — CI-visible wrapper for the governed tests

## Local Contracts

- Public API stability: `SigmaAgent.run_test_suite()`, `enforce_coverage_threshold()`, `run_security_scan()`, `enforce_type_checking()`, `generate_gate_report()`, `gate_pull_request()`, and merge actions must remain backward compatible.
- The AI Code Review section of `generate_gate_report()` routes through `GovernedInferenceRouter` when a PR diff is provided and an OpenAI API key is present (or when a router is injected).
- The legacy direct OpenAI SDK path remains as a fallback until an explicit retirement phase.
- No real external API calls are made in tests.

## Work Guidance

- When modifying the AI review path, update both the governed route and the legacy fallback.
- Keep `InferenceRequest` mapping consistent with other agents:
  - `task_type="pr_review"`
  - `capability="reasoning"`
  - `data_classification=DataClassification.PUBLIC`
  - `quality_floor=QualityFloor.STANDARD`
- Preserve the gate report markdown shape: the AI review section must remain optional and appear after the standard sections.
- Add regression tests for routing changes; keep existing `tests/test_sigma_agent.py` green.

## Verification

- Run `python -m pytest tests/test_sigma_agent.py -q` after any change to Sigma Agent behavior.
- Run `python -m pytest tests/test_sigma_agent_governed.py -q` after changing governed inference routing.
- Run `python -m pytest agents/sigma/tests/test_sigma_agent_governed.py -q` for local development.
- Run the full suite (`python -m pytest --tb=short -q -o addopts=`) before certification.
- Run the smoke lane (`python scripts/smoke/e2e_skills_smoke.py`) before certification.

## Child DOX Index

*(None — modules are leaf modules.)*
