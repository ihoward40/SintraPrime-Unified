# Phase 5A — Capability Matrix

## Capability Intersection

Every execution request receives the **intersection** of:

```
workflow requested permissions
∩ agent permissions
∩ tenant permissions
∩ Principal policy
```

Never the union.

## Phase 5A Capability Registry

| Capability | Phase 5A Status | Notes |
|---|---|---|
| `github.read` | Declared, stub op `github.issue.fetch` | deterministic stub, no network |
| `repository.write_worktree` | Declared, enforced by runner | worktree isolation is Phase B+; runner refuses un-isolated writes |
| `tests.execute` | Declared, stub op `test.changed_scope` | deterministic stub, no side effects |

## Enforcement Points

1. **Workflow definition** — declares `capabilities` (config, not grant).
2. **Run context** — `run.context["permissions"]` is set at start.
3. **ContextPackage** — agent nodes receive `permissions` from run context.
4. **Runner** — permission set is immutable during execution (proven by
   `test_no_authority_escalation`).

## Explicit Non-Capabilities (Phase 5A)

- No deployment capability.
- No merge capability.
- No outbound communication capability.
- No credential access.
- No financial actions.
- No legal/tax filing.
- No destructive operations.

Any capability beyond the manifest requires a documented workflow
extension + Principal policy approval (Phase B+).
