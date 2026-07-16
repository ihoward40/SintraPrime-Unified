# Non-Mission Approval Gap

**Status:** Known limitation (G4.6 stabilization)
**Resolution target:** G4.8

## Affected Actions

The following `ExecutionAction` values are non-mission-scoped (they have no
`mission_id` context) but require authorization:

| Action | Governance Gate | Auth Mechanism |
|--------|----------------|----------------|
| `kill_switch.clear` | G-05 | `requires_authenticated_principal=True`, `required_roles={system_admin, incident_commander}` |
| `identity.action` | G-02 | `requires_authenticated_principal=True`, `required_roles={system_admin}` |
| `approval.decision` | None | `requires_authenticated_principal=True`, `required_roles={system_admin}` |

## Schema Limitation

The `Approval` model has:

```python
mission_id: Mapped[UUID] = mapped_column(ForeignKey("observatory_missions.id"), nullable=False)
```

This means persisted approvals can only exist in the context of a mission.
Actions that are not mission-scoped (kill switch, identity, approval decisions)
cannot obtain a persisted `Approval` record.

## Current Authorization Mechanism (G4.7)

For non-mission actions, authorization is enforced through:

1. **`requires_authenticated_principal`** — Step 3b of the execution guard
   checks that a `PrincipalContext` with `is_authenticated=True` is provided.
2. **`required_roles`** — The principal must have one of the specified roles.
3. **`approval=NOT_REQUIRED`** — These actions skip the approval provider entirely.

The `PersistedApprovalProvider` returns `approved=False` with reason
`non_mission_approval_not_implemented` for any action where `mission_id=None`.

## Approval Provider Architecture

### Production: `PersistedApprovalProvider`

- Queries the `Approval` table for mission-scoped actions.
- Returns `approved=False` for non-mission actions (known gap).
- Never synthesizes approval.
- Fails closed on database errors.
- Does not derive authorization from `cleared_by`.
- Does not accept authenticated identity alone as approval for `REQUIRED` actions.

### Test: `TestApprovalProvider` (in `portal/tests/support/`)

- Explicit allowlist of `(subject_id, action)` combinations.
- Deny-by-default.
- Requires `PrincipalContext.for_testing()` (authenticated, method="test").
- Records all queries and resolutions for assertions.
- Never selected through environment variables.
- Never imported by production code.
- Injected via `approval_provider=` parameter.

### Dependency Injection

- `ExecutionGuard.evaluate()` and `require_allowed()` accept `approval_provider=None` (default).
- When `None`, a fresh `PersistedApprovalProvider()` is created — no mutable class variable, no global state.
- Tests pass `TestApprovalProvider(allowed={...})` explicitly.
- No environment-variable bypass exists in the guard.

## Prohibitions

- **No environment-variable bypass** in `ExecutionGuard` or `PersistedApprovalProvider`.
- **No `cleared_by` authorization** — `cleared_by` is attribution only.
- **No arbitrary actor string** accepted as proof of authorization.
- **No mutable global provider** — `ExecutionGuard` has no class-level provider state.
- **No `TestApprovalProvider` import** in production code — it lives in `portal/tests/support/`.

## Planned G4.8 Solution

Introduce system-scoped approvals with a scope discriminator:

```python
class ApprovalScope(str, Enum):
    MISSION = "mission"
    SYSTEM = "system"
    IDENTITY = "identity"
    KILL_SWITCH = "kill_switch"
    ORGANIZATION = "organization"
```

This requires:
- Making `Approval.mission_id` nullable (or adding a separate `scope` column).
- Creating approval records for system-level actions.
- Updating `PersistedApprovalProvider.resolve()` to handle non-mission scopes.
- Migration to add the scope column and update existing records.
- Router/API changes to submit and manage system-scoped approvals.

**Do not make `mission_id` nullable without a full scope and integrity design.**

## Migration Considerations

- Existing `Approval` records are all mission-scoped.
- Adding a `scope` column with default `"mission"` is backward-compatible.
- Making `mission_id` nullable requires updating all queries that join on it.
- Non-mission approval records need a separate unique constraint.

## Unresolved Authorization Risks

1. **No system-scoped approval mechanism exists** — non-mission actions rely
   entirely on principal-based auth (roles). If a role is incorrectly assigned,
   there is no second factor.
2. **Principal authentication is placeholder** — `PrincipalContext.for_testing()`
   with `authentication_method="test"` is not real authentication. G4.8 must
   integrate with an actual identity provider.
3. **No approval revocation** — once an `Approval` record is `APPROVED`, there
   is no mechanism to revoke it before the action executes.
4. **No approval expiry** — approved actions can be executed indefinitely
   after approval.