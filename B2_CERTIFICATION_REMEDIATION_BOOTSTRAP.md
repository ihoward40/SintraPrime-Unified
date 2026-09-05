# JARVIS-001 B2 Durability + Runtime Containment Remediation

```text
BASE_SHA = f3e40b92
CURRENT_HEAD = f3e40b92
CURRENT_WORKTREE = DIRTY

HIGH_FINDING = IMPL-DURABILITY-001
DURABLE_MODELS = PRESENT
MIGRATION = PRESENT
DURABLE_LEASE_CAS = PRESENT
SERVICE_WIRING = INCOMPLETE
LEGACY_CONTAINMENT = PARTIAL
POSTGRES = NOT_CERTIFIED

NEXT_ACTION = wire existing B2 runtime services to durable repositories

INVARIANTS =
  INTELLIGENCE != AUTHORITY
  UNKNOWN_EXTERNAL_STATE -> NO_SECOND_MUTATION
  RECEIPT != AUTHORITY
  MEMORY != AUTHORITY
  PROTECTED_STATE_BACKEND != PROCESS_MEMORY

DO_NOT_TOUCH =
  no real providers, credentials, external effects
  no push, PR, deploy
  no unrelated features or architecture redesign
  preserve frozen authority semantics
  stop on migration architecture conflict, cross-tenant defect, or raw-secret persistence requirement

PENDING_CLOSURE =
  durable service wiring
  real PostgreSQL concurrency/restart certification
  complete legacy callable-path containment
  ORM/migration parity
  integrated contract/cross-tenant matrix
  independent Breaker deferred until exact local candidate is green
```
