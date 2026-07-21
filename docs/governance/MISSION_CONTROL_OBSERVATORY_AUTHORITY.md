# Mission Control / Observatory Authority Boundary

Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).

## Mission Control
Owns:
- command intent ledger (`MissionControlCommand`);
- refusal-only command handling (`mission_control_command_guard.py` → `COMMAND_EXECUTION_NOT_ENABLED`);
- permissions (`portal/services/permission_provisioning.py`);
- run-control projection (`mission_control_run_control_service.py`, read-only state machine);
- immutable governance history (`MissionControlRunControlEvent`, hash-chained).

Does NOT currently own:
- runner execution;
- live pause;
- live resume;
- durable workflow mutation.

## Observability
Owns:
- telemetry (`observability/metrics.py`);
- monitoring (`observability/tracer.py`);
- event projection (read models);
- operator visibility (dashboards).

Does NOT currently own:
- command authorization;
- execution permission;
- workflow mutation;
- live pause authority.

## Durable workflow engine
`workflow_builder/` + `scheduler/` own **actual workflow execution truth**. Mission
Control records intent and projection; it does not drive the runner.

## Security certification boundary (PRs #214–#217)

Security certifications from PRs #214–#217 enforce identity claims, tenant scoping,
audit correlation, and transport hardening at the code level. These certifications
do NOT alter the Mission Control boundary. Mission Control remains refusal-only with
no live execution authority. The certifications ensure that when the shared execution
protocol is eventually introduced, the identity, tenant, audit, and transport
controls are already in place.

Specifically certified:
- Identity-claim validation and tenant-scoped authorization (PR #214);
- Audit envelope correlation and non-HTTP authorization (PR #215);
- HTTP request-ID correlation and WebSocket transport hardening (PR #217).

These are CERTIFIED FOR THE RECORDED SCOPE. They do NOT constitute production
certification, compliance certification, or distributed enforcement.

## Future convergence rule
No G4.8 (Observatory) or Increment Two B (Mission Control live pause) work may add
execution authority until ONE shared protocol defines:
- command authorization;
- runner acknowledgement;
- durable state transition;
- failure handling;
- timeout;
- idempotency;
- audit event;
- compensation;
- operator projection.

## PR #206 classification
`CLOSE AS SUPERSEDED`

PR #206 (Observatory G4.7 centralized execution guard) is CONFLICTING against current
`main`, carries +46,704 lines and temporary authorization placeholders, and would
introduce a third execution-control surface alongside Mission Control and
`secure_execution/`. It is 39 commits behind current main and predates the security
certifications from PRs #214–#217. It should be closed as superseded; useful concepts
should be extracted into the shared execution protocol described above. This
document does NOT modify PR #206.