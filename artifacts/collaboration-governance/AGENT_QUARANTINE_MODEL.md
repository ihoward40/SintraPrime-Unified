# Agent Quarantine Model

## State (§47)

```text
QUARANTINED
```

Triggers:

```text
security_violation
capability_violation
repeated_malformed_outputs
repeated_hallucinated_capabilities
loop_behavior
cost_anomaly
data_boundary_violation
poison_event
```

## Effects

Quarantined agents:

- receive **no new tasks** — `EventPolicyEngine` step 3a returns
  `SKIPPED_QUARANTINE` before any model invocation;
- receive **no new capability leases** (lease issuance remains
  governed; quarantine is the gate);
- remain **inspectable** (`AgentQuarantineService.get/list_active`);
- may run only **approved diagnostic tests** (`diagnostic_only=True`).

## Record

```text
AgentQuarantineRecord:
  agent_id, reason, trigger, quarantined_at
  quarantined_by, diagnostic_only, active
```

## Persistence (§141)

Quarantine survives process restart: stored via
`CollaborationStore`; `test_quarantine_survives_restart` reloads the
record from a fresh service instance.

## Policy Integration

```text
EventPolicyEngine(quarantine_service=AgentQuarantineService(store))
```

Wired into the deterministic dispatch chain before event-type
matching — a quarantined agent is never woken, regardless of
subscription.

## Proof Tests

- `test_quarantine_blocks_activation` — engine-level skip
- `test_quarantine_survives_restart` — persistence
- `test_list_active` — inspection
- `test_release_restores` — release path

## Relationship to Poison Events

Poison events quarantine the *event* (DeadLetterQueue →
`PoisonEvent`); agent quarantine quarantines the *agent*. Both
persist; both are inspectable; neither auto-clears.
