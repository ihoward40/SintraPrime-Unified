# parl — Parallel Agent Orchestration

## Purpose

Owns SintraPrime's central multi-agent orchestration, experience replay, policy synchronization, reward logic, Principal Command admission control, GOD-0 Principal Brief, and bounded GOD-1 swarm planning.

## Ownership

- `orchestrator.py` — base PARL task decomposition and parallel execution
- `governed_orchestrator.py` — governed facade and scoped OmniBrain context injection
- `god_mode.py` — Principal Command / God Mode session tiers and admission policy
- `principal_brief.py` — read-only GOD-0 Principal Brief and Mission Control snapshot contract
- `swarms.py` — GOD-1 Council, Research, and Build swarm templates
- `agent_adapters.py` — runtime-specific agent adapters
- `experience_replay.py`, `reward_engine.py`, `policy_sync.py` — PARL learning infrastructure
- `tests/` — PARL, Principal Command, context, brief, and swarm behavioral tests

## Local Contracts

- God Mode belongs to the authenticated Principal, never to a model or subagent.
- `GovernedPARLOrchestrator` is the preferred entrypoint for new orchestration work.
- Every governed subtask receives a scope-filtered OmniBrain context package before worker execution.
- Context retrieval does not grant action authority and must preserve memory provenance.
- Missing `risk_level` remains ordinary orchestration for backward compatibility.
- `write`, `external`, and `critical` risk levels require an authenticated, non-expired Principal session at the required tier.
- External and critical admission never substitutes for downstream approval gateways.
- `disable_governance`, `self_elevate`, `reveal_secrets`, `export_raw_credentials`, and `bypass_approval` are non-delegable capabilities.
- Critical administration requires step-up verification.
- GOD-0 Principal Brief and Mission Control are read-only aggregation surfaces.
- GOD-1 Council, Research, and Build swarms are orchestration-only and do not receive external-write authority.
- Agent compromise must remain compartmentalized; no worker receives global credentials merely because a Principal session exists.

## Work Guidance

- Prefer extending the governed facade over modifying base PARL execution semantics when the change concerns authority, context, or approval.
- Keep Principal Command provider/model neutral.
- Add a behavioral test for every new tier, risk class, non-delegable capability, approval rule, or swarm mode.

## Verification

Run:

`pytest parl/tests/test_god_mode.py parl/tests/test_governed_orchestrator.py parl/tests/test_principal_brief_and_swarms.py parl/tests/test_parl.py memory/tests/test_context_packages.py memory/tests/test_omnibrain_projection.py`

## Child DOX Index

*(No child AGENTS.md files yet.)*
