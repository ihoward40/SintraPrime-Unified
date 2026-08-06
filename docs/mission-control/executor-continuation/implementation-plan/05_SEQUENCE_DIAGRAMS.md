# 05 — Sequence Diagrams: Executor Continuation

**Status:** PLANNING ONLY — no runtime code
**Scope:** Implementation planning artifact for ADR-MC-001 (Executor Continuation After Lease Expiry)
**Source of truth:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05), Section 3 (sequence diagrams) and Sections 2.1–2.15 (rules)
**Related docs:** `../ADR_MC_001_EXECUTOR_CONTINUATION.md`, `../MISSION_CONTROL_FOUNDATION_ARCHITECTURE.md`

## 1. Purpose

This document expands the three sequence diagrams in ADR-MC-001 Section 3 into ten detailed, end-to-end ASCII sequence diagrams covering the executor continuation lifecycle. It is a planning artifact: it specifies participant interactions, message ordering, guards, and notes so that implementers can derive protocol contracts, audit event orderings, and test scenarios from a single source. It introduces no runtime code, no new authority, and no deviation from ADR-MC-001.

Each diagram cites the ADR-MC-001 section that governs the behavior shown. Where a diagram adds detail beyond the ADR (e.g., explicit Witness or Audit Ledger participants), that detail is a faithful expansion of the ADR's rules, not a new rule.

## 2. Conventions

### 2.1 Participants

| Alias | Role | ADR-MC-001 term |
|---|---|---|
| `Brain` | Central command authority; sole owner of intent, dispatch, cancellation, lease, capability, revocation, and reconciliation | Brain |
| `Exec` | Worker process holding a lease and optionally continuing after expiry | Executor |
| `ExecB` | A second executor (used in split-brain and cross-tenant diagrams) | Executor |
| `Wit` | Independent control-plane witness publishing signed Brain-availability statements | Witness (Section 2.2.4) |
| `Down` | Downstream system that receives and validates externally visible effects | Downstream system |
| `Ledger` | Immutable audit ledger; authoritative storage is never truncated (Section 2.13) | Audit ledger |
| `Op` | Human operator in the manual review queue (Sections 2.6.3.4, 2.12.2) | Operator |

### 2.2 Notation

```
 Brain  Exec   Wit   Down  Ledger      <- participant header
  |      |     |     |     |
  |----> msg ---->|   |     |           <- synchronous request
  |<----- ack ----|   |     |           <- response
  |===== note ====|   |     |           <- note / inline action
  |---[guard]---->|   |     |           <- message guarded by condition
  |xxx rejected xxx|   |     |           <- rejected / forbidden path
  |~~~ async ~~~>|   |     |            <- asynchronous / streamed
```

- `-->` and `<--` denote signed, async, or streamed messages (e.g., audit appends, revocation stream entries).
- `[guard]` text immediately above or on a message arrow is a precondition; the message is sent only if the guard holds.
- `==` notes are side actions or internal checks performed by a participant (not a message).
- Messages are numbered within each diagram as `M#` for cross-reference.
- Quoted fields (e.g., `expires_at`, `capability_id`) reference ADR-MC-001 capability/lease fields.
- "Section refs" point to ADR-MC-001 subsections.

### 2.3 Cross-cutting rules assumed in every diagram

These hold unless a diagram explicitly shows a violation path:

1. **Authoritative audit storage is never truncated** (Section 2.13). Every event in every diagram is appended to `Ledger`; only the projection may truncate.
2. **Tenant isolation** (Section 2.14): all messages carry `tenant_id`; cross-tenant attempts are security events (Diagram 10).
3. **Trusted comparable signed time** (Section 2.6.3.1, 2.8): every timestamp-bearing message is signed by the Brain or a witness; executor-local monotonic clocks are never compared across machines for ordering.
4. **Default decision is STOP** (Section 2.3): every eligibility gate below has an implicit `else STOP` branch not always drawn.

## 3. Diagrams

### Diagram 1 — Normal Lease Lifecycle with Capability Issuance

Scope: ADR-MC-001 Sections 2.1.1 (acquisition), 2.1.2 (renewal), 2.1.4 (capability issuance), 2.13 (audit chain). Shows the happy path: dispatch, capability issuance alongside the lease, work, optional renewal with capability rotation, completion, and audit close-out. No continuation occurs.

```
 Brain                Exec                 Down                Ledger
  |                    |                    |                    |
  |== dispatch command C to Exec ==========|                    |
  |--- issue lease L0 + capability C0 ---->|                    |
  |    L0: {command_id, executor_id,        |                    |
  |         tenant_id, issued_at,           |                    |
  |         expires_at, lease_token,        |                    |
  |         policy_snapshot_id,             |                    |
  |         continuation_class,             |                    |
  |         continuation_capability_id=C0}  |                    |
  |    C0: {capability_id, command_id,      |                    |
  |         tenant_id, executor_id,          |                    |
  |         not_valid_before = L0.expires_at|                    |
  |         not_valid_after,                |                    |
  |         max_continuation_*,             |                    |
  |         continuation_class,             |                    |
  |         permitted_operation_ids,        |                    |
  |         side_effect_slot_spec,          |                    |
  |         policy_snapshot_hash,           |                    |
  |         revocation_watermark_required,  |                    |
  |         signed_capability_token}        |                    |
  |--- append LEASE_ISSUED(C0,L0) -------->|------------------>| M1
  |--- append CAPABILITY_ISSUED(C0) ------>|------------------>| M2
  |                    |                    |                    |
  |            [lease L0 valid]             |                    |
  |                    |--- perform op_1 -->|                    |
  |                    |<-- result_1 -------|                    |
  |                    |--- append OP_1 ----|------------------>| M3
  |                    |                    |                    |
  |   [renew before L0.expires_at]          |                    |
  |<--- renew request ---|                  |                    |
  |== check: not cancelled; Exec is holder; |                    |
  |== max duration not exceeded;            |                    |
  |== policy snapshot not superseded;       |                    |
  |== Brain available                       |                    |
  |--- renew ok: L1 + new capability C1 -->|                    |
  |    L1.expires_at extended               |                    |
  |    L0.lease_token REVOKED               |                    |
  |    C0 SUPERSEDED by C1 (Invariant 3a;  |                    |
  |        Section 2.1.2)                   |                    |
  |--- append LEASE_RENEWED(L1) ---------->|------------------>| M4
  |--- append CAPABILITY_ISSUED(C1) ------>|------------------>| M5
  |--- append CAPABILITY_SUPERSEDED(C0) --->|------------------>| M6
  |--- append LEASE_REVOKED(L0) ---------->|------------------>| M7
  |                    |                    |                    |
  |            [lease L1 valid]             |                    |
  |                    |--- perform op_2 -->|                    |
  |                    |<-- result_2 -------|                    |
  |                    |--- append OP_2 ----|------------------>| M8
  |                    |                    |                    |
  |<--- complete (final result) ---|        |                    |
  |--- append COMMAND_SUCCEEDED ---------->|------------------>| M9
  |--- append LEASE_CLOSED(L1) ----------->|------------------>| M10
  |--- append CAPABILITY_REVOKED(C1) ------>|------------------>| M11
  |                    |                    |                    |
  Note: C0 was never exercised (Brain stayed available).
        C0 becomes permanently unusable at L0 expiry by both
        not_valid_before (== L0.expires_at) and supersession.
        Downstream never sees a continuation effect in this path.
```

