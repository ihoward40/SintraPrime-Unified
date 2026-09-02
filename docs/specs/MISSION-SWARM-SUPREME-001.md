# Spec: MISSION-SWARM-SUPREME-001

## Status

`SPECIFICATION DRAFT — IMPLEMENTATION NOT AUTHORIZED BY THIS DOCUMENT`

## Objective

Define a reliability program for SintraPrime in which model intelligence is replaceable, constitutional authority is centralized, work and evidence are durable, failures are expected and recoverable, and important claims are independently challengeable.

The first implementation slice is S1: real semantic worker inference and provider failover. Durable workflow authority remediation is a separate A1 lane and must not be mixed with S1.

## Baseline

```text
REMOTE_MAIN_SHA = 56b1689162efefce4780bfac8fe06d69a75e392a
S1_ISSUE = #296
A1_ISSUE = #295
```

## Architecture planes

1. Principal Authority Plane — Principal Gateway → policy → exact action envelope → executor.
2. Mission Plane — immutable mission constitution: identity, tenant, scope, base SHA, budgets, deadline, risk, acceptance, termination, authority ceiling.
3. Swarm Control Plane — scheduling, leases, heartbeats, retry, replacement, concurrency, ownership, isolation, artifacts, quarantine, shutdown.
4. Governed Inference Plane — worker → SwarmInferenceAdapter → GovernedInferenceRouter → provider health → provider.
5. Evidence Plane — append-only artifact/event ledger with hashes and provenance lineage.
6. Reliability Plane — backpressure, health, cooldown, circuit breakers, resource pressure, and no-progress termination.
7. Durable Execution Plane — checkpointed mission/task/worker/attempt state; recovery from ledger, never RAM-only assumptions.
8. Verification Plane — deterministic checks, Breaker, Dissenter, Arbiter, and evidence independence.
9. External Action Plane — exact action envelopes, approval binding, idempotency, reconciliation, and receipts.
10. Memory Plane — tenant-scoped living memory derived only from verified evidence and approved records.

## Worker species

```text
D-WORKER = deterministic inventory, AST, call graph, schemas, hashes, tests, CI, SQL/RLS
S-WORKER = bounded semantic interpretation through governed inference
B-WORKER = isolated implementation with exclusive file ownership
X-WORKER = adversarial verification / Breaker
```

Builders cannot certify their own changes. Semantic workers receive bounded evidence packets, not unrestricted repositories.

## S1 implementation scope

### Required chain

```text
ModelReasoningWorker
→ SwarmInferenceAdapter
→ GovernedInferenceRouter
→ provider adapter
```

The worker may own worker/task identity, prompt, heartbeat, checkpoint, and artifact output. It may not select providers or define constitutional policy.

### Provider attempt contract

- Provider-attempt timeout is shorter than worker lifetime.
- A timeout emits an attempt record and updates provider health.
- The same worker/task identity continues with an alternate provider.
- Exactly one final artifact is accepted.
- Provider health is loaded before selection and persisted after outcome.
- Cooldown state survives controller restart and prevents selection during cooldown.

### S1 acceptance

```text
MODEL_REASONING_WORKER_STARTED = TRUE
SWARM_INFERENCE_ADAPTER_CALLED = TRUE
GOVERNED_INFERENCE_ROUTER_CALLED = TRUE
PROVIDER_A_ATTEMPTED = TRUE
PROVIDER_A_TIMED_OUT = TRUE
PROVIDER_A_HEALTH_UPDATED = TRUE
PROVIDER_B_SELECTED = TRUE
PROVIDER_B_SUCCEEDED = TRUE
WORKER_COMPLETED = TRUE
FINAL_ARTIFACT_VALID = TRUE
FINAL_ARTIFACT_COUNT = 1
FAILOVER_COUNT = 1
```

Additional required tests:

- `SWARM-SEMANTIC-ACCEPTANCE-001`: real worker, fake primary timeout, fake fallback success through the real governed router.
- `SWARM-SEMANTIC-ACCEPTANCE-002`: provider cooldown survives controller restart and suppresses selection.
- Hermes-facing delegation test: actual `delegate_task` surface → HermesSwarmAdapter → SwarmController → ModelReasoningWorker → governed router.
- Five bounded semantic workers: five completed workers, five valid final artifacts, no orchestrator fallback.

## Reliability classes

```text
R0 = experimental / happy path
R1 = recoverable worker crash
R2 = durable controller restart
R3 = provider-resilient real failover
R4 = replay-safe and duplicate-suppressed
R5 = authority/effect safe
R6 = compound chaos certified
R7 = sustained production observation
```

