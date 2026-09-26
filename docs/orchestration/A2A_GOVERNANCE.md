# A2A governance controls

The A2A transport now separates **internal collaboration** from **external action**.

## Enforced defaults

- External actions are **blocked by default**.
- Unsupported or risky evidence claims are blocked from dispatch.
- Approval receipts bind approval to the exact recipient and final content hash.
- Attachment hashes must match the approved receipt.
- Every message carries a final content hash in its headers for auditability.
- Agent permissions are described in [`orchestration/agent_registry.json`](../../orchestration/agent_registry.json), including the orchestrator plus Blackstone Verifier, Justice Scribe, Source Hunter, Trust Vault Clerk, SintraPrime Builder, Covenant Auditor, and the blocked Dispatch Desk candidate.
- The HTTP dispatch boundary now loads that registry through `orchestration/agent_policy.py`; unknown, planned, disabled, and blocked sender profiles fail closed.
- Raw in-memory and Redis transport seams reject messages that declare external-action intent. This is a Patch C slice, not full bypass certification.
- External approval receipts are now HMAC-bound to the sender, recipient, canonical content hash, attachment hashes, delivery method, receipt ID, and expiry. Set `A2A_APPROVAL_HMAC_SECRET` through deployment secret management; never place it in the registry or source control.
- The HTTP A2A boundary now authenticates opaque agent tokens from `A2A_AGENT_CREDENTIALS`, binds the principal to `agent_id` and `tenant_id`, rejects body/principal mismatches, and audits failed authentication attempts. Credentials must be provisioned through deployment secret management.
- Approval lifecycle events are persisted to `A2A_APPROVAL_STORE` (default `var/a2a_approvals.jsonl`) with fsync-backed issued/used/expired/revoked states. Receipts are one-time and must exist in the durable store before a future external dispatch path can consume them.
- Pending governed dispatch intent can be persisted to `A2A_OUTBOX_STORE` (default `var/a2a_outbox.jsonl`). Restart revalidation checks approval presence/status, registry profile, tenant scope, recipient, and payload hash before an item can become `validated`; no external execution is enabled by this store.
- `ExecutionWorker` processes validated outbox records in dry-run mode by default. It derives an idempotency key, revalidates immediately, prevents terminal-record replay, enforces retry limits, and moves permanent failures to `dlq`; no external executor is called unless a future explicitly reviewed enablement changes the fail-closed defaults.
- Audit, approval, and outbox JSONL writes now use a cross-process `fcntl` lock, fsync, and monotonic sequence numbers. Each store exposes an integrity check that rejects malformed historical lines or sequence gaps; normal reads may ignore only a final partial line.
- Redis delivery now tracks persistent in-flight envelopes, supports explicit `ack`, visibility-timeout `reclaim`, retry counters, and a DLQ after retry exhaustion. Delivery IDs derive from message IDs, retry state survives requeue, and delivery/reclaim/DLQ events can be audit-linked; external intent remains rejected.
- Autonomous self-improvement, deployment, publishing, filing, payments, and third-party contact remain disabled for the default orchestrator profile.

## Evidence classifications

Claims should be explicitly classified as one of:

`PROVEN`, `USER-STATED`, `INFERRED`, `UNVERIFIED`, `UNSUPPORTED`, or `RISKY`.

`UNSUPPORTED` and `RISKY` claims require review before a message can be dispatched.

## Approval receipt

An external action must include:

- `approved_by`
- `approved_output_id`
- `recipient`
- `final_content_hash`
- `attachment_hashes`
- approval timestamp
- delivery method

Changing even one character after approval causes the content hash check to fail.

## Verification matrix

| Control | Status | Proof |
|---|---|---|
| Internal A2A delivery | DONE | Existing A2A tests and Redis transport tests |
| Cross-process Redis delivery | DONE | `orchestration/tests/test_redis_a2a.py` |
| Approval gate for external messages | DONE | `orchestration/tests/test_a2a_governance.py` |
| Evidence gate | DONE | Unsupported/risky claim test |
| Content and attachment hash binding | DONE | Governance validator and mismatch test |
| Agent registry | PATCH A COMPLETE / PATCH C PARTIAL | Runtime sender policy is enforced at the HTTP boundary; all raw-seam and restart-revalidation coverage remains pending |
| Trusted approval receipts | PATCH C2 PARTIAL | Server-issued HMAC verification, sender binding, and expiry checks are test-backed; durable issuance, revocation, and authenticated identity remain pending |
| Authenticated identity / tenant scope | PATCH C3 PARTIAL | Token-to-agent/tenant binding and mismatch auditing are test-backed; production identity provider integration remains pending |
| Durable approval lifecycle | PATCH C4 PARTIAL | Restart-safe issued/used/revoked/expired store and lifecycle audit are test-backed; production approval authority and external dispatch integration remain blocked |
| Durable outbox / restart revalidation | PATCH C5 PARTIAL | Pending intent persistence, revalidation, blocked states, and audit links are test-backed; execution worker, idempotent delivery, and production restart proof remain pending |
| Dry-run execution worker / delivery semantics | PATCH C6 PARTIAL | Dry-run worker, idempotency, retry limits, DLQ, and no-side-effect tests are present; production executor, Redis ACK/DLQ integration, and external enablement remain blocked |
| Multi-process audit / JSONL integrity | PATCH C7 PARTIAL | Cross-process locks, sequence numbers, strict integrity checks, and concurrent-writer tests are present; production filesystem and multi-host guarantees remain pending |
| Redis ACK / retry / DLQ | PATCH C8 PARTIAL | In-flight tracking, ack, reclaim, retry limits, DLQ, retry-state persistence, and FakeRedis tests are present; live Redis/ACL/consumer-group production validation remains pending |
| Durable append-only audit storage | PARTIAL / PATCH B IN PROGRESS | Local JSONL append + fsync and fresh-store recovery are tested; production durable-volume and multi-process guarantees remain pending |
| Restart persistence and bypass-resistance integration test | PENDING | Fresh-store recovery is covered; production restart/revalidation and raw transport bypass tests remain pending |
| Broad external-action enablement | BLOCKED BY DEFAULT | Requires explicit approval and a reviewed agent profile |

The implementation status intentionally distinguishes technical enforcement from rules that only exist in documentation. No agent collaboration capability should be treated as production-complete until it has **proof, enforcement, and an audit trail**.