Guards and notes:
- M1–M2: Lease and capability issuance are paired audit events with a causation link to the dispatch event (Section 2.1.1, 2.13).
- M4–M7: Renewal rotates the capability. `C0` is superseded even if its `not_valid_after` is later than `C1`'s (Invariant 3a; Section 2.1.2). Downstream systems must reject `C0` by capability ID after M6.
- M9–M11: Completion closes the lease and revokes the (unused) capability so it can never be exercised later.

---

### Diagram 2 — Lease Expiry with Continuation

Scope: ADR-MC-001 Sections 2.1.3 (expiry), 2.2 (outage detection), 2.2.4 (witnesses), 2.3 (eligibility), 2.1.4 (capability + outage evidence), 2.4 (limits), 2.5 (idempotency), 2.6.2 (completion report), 2.9 (side-effect class), 2.10 (revocation watermark), 2.13 (audit). This is the canonical continuation flow: outage detection → eligibility → capability + outage-evidence validation by downstream → bounded operation → receipt → report on recovery.

```
 Brain                Exec                 Wit                 Down                Ledger
  |                    |                    |                    |                    |
  |--- issue L0 + C0 ->|                    |                    |                    |
  |--- append LEASE_ISSUED, CAPABILITY_ISSUED ----------------->|------------------>| M1
  |                    |--- perform op_1 -->|                    |                    |
  |                    |<-- result_1 -------|                    |                    |
  |                    |--- append OP_1 ----|------------------>|------------------>| M2
  |                    |                    |                    |                    |
  |== Brain becomes unavailable ===========|                    |                    |
  |                    |                    |                    |                    |
  |   [heartbeat ack missing >=             |                    |                    |
  |    brain_heartbeat_miss_threshold]      |                    |                    |
  |<xxx heartbeat xxx (no ack)             |                    |                    |
  |                    |                    |                    |                    |
  |   [lease renewal rejected >=            |                    |                    |
  |    lease_rejection_threshold as         |                    |                    |
  |    BRAIN_UNAVAILABLE]                   |                    |                    |
  |<xxx renew? xxx BRAIN_UNAVAILABLE        |                    |                    |
  |                    |                    |                    |                    |
  |== L0.expires_at reached (Exec derives   |                    |                    |
  |   locally from last signed anchor +     |                    |                    |
  |   monotonic elapsed; Section 2.8) =====|                    |                    |
  |                    |                    |                    |                    |
  |== grace period: wait brain_outage_      |                    |                    |
  |   grace_period (default 30s) ==========|                    |                    |
  |                    |                    |                    |                    |
  |            [need 2 independent signals, |                    |                    |
  |             one direct-Brain           |                    |                    |
  |             (heartbeat/renew/status)]  |                    |                    |
  |                    |--- query witnesses: "Brain available?" -->|                 |
  |                    |<-- signed stmts (N>=3f+1, quorum 2f+1) --|                 |
  |                    |    each: {witness_id, tenant_id,         |                 |
  |                    |           brain_region, statement_id,    |                 |
  |                    |           nonce, signed anchor,          |                 |
  |                    |           timestamp, "UNAVAILABLE"}      |                 |
  |                    |== verify: distinct witnesses, fresh,     |                 |
  |                    |   non-replayed, self-exclusion ok       |                 |
  |                    |                    |                    |                    |
  |                    |== declare outage: persist record with   |                    |
  |                    |   {signals, witness quorum,             |                    |
  |                    |    monotonic_outage_start,              |                    |
  |                    |    wall_outage_declared_at (signed),    |                    |
  |                    |    grace_period_end,                    |                    |
  |                    |    lease_token_fingerprint}            |                    |
  |                    |--- append OUTAGE_DECLARED ------------>|------------------>| M3
  |                    |                    |                    |                    |
  |                    |== eligibility check (Section 2.3) =====|                    |
  |                    |  [x] lease expired + C0.not_valid_before reached            |
  |                    |  [x] outage declared (2 signals incl. direct-Brain)        |
  |                    |  [x] C0 signed, unexpired, scoped to cmd/exec/tenant       |
  |                    |  [x] revocation_watermark_observed >= C0.revocation_       |
  |                    |      watermark_required; cache age <= max_revocation_cache_age
  |                    |  [x] no cancellation in cached events up to watermark      |
  |                    |  [x] local state sufficient vs task manifest               |
  |                    |  [x] continuation_class & C0 permit op_2                  |
  |                    |  [x] policy_snapshot_hash pinned & not past                |
  |                    |      policy_snapshot_not_valid_after                       |
  |                    |  [x] estimate within max_continuation_duration &          |
  |                    |      max_continuation_operations (default 1)              |
  |                    |  [x] tenant_id matches execution context                   |
  |                    |  [x] can emit audit events + receipts                     |
  |                    |  [x] signed wall-clock within C0 validity window          |
  |                    |  else: STOP -> safe-hold (not drawn)                       |
  |                    |--- append ELIGIBILITY_DECIDED = CONTINUE ->|-------------->| M4
  |                    |                    |                    |                    |
  |                    |== build outage_evidence bundle =========|                    |
  |                    |   {outage declaration record,            |                    |
  |                    |    witness statements,                  |                    |
  |                    |    signal thresholds crossed,            |                    |
  |                    |    signed time anchor at declaration,    |                    |
  |                    |    capability_id=C0, command_id}        |                    |
  |                    |                    |                    |                    |
  |                    |== continue op_2 (within C0 bounds) =====|                    |
  |                    |--- perform op_2 + present C0 token + outage_evidence ---->|
  |                    |                    |                    |                    |
  |                    |                    |          [Down validates:            |
  |                    |                    |           - C0 signed & unexpired    |
  |                    |                    |           - C0.not_valid_before <= now|
  |                    |                    |           - C0.not_valid_after >= now|
  |                    |                    |           - C0.tenant_id == op tenant|
  |                    |                    |           - C0.permitted_operation_ids|
  |                    |                    |             contains op_2            |
  |                    |                    |           - side_effect_slot_spec ok |
  |                    |                    |           - outage_evidence present, |
  |                    |                    |             signed, bound to C0 & cmd|
  |                    |                    |           - (cmd,op_2,slot) not      |
  |                    |                    |             already applied         |
  |                    |                    |           - C0 not superseded/revoked]
  |                    |                    |<-- apply effect, ack ------------|
  |                    |<-- result_2 -------|                    |                    |
  |                    |--- append OP_2 (with stable effect identity) ------------>| M5
  |                    |                    |                    |                    |
  |                    |== generate signed receipt R ===========|                    |
  |                    |   {continuation_id, capability_id=C0,   |                    |
  |                    |    command_id, operations_performed,    |                    |
  |                    |    result_digest, evidence_refs,        |                    |
  |                    |    continuation_journal (encrypted),    |                    |
  |                    |    outage_evidence, revocation_watermark |
  |                    |    observed, signed by Exec}            |                    |
  |                    |--- append CONTINUATION_RECEIPT(R) ---->|------------------>| M6
  |                    |                    |                    |                    |
  |== Brain recovers (available >=          |                    |                    |
  |   brain_recovery_confirmation_period) ==|                    |                    |
  |--- append RECOVERY_DETECTED ---------->|------------------>|------------------>| M7
  |                    |                    |                    |                    |
  |            [within completion_report_deadline]              |                    |
  |<--- submit completion report (R + journal + outage_evidence) ---|              |
  |                    |--- append COMPLETION_REPORT ---------->|------------------>| M8
  |                    |                    |                    |                    |
  |== reconcile (see Diagram 6) ===========|                    |                    |
  |== terminal state: VALID_CONTINUATION -> SUCCEEDED =========|                    |
  |--- append RECONCILED, COMMAND_SUCCEEDED -------------------->|------------------>| M9
  |--- append LEASE_CLOSED, CAPABILITY_REVOKED(C0) ------------>|------------------>| M10
```

