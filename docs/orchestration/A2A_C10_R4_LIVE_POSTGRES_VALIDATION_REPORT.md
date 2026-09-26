# C10-R4 Live PostgreSQL Validation Report

**Baseline:** `3d7006d6e71c89a042f4a06a64f4bf96f154fefe`  
**Validation runtime:** PostgreSQL 16.15 on localhost  
**Status:** PARTIAL — live local validation passed; production topology and fully integrated shadow dual-write remain pending.

## Safety boundary

This was an isolated local test database. No production database, external executor, email, filing, publishing, payment, deployment, or third-party contact occurred. Dispatch Desk remained blocked and no registry profile had `can_send_external=true`.

## Bootstrap

- Created isolated database `a2a_c10r4`.
- Applied `orchestration/postgres_schema.sql` cleanly.
- Created a restricted non-owner application role.
- Enabled tenant RLS policies on all seven A2A tables.
- Granted only schema, table, and sequence privileges required for the test role.
- Detected and corrected one schema/adapter mismatch: outbox terminal transitions required a `reason` column that was missing from the first schema draft. The schema was updated and the entire database was recreated before the passing run.

## Live results

The corrected harness passed:

```text
RLS cross-tenant read blocked
approval issue/use/reuse passed
concurrent approval exactly-one winner passed
outbox idempotency/concurrent claim/stale lease passed
transaction rollback passed
```

The database reported:

```text
PostgreSQL 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
```

## Interpretation

The local PostgreSQL adapter now has live evidence for schema bootstrap, tenant isolation, one-time approval consumption, concurrent approval locking, idempotency uniqueness, concurrent outbox claims, stale lease rejection, and transactional rollback.

This does not certify production. Remaining gates include production PostgreSQL topology, backup/failover, migration tooling, RLS policy review, integrated shadow writes across every lifecycle path, and crash/restart proof under the deployed connection and worker topology.

## Repository validation after C10-R4 changes

```text
Focused C10/A2A lane: 49 passed
Standalone agent_protocol lane: passed
Complete repository suite: all collected tests passed, exit code 0
```
