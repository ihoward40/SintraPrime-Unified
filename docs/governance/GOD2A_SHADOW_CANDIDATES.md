# GOD-2A Shadow Candidates

The following operation-specific records are candidates for future shadow certification only:

## E0 read-only candidates

- `a2a.read_messages`
- `evidence_vault.read`
- `repository.read_state`
- `redis.read_status`
- `postgres.read_governance`
- `dispatch.read_queue`
- `connector.read_metadata`

## E1 draft-only candidates

- `a2a.draft_message`
- `evidence_vault.draft_index`
- `repository.draft_change`
- `redis.draft_delivery`
- `postgres.draft_reconciliation`
- `dispatch.draft_packet`
- `connector.draft_payload`

Shadow mode must record the operation, resource, arguments hash, effect class, authority basis, approval requirement, expected postcondition, and rollback/no-mutation basis. Shadow mode performs no external mutation. A draft is structurally distinct from send, submit, post, publish, or file operations.

All candidates remain `SHADOW_ONLY`; none is admitted.