Guards and notes:
- M3: Outage declaration requires ≥2 independent signals, one of which is a direct-Brain signal (heartbeat, lease renewal rejection, or status query). Witness statements alone are never sufficient (Section 2.2.2).
- M4: The eligibility check is the single gate. Every criterion in Section 2.3 must pass; otherwise STOP. The default is STOP.
- M5: The stable external-effect identity `(command_id, operation_id, side_effect_slot)` is used at Down and in the journal (Section 2.5). `continuation_id` and `executor_id` are metadata only.
- The downstream validation block is the crux of Sections 2.1.4 and 2.5.2: a capability alone is insufficient while the Brain is healthy; the outage evidence bundle bound to `capability_id` and `command_id` is mandatory proof that the precondition held.
- M6: Receipt is signed by the executor and immutable (Invariant 6).
- M8: Reporting is mandatory regardless of outcome. Silent continuation is forbidden (Section 2.6.2).

---

### Diagram 3 — Lease Renewal with Capability Rotation / Supersession

Scope: ADR-MC-001 Sections 2.1.2, 2.1.4, Invariant 3a, 2.13. Focuses on the rotation mechanics and the downstream-visible supersession. Two renewals are shown to illustrate that only the capability referenced by the latest valid lease may be exercised.

```
 Brain                Exec                 Down                Ledger
  |                    |                    |                    |
  |--- issue L0 + C0 ->|                    |                    |
  |--- append LEASE_ISSUED(L0), CAPABILITY_ISSUED(C0) ---------->|------------------>| M1
  |                    |--- perform op_1 -->|                    |                    |
  |                    |<-- result_1 -------|                    |                    |
  |                    |                    |                    |                    |
  |   [renew #1: before L0.expires_at]      |                    |                    |
  |<--- renew request ---|                  |                    |                    |
  |== Brain available; checks pass =========|                    |                    |
  |--- renew ok: L1 + C1 -->|              |                    |                    |
  |    L0.token REVOKED; C0 SUPERSEDED by C1 (Invariant 3a)     |                    |
  |--- append LEASE_RENEWED(L1), CAPABILITY_ISSUED(C1),         |------------------>| M2
  |--- append CAPABILITY_SUPERSEDED(C0), LEASE_REVOKED(L0) ---->|------------------>| M3
  |                    |                    |                    |                    |
  |                    |--- perform op_2 -->|                    |                    |
  |                    |    (uses L1.token; C1 is the live       |                    |
  |                    |     continuation capability)            |                    |
  |                    |<-- result_2 -------|                    |                    |
  |                    |                    |                    |                    |
  |   [renew #2: before L1.expires_at]      |                    |                    |
  |<--- renew request ---|                  |                    |                    |
  |== Brain available; checks pass =========|                    |                    |
  |--- renew ok: L2 + C2 -->|              |                    |                    |
  |    L1.token REVOKED; C1 SUPERSEDED by C2                   |                    |
  |--- append LEASE_RENEWED(L2), CAPABILITY_ISSUED(C2),         |------------------>| M4
  |--- append CAPABILITY_SUPERSEDED(C1), LEASE_REVOKED(L1) ---->|------------------>| M5
  |                    |                    |                    |                    |
  |== later: outage occurs, L2 expires =====|                    |                    |
  |                    |== attempt to continue using C2 (live) ==|                    |
  |                    |--- continue op_3 + C2 token + outage_evidence --------->|
  |                    |                    |                    |                    |
  |                    |                    |  [Down rejects C0 AND C1 by ID       |
  |                    |                    |   (superseded); accepts C2 only]      |
  |                    |                    |<-- apply effect, ack ---------------|
  |                    |<-- result_3 -------|                    |                    |
  |                    |                    |                    |                    |
  |  Note: If Exec had tried to use C0 or C1 here, Down would   |                    |
  |        reject on CAPABILITY_SUPERSEDED regardless of their  |                    |
  |        not_valid_after values (Invariant 3a, Section 2.1.2).|                    |
  |        The supersession audit chain is the source of truth. |                    |
  |                    |                    |                    |                    |
  |== Brain recovers; reconcile ============|                    |                    |
  |<--- completion report (C2 used) ---|    |                    |                    |
  |--- append RECONCILED ------------------>|------------------>| M6
```

Guards and notes:
- Supersession is authoritative even when a former capability's `not_valid_after` is later than the new one's (Invariant 3a). Downstream tracks capability IDs against the supersession stream, not just time windows.
- Only `C2` (referenced by the latest valid lease `L2`) is exercisable. `C0` and `C1` are dead even though their `not_valid_after` may not have elapsed.
- The audit chain at M2–M5 is the evidence downstream consults.

---

### Diagram 4 — Split-Brain: Two Executors Continue the Same Command

Scope: ADR-MC-001 Sections 2.12.1 (detection), 2.12.2 (resolution), 2.5 (idempotency), 2.6.3.1 (result selection), 2.6.3.2 (effect reconciliation). Shows the agreeing-results/idempotent-effects path (terminates SUCCEEDED) and notes the divergent-results path (terminates MANUAL_REVIEW_REQUIRED).

