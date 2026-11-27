# C10 Runtime Evidence

**Task:** `SINTRAPRIME-A2A-C10-PRODUCTION-VALIDATION-001`  
**Commit:** `e7cc42fa57d772a80438917c5d205913f4cf09c9`  
**Evidence timestamp:** `2026-09-26T21:47:20Z`  
**Runtime:** Ubuntu sandbox, Python 3.12, Redis Server 7.0.15 on `127.0.0.1:6390`  
**Mode:** Read/test/report only; external actions disabled.

## Live Redis evidence

An isolated Redis 7.0.15 instance was started on localhost with two ACL identities:

- `c10admin`: administrative test identity, used only to inspect/clear the isolated test database.
- `c10consumer`: restricted to the `c10:*` keyspace and only the commands needed by the transport (`PING`, list operations, and `EXPIRE`).

The default Redis user was disabled.

Observed results:

```json
{
  "authorized_delivery": true,
  "ack_removed_inflight": true,
  "reclaim_count": 1,
  "dlq_length": 1,
  "external_intent_rejected": true,
  "audit_records": 6,
  "unauthorized_ping_output": "NOAUTH Authentication required."
}
```

The restricted consumer was also denied the administrative `FLUSHDB` command, proving ACL scope was active. The Redis instance was shut down after validation.

### Live Redis limitation

The validation instance used `--save "" --appendonly no`, so **Redis restart persistence was intentionally not claimed**. A production-like AOF/RDB configuration and restart test remains required.

## Runtime identity evidence

Configured test credential mapping:

```json
{
  "c10-token": {
    "agent_id": "orchestrator",
    "tenant_id": "tenant-a"
  }
}
```

Observed:

| Probe | Result |
|---|---:|
| Valid token and tenant | PASS |
| Unknown token | Rejected |
| Wrong tenant | Rejected |
| Dispatch Desk sender authorization | Rejected |
| Inactive/blocked specialist authorization | Rejected |

The probe used a test-only `A2A_APPROVAL_HMAC_SECRET`; no secret value is stored in this report.

## Store durability and integrity evidence

Fresh instances reconstructed these stores successfully from their files:

- `A2AAuditStore`: record readable after reconstruction; integrity check passed.
- `ApprovalStore`: issued receipt readable after reconstruction; integrity check passed.
- `DurableOutbox`: pending record readable after reconstruction; integrity check passed.

The C7 concurrent-writer test also wrote 40 audit records and verified sequence continuity from `1` through `40`.

## Test evidence

### Focused governance and red-team lane

```text
python -m pytest -q \
  orchestration/tests/test_a2a_redteam.py \
  orchestration/tests/test_a2a_governance.py \
  orchestration/tests/test_redis_a2a.py

34 passed
```

### Existing protocol regression lane

```text
python -m pytest -q agent_protocol/tests/test_agent_protocol.py

all tests passed
```

This lane was run as a separate process because its legacy synchronous helper assumes a persistent event loop. Combining it after async pytest lanes causes a test-runner lifecycle failure; the independent protocol lane passes.

## Safety evidence

- Registry inspection: all `can_send_external` values are `false`.
- `dispatch_desk` remains `blocked`.
- Dry-run worker tests confirm executor callbacks are not invoked while disabled.
- No external network action, email, filing, publishing, deployment, payment, or third-party contact occurred.

## Unresolved validation gaps

1. Redis persistence across restart with production AOF/RDB settings.
2. Redis ACL and consumer-group validation in the production topology.
3. Production identity-provider integration and credential rotation/revocation.
4. Multi-host or network-mounted filesystem locking behavior.
5. Complete deployed-route inventory and live-service bypass testing.

These gaps make the C10 result **PARTIAL**, not production certification.