Initial target after S1:

```text
OS_PROCESS_LAYER = R3/R4 evidence retained
DETERMINISTIC_WORKERS = R3
WORKTREE_ISOLATION = R3
CONTROLLER_RECOVERY = R3
SEMANTIC_WORKER = R3 only after real acceptance passes
REAL_PROVIDER_FAILOVER = R3 only after real acceptance passes
AUTHORITY_EFFECT_EXECUTION = HOLD pending A1
```

## Flight recorder

Every mission must produce an append-only, hash-chained `SWARM_FLIGHT_RECORDER.jsonl` containing at minimum:

```text
MISSION_CREATED
TASK_CREATED
WORKER_LEASED
WORKER_STARTED
PROVIDER_SELECTED
PROVIDER_TIMEOUT
PROVIDER_FAILED_OVER
CHECKPOINT_WRITTEN
ARTIFACT_WRITTEN
WORKER_CRASHED
WORKER_REPLACED
BREAKER_REJECTED
PRINCIPAL_APPROVAL_REQUESTED
PRINCIPAL_APPROVED
ACTION_STARTED
ACTION_UNKNOWN
RECONCILIATION_STARTED
ACTION_CONFIRMED
MISSION_COMPLETED
```

Controller-derived accounting is authoritative:

```text
workers_requested
workers_started
workers_completed
workers_failed
workers_timed_out
workers_replaced
artifacts_expected
artifacts_final
artifacts_partial
provider_attempts
provider_failovers
orchestrator_fallbacks
max_concurrency
```

Hermes renders these values; it must not infer or rewrite them.

## Failover levels

1. Provider failover — same worker, alternate provider.
2. Worker replacement — same task, new process, checkpoint resume.
3. Mission replanning — deterministic decomposition or strategy change after repeated failure.

## A1 deferred authority lane

A1 is not part of S1. It must prove:

- anonymous generic start denied;
- authenticated unauthorized start denied;
- unapproved E2 start denied;
- approved exact E2 action reaches engine;
- payload mutation denied;
- workflow type mutation denied;
- cross-tenant activation denied;
- approval replay denied.

The generic workflow route must be removed, restricted, or routed through `DurableOrchestrationAuthority`. The engine remains execution infrastructure, not constitutional authority.

## Chaos certification matrix

The eventual R6 suite must include worker kill, controller kill, DB failure, provider stall/500/429/malformed output, network partition, read-only/full disk, corrupt artifact, ownership conflict, duplicate dispatch, lease collision, restart during failover, approval expiry, post-approval payload mutation, lost response after DB commit, unknown external outcome, Builder/Breaker disagreement, correlated false consensus, and unique correct minority evidence.

## Commands

```bash
python3 -m compileall -q swarm_runtime governed_inference
python3 -m pytest swarm_runtime/tests/test_semantic_worker_inference.py -q -o addopts=''
python3 -m pytest governed_inference/tests/test_governed_inference.py -q -o addopts=''
python3 -m pytest governed_inference/tests/test_governed_inference_adapters.py -q -o addopts=''
```

## Boundaries

- Always: work from exact remote base; use isolated worktrees; preserve tenant/mission/action identity; require deterministic evidence; separate Builder and Breaker; keep extraction frozen.
- Ask first: merge, push, draft PR publication, dependency changes, production providers, external actions, schema changes, and A1 implementation.
- Never: treat simulated failover as real failover; let workers select constitutional authority; use direct provider calls; count partial artifacts as final; use orchestrator rescue as worker completion; merge or deploy without Principal approval.

## Success criteria

The program is not complete until each claimed reliability class has exact tests and machine-derived evidence. S1 is complete only when real semantic provider timeout and fallback are exercised through the actual worker path, provider health persistence/cooldown restart passes, the Hermes-facing path is proven, five bounded semantic workers complete with five final artifacts, and remote CI is green.

## S1 governed tie-break

After eligibility and governed score, equal-score candidates are ordered by `InferencePolicy.provider_priority` (lower integer wins). Unspecified providers receive neutral priority `0`. If both score and governed priority tie, canonical provider identifier ascending is used solely for deterministic reproducibility; it is not a business preference and cannot be supplied by task or worker input.


- Exact production Hermes `delegate_task` dispatch mapping to the repository adapter remains to be proven.
- Whether provider timeout enforcement should live in `GovernedInferenceRouter`, provider adapters, or both requires contract-level alignment.
- The A1 disposition of the generic workflow route remains separate and deferred.