```
 Brain              ExecA             ExecB            Wit            Down           Ledger
  |                  |                 |               |              |               |
  |== dispatch cmd X to ExecA only ==| (lease exclusivity)          |               |
  |--- issue L_A + C_A to ExecA ---->|                |              |               |
  |--- append LEASE_ISSUED(L_A), CAPABILITY_ISSUED(C_A) ---------->|-------------->| M1
  |                  |                 |               |              |               |
  |== Brain unavailable =============|                |              |               |
  |                  |                 |               |              |               |
  |                  |== A: outage declared (2 signals + witness quorum)          |
  |                  |                 |== B: ALSO independently declares outage  |
  |                  |                 |   (B is a second executor for same cmd;   |
  |                  |                 |    this is the split-brain condition)    |
  |                  |                 |               |              |               |
  |                  |== A: eligibility ok; continue op_2 with C_A ==|              |
  |                  |                 |== B: eligibility ok; continue op_2 with C_B
  |                  |                 |               |              |               |
  |                  |--- op_2 + C_A + outage_evidence_A ----------->|              |
  |                  |                 |--- op_2 + C_B + outage_evidence_B ------->|              |
  |                  |                 |               |              |               |
  |                  |                 |               |  [Down receives both; stable |
  |                  |                 |               |   effect identity is        |
  |                  |                 |               |   (root_command_id, op_2,   |
  |                  |                 |               |    slot) for BOTH]          |
  |                  |                 |               |              |               |
  |                  |                 |               |  [CASE A: idempotent slot +  |
  |                  |                 |               |   identical result_digest   |
  |                  |                 |               |   -> Down applies first,    |
  |                  |                 |               |      rejects second as      |
  |                  |                 |               |      DUPLICATE by identity] |
  |                  |<-- ack_2A ------|               |              |               |
  |                  |                 |<-- ack_2B (DUPLICATE) ------|               |
  |                  |                 |               |              |               |
  |                  |== A: receipt R_A; B: receipt R_B ==|          |               |
  |                  |--- append CONTINUATION_RECEIPT(R_A) ---------->|-------------->| M2
  |                  |                 |--- append CONTINUATION_RECEIPT(R_B) ----->|-------------->| M3
  |                  |                 |               |              |               |
  |== Brain recovers ================|                |              |               |
  |--- append RECOVERY_DETECTED ---->|------------------------------------------------>| M4
  |                  |                 |               |              |               |
  |<--- report X-A (R_A) ------------|                |              |               |
  |<--- report X-B (R_B) ------------------------------|              |               |
  |--- append COMPLETION_REPORT_A, COMPLETION_REPORT_B ------------->|-------------->| M5
  |                  |                 |               |              |               |
  |== detect split-brain: 2 continuation_ids for cmd X (Section 2.12.1) ============|
  |== result selection (Section 2.6.3.1): ========================================|
  |   IF result_digests agree AND effects idempotent:                           |
  |     - winner = first completed by trusted comparable signed time              |
  |       (signed anchors, NOT executor-local monotonic clocks)                  |
  |     - tie-breaker if signed time agrees: lowest executor_id wins             |
  |     - others marked DUPLICATE_AGREED                                        |
  |   ELSE (divergent results OR non-reversible effects):                       |
  |     - no automatic selection -> MANUAL_REVIEW_REQUIRED                      |
  |     - freeze all affected downstream effects                               |
  |== effect reconciliation (Section 2.6.3.2): ====================================|
  |   IF idempotent: deduplicate by (root_command_id, op_2, slot)               |
  |   IF non-reversible & multiple attempted: freeze + manual review            |
  |== classification: ============================================================|
  |   agreeing+idempotent -> VALID_CONTINUATION (winner) + DUPLICATE_AGREED      |
  |   divergent / non-reversible -> CONFLICTING_REPORTS / MANUAL_REVIEW_REQUIRED|
  |                  |                 |               |              |               |
  |  [AGREE path drawn below]         |               |              |               |
  |--- append RECONCILED: winner=ExecA (signed time earlier or executor_id lower)|
  |--- append DUPLICATE_AGREED: ExecB ------------------------------------------------------------>| M6
  |--- append COMMAND_SUCCEEDED ----------------------------------------------------------------->| M7
  |                  |                 |               |              |               |
  |  [DIVERGE path: not drawn in detail]                                                         |
  |   -> append CONFLICTING_REPORTS, EFFECTS_FROZEN, MANUAL_REVIEW_REQUIRED                     |
  |   -> freeze downstream resource; enqueue for Op                                              |
  |                  |                 |               |              |               |
  Note: No silent conflict resolution. Both reports, both receipts, both journals
        are retained in the ledger. The frozen downstream resource stays frozen
        until an operator resolves the manual review queue entry.
```

Guards and notes:
- Lease exclusivity (Section 2.1.1) means the Brain dispatched to only one executor; the split-brain condition arises when a second executor independently continues (e.g., a stale lease, peer propagation, or operator error). Detection is by two distinct `continuation_id` values for the same `command_id` (Section 2.12.1).
- Ordering across machines uses trusted comparable signed time only (Section 2.6.3.1). Executor-local monotonic clocks are never compared.
- Downstream dedup key is `(root_command_id, operation_id, side_effect_slot)` — identical for both attempts (Section 2.5.1). This is what makes the agree-path safe.
- The diverge path is explicitly not auto-resolved; it freezes effects and routes to manual review (Section 2.12.2).

---

### Diagram 5 — Brain Recovery During Active Continuation (Operation Atomicity Rule)

Scope: ADR-MC-001 Sections 2.12.2 (row "Brain recovers while continuation active"), 2.15 (recovery protocol steps 1–3), 2.9 (side-effect class). Shows the Brain recovering mid-continuation and the executor applying the operation atomicity rule: committed/irreversible operations are finished and reported; uncommitted operations are aborted. The same operation is never both finished and aborted.

```
 Brain              Exec               Wit             Down            Ledger
  |                  |                  |              |               |
  |--- issue L0+C0 ->|                  |              |               |
  |== Brain unavailable ===============|              |               |
  |                  |== outage declared; eligibility ok ============|
  |                  |== continue: op_2 in progress =================|
  |                  |--- append ELIGIBILITY_DECIDED, OP_2_START --->|-------------->| M1
  |                  |                  |              |               |
  |== op_2 has TWO sub-states: committed vs not-yet-committed ======|
  |                  |                  |              |               |
  |== Brain recovers (available >= brain_recovery_confirmation_period) by direct signal + witness |
  |--- append RECOVERY_DETECTED ------------------------------------>|-------------->| M2
  |--- notify Exec via heartbeat channel: "RECOVERED, stop continuing" ->|         |
  |                  |<-- RECOVERED signal ---|         |              |               |
  |                  |== STOP accepting new continuation operations ==|
  |                  |                  |              |               |
  |                  |== ATOMICITY RULE per in-progress op (Section 2.15 step 2): |
  |                  |   FOR op_2:                                                     |
  |                  |     IF op_2 already committed OR irreversible:               |
  |                  |       - finish op_2 (do not abort)                              |
  |                  |       - report its result                                       |
  |                  |     ELSE IF op_2 not yet committed:                             |
  |                  |       - abort op_2 (do not finish)                              |
  |                  |       - report ABORTED                                          |
  |                  |     NEVER both finish and abort the same op state              |
  |                  |                  |              |               |
  |   [SUB-CASE 5a: op_2 already committed to Down]                   |
  |                  |--- finish op_2 (finalize side effect) -------->|
  |                  |<-- final ack ----|              |               |
  |                  |--- append OP_2_COMMITTED ---------------------->|-------------->| M3
  |                  |                  |              |               |
  |   [SUB-CASE 5b: op_2 NOT yet committed]                           |
  |                  |== abort op_2 (no external effect emitted) =====|
  |                  |--- append OP_2_ABORTED ------------------------>|-------------->| M4
  |                  |                  |              |               |
  |   [SUB-CASE 5c: op_2 irreversible mid-flight (Class 3 attempted — prohibited)]
  |                  |== Class 3 is PROHIBITED during continuation (Section 2.9) ===|
  |                  |== if attempted anyway: INVALID_CONTINUATION; freeze; security |
  |                  |   event; manual review (not drawn in detail) =================|
  |                  |                  |              |               |
  |                  |== generate receipt R (records finished and/or aborted ops) ==|
  |                  |--- append CONTINUATION_RECEIPT(R) ------------>|-------------->| M5
  |                  |                  |              |               |
  |            [within completion_report_deadline]                    |
  |<--- completion report (R + journal) ---|         |              |               |
  |--- append COMPLETION_REPORT ------------------------------------>|-------------->| M6
  |                  |                  |              |               |
  |== reconcile (Diagram 6) -> RECONCILING -> terminal ============|
  |--- append RECONCILING, then RECONCILED/INVALID/CONFLICT -------->|-------------->| M7
  |                  |                  |              |               |
  Note: The atomicity rule prevents the dual-hazard where a recovering Brain
        simultaneously tells some executors to finish and others to abort the
        same operation. Each executor decides per its own op state, and the
        rule is "finish committed, abort uncommitted" — never both.
        Class 3 side effects are never permitted during continuation; an
        attempted Class 3 effect is itself a violation (Section 2.9).
```

