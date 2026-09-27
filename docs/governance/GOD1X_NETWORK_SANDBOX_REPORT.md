# SP-GOD1X-OS-NETWORK-SANDBOX-001 — Network Containment Report

**Mission:** Harden the `swarm_runtime` execution backend with OS/runtime-level
network containment so GOD-1X network denial is not only policy-enforced.
**Authorization:** DESIGN / IMPLEMENT / TEST / DOCUMENT ONLY — no GOD-2, no
Dispatch Desk, no external effects, no deployment.

**Baseline:** `main` `051e2594` (PR #326, SP-GOD1X-SWARM-RUNTIME-001 merged).
**Result:** PASS (no external network effect occurred; policy/OS posture wired;
fail-closed enforced; CI-safe fallback honest).

---

## 1. Supported-option inventory

| Option | Platform | Kernel-enforced? | CI-safe? | Adopted |
| --- | --- | --- | --- | --- |
| Admission-class denial (`NETWORKED`/`EXTERNAL_EFFECT`) | any | policy | yes | yes (existing GOD-1X gate) |
| Proxy / escape env-var stripping | any | policy | yes | yes (new) |
| Linux network namespace (`unshare(CLONE_NEWNET)`) | Linux | **yes** | only with `CAP_SYS_ADMIN` | yes, when capable (probe-gated) |
| `container --network=none` | container runtime | **yes** | yes (declared) | yes, when declared |
| Windows job-object / firewall / token restriction | Windows | partial / requires admin | no | **not claimed** — reported unavailable |
| subprocess arg-vector denylist (no `shell=True`) | any | policy | yes | yes (existing) |

Key honest finding: **Windows has no built-in per-process network namespace.**
Without a container/sandbox tool, OS-level enforcement is unavailable. The module
therefore reports `unavailable_fail_closed` on Windows rather than mislabeling
policy as OS.

## 2. Sandbox modes (added)

`swarm_runtime/network_sandbox.py` defines `NetworkSandboxMode`:
`POLICY_ONLY` · `OS_ENFORCED` · `CONTAINER_NETWORK_NONE` · `UNAVAILABLE_FAIL_CLOSED`.

Resolution (`NetworkSandbox.resolve()`) never upgrades posture:
- `POLICY_ONLY` → level `policy_enforced` (always available).
- `OS_ENFORCED` → probes a throwaway child with the same libc-based `unshare +
  no_new_privs + drop-caps` launch hook used for real workers; if the capability
  or hardening sequence is absent it FAILS CLOSED (`unavailable_fail_closed`),
  never downgrades.
- `CONTAINER_NETWORK_NONE` → asserts OS-level (`os_enforced`) only when
  `SWARM_NETWORK_CONTAINER=none` is declared **and**
  `SWARM_NETWORK_CONTAINER_VERIFIED_BY=<trusted component>` identifies the
  orchestration/runtime component that verified the boundary; otherwise unavailable.
- `UNAVAILABLE_FAIL_CLOSED` → denies all executions.

## 3. Configuration (added)

`SWARM_NETWORK_ENFORCEMENT = policy_only | os_enforced | container_network_none |
unavailable_fail_closed` (default `policy_only`). Backward-compatible aliases
`policy`, `os`, and `container` are also accepted. `SWARM_NETWORK_CONTAINER = none`
declares a net=none container, and `SWARM_NETWORK_CONTAINER_VERIFIED_BY` names the
trusted component that verified that boundary.
`SWARM_NETWORK_MODE = deny` is the invariant (no network admission path exists).

## 4. Fail-closed guarantees

- `launch_governed` resolves the sandbox only after the pure admission /
  filesystem / secret-boundary checks pass. If `fail_closed`, the execution is
  DENIED with reason `NETWORK_SANDBOX_UNAVAILABLE` and the receipt records
  `network_enforcement_level = unavailable_fail_closed`.
- Denied authority/env/filesystem requests short-circuit before the sandbox probe,
  so denied work cannot spawn probe subprocesses.
- Network execution classes remain denied at the admission gate (unchanged).
- Proxy / network-escape environment variables (`HTTP(S)_PROXY`, `ALL_PROXY`,
  `GIT_PROXY_COMMAND`, `PIP_INDEX_URL`, …) are stripped from every governed
  worker environment — defense-in-depth even in `POLICY_ONLY`.
- On Linux with a capable kernel, the worker child is launched inside a fresh
  network namespace via `preexec_fn`, then immediately drops namespace-reentry
  capabilities before worker-controlled Python executes (no effect on the
  controller process). If the real child launch fails, the governed receipt is
  terminal `FAILED`; the system does not claim OS enforcement for that worker.

## 5. Tests (`swarm_runtime/tests/test_network_sandbox.py`)

- networked execution class is denied
- shell-based network escape is denied (shell requires explicit authority)
- env-based proxy escape is denied (vars stripped from worker env)
- `OS_ENFORCED` unavailable → fails closed (platform-independent)
- probe uses isolated Python startup and sanitized environment
- documented config aliases normalize to the canonical settings
- CI fallback (`POLICY_ONLY`) does **not** claim OS enforcement
- receipts distinguish `policy_enforced` vs `unavailable_fail_closed`
- `CONTAINER_NETWORK_NONE` requires explicit verification and never installs the
  Linux `preexec_fn`
- unknown enforcement string → fail closed
- live `launch_governed` receipt carries `network_enforcement_level`
- denied authority requests do not spawn the probe
- worker spawn / preexec failure becomes a terminal governed receipt
- namespace hardening hook applies capability drop before worker code

## 6. Mission Control brief state (`omnibrain/principal_brief.py`)

`BriefExecutionState` gains four observed fields (additive, schema-compatible):
`network_policy_status` (`deny`), `network_enforcement_level`,
`network_sandbox_available`, `network_certification`. These surface the real
posture — never "os_enforced" unless actually established, and unobserved portal
defaults fail closed until the route passes a resolved runtime posture.

## 7. Certification status

- `POLICY_ONLY` deployment: **certified — policy_only** (default, CI-safe).
- OS/kernel or container enforcement: **certified — os_enforced** only where the
  capability is genuinely present; otherwise the system reports `unavailable` and
  blocks, it does not pretend.
- No external network effect occurred. No GOD-2 capability admitted. No
  deployment performed. Dispatch Desk inactive. `can_send_external` untouched.

## 8. Stop conditions — all honored

| Stop if… | Status |
| --- | --- |
| any external network effect occurs | not occurred |
| external effects become admitted | not admitted |
| Dispatch Desk becomes active | inactive |
| `can_send_external=true` appears | not present |
| sandbox unavailable treated as pass | rejected — fails closed |
| policy-only mislabeled as OS-enforced | rejected — levels distinct |
