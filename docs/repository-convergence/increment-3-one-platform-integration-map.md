# Repository Convergence Increment Three — One-Platform Integration Map

**Issue:** [#378 SP-ONE-PLATFORM-CONVERGENCE-001 — unify modules and governed agent workforce](https://github.com/ihoward40/SintraPrime-Unified/issues/378)
**Baseline commit (main):** `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`
**Branch:** `cline/sp-378-one-platform-integration-map`
**Generated:** 2026-11-08
**Scope:** Documentation and planning only. No runtime, route, schema, migration, or authority changes. Inspection limited to `ihoward40/SintraPrime-Unified`; all other repositories are marked NOT INSPECTED.

This map extends Increment Two (`increment-2-architectural-map.md`, authoritative at `48e2caa7…`) to the current baseline and adds the open-PR-branch dimension required by issue #378. It covers the five areas named in the assignment: Mission Control, agents, Hermes, IKE-Bot, and Agent Commons.

## Status legend

| Label | Meaning |
|---|---|
| IMPLEMENTED ON MAIN | Verified present at baseline commit `051e2594` by file inspection |
| OPEN PR BRANCH ONLY | Exists only on an open PR branch; head SHA recorded; contents not merged |
| REFERENCED — NOT VERIFIED | Mentioned in docs/issues/PR titles but not confirmed against code |
| NOT INSPECTED | Outside this repository or otherwise not examined in this increment |

## Method

- `git log` / `git status` / `git ls-tree` / `git ls-remote` at the baseline commit.
- `gh issue view 378`, `gh issue view 243`, `gh pr list --state open --limit 100`, `gh pr view` (2026-11-08).
- File inspection of entrypoints and modules listed below; `grep` surveys for `agent_commons`, `ike-bot`, `hermes`.

---

## 1. Mission Control

**IMPLEMENTED ON MAIN**

- Entrypoint: `portal/main.py` mounts `portal/routers/mission_control.py` and `portal/routers/mission_control_commands.py` (verified at baseline).
- Services/models: `portal/services/mission_control_command_guard.py`, `mission_control_command_service.py`, `mission_control_run_control_service.py`, `permission_provisioning.py`; `portal/models/mission_control_*.py`.
- Tests: `portal/tests/test_mission_control.py`, `test_mission_control_commands.py`, `test_mission_control_run_controls.py`, `test_permission_provisioning.py`.
- Status per Increment Two: SUPPORTED, refusal-only (`COMMAND_EXECUTION_NOT_ENABLED`); no live pause/resume, no runner ownership. PostgreSQL race lane proves immutability + hash chain.
- Docs: `docs/mission-control/` (ADR_MC_001, ADR_MC_002, architecture, security, phase-2 evidence).

**OPEN PR BRANCH ONLY**

| PR | Title | Head SHA | Draft |
|---|---|---|---|
| [#265](https://github.com/ihoward40/SintraPrime-Unified/pull/265) | Phase 3C — Mission Control Command Authority and Dashboard Integration | `1a5d9958248e0c99454dcd980bc85dbc0398e253` | no |
| [#279](https://github.com/ihoward40/SintraPrime-Unified/pull/279) | R1: Fix ORM/Schema UUID Drift — MC Command Proven on PostgreSQL | (see PR) | yes |
| [#262](https://github.com/ihoward40/SintraPrime-Unified/pull/262) | Executor continuation implementation authorization review | `c3ca4f3d8eec231eee0c5658becfdd884db5e3b9` | yes |
| [#353](https://github.com/ihoward40/SintraPrime-Unified/pull/353) | SP-MC3D-001 governed SintraPrime Command Town | `a95a8383ccc5fd8d29ab656e9742f9bf9cfbdc94` | no |
| [#367](https://github.com/ihoward40/SintraPrime-Unified/pull/367) | SP-COMPLETION-MAP-001 + BASELINE-001 canonical completion plan | `feaf658e0a34d0e9bb1a23767b3becb1a8419ae1` | yes |

**REFERENCED — NOT VERIFIED**

- PR [#264](https://github.com/ihoward40/SintraPrime-Unified/pull/264) "Phase 3B Mythos Brain … (CERTIFIED)" — certification claim not independently verified in this increment.


---

## 2. Agents and agent runtime

**IMPLEMENTED ON MAIN**

- `agents/` — Nova, Sigma, Zero, Chat, Howard intake/recovery/template agents (Howard is approval-gated, evidence-intake only; see `agents/AGENTS.md`).
- `agent_runtime/` — canonical registry, delegation, executor binding, receipts, tool policy, certification (`canonical.py`, `registry.py`, `delegation.py`, `receipts.py`, `certify.py`, …) with `agent_runtime/tests/`.
- `swarm_runtime/` — governed swarm execution backend brought under the GOD-1 authority envelope by baseline commits `08060be7` and `051e2594` (controller, governed_execution, supervisor, worker, capability lease, health persistence).
- `omnibrain/` — GOD-1 / OmniBrain phases (swarm state in Principal Brief per commit `d062745b`).
- `mission_wiring/` — wires the certified-but-previously-unwired `agent_runtime` into the mission path (`mission_wiring/mission_runner.py`).
- `orchestration/` — `a2a_protocol.py` (in-memory priority bus, registry, capability discovery, delegation), `orchestration_api.py`, `durable_execution.py` (added by `6105a913`).
- `agent_protocol/`, `core/universe`, `superintelligence/` — present; Increment Two records Agent Runtime authority as **UNRESOLVED — convergence required**; `artifacts/convergence/mission-wiring/CONVERGENCE-DUPLICATES-001.md` records `agents/` as orphaned (zero production importers) and `superintelligence/` as unreachable.

**OPEN PR BRANCH ONLY**

| PR | Title | Head SHA | Draft |
|---|---|---|---|
| [#271](https://github.com/ihoward40/SintraPrime-Unified/pull/271) | SP-OMNIBRAIN-001: Principal Command + OmniBrain Phase 2 | `e717710d9bc48546a0f69ae9514370baa2ff7d15` | yes |
| [#352](https://github.com/ihoward40/SintraPrime-Unified/pull/352) | Governed agentic build, auto-heal, long-context and media runtime | `e6bf0e67621364358398d0bc646dbad5be0a73a7` | no |
| [#283](https://github.com/ihoward40/SintraPrime-Unified/pull/283) | SP-AMR-001 governed autonomous mission runtime | `11364d0cac90a3d9711878b2b3158c641e1f9d6f` | yes |
| [#325](https://github.com/ihoward40/SintraPrime-Unified/pull/325) | GOD-2A capability inventory integration | `dce634b9f7b04eac4aa9675b1c6cdf9fd708fd2c` | no |
| [#327](https://github.com/ihoward40/SintraPrime-Unified/pull/327) | Agent-to-agent Redis messaging | `8f489fd2f86aff6948198750a497790b61f36a15` | no |
| [#361](https://github.com/ihoward40/SintraPrime-Unified/pull/361) | Learning memory (retain/recall/reflect) | (see PR) | no |
| [#366](https://github.com/ihoward40/SintraPrime-Unified/pull/366) | SP-COLLECTIVE-INTELLIGENCE-001 organizational learning loop | (see PR) | yes |

---

## 3. Hermes

**IMPLEMENTED ON MAIN**

- `swarm_runtime/hermes_adapter.py` — canonical bridge from Hermes `delegate_task` to `SwarmController` (preserves task semantics: role, base SHA, read/write authority, expected artifact).
- `local_llm/hermes_adapter.py` — **different concern with the same name**: NousResearch Hermes LLM adapter over Ollama (ChatML tokens, Hermes JSON tool-call format). Not a duplicate of the swarm adapter; the shared name is a collision risk to note, not merge.
- `registry/agents/AGENT-HERMES-2-0.md` — Hermes Agent v2.0 registry entry, status ACTIVE, BKGC Article XXXII oath acceptance.
- `docs/IKE_HERMES_OPERATING_MANUAL.md` — operating manual; safety mode is draft-only (nothing sent/filed/modified without explicit approval); 3-tier approval model.
- `blackstone/bra/certifications/cert_AGT-001_hermes.json`; `agent_runtime/tests/test_hermes_delegation_certification.py`; `swarm_runtime/tests/test_acceptance_006_hermes.py`.

**OPEN PR BRANCH ONLY**

| PR | Title | Head SHA | Draft |
|---|---|---|---|
| [#227](https://github.com/ihoward40/SintraPrime-Unified/pull/227) | Hermes governed memory vault — Increment 1 | `6954818bb6b7e6012dfda0a58482284bfdd4179a` | no |
| [#230](https://github.com/ihoward40/SintraPrime-Unified/pull/230) | Hermes Quicksilver governed read-only adapter — Increment One | `778e1c63951dd56db12e8ed51cb41ba29340a17a` | no |
| [#282](https://github.com/ihoward40/SintraPrime-Unified/pull/282) | Govern trust authority routing across SintraPrime and Hermes | `078db122e3e56f5ae60906165d5a97fff3b2f537` | no |
| [#371](https://github.com/ihoward40/SintraPrime-Unified/pull/371) | SP-A2A-AUTHORITY-ENFORCEMENT-001 principal-bound swarm execution authority (touches `swarm_runtime/hermes_adapter.py`) | `04b8e6785ccbe5e21447a95f57216db3ea09e19e` | yes |

**REFERENCED — NOT VERIFIED**

- Branch `copilot/hermes-development-plan` exists at `753d2f87be1f8a635c525b9834771af8f89ea10a` with **no open PR** (the only PR ever associated with that head, #133, is closed). Branch contents not inspected beyond existence.

---

## 4. IKE-Bot

**IMPLEMENTED ON MAIN**

- `apps/ike-bot/` — vendored IKE-Bot code: Flask entrypoint `apps/ike-bot/main/main.py`, TypeScript server `apps/ike-bot/main/src/server.ts`, `features/` packages, `supabase/` migrations; last touched by `dbf2c56a` ("feat(trust-compliance): Add Trust Document Compliance Refactor module"). Described in its README as a backend API for trust automation, enforcement actions, and beneficiary management.
- `apps/ike-trust-agent/` — present at baseline (`git ls-tree origin/main apps/`).
- Airlock webhook: `apps/sintraprime/airlock_server/routes/ikebotTask.ts` — receives tasks, verifies HMAC signature, generates a governance receipt, forwards.
- **Case-variant duplicate (material):** git tracks both `apps/SintraPrime` and `apps/sintraprime` on main; these collide on case-insensitive filesystems and contain duplicate airlock code (also recorded in `artifacts/convergence/mission-wiring/CONVERGENCE-DUPLICATES-001.md`).

**OPEN PR BRANCH ONLY**

| PR | Title | Head SHA | Draft |
|---|---|---|---|
| [#285](https://github.com/ihoward40/SintraPrime-Unified/pull/285) | feat(ike-bot): governed multimodal top-features runtime (large; includes CI workflow changes and certification bundles) | `894f2b9d887483790c6e048de947d6af69f285de` | yes |

**NOT INSPECTED**

- External repositories `ike-bot` and `ike-trust-agent` (listed in issue #378) — outside this repository; not examined.

---

## 5. Agent Commons

**NOT ON MAIN.** A survey of `*.py` and `*.md` at baseline for `agent_commons` / `Agent Commons` / `agent-commons` returned zero matches. Agent Commons exists only on open PR branches.

**OPEN PR BRANCH ONLY — two competing implementations of issue [#243](https://github.com/ihoward40/SintraPrime-Unified/issues/243) Increment 1:**

| PR | Approach | Key files | Head SHA | Draft |
|---|---|---|---|---|
| [#244](https://github.com/ihoward40/SintraPrime-Unified/pull/244) | New top-level package | `agent_commons/{__init__,adapters,events,models,provider_adapters,store,supervisor}.py` + tests + Dockerfile | `68f17304d27ffe7f10851021c8dca6b5d51eac95` | yes |
| [#346](https://github.com/ihoward40/SintraPrime-Unified/pull/346) | Module inside `orchestration/` | `orchestration/agent_commons.py`, `orchestration/orchestration_api.py`, `orchestration/tests/test_agent_commons.py` + DOX updates | `eb60476a74b84e41fce9d89d97889c4393da27f9` | no |

**Related PRs named for reconciliation in issue #378 (do not create redundant authority frameworks):**

| PR | Title | Head SHA | Draft |
|---|---|---|---|
| [#371](https://github.com/ihoward40/SintraPrime-Unified/pull/371) | A2A principal-bound swarm execution authority | `04b8e6785ccbe5e21447a95f57216db3ea09e19e` | yes |
| [#375](https://github.com/ihoward40/SintraPrime-Unified/pull/375) | Constrain public GET exemptions + regression coverage | `856ee9d34bb466aaaf4a67ff31c1d8448d46c18f` | no |
| [#376](https://github.com/ihoward40/SintraPrime-Unified/pull/376) | Principal-only activation and ambiguous side-effect replay denial | `b5d733ec5c7c7e676372caff1e9474ff86c6275d` | yes |

---

## 6. External repositories — NOT INSPECTED

Issue #378 lists related repositories: `SintraPrime`, `ike-bot`, `ike-trust-agent`, `ikeos`, `sintraprime-kilo-implementation`, `my-agent`, `howard-trust-navigator`, and `worktree-2025-12-13T10-05-32`. Per the assignment's scope limit, none were inspected. No claim in this document relies on their contents. Their UNIQUE / DUPLICATE / ALREADY IN UNIFIED / EXPERIMENTAL / INDEPENDENT / INCONCLUSIVE classification remains open.

---

## 7. Material convergence conflicts

1. **Duplicate Agent Commons implementations** — PR #244 (top-level `agent_commons/` package) and PR #346 (`orchestration/agent_commons.py`) both implement issue #243 Increment 1. One canonical location must be chosen before either merges; merging both would create a third parallel runtime authority.
2. **Case-variant `apps/` duplicate** — `apps/SintraPrime` vs `apps/sintraprime` both tracked on main; POSIX-controlled `git mv` remediation still pending.
3. **Agent runtime authority still UNRESOLVED** (Increment Two, section 12) and further fragmented by open PRs #271, #283, #325, #327, #352.
4. **Overlapping Hermes authority increments** — #227, #230, #282, and #371 all touch the Hermes authority boundary with no merged ordering between them.

---

## 8. Recommended next implementation task (ONE)

**MODULE-REGISTRY-001 — machine-readable one-product module registry (seeded from this map).**

- **Scope:** Add `registry/modules.json` (entries: module name, canonical path, owning domain, status [`canonical` / `experimental` / `pr-branch-only` / `external-not-inspected`], entrypoint, source-of-truth doc, last-verified SHA) plus `scripts/ci/validate_module_registry.py` and `scripts/ci/tests/test_validate_module_registry.py`. Seed only the five areas mapped here: Mission Control, agents/agent runtime, Hermes, IKE-Bot, Agent Commons (status `pr-branch-only` pending the #244/#346 decision). Wire the validator into the existing `claims-validation` CI lane alongside `validate_repository_claims.py`.
- **Acceptance checks:** (1) validator exits 0 on the seeded registry and fails when an entry's path does not exist at the checked commit; (2) new unit tests pass; (3) existing `validate_repository_claims.py` still passes; (4) DOX pass updates the owning AGENTS.md files for `registry/` and `scripts/ci/` scope as required.
- **Dependencies:** This Increment Three map (for seed data and statuses). No code dependencies. Does not conflict with PR #367 — that PR is a completion *plan*; the registry is a machine-readable *current-state* artifact. Must not pre-empt the #244/#346 Agent Commons placement decision (Agent Commons is seeded as `pr-branch-only`).
- **Rollback:** Delete `registry/modules.json`, the validator, its tests, and the CI lane step. No runtime or schema impact.
- **Coverage check:** Verified 2026-11-08 via `gh pr list --state open --limit 100` and a `module_registry` grep that no open PR or main-path file provides a module registry; this task is not covered by active work.

---

## 9. Evidence index

| Claim class | Evidence |
|---|---|
| Baseline commit | `git log -1 origin/main` → `051e2594c67a805ceacc66ea2a6fc6db9c0bc793` |
| Open PR inventory | `gh pr list --state open --limit 100` (2026-11-08); per-PR `gh pr view <n> --json files,headRefName,isDraft` |
| Branch head SHAs | `git ls-remote origin <branch>` (recorded inline above) |
| Mission Control on main | `portal/main.py` router imports; Increment Two section 3 |
| Agent Commons absent on main | repo-wide `grep` for `agent_commons` / `Agent Commons` at baseline → zero matches |
| IKE-Bot on main | `git ls-tree origin/main apps/`; `apps/ike-bot/main/` file inspection; `git log -- apps/ike-bot` → `dbf2c56a` |
| Hermes on main | `find -iname '*hermes*'`; file inspection of both adapters and `registry/agents/AGENT-HERMES-2-0.md` |
| Case-variant duplicate | `git ls-tree origin/main apps/` shows both `apps/SintraPrime` and `apps/sintraprime` |

## 10. Gaps and limits

- External repositories: NOT INSPECTED (section 6).
- Deployed entrypoints and runtime behavior: not inspected; no environment access in this increment. Static inspection is not runtime authorization.
- Open PR branch contents were assessed from PR metadata (file lists, head SHAs, titles), not full code review.
- "CERTIFIED" labels in PR titles (e.g., #264, #265) are REFERENCED — NOT VERIFIED unless matched to a merged certification lane.
- `docs/CLAIMS.md` and `docs/CAPABILITY_INDEX.md` remain authoritative at the older commit `48e2caa7…`; refreshing them is out of scope here.


