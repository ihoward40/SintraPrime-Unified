# Authority Model

## Authority Classes (§14)

```text
A0 — read-only
A1 — internal reversible
A2 — external reversible
A3 — consequential
A4 — irreversible/high-impact
```

Persistent collaborative agents default to A0/A1 (fabric
`AgentBehaviorContract.authority_class`). A3/A4 require explicit
authorization per operation — enforced by the invariant
NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY.

## No Authority Manufacture

Core law (directive §1): *Intelligence may recommend and compute.
Authority must come from policy and the Principal.*

Enforced by:
- `InvariantEngine`: NO_AGENT_SELF_APPROVAL,
  NO_AGENT_SELF_PERMISSION_GRANT, NO_UNVERIFIED_AUTHORITY_ESCALATION.
- `GovernanceLinter`: HIGH_AUTHORITY_NO_APPROVAL,
  SELF_CERTIFICATION, PRIVILEGED_PUBLIC_AGENT.
- Fabric actor policies: ALLOWLIST default for sensitive agents.
- Effect receipts record `authorization` per effect (§117).

## Certification Independence (§73, §132)

- `NO_CERTIFICATION_BY_IMPLEMENTER` invariant: an agent that
  implemented work cannot certify it (implementer_id == actor_id is
  blocked).
- `GovernanceLinter.SELF_CERTIFICATION`: static workflow definitions
  where certifier == implementer are rejected.
- This evidence packet is implementer-produced; final certification
  requires the independent certification plane per directive §73.
- Implementer session is not reused for final evaluation (§132).

## Governance Modes (§85)

`GovernanceMode`: LAB, DEVELOPMENT, CERTIFIED, PRODUCTION, RESTRICTED.
Modes restrict which components may run; they never waive
foundational invariants.

## Break-Glass (§83) and Two-Person Rule (§84)

Policy-extensible design only in CF-1: break-glass requires explicit
Principal activation, reason, scope, expiry, heightened audit; the
two-person rule is an optional policy for A4 operations. Neither
waives constitutional invariants automatically.
