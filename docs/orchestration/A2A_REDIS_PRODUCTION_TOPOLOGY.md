# A2A Redis Production Topology Assessment

## Tested local topology

| Property | C10-R1 evidence |
|---|---|
| Redis version | 7.0.15 |
| Bind address | `127.0.0.1` |
| Test ports | 6390 for ACL delivery test; 6391 for AOF restart test |
| A2A namespace | `c10:*` / `r1b:*` in isolated tests |
| Persistence proof | AOF enabled, `appendfsync always`, `save ""` on port 6391 |
| Consumer identity | Restricted `c10consumer` in ACL test; password-authenticated default user in AOF test |
| In-flight key | `<namespace>:inflight:<agent_id>` |
| Inbox key | `<namespace>:inbox:<agent_id>` |
| DLQ key | `<namespace>:dlq:<agent_id>` |
| Delivery ID | UUID5 derived from message ID |
| Retry state | Stored in in-flight envelope and preserved through requeue |
| ACK behavior | `LREM` removes the matching in-flight envelope |
| Reclaim behavior | Visibility timeout removes/requeues or moves to DLQ |

## Live ACL result

The isolated ACL test configured a restricted consumer with access to the `c10:*` keyspace and only the required list, expiry, and ping commands. The default Redis user was disabled. Observed results:

- Authorized transport operations succeeded.
- Unauthenticated `PING` returned `NOAUTH Authentication required.`
- Restricted consumer was denied administrative `FLUSHDB`.
- Raw external-action intent was rejected and audit-linked.

## AOF restart result

With AOF enabled and `appendfsync always`:

```json
{
  "inflight_before": 1,
  "inflight_after": 1,
  "dlq_before": 1,
  "dlq_after": 1,
  "acked_inflight_before": 0,
  "acked_inflight_after": 0,
  "inflight_survived": true,
  "dlq_survived": true,
  "acked_absent": true
}
```

The AOF proof used separate worker queues to avoid conflating reclaim behavior across consumers.

## Production topology decision

The actual production Redis endpoint, ACL users, consumer groups, TLS, Sentinel/Cluster mode, and namespace have not been supplied. Therefore this document is a **validated local topology assessment**, not production topology certification.

Before production use, require:

1. TLS and secret-manager provisioned credentials.
2. Explicit ACL users for producers, consumers, operators, and monitoring.
3. Key-prefix isolation per tenant/environment.
4. AOF/RDB durability decision and restore test.
5. Consumer-group or equivalent worker ownership decision.
6. Redis restart and failover test with in-flight and DLQ assertions.
