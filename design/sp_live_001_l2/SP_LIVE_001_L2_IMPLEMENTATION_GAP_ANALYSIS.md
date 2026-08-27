# SP-LIVE-001 L2 Zero-Write Implementation Gap Analysis

## Scope

This analysis compares the L2 design contract against the current repository. It authorizes no implementation, provider use, credential change, or external side effect.

## Existing foundations

| Domain | Existing asset | Current strength | L2 disposition |
|---|---|---|---|
| Mission | `sintra_live/mission/mission_manager.py` | State machine, authority snapshot, transition evidence | Reuse concepts; correct state value mismatch and add durable/CAS persistence |
| Memory | `sintra_live/memory/governed_memory.py` | Trust labels, provenance hashes, injection filtering | Extend from fixtures to versioned, Principal/tenant/mission-scoped live retrieval |
| Specialists | `sintra_live/swarm/swarm.py` | Two roles, immutable inputs/outputs, read-only policies | Add real process/context isolation, non-transitive grants, and credential denial |
| Model routing | `sintra_live/models/model_router.py` | Candidate/selection decision records and budgets | Add provider/model attestation, real policy enforcement, and authority-delta checks |
| Approval | `sintra_live/approval/approval.py` | Immutable action envelope, approval lifecycle, single-use semantics | Consolidate with live envelope; bind baseline, adapter, provider, execution ID/nonce |
| Program authority | `sintra_live/authorization/gate.py` | Immutable snapshots, scope/capability/side-effect budget checks | Integrate at every L2 state transition and durable execution boundary |
| Live capability | `sintra_live/github_live/l1_runner.py` | Certified one-write path, envelope-bound execution identity, durable state/readback | Keep frozen as reference; wrap only under a future separately frozen L2 adapter gate |
| Independent verification | `sintra_live/verification/independent_verifier.py` | Expected/observed comparison contract | Replace fake-provider dependency with provider-neutral read-only adapter contract |
| Evidence | `sintra_live/evidence/evidence_chain.py` | Append-only SHA-256 chain and seal | Add durable storage, package manifest, required-evidence schema, and post-seal tamper checks |
| Principal Brief | `sintra_live/brief/principal_brief.py` | Immutable written/spoken brief derived from evidence root | Add evidence completeness gate and exact receipt/consumption disclosures |
| Synthetic integration | `sintra_live/integration.py` | End-to-end offline pipeline | Valuable harness seed; currently synthetic-only and not a live L2 implementation |
| Design basis | `docs/certification/sp-live-001-d1/*` | Mission, memory, swarm, authority, threat, and acceptance contracts | Preserve principles; L2 design makes the complete architecture explicit after L1 learnings |

## Critical implementation gaps

### G-01 — No unified durable L2 mission aggregate

The synthetic integration passes Python objects in one process. L2 needs a durable mission aggregate with immutable versions, compare-and-swap transitions, restart recovery, cancellation, and append-only state/evidence persistence.

**Required future artifact:** `L2MissionStore` with atomic transition API and replay/concurrency tests.

### G-02 — State-machine naming and sequencing mismatch

`MissionState.MEMORY_RESOLVED` currently has value `MISSION_RESOLVED`, and current states omit explicit workforce selection, model resolution, policy resolution, authority resolution, and brief generation.

**Required future artifact:** versioned L2 state machine; do not mutate the L1-frozen runtime under this design gate.

### G-03 — Principal identity remains fixture/offline outside the M3C GitHub binding

The repository has a synthetic Principal fixture and a provider-specific GitHub authenticated identity, but no provider-neutral Principal Gateway binding a current human session to an L2 mission and approval.

**Required future artifact:** independently certified Principal identity/session interface and step-up rules.

### G-04 — Living memory is fixture-backed

Current memory uses in-process fixtures and coarse scopes. It lacks tenant/Principal isolation, version/supersession validity, real collection policy, query records, contradiction resolution, and durable retrieval evidence.

**Required future artifact:** governed retrieval adapter plus immutable `MemoryRetrievalRecord`; authority delta mechanically fixed at zero.

### G-05 — Specialist isolation is logical, not host-enforced

Current specialists execute in one process and do not prove fresh context/workspace, no hidden channel, or credential isolation.

**Required future artifact:** host process/workspace isolation, explicit input manifests, tool allowlists, secret stripping, and sealed output packages.

### G-06 — Model routing is synthetic-only

The model catalog is synthetic and lacks real provider/model identity, invocation receipts, prompt/context hashes, fallback policy enforcement, cost/latency accounting, and authority-delta verification.

**Required future artifact:** provider-neutral model adapter contract and attested `ModelDecisionRecord`. Model/provider drift must fail closed like the separately open cron drift.

### G-07 — Policy resolver is not a first-class component

Authority checks exist, but there is no unified resolver mechanically evaluating mission, data, model, consequence, capability, and evidence policies by frozen versions/hashes.

**Required future artifact:** deterministic `PolicyResolver` returning allow, deny, or explicit-approval-required with complete inputs and policy hashes.

### G-08 — Approval models are split

The synthetic `ActionEnvelope`/`ApprovalManager` and L1 `L1ActionEnvelope`/runner approval record overlap but differ. L2 cannot safely compose them without one canonical schema and serialization.

