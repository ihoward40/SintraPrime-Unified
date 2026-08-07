# parl — Parallel Agent Orchestration

## Purpose

Owns SintraPrime's central multi-agent orchestration, experience replay, policy synchronization, reward logic, and Principal Command admission control.

## Ownership

- `orchestrator.py` — base PARL task decomposition and parallel execution
- `governed_orchestrator.py` — governed facade for SintraPrime-wide agent execution
- `god_mode.py` — Principal Command / God Mode session tiers and admission policy
- `agent_adapters.py` — runtime-specific agent adapters
- `experience_replay.py`, `reward_engine.py`, `policy_sync.py` — PARL learning infrastructure
- `tests/` — PARL and Principal Command behavioral tests

## Local Contracts

- God Mode belongs to the authenticated Principal, never to a model or subagent.
- `GovernedPARLOrchestrator` is the preferred entrypoint for new orchestration work.
- Missing `risk_level` remains ordinary orchestration for backward compatibility.
- `write`, `external`, and `critical` risk levels require an authenticated, non-expired Principal session at the required tier.
- External and critical admission never substitutes for downstream approval gateways.
- `disable_governance`, `self_elevate`, `reveal_secrets`, `export_raw_credentials`, and `bypass_approval` are non-delegable capabilities.
- Critical administration requires step-up verification.
- Agent compromise must remain compartmentalized; no worker receives global credentials merely because a Principal session exists.

## Work Guidance

- Prefer extending the governed facade over modifying the base PARL execution semantics when the change concerns authority or approval.
- Keep Principal Command provider/model neutral.
- Add a behavioral test for every new tier, risk class, non-delegable capability, or approval rule.

## Verification

Run:

`pytest parl/tests/test_god_mode.py parl/tests/test_governed_orchestrator.py parl/tests/test_parl.py`

## Child DOX Index

*(No child AGENTS.md files yet.)*
