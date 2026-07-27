# Nova Agent Migration — Deferred Planning Item

**Date:** 2026-07-27
**Status:** DEFERRED
**Deferring phase:** Phase 3.3.3 (Sigma migration)
**Planned future phase:** TBD — requires dedicated risk review and controls design

---

## Why Nova is Deferred

The Nova Agent's LLM call path differs materially from the agents migrated in Phase 3.3 (Chat, Zero, Sigma). Nova's `execute_action()` can dynamically generate a Python handler for an unknown action type using an LLM, then compile and execute that generated code with `exec()`. This creates a distinct risk profile that is not addressed by the standard agent migration checklist.

Key risk factors:

1. **Dynamic code execution**: Generated code is executed in-process via `exec()`, which can affect runtime state, file system, and available globals.
2. **Prompt injection to code injection**: A compromised or manipulated LLM response could produce malicious or destructive code.
3. **Approval boundary**: The dynamic generation is gated by `NOVA_ALLOW_DYNAMIC_EXEC=true`, but the inference call itself currently bypasses the governed control plane.
4. **Audit and attribution**: Generated handlers are registered and executed; their provenance must be traceable in the execution ledger.
5. **Rollback complexity**: While the registry entry can be removed, any side effects from executed generated code are not automatically reversible.

Because of these factors, Nova should not be migrated under the same low-risk cadence as Chat, Zero, and Sigma.

---

## Additional Controls Required

Before Nova can be migrated onto `GovernedInferenceRouter`, the following controls must be designed and implemented:

| Control | Description |
|---|---|
| Execution sandbox | Generated code must run in a restricted environment (e.g., limited builtins, no network/file access unless explicitly declared). |
| Resource limits | CPU/time/memory caps on generated handler execution. |
| Static analysis | Generated code should pass a lightweight safety scan before execution. |
| Immutable provenance | The exact LLM prompt, response, and generated code must be recorded in the execution ledger. |
| Explicit approval | Dynamic handler generation must require explicit human approval regardless of `auto_approve_low_risk`. |
| Capability mapping | The inference request must use a restricted capability/task type (e.g., `dynamic_handler_generation`) with a strict policy. |
| Policy denial defaults | The governed policy should treat dynamic-code generation as a premium/restricted operation requiring explicit authorization. |
| Rollback procedure | A documented procedure to unregister a generated handler and remediate any executed side effects. |
| Test coverage | Dedicated tests for sandbox escape attempts, malformed generated code, and approval enforcement. |

---

## Entry Criteria for a Dedicated Migration Phase

Nova may be scheduled for migration only when:

1. A design document for the sandbox and controls is approved.
2. The execution sandbox is implemented and tested.
3. The Nova Agent test suite includes coverage for dynamic handler generation.
4. The governed inference policy supports a dedicated dynamic-code task type with explicit approval.
5. Isiah Howard authorizes a dedicated migration phase with an explicit risk acceptance statement.

---

## Current State

- Nova's legacy direct OpenAI SDK path remains in `agents/nova/nova_agent.py`.
- The existing Nova Agent tests do not exercise the dynamic generation path.
- No migration work has been performed on Nova during Phase 3.3.

---

## Next Action

Keep this planning item open until the above controls and entry criteria are satisfied. Do not include Nova in routine Phase 3.3.x migration authorizations.