Guards and notes:
- The recovery signal is delivered through the heartbeat channel (Section 2.6.1) and is time-anchored and signed.
- The atomicity rule (Section 2.15 step 2) is local to each executor's view of its own operation state. There is no global "finish all" or "abort all" instruction.
- If `op_2` was already committed to Down before recovery, the executor finishes/finalizes it and reports; Down already holds the effect and reconciliation will deduplicate it (Diagram 6).
- If `op_2` had not committed, the executor aborts and reports ABORTED; no external effect was emitted, so there is nothing for reconciliation to undo at Down (though the Brain may later authorize a replay — Diagram 7).

---

### Diagram 6 — Reconciliation After Recovery

Scope: ADR-MC-001 Sections 2.6 (reconciliation protocol), 2.6.3.1 (result selection), 2.6.3.2 (effect reconciliation), 2.6.3.3 (compensation), 2.6.3.4 (manual review), 2.6.4 (classifications), 2.15 (recovery protocol steps 4–9). Shows the four reconciliation concerns in order and the classification outcomes.

```
 Brain              ExecA             ExecB            Down            Op            Ledger
  |                  |                 |               |               |              |
  |== recovery confirmed; reports collected within completion_report_deadline ======|
  |--- append RECOVERY_DETECTED, REPORTS_COLLECTED -------------------------------->|-------------->| M1
  |                  |                 |               |               |              |
  |== STEP 1: RESULT SELECTION (Section 2.6.3.1) ====================================|
  |   reports: {X-A: R_A, result_digest=dA, effects E_A}                             |
  |            {X-B: R_B, result_digest=dB, effects E_B}                            |
  |   CASE 1: single valid report -> select it                                       |
  |   CASE 2: multiple, dA==dB, effect identities match ->                          |
  |     winner = first completed by trusted comparable signed time;                  |
  |     tie-breaker lowest executor_id; others DUPLICATE_AGREED                      |
  |   CASE 3: dA != dB (divergent) -> no auto select -> MANUAL_REVIEW_REQUIRED       |
  |   CASE 4: invalid continuation -> discard; flag executor                         |
  |                  |                 |               |               |              |
  |  [CASE 2 drawn: dA==dB, idempotent effects]                                     |
  |== winner = ExecA (signed time earlier; else lowest executor_id) =================|
  |--- append RESULT_SELECTED: ExecA ------------------------------------------------>|-------------->| M2
  |--- append DUPLICATE_AGREED: ExecB ----------------------------------------------->|-------------->| M3
  |                  |                 |               |               |              |
  |== STEP 2: EFFECT RECONCILIATION (Section 2.6.3.2) ===============================|
  |   FOR each effect identity (root_command_id, op_id, slot) across A and B:       |
  |     IF identity already applied at Down -> mark DUPLICATE; do not re-apply      |
  |     IF identity new and result authoritative -> apply                            |
  |     IF identity conflicts with another applied effect -> freeze; manual review   |
  |     IF non-reversible and multiple attempted -> freeze; manual review            |
  |     IF Class 3 (high-risk/irreversible) -> freeze; manual review (always)       |
  |--- query Down: which (root_command_id, op_id, slot) already applied? ---------->|
  |<-- applied set ----------------------------------------------------|              |
  |== apply any authoritative-but-unapplied effects; mark duplicates ===============|
  |--- append EFFECTS_RECONCILED ---------------------------------------------------->|-------------->| M4
  |                  |                 |               |               |              |
  |== STEP 3: COMPENSATION (Section 2.6.3.3) ========================================|
  |   IF a losing executor emitted a reversible/idempotent effect that diverges:    |
  |     - Brain issues a COMPENSATION command (own lease, own idempotency key,       |
  |       own audit chain) to reverse/re-issue                                      |
  |   IF effect is irreversible/destructive: NO automatic compensation              |
  |     -> escalate to manual review                                                |
  |  [drawn: ExecB emitted reversible effect E_B that diverges from winner E_A]     |
  |--- issue compensation command C_comp (new lease) to ExecB ---------------------->|              |
  |                  |                 |--- reverse E_B / re-issue E_A with E_A idempotency ---->|
  |                  |                 |<-- ack ------|              |               |
  |                  |                 |--- append COMPENSATION_APPLIED ------------>|-------------->| M5
  |                  |                 |               |               |              |
  |== STEP 4: MANUAL REVIEW ROUTING (Section 2.6.3.4) ===============================|
  |   IF divergent results, non-reversible effects, disputed capability,           |
  |      unknown revocation/cancellation at continuation time, or                  |
  |      any non-deterministic step:                                               |
  |     -> freeze affected downstream resource                                      |
  |     -> enqueue manual review entry with all evidence, receipts, journals         |
  |     -> command stays MANUAL_REVIEW_REQUIRED until Op resolves                   |
  |  [drawn: a divergent subset exists for op_3]                                    |
  |--- append EFFECTS_FROZEN(op_3), MANUAL_REVIEW_QUEUED --------------------------->|-------------->| M6
  |--- notify Op ------------------------------------------------------>|------------>| M7
  |                  |                 |               |               |              |
  |== STEP 5: CLASSIFICATION (Section 2.6.4) ========================================|
  |   VALID_CONTINUATION        -> SUCCEEDED                                         |
  |   VALID_BUT_RECONCILED      -> RECONCILED (compensation applied) -> SUCCEEDED    |
  |   INVALID_CONTINUATION      -> executor flagged; effects frozen; REVIEW          |
  |   CONFLICTING_REPORTS       -> MANUAL_REVIEW_REQUIRED                           |
  |   MANUAL_REVIEW_REQUIRED     -> awaiting Op                                      |
  |--- append CLASSIFICATION(VALID_BUT_RECONCILED for A; MANUAL_REVIEW for op_3) ---->|-------------->| M8
  |                  |                 |               |               |              |
  |== STEP 6: POLICY REFRESH + WATERMARK (Section 2.15 step 8) =====================|
  |--- broadcast refreshed policy snapshot + revocation watermark ----------------->| ExecA, ExecB |
  |--- append POLICY_REFRESHED ------------------------------------------------------>|-------------->| M9
  |                  |                 |               |               |              |
  |== STEP 7: AUDIT COMPLETION (Section 2.15 step 9) ===============================|
  |--- append RECONCILIATION_COMPLETE, COMMAND_TERMINAL ---------------------------->|-------------->| M10
  |                  |                 |               |               |              |
  |  [Op resolves manual review entry for op_3 out-of-band; not part of automatic |
  |   reconciliation. Resolution appends a MANUAL_REVIEW_RESOLVED event.]           |
```

