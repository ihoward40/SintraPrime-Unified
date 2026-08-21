# SP-LIVE-001 authority state machine

## Governing principle

No side effect may occur without current mission authority, required approval, a certified capability, and evidence-capable execution. State is durable, append-only, compare-and-swap guarded, and hash-linked.

## Happy-path states

```text
RECEIVED
→ PRINCIPAL_IDENTIFIED
→ MISSION_SCOPED
→ MEMORY_RESOLVED
→ SPECIALISTS_DISPATCHED
→ RECONCILED
→ ACTION_PROPOSED
→ APPROVAL_REQUIRED
→ APPROVED
→ CAPABILITY_RESOLVED
→ READY
→ EXECUTING
→ VERIFYING
→ EVIDENCE_RECONCILIATION
→ COMPLETE
```

## Transition guards

| Transition | Required guard/evidence |
|---|---|
| `RECEIVED → PRINCIPAL_IDENTIFIED` | voice/session captured; identity verification succeeds |
| `PRINCIPAL_IDENTIFIED → MISSION_SCOPED` | immutable request hash, purpose, budgets, expiry, consequence ceiling |
| `MISSION_SCOPED → MEMORY_RESOLVED` | allowed memory scopes and retrieval provenance fixed |
| `MEMORY_RESOLVED → SPECIALISTS_DISPATCHED` | isolated roles and delegated non-expanding scopes issued |
| `SPECIALISTS_DISPATCHED → RECONCILED` | outputs sealed; contradictions/confidence handled mechanically |
| `RECONCILED → ACTION_PROPOSED` | exact action envelope canonicalized and hashed |
| `ACTION_PROPOSED → APPROVAL_REQUIRED` | consequence policy says approval required; spoken/display proposal matches hash |
| `APPROVAL_REQUIRED → APPROVED` | Principal identity current; unambiguous approval; hash and expiry bound |
| `APPROVED → CAPABILITY_RESOLVED` | approval still current; certified capability exactly matches action |
| `CAPABILITY_RESOLVED → READY` | kill switches clear; evidence, idempotency, rate, destination, credential lease ready |
| `READY → EXECUTING` | atomic attempt record created; side-effect count was zero; CAS succeeds |
| `EXECUTING → VERIFYING` | terminal receipt or reconciled ambiguous attempt preserved |
| `VERIFYING → EVIDENCE_RECONCILIATION` | independent verifier returns evidence-bound observation |
| `EVIDENCE_RECONCILIATION → COMPLETE` | all acceptance predicates true; chain verifies; briefs delivered |

## Fail-closed and interruption states

- `IDENTITY_AMBIGUOUS` — speaker/session cannot be verified; no mission authority.
- `AUTHORITY_MISSING` — requested operation exceeds mission or delegated authority.
- `APPROVAL_REQUIRED` — stable waiting state; no execution.
- `APPROVAL_INVALID` — ambiguous, wrong Principal/session/hash, or substituted action.
- `APPROVAL_EXPIRED` — approval or mission expiry elapsed.
- `CAPABILITY_UNAVAILABLE` — no exact certified capability.
- `EXECUTION_FAILED` — terminal provider failure with receipt.
- `VERIFICATION_FAILED` — postcondition contradicted or verifier invalid.
- `EVIDENCE_INCOMPLETE` — required receipt, transcript, provenance, or chain element absent.
- `CANCELLED` — Principal or kill switch cancelled before completion.

`FAIL` and `INCOMPLETE` are verdicts derived from terminal/interruption evidence; they do not permit automatic restart.

## Global invalidation events

Identity loss, mission mutation, approval material change, scope/capability drift, destination or parameter change, expiry, cancellation, kill switch, evidence writer failure, or duplicate-attempt detection immediately invalidates `READY` or `APPROVED`. Recovery requires a new proposal and approval; prior approval cannot be reused.

## Concurrency and replay

A mission has one canonical state version. Every transition supplies expected version and previous-event hash. Duplicate messages replay the existing transition result. Competing attempts lose CAS and cannot call a provider. Restart reconstructs state solely from the verified durable chain.
