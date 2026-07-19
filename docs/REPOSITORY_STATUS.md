# Repository Status Taxonomy

## Definitions
- SUPPORTED: maintained, tested in CI, intended for use.
- CERTIFIED: SUPPORTED + explicit compliance/audit certification completed.
- FUNCTIONAL: works but not fully covered by CI or not on supported path.
- PARTIAL: partially implemented; key paths missing.
- EXPERIMENTAL: prototype / POC; not production-intended.
- DOCUMENTED ONLY: described but not verified by automated tests.
- LEGACY: older implementation retained for compatibility.
- DUPLICATED: overlaps another subsystem with unclear authority.
- ORPHANED: unreferenced or disconnected from main flows.
- OBSOLETE: superseded; should be removed.
- UNKNOWN: cannot determine status from current tree.

## Subsystem map
| Subsystem | Status | Basis |
|-----------|--------|-------|
| `portal/` | SUPPORTED | Authoritative backend; CI test lane; merged Mission Control. |
| `web/` | SUPPORTED | React frontend; CI lint/type/build. No exec mutation. |
| `workflow_builder/` | FUNCTIONAL | Engine + API present; not gated by dedicated CI WF test. |
| `scheduler/` | FUNCTIONAL | Executor/dispatcher; arming test verified (PR #164). |
| `agents/` | EXPERIMENTAL | Multiple agent packages; no unified runtime authority. |
| `agent_protocol/` | EXPERIMENTAL | Agent orchestration protocol; separate from durable WF. |
| `core/universe` | EXPERIMENTAL | Exploratory; unclear production role. |
| `observability/` | FUNCTIONAL | Telemetry module; not a control plane. |
| Mission Control (`portal/services/mission_control_*`) | SUPPORTED | Merged PR #212; PG race proof; refusal-only. |
| `secure_execution/` | EXPERIMENTAL | TEE/zero-trust module; not wired to portal RBAC. |
| `trust_law/` | FUNCTIONAL | 19 jurisdictions; test path under trust_law/tests. |
| `legal_integrations/` | FUNCTIONAL | Billing/legal integration context. |
| `backend/stripe-payments/` | DUPLICATED | Separate payment app vs `legal_integrations`; competes for payment authority. |
| `apps/SintraPrime` | LEGACY | Vendored app shell; superseded by `web/` + `portal/`. |
| `apps/sintraprime` | LEGACY | Duplicate naming; legacy. |
| `phase18/mobile_app` | UNKNOWN | Not present on current `main` tree (verify before claiming). |
| `app_builder/` | EXPERIMENTAL | Scaffolding tool. |
| `deployment/` (linux/windows) | DOCUMENTED ONLY | Scripts; no CI deploy verification. |
| `infrastructure/` (aws/azure/gcp) | DOCUMENTED ONLY | Terraform/Bicep present; not applied in CI. |
| Evidence/receipts (`docs/`, `artifacts/`, `mission-control-evidence/`) | SUPPORTED (governance) | Current Mission Control evidence fresh; historical PHASE_* stale. |

> Status is assigned from current `main` tree and CI, not from marketing claims.
> Tests alone do NOT certify a subsystem.