Guards and notes:
- The four concerns run in order: result selection → effect reconciliation → compensation → manual review (Section 2.6.3). Compensation may issue a new command with its own lease and audit chain (Section 2.6.3.3).
- Result selection by timestamp is permitted **only** when all reported effects are provably idempotent and equivalent (Section 2.6.3.1). The divergent `op_3` subset bypasses timestamp selection and goes to manual review.
- Effect reconciliation queries Down for the already-applied set keyed by stable identity, not by executor or attempt (Section 2.5.1).
- Irreversible/destructive effects never auto-compensate (Section 2.6.3.3). They freeze and route to `Op`.
- Policy refresh and revocation watermark refresh (Section 2.15 step 8) happen before any new work is accepted.

---

### Diagram 7 — Replay Authorization and Execution

Scope: ADR-MC-001 Section 2.7 (replay semantics), 2.5.1 (replay identity rule — `root_command_id`), 2.6 (reconciliation must precede replay), 2.15 step 7. Shows the Brain authorizing a replay only after reconciliation, and the executor preserving the original external-effect identity.

```
 Brain              Exec               Down            Ledger
  |                  |                  |               |
  |== prior: cmd X continuation was reconciled but did not complete (e.g., ABORTED, |
  |   or SUCCEEDED with missing effects). Brain determines replay is warranted. ====|
  |--- append REPLAY_AUTHORIZED(X) ------------------------------------>|-------------->| M1
  |                  |                  |               |
  |== Brain MUST reconcile all continuation reports BEFORE authorizing replay.   |
  |   Unknown or unreconciled effect status BLOCKS replay or requires            |
  |   compensation/manual review first (Section 2.7).                            |
  |                  |                  |               |
  |--- issue NEW lease L_R + NEW execution identity replay_attempt_id --------->|
  |    cmd record X' created; X' is EXECUTION METADATA ONLY                       |
  |    X' is NOT the identity root for external effects                           |
  |    original cmd X marked REPLAYED; X' linked to X by causation                |
  |--- append LEASE_ISSUED(L_R), COMMAND_REPLAYED(X -> X') ---------------------->|-------------->| M2
  |                  |                  |               |
  |                  |== replay executes op_1, op_2, op_3 =====================|
  |                  |== CRITICAL: external-effect identity for each op derives  |
  |                  |   from root_command_id = X (the ORIGINAL command),       |
  |                  |   NEVER from X' (the replay-attempt command record)       |
  |                  |   stable key = (X, op_id, slot)  [Section 2.5.1, 2.7]    |
  |                  |                  |               |
  |                  |--- perform op_1 with identity (X, op_1, slot) ---------->|
  |                  |   [Down checks: already applied by original X or any     |
  |                  |    prior continuation? if yes -> DUPLICATE, skip]         |
  |                  |<-- ack (applied or duplicate) --|               |
  |                  |--- append OP_1_REPLAYED (identity = (X,op_1,slot)) ----->|-------------->| M3
  |                  |                  |               |
  |                  |--- perform op_2 with identity (X, op_2, slot) ---------->|
  |                  |<-- ack ----------------|               |
  |                  |--- append OP_2_REPLAYED ------------------------------>|-------------->| M4
  |                  |                  |               |
  |                  |--- perform op_3 with identity (X, op_3, slot) ---------->|
  |                  |<-- ack ----------------|               |
  |                  |--- append OP_3_REPLAYED ------------------------------>|-------------->| M5
  |                  |                  |               |
  |<--- complete (final result) ---|                  |               |
  |--- append COMMAND_SUCCEEDED(X') ----------------------------------->|-------------->| M6
  |--- append LEASE_CLOSED(L_R) ---------------------------------------->|-------------->| M7
  |                  |                  |               |
  Note: Executors must NOT autonomously replay during continuation (Section 2.7).
        Replay is always Brain-authorized, post-reconciliation. The replay-attempt
        command record X' is metadata; using X' in the effect identity would bypass
        deduplication against effects already produced by X or any prior
        continuation of X. Implementers must never use X' in the stable key.
```

Guards and notes:
- Replay is preceded by reconciliation. If any effect status is unknown or unreconciled, replay is blocked or routed through compensation/manual review (Section 2.7).
- The replay-attempt command record `X'` gets a new lease and a new `replay_attempt_id`, but `X'` is execution metadata. The stable external-effect identity always uses `root_command_id = X` (Section 2.5.1 replay identity rule).
- Downstream dedup is what makes replay safe: any op already applied by `X` or a prior continuation of `X` is rejected as a duplicate by identity, not re-applied.

---

### Diagram 8 — Revocation During Outage

Scope: ADR-MC-001 Sections 2.1.4 (capability revocable through signed revocation stream), 2.10 (revocation/cancellation watermark), 2.3 (eligibility — no revocation observed above watermark), 2.15. Shows the executor observing a revocation stream entry mid-outage and stopping immediately, and the fail-closed behavior when the watermark is stale.

```
 Brain              Exec               Wit             Down            Ledger
  |                  |                  |              |               |
  |--- issue L0+C0 ->|                  |              |               |
  |== Brain unavailable ===============|              |               |
  |                  |== outage declared; eligibility ok; continuing =|
  |                  |--- append ELIGIBILITY_DECIDED, OP_2_START --->|-------------->| M1
  |                  |                  |              |               |
  |== Brain (or surviving revocation channel) publishes a signed revocation        |
  |   stream entry for cmd X (e.g., operator cancels; policy emergency deny):     |
  |   {seq=42, tenant_id, command_id=X, capability_id=C0, REASON, signed, time}   |
  |--- append REVOCATION_ENTRY(seq=42) -------------------------------->|-------------->| M2
  |                  |                  |              |               |
  |== revocation stream is survivable (signed stream / witness broadcast;         |
  |   Section 2.11 emergency deny channel). Exec can receive it even mid-outage.  |
  |                  |                  |              |               |
  |~~~ revocation entry (seq=42) ~~~~~~~~~~~~~~>| (via witness broadcast or stream)|
  |                  |<-- revocation entry (seq=42) ---|              |               |
  |                  |== update revocation_watermark_observed = 42 ==|
  |                  |== Section 2.10: "If executor receives a revocation entry   |
  |                  |   during outage, it must stop immediately" =================|
  |                  |== ABORT in-progress op_2 (apply atomicity rule:            |
  |                  |   if not committed -> abort; if committed -> finish+report)|
  |                  |--- append OP_2_ABORTED (or OP_2_COMMITTED if already done) ->|-------------->| M3
  |                  |== STOP continuation; enter safe-hold =====================|
  |                  |--- append CONTINUATION_STOPPED(reason=REVOCATION_OBSERVED) ->|-------------->| M4
  |                  |                  |              |               |
  |== Brain recovers ================|              |               |
  |<--- completion report (ABORTED + reason) ---|    |              |               |
  |--- append COMPLETION_REPORT, RECONCILED -------------------------->|-------------->| M5
  |                  |                  |              |               |
  |  [CONTRAST CASE: stale watermark at lease expiry]                              |
  |                  |== at expiry, revocation_watermark_observed < C0.revocation_  |
  |                  |   watermark_required  OR cache age > max_revocation_cache_age|
  |                  |== Section 2.10: fail-closed -> STOP, no continuation ======|
  |                  |--- append ELIGIBILITY_DECIDED = STOP (stale watermark) ---->|-------------->| M6
  |                  |                  |              |               |
  |  [CONTRAST CASE: cancellation observed in cached events at/before watermark]   |
  |                  |== cancellation for cmd X in cached ledger events up to      |
  |                  |   watermark -> continuation forbidden (Section 2.3) ======|
  |                  |--- append ELIGIBILITY_DECIDED = STOP (cancellation) -------->|-------------->| M7
  |                  |                  |              |               |
  Note: Absence of evidence is not evidence of absence (Section 2.10). A missing or
        stale watermark is treated as "could be revoked" and blocks continuation.
        High-risk/legal/financial/destructive/irreversible commands default to STOP
        and may not continue without fresh revocation knowledge.
```

