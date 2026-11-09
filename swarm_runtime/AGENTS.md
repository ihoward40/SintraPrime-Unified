# swarm_runtime — Governed Swarm Execution Runtime

## Purpose

Owns the governed swarm execution backend: subprocess worker launch, admission boundaries, worker lifecycle, artifact persistence, and runtime-side containment/hardening.

## Ownership

- `controller.py`, `governed_execution.py`, `network_sandbox.py`, `worker.py`
- Runtime orchestration/support modules in `swarm_runtime/`
- Runtime-focused tests in `swarm_runtime/tests/`

## Local Contracts

- `SwarmController.launch_governed()` is fail-closed: denied authority or unavailable required containment must not spawn a governed worker.
- `network_sandbox.py` distinguishes policy-only posture from verified OS/runtime containment and must never claim OS enforcement unless the actual boundary is both resolved and launchable.
- Container `network=none` posture is only trusted when a separate verification component is declared; env declaration alone is insufficient.
- Launch failures must terminate the governed `ExecutionResult` and receipt honestly; no governed execution may remain `RUNNING` without a worker process.

## Work Guidance

- Keep sandbox probing side-effect free for the controller process and isolated from inherited Python/dynamic-loader startup hooks.
- Prefer deterministic unit tests with monkeypatched host capability checks; guard any live host netns integration behind an explicit opt-in.

## Verification

- Run `python -m pytest swarm_runtime/tests/test_network_sandbox.py swarm_runtime/tests/test_governed_build_swarm.py`
- Run `python -m pytest omnibrain/tests/test_principal_brief_execution.py portal/tests/test_principal_brief.py`

## Child DOX Index

*(None - runtime files and tests are covered directly here.)*
