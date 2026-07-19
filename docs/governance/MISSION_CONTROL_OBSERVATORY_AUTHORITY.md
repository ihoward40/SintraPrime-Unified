# Mission Control / Observatory Authority Boundary

Authoritative as of commit 10cad07f046b5675ed10a1fba1aa4a955636f739.

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
`HOLD — architectural reconciliation required`

PR #206 (Observatory G4.7 centralized execution guard) is CONFLICTING against current
`main`, carries +46,704 lines and temporary authorization placeholders, and would
introduce a third execution-control surface alongside Mission Control and
`secure_execution/`. It must be rebased and reconciled into the single shared
protocol above before merge. This document does NOT modify PR #206.