Guards and notes:
- The revocation stream is signed, monotonic, and tenant-partitioned (Section 2.10). It is the survivable channel for emergency denies (Section 2.11).
- Receiving a revocation entry mid-outage is an immediate stop (Section 2.10 "Revocation during outage"). The atomicity rule still applies to any in-flight op (Diagram 5).
- The two contrast cases (M6, M7) illustrate fail-closed behavior: stale watermark or observed cancellation both force STOP.

---

### Diagram 9 — Outage Evidence Verification by Downstream System

Scope: ADR-MC-001 Section 2.1.4 (downstream must verify outage evidence bound to capability + command; capability alone is insufficient while Brain is healthy). Focuses on the downstream validation logic and the reject paths. This diagram zooms into the downstream validation block referenced in Diagram 2.

```
 Exec               Down               Brain (if reachable)   Ledger
  |                  |                    |                      |
  |== Exec in continuation; presents effect for op_2 with: ==|
  |   - signed capability token C0                          |
  |   - outage_evidence bundle B =                          |
  |       {outage declaration record,                       |
  |        witness statements (quorum),                     |
  |        signal thresholds crossed,                       |
  |        signed time anchor at declaration,               |
  |        capability_id=C0, command_id=X}                  |
  |   - stable effect identity (X, op_2, slot)              |
  |                  |                    |                      |
  |--- apply effect + C0 + B + identity -->|                  |   |
  |                  |                    |                      |
  |                  |== DOWNSTREAM VALIDATION (Section 2.1.4) ==|
  |                  |  1. Validate C0 signed by Brain, unexpired
  |                  |  2. C0.not_valid_before <= now (signed) <= C0.not_valid_after
  |                  |  3. C0.tenant_id == effect tenant
  |                  |  4. C0.executor_id == presenting executor
  |                  |  5. C0.command_id == X
  |                  |  6. op_2 in C0.permitted_operation_ids
  |                  |  7. slot in C0.side_effect_slot_spec
  |                  |  8. C0.continuation_class permits op_2 (not Class 3)
  |                  |  9. C0 NOT superseded/revoked (check supersession stream)
  |                  | 10. policy_snapshot_hash pinned; not past
  |                  |     policy_snapshot_not_valid_after
  |                  | 11. outage_evidence B present and signed
  |                  | 12. B.capability_id == C0.capability_id
  |                  | 13. B.command_id == X
  |                  | 14. B witness quorum valid (distinct, fresh, non-replayed)
  |                  | 15. B signal thresholds crossed (>=2 signals, one direct-Brain)
  |                  | 16. B signed time anchor consistent with C0 window
  |                  | 17. stable identity (X, op_2, slot) not already applied
  |                  |                    |                      |
  |                  |  [IF Brain reachable (healthy): capability ALONE is      |
  |                  |   INSUFFICIENT — B must still be present and valid;     |
  |                  |   if Brain is healthy and B is absent/invalid -> REJECT |
  |                  |   as security event (Section 2.1.4)]                    |
  |                  |                    |                      |
  |                  |  [IF Brain unreachable: B is the proof that the          |
  |                  |   precondition for continuation was satisfied;          |
  |                  |   still validate B cryptographically]                   |
  |                  |                    |                      |
  |                  |== DECISION =====================================|
  |                  |  PASS  -> apply effect, ack, log idempotency key
  |                  |  FAIL  -> reject; freeze; security event; do not apply
  |                  |                    |                      |
  |  [PASS path]     |                    |                      |
  |                  |--- append EFFECT_APPLIED (identity=(X,op_2,slot)) ----->|-------------->| M1
  |<-- ack (applied) |                    |                      |
  |                  |                    |                      |
  |  [FAIL path A: capability valid but outage_evidence missing/invalid]        |
  |                  |== REJECT: capability alone insufficient while Brain    |
  |                  |   healthy (Section 2.1.4) ============================|
  |                  |--- append EFFECT_REJECTED(reason=NO_OUTAGE_EVIDENCE) ->|-------------->| M2
  |<xx reject xx ----|                    |                      |
  |                  |                    |                      |
  |  [FAIL path B: capability superseded (C0 superseded by C1)]                  |
  |                  |== REJECT: Invariant 3a; downstream rejects superseded    |
  |                  |   capability IDs regardless of not_valid_after =========|
  |                  |--- append EFFECT_REJECTED(reason=CAPABILITY_SUPERSEDED) ->|-------------->| M3
  |<xx reject xx ----|                    |                      |
  |                  |                    |                      |
  |  [FAIL path C: stable identity already applied]                              |
  |                  |== REJECT as DUPLICATE by (X, op_2, slot) (Section 2.5.2) |
  |                  |--- append EFFECT_DUPLICATE ----------------------------->|-------------->| M4
  |<-- dup ack ------|                    |                      |
  |                  |                    |                      |
  |  [FAIL path D: Class 3 side effect attempted during continuation]            |
  |                  |== REJECT: Class 3 prohibited during continuation          |
  |                  |   (Section 2.9); security event; freeze; manual review ==|
  |                  |--- append EFFECT_REJECTED(reason=CLASS_3_PROHIBITED),    |
  |                  |   SECURITY_EVENT --------------------------------->|-------------->| M5
  |<xx reject + security event xx ---|    |                      |
  |                  |                    |                      |
  Note: The outage evidence bundle B is the proof that turns "an executor claims
        the Brain was down" into "the precondition for continuation was
        cryptographically satisfied." Without B, a valid capability is not
        authority to produce effects while the Brain is healthy. Downstream
        treats a missing/invalid B as a security event, not a soft skip.
```

Guards and notes:
- Step 11–16 are the heart of Section 2.1.4: the outage evidence is bound to the capability and command and is mandatory. A capability alone is not sufficient.
- Fail path A is the key new rule from Section 2.1.4: capability + no outage evidence = reject, even if the Brain is currently unreachable, because the precondition proof is missing.
- Fail path B enforces Invariant 3a at the downstream boundary.
- Fail path D enforces the Class 3 prohibition (Section 2.9) at the downstream boundary, making it a defense-in-depth check (the executor should already have refused).

---

### Diagram 10 — Cross-Tenant Continuation Attempt (Security Event)

Scope: ADR-MC-001 Sections 2.14 (tenant isolation), 2.1.4 (capability tenant scope), 2.3 (tenant isolation eligibility criterion), 2.13 (audit), threat model row "Cross-tenant continuation." Shows an executor attempting to continue a command outside its tenant scope and the rejection at every layer.

