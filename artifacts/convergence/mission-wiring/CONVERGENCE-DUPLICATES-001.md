# CONVERGENCE-DUPLICATES-001 — Duplicate / Parallel System Inventory

**Worktree:** `C:/Users/admin/SintraPrime-Unified-w4-registry` @ `05885aa2` · Read-only; nothing moved, deleted, or modified.
**Provenance:** executed directly by the orchestrator after three subagent dispatch attempts failed on provider connection errors. Machine-readable twin: `CONVERGENCE-DUPLICATES-001.json`.

## Counts by convergence priority

```text
P0 (security/control-plane conflict)      = 1
P1 (multiple production implementations)  = 6
P2 (duplicate support infra)              = 1
P3 (organizational clutter only)          = 1
```

## P0

- **Browser executors.** The governed boundary (`mission_wiring/browser_executor.py`) exists only in the unpublished ZD-001 derivative; the reachable production browser surfaces (`apps/.../automation/browserRunner.ts` wired at `index.ts:129`; `browserOperator/l0.ts`+`runBrowserOperator.ts` wired at `executePlan.ts:12-13`) have URL/SSRF policy but **no capability-registry or authority binding**. `operator/browser_controller.py` (canonical Python mechanism per ZD-001 stage-4) has **zero production importers**. This is exactly the W4-5 blocker: `BLOCKED_BY_MISSION_WIRING_PUBLICATION`.

## P1 (one line each)

- **apps/ case-variant pair:** git tracks BOTH `apps/SintraPrime` and `apps/sintraprime` (git ls-tree); on case-insensitive Windows these collide — needs a controlled `git mv` on POSIX CI.
- **Stripe/payments:** `backend/stripe-payments/` (full surface) vs `phase18/stripe_webhooks/` vs `app_builder/stripe_integrator.py` vs `saas/saas_api.py` stub vs `apps/ike-bot` webhook vs `phase19` smoke — payments corrections remain classify-only per doctrine.
- **Agents:** `agents/` (nova/sigma/zero/chat, howard intake) orphaned (zero production importers) vs reachable `swarm_runtime/`+`orchestration/` vs certified `agent_runtime/` being wired by Wave 4; `superintelligence/` unreachable.
- **Workflow engines:** `orchestration/` (canonical, Mission Control consumes) vs `workflow_builder/` (reachability unknown) vs `scheduler/` (executors exist but no non-test callers) vs portal durable engine.
- **Provider routers:** governed `governed_inference/` (16 modules, policy-gated, fail-closed) vs parallel `local_llm/`, `local_models/model_router.py`, `phase17/llm_wiring/`.
- **Memory:** certified `agent_runtime` §21-§23 `MemoryWriteAuthority` (policy/provenance) vs four parallel storage stacks (`memory/`, `core/universe/memory_system.py`, `superintelligence/memory_system.py`, `agent_protocol/shared_memory.py`, plus `twin_layer/shm_ipc.py` adjacent).

## P2

- **Audit logging:** canonical = `portal/models/audit.py`+`audit_record.py` + `add_audit_records.sql` (DB-certified immutable trigger); duplicates = `superintelligence/self_audit.py`, phase18 audit code.

## Root inventory (nothing moved)

16 receipt/phase-completion `.md` files + 9 root scripts (`.bat/.vbs/.ps1/.sh` + `PHASE_11_14_INTEGRATION_ORCHESTRATOR.py`) inventoried in the JSON twin. Reference check (`rg` per filename across code/CI) could **not** be completed this pass — full-tree rg repeatedly timed out on this host. `SAFE_TO_MOVE_LATER = UNKNOWN` for all; the JSON contains a batched-reference-check cleanup plan for a future authorized lane. Nothing was moved.

## Caveats

- `rg` multi-pattern full-tree scans timed out repeatedly on this host; families were evidenced via `git ls-tree`, `os.listdir`, and targeted `search_files` queries. `workflow_builder/` reachability is UNKNOWN.
- Payments remain **classify-only**: no migration, no live payment code changes recommended here.
- `mission_wiring/` is recorded as UNPUBLISHED derivative, not as a production implementation.