**Required future artifact:** single L2 action-envelope schema incorporating L1 execution-identity and baseline lessons; formal migration/compatibility tests.

### G-09 — Capability registry and exact-resolution policy are incomplete

The L1 constants prove one exact capability, but there is no general registry for versioned capability identity, adapter, entrypoint, provider class/mode, credential boundary, baseline, and no-fallback policy.

**Required future artifact:** immutable certified-capability registry with exact lookup only; aliases never authorize.

### G-10 — Live execution is not orchestrated by the mission state machine

L1 is a standalone canonical runner. The synthetic mission uses a fake executor. There is no governed bridge that can hand an approved L2 envelope to a live adapter while preserving all upstream hashes and authority.

**Required future artifact:** `CanonicalCapabilityExecutor` interface whose live implementations require envelope-bound execution identity and return durable attempt/receipt records.

### G-11 — Independent verifier is fake-provider-specific

The verifier derives expected state partly from fake provider state and lacks a provider-neutral readback receipt contract.

**Required future artifact:** read-only verifier adapter isolated from execution return, binding provider object ID, target, account, timestamp, exact state/body, and match count.

### G-12 — Evidence completeness is not schema-enforced

Current evidence chains hash records but do not enforce a required set per mission type, durable sealing, package manifests, cross-artifact identities, or no-completion guards.

**Required future artifact:** L2 evidence schema, mechanical completeness checker, post-seal tamper test, and certification manifest.

### G-13 — Principal Brief can be generated without proving full required evidence

Current brief binds an evidence root but does not independently verify that the root contains every required mission record.

**Required future artifact:** brief generator accepts only a sealed package that passes the completeness schema and derives both spoken/written representations from one immutable brief object.

### G-14 — Secrets and credential leases need mission-scoped lifecycle

L1 used a local token state for one capability. L2 requires short-lived credential leases, no delegation to specialists/models, account/installation revalidation immediately before I/O, redaction, and zero-leak evidence.

**Required future artifact:** credential broker/lease contract; live credentials never enter mission memory or specialist inputs.

### G-15 — Replay, ambiguity, and crash recovery need end-to-end tests

L1 contains durable execution state and reconciliation logic; the broader mission has no restart/replay behavior across every stage.

**Required future artifact:** crash-window matrix from request through brief, with special focus on provider commit before local receipt and evidence seal before brief.

## Security and governance gaps

| Gap | Required future control |
|---|---|
| Specialist self-authorization | Type-level advisory result; no approval/capability methods or credential access |
| Swarm scope expansion | Parent-hash grants, subset validation, immutable budgets |
| Memory-derived authority | Dedicated context-only interface; authority resolver ignores memory values except policy-proven facts |
| Model-derived authority | Routing result schema has no authority field; frozen authority snapshot compared before/after |
| Approval reuse | Durable single-use approval ledger keyed by envelope hash, mission, execution ID, nonce |
| Capability aliasing | Exact versioned registry keys; no fuzzy/name matching |
| Live mock fallback | Live adapter constructor has no mock fallback; fail on unavailable provider |
| Missing evidence completion | Mission state transition guard requires schema-complete sealed package |
| Operator/config drift | Execution-source/config manifest defines relevant paths; out-of-manifest changes classified explicitly |

## Non-authoritative and out-of-scope state

- L1 is closed/frozen and not modified by L2 design.
- Untracked `sintra_live/github_live/auth.py` and `sintra_live/github_live/dry_run.py` are non-certified; L2 authority over them is `NONE`.
- The `sintraprime-ui-foundation-guard` inference configuration drift is operationally separate: `OPS_INFERENCE_CONFIG_DRIFT = OPEN`, `L1_CERTIFICATION_IMPACT = NONE`, `CRON_FAIL_CLOSED_BEHAVIOR = PASS`, `UNINTENDED_SPEND_PREVENTED = TRUE`.
- No cron configuration is changed by this design.

## Proposed future implementation sequence (not authorized)

1. **I1 — Schemas and durable mission store**
2. **I2 — Principal Gateway and mission scoping**
3. **I3 — Governed living-memory retrieval**
4. **I4 — Host-isolated workforce execution**
5. **I5 — Attested model routing**
6. **I6 — Policy and authority resolvers**
7. **I7 — Canonical action envelope and single-use approval ledger**
8. **I8 — Exact capability registry and canonical executor interface**
9. **I9 — Provider-neutral independent readback**
10. **I10 — Evidence completeness/sealing and Principal Brief**
11. **I11 — Offline/host acceptance cases**
12. **I12 — Separately authorized live dogfood with a new envelope**

Each stage requires separate implementation authority. I12 additionally requires fresh live-execution authority and Principal approval.

## Gap conclusion

The repository contains strong synthetic D1 foundations and a separately certified L1 GitHub live adapter, but it does not yet implement the full L2 governed architecture. Therefore:

- `L2_DESIGN_READINESS = PASS`
- `L2_IMPLEMENTATION_READINESS = INCOMPLETE`
- `L2_LIVE_EXECUTION_READINESS = NOT_AUTHORIZED`
- `L2_IMPLEMENTATION_AUTHORITY = NONE`
- `L2_LIVE_EXECUTION_AUTHORITY = NONE`