```
 Brain              Exec (tenant A)     ExecB (tenant B)   Wit (tenant A)   Down (tenant B)  Ledger
  |                  |                    |                  |               |               |
  |== dispatch cmd X (tenant B) to ExecB ==| (lease exclusivity per tenant)  |               |
  |--- issue L_B + C_B to ExecB (tenant B) ------------------>|               |               |
  |    C_B.tenant_id = B                                                       |
  |--- append LEASE_ISSUED(L_B), CAPABILITY_ISSUED(C_B) -------------------->|-------------->| M1
  |                  |                    |                  |               |               |
  |== Brain unavailable (tenant B partition) ================================|               |
  |                  |                    |                  |               |               |
  |== Exec (tenant A) somehow obtains/presents C_B (tenant B's capability) ==|               |
  |   (this is the attack: cross-tenant capability use)                      |               |
  |                  |                    |                  |               |               |
  |                  |== Exec (A) eligibility self-check (Section 2.3) ======|
  |                  |  [x] lease expired? (irrelevant — C_B is not Exec A's)|
  |                  |  [ ] TENANT ISOLATION: C_B.tenant_id=B !=              |
  |                  |      execution context tenant_id=A  -> FAIL           |
  |                  |== STOP. Default is STOP; cross-tenant is forbidden. ==|
  |                  |--- append ELIGIBILITY_DECIDED = STOP (tenant mismatch) ->|-------------->| M2
  |                  |--- append SECURITY_EVENT(cross_tenant_capability_presented) ->|------>| M3
  |                  |                    |                  |               |               |
  |  [Suppose Exec (A) bypasses self-check and tries Down (tenant B) anyway]                 |
  |                  |--- present C_B + outage_evidence_B + effect for op_2 -------------------->|
  |                  |                    |                  |               |               |
  |                  |                    |                  |  [Down (tenant B) validation:  |
  |                  |                    |                  |   - C_B.tenant_id == B (ok)    |
  |                  |                    |                  |   - BUT presenting executor's  |
  |                  |                    |                  |     context tenant_id == A     |
  |                  |                    |                  |     != C_B.tenant_id           |
  |                  |                    |                  |   - C_B.executor_id != Exec A  |
  |                  |                    |                  |   -> REJECT: tenant mismatch  |
  |                  |                    |                  |   -> SECURITY_EVENT]            |
  |                  |                    |                  |<xx reject + security event xx |
  |                  |                    |                  |--- append EFFECT_REJECTED(reason=TENANT_MISMATCH) ->|-->| M4
  |                  |                    |                  |--- append SECURITY_EVENT(cross_tenant_effect_attempt) ->|-->| M5
  |                  |                    |                  |               |               |
  |== Brain recovers ================|    |                  |               |               |
  |<--- security alert: cross-tenant capability presentation by Exec (A) ---|               |
  |--- append SECURITY_EVENT_REVIEW ---------------------------------->|-------------->| M6
  |== Brain flags Exec (A); revocation stream may revoke Exec A's leases;   |
  |   manual review; audit chain preserved (Section 2.14, threat model) =====|
  |--- append CROSS_TENANT_INCIDENT ---------------------------------->|-------------->| M7
  |                  |                    |                  |               |               |
  Note: Cross-tenant continuation is forbidden and treated as a security event at
        EVERY layer: executor self-check (Section 2.3 tenant isolation), downstream
        validation (Section 2.1.4 tenant scope), and reconciliation (Section 2.14).
        Capabilities, revocation streams, and witness statements are all
        tenant-scoped; a witness for tenant A cannot declare outage for tenant B
        (Section 2.2.4 tenant partitioning). The incident is never silently dropped.
```

Guards and notes:
- Tenant isolation is enforced at three independent layers: executor eligibility self-check (Section 2.3), downstream capability/effect validation (Section 2.1.4), and reconciliation (Section 2.14). Any one of them rejecting is sufficient; all three reject here.
- Witness statements are tenant-partitioned (Section 2.2.4). A tenant-A witness cannot supply quorum for a tenant-B outage declaration, so `outage_evidence_B` could not have been legitimately assembled by Exec (A).
- The event is appended to the audit ledger as a security event and surfaced for operator review. Silent handling is forbidden.

## 4. Cross-references

| Diagram | Primary ADR-MC-001 sections | Key invariants |
|---|---|---|
| 1 — Normal lease lifecycle | 2.1.1, 2.1.2, 2.1.4, 2.13 | 1, 2, 3, 3a, 6, 11 |
| 2 — Lease expiry with continuation | 2.1.3, 2.2, 2.2.4, 2.3, 2.1.4, 2.4, 2.5, 2.6.2, 2.9, 2.10, 2.13 | 2, 3, 4, 5, 6, 7, 10, 11, 13, 15 |
| 3 — Renewal with capability rotation | 2.1.2, 2.1.4, 2.13 | 3a, 11 |
| 4 — Split-brain | 2.12.1, 2.12.2, 2.5, 2.6.3.1, 2.6.3.2 | 8, 10, 11 |
| 5 — Recovery during continuation | 2.12.2, 2.15, 2.9 | 5, 7, 15 |
| 6 — Reconciliation after recovery | 2.6, 2.6.3.1–2.6.3.4, 2.6.4, 2.15 | 7, 8, 10, 11 |
| 7 — Replay authorization and execution | 2.7, 2.5.1, 2.6, 2.15 | 10, 11 |
| 8 — Revocation during outage | 2.1.4, 2.10, 2.3, 2.11, 2.15 | 13, 15 |
| 9 — Outage evidence verification | 2.1.4, 2.5.2, 2.9 | 2, 3, 3a, 10, 15 |
| 10 — Cross-tenant attempt | 2.14, 2.1.4, 2.3, 2.2.4, 2.13 | 9, 11 |

## 5. Implementation notes (non-binding)

These are planning observations, not requirements. They do not modify ADR-MC-001.

1. **Message numbering.** The `M#` markers are for cross-reference within this document. Implementers should map each `append` to a concrete audit event type in the audit event pipeline (ADR-MC-001 Section 9.1, "Audit event pipeline").
2. **Outage evidence bundle.** Diagram 9 steps 11–16 are the most likely place for a shared validation library consumed by both executor self-check and downstream validation. The bundle shape is fixed by Section 2.1.4 and must be replay-resistant.
3. **Trusted comparable signed time.** Diagram 4's result selection and Diagram 6's compensation ordering both depend on a single signed-time service (ADR-MC-001 Section 2.8, "Signed time anchors"). Executor-local monotonic clocks must never be compared across machines.
4. **Supersession stream.** Diagrams 3 and 9 both require downstream to consult a capability supersession stream, not just time windows. The supersession audit chain (Diagram 1 M6, Diagram 3 M2–M5) is the source of truth.
5. **Atomicity rule locality.** Diagram 5's atomicity rule is per-executor-per-operation-state. There is no global abort/finish broadcast. Implementers should ensure the recovery signal does not carry per-operation finish/abort instructions.

## 6. Non-goals

This document does not:

- Implement any runtime code, service, or protocol.
- Activate `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` (remains BLOCKED).
- Enable cancellation controls (remain DISABLED).
- Modify ADR-MC-001 or introduce new rules beyond faithful expansion of its Section 3 diagrams.
- Authorize deployment of any component listed in ADR-MC-001 Section 9.1.

## 7. Status

| Item | State |
|---|---|
| ADR-MC-001 | ACCEPTED — ratified 2026-08-05 |
| This document | PLANNING ONLY — no runtime code |
| `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` | BLOCKED — implementation not yet certified |
| Cancellation controls | DISABLED |
| Phase 3B | BLOCKED |
| Implementation | NOT AUTHORIZED — architecture approved; planning gate open, safety lock closed |
| Deployment | NOT AUTHORIZED |