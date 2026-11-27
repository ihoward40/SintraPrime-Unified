# C10 Validation Matrix

**Commit:** `e7cc42fa57d772a80438917c5d205913f4cf09c9`  
**Timestamp:** `2026-09-26T21:47:20Z`  
**Overall:** `PARTIAL`

| # | Control | Test command / method | Expected result | Actual result | Audit evidence | Result | Limitation |
|---:|---|---|---|---|---|---:|---|
| 1 | Raw memory external-intent bypass | `pytest orchestration/tests/test_a2a_redteam.py` | Reject and audit | `PermissionError`; `raw_external_intent` record | Local JSONL audit record | PASS | Local runtime only |
| 2 | Raw Redis external-intent bypass | Live Redis Python probe | Reject and audit | `PermissionError`; `redis_delivery/blocked` record | Live audit store | PASS | Local Redis only |
| 3 | HTTP external-action bypass | C9 red-team test | Reject and audit | HTTP rejection; blocked audit record | A2A audit JSONL | PASS | Full deployed route inventory pending |
| 4 | Unknown token | Runtime identity probe | Reject | `PermissionError` | Auth failure path is audit-capable | PASS | Static credential map |
| 5 | Wrong tenant | Runtime identity probe | Reject | `PermissionError` | Tenant mismatch path | PASS | Static credential map |
| 6 | Blocked/planned sender | `AgentPolicy.authorize_sender` | Reject | `PermissionError` | API denial path | PASS | Registry fixture |
| 7 | Forged approval | C9 red-team test | Reject | Unsigned receipt rejected | Governance rejection path | PASS | Local test secret |
| 8 | Expired approval | Governance test | Reject | Expired receipt rejected | Governance rejection path | PASS | Local clock |
| 9 | Revoked approval | Approval-store test | Reject | Revoked receipt rejected | Lifecycle audit event | PASS | Local store |
| 10 | Reused approval | Approval-store test | Reject | Used receipt rejected | Lifecycle audit event | PASS | Local store |
| 11 | Wrong-tenant receipt | Governance/C9 tests | Reject | Tenant binding rejected | Governance rejection path | PASS | Static identity source |
| 12 | Payload/attachment drift | Governance/outbox tests | Reject | Hash mismatch rejected | Outbox blocked audit | PASS | Local stores |
| 13 | Dispatch Desk activation | Registry and policy tests | Remain blocked | Status `blocked`; external capability false | Registry/policy evidence | PASS | Production registry deployment pending |
| 14 | Direct executor while disabled | C6 worker test | No side effect | Executor not called; worker blocked dry-run | Outbox blocked audit | PASS | No production executor tested |
| 15 | Terminal outbox replay | C9/C6 tests | Reject replay | Terminal status rejected | Outbox audit | PASS | Local store |
| 16 | Redis ACK | Live Redis probe | Remove in-flight record | `ack()` returned true | Redis delivery audit | PASS | Local Redis |
| 17 | Redis reclaim/retry | Live Redis probe | Requeue after visibility timeout | Reclaim succeeded; retry count preserved | Redis reclaim audit | PASS | Local Redis |
| 18 | Redis DLQ | Live Redis probe | DLQ after retry exhaustion | DLQ length `1` | Redis DLQ audit | PASS | Local Redis |
| 19 | Runtime store restart | Fresh audit/approval/outbox instances | State readable | All restart checks true | Sequence/integrity checks true | PASS | Redis persistence restart not proven |
| 20 | Concurrent JSONL writers | C7 test lane | No corruption/gaps | 40 concurrent audit writes; sequence 1–40 | `integrity_check()` passed | PASS | Actual production filesystem pending |
| 21 | Live Redis ACL | Redis 7.0.15 isolated instance | Unauthorized access rejected | Unauthenticated `PING`: `NOAUTH`; restricted user denied `FLUSHDB` | ACL runtime output | PASS | Production ACL/consumer groups pending |
| 22 | Redis restart persistence | Required C10 runtime proof | In-flight/DLQ survive restart | Not run with persistence-enabled deployment | N/A | PARTIAL | Need AOF/RDB and deployment topology |
| 23 | Multi-host filesystem | Required C10 topology proof | Locking safe across deployment topology | Not available in sandbox | N/A | PARTIAL | Need Docker/shared-volume/network-volume test |
| 24 | Production identity provider | Required C10 runtime proof | Provider-backed principal | Not available; static credential map tested | N/A | PARTIAL | Provider integration pending |

## Commands executed

```bash
python -m pytest -q orchestration/tests/test_a2a_redteam.py \
  orchestration/tests/test_a2a_governance.py \
  orchestration/tests/test_redis_a2a.py

python -m pytest -q agent_protocol/tests/test_agent_protocol.py
```

The legacy protocol suite was run independently because its synchronous helper assumes a persistent event loop; combining it after async pytest lanes causes a test-runner lifecycle failure unrelated to the A2A controls.
