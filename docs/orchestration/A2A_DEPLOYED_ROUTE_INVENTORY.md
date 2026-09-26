# A2A Route and Seam Inventory

**Inventory basis:** repository inspection at C10-R1; current orchestration router and A2A modules.  
**Deployment caveat:** this is a source/runtime inventory, not proof of every route exposed by a production gateway.

| Route or seam | Type | Governance label | Auth | Approval | Audit | External side effects |
|---|---|---|---|---|---|---|
| `POST /orchestration/workflows/start` | HTTP | governed workflow route | App-level route policy; verify deployment auth | Workflow-dependent | Workflow state/audit | No direct external action shown |
| `GET /orchestration/workflows/{workflow_id}/status` | HTTP | governed read route | App-level route policy | No | Workflow state | None |
| `POST /orchestration/workflows/{workflow_id}/resume` | HTTP | governed workflow route | App-level route policy | Workflow-dependent | Workflow state/audit | No direct external action shown |
| `GET /orchestration/workflows/{workflow_id}/history` | HTTP | governed read route | App-level route policy | No | Workflow state | None |
| `GET /orchestration/agents/registry` | HTTP | governed registry read | App-level route policy | No | Registry access | None |
| `POST /orchestration/agents/message` | HTTP | governed A2A dispatch | A2A principal dependency | External action requires approval; external path blocked | Accepted/blocked lifecycle audit | External disabled/fail-closed |
| `GET /orchestration/agents/{agent_id}/messages/receive` | HTTP | governed receive route | App-level route policy; inspect deployment auth | No | Receive lifecycle | None |
| `POST /orchestration/workflows/langgraph/run` | HTTP | governed workflow route | App-level route policy | Workflow-dependent | Workflow state/audit | No direct external action shown |
| `GET /orchestration/health` | HTTP | health route | Deployment-dependent | No | Health logging | None |
| `MessageBus.publish` | Memory seam | blocked external raw seam | Caller process boundary | Raw external intent always rejected | Optional audit store records blocked intent | None |
| `RedisA2ATransport.send` | Redis seam | blocked external raw seam | Redis ACL plus caller identity | Raw external intent always rejected | Delivery audit hook | None |
| `RedisA2ATransport.receive/ack/reclaim` | Redis delivery seam | governed transport | Redis ACL/worker identity | Message policy remains upstream | In-flight/reclaim/DLQ audit hooks | None |
| `ApprovalStore.issue/revoke/verify_and_consume` | Approval seam | governed approval lifecycle | Caller must be trusted issuance authority | Signed, tenant-bound, one-time | Lifecycle audit | No external action |
| `DurableOutbox.enqueue/revalidate` | Outbox seam | governed durable intent | Sender policy and tenant scope | Durable approval required for future execution | Blocked/failed audit | No execution by itself |
| `ExecutionWorker.run_once` | Worker seam | dry-run/blocking worker | Runtime policy and store revalidation | Immediate revalidation | Worker/outbox audit | Disabled by default |
| `A2A_AGENT_CREDENTIALS` loader | Identity seam | authenticated principal boundary | Token map in private runtime | N/A | Failed auth audit | None |
| Admin/test-only direct constructors | Test seam | test-only / not externally reachable | Process-local | Tests only | Test evidence | No production side effects |

## Inventory findings

The source-level inventory has no route that enables `can_send_external=true` or activates Dispatch Desk. The primary HTTP dispatch route is governed by authenticated principal, runtime policy, audit, approval, and transport checks. The source tree does not establish the complete production gateway route inventory, so deployed reverse-proxy and service-mount configuration must still be reviewed before production certification.

## Required deployed review

The production deployment owner must export the mounted route list, authentication middleware configuration, Redis consumer entrypoints, admin/test route exposure, and worker process command lines. Each must be reconciled against this inventory and rerun through the C9 bypass matrix.
