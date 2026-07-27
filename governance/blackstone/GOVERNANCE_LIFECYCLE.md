# Blackstone Governance Lifecycle

## States

```text
Draft
    ↓
Governance Baseline Candidate (GBC)
    ↓
Governance Baseline (GB)
    ↓
Reference Standard (RS)
```

### Draft

Material under development. Subject to frequent revision. Not yet proposed for baseline.

### Governance Baseline Candidate (GBC)

A complete proposed baseline undergoing review, consistency audit, and traceability validation. Examples: GBC-1, GBC-2.

### Governance Baseline (GB)

A ratified baseline. The Constitution and downstream volumes are stable for operational use. Example: GB-1.

### Reference Standard (RS)

A baseline that has survived real engineering use and at least one independent review cycle. Example: RS-1 (future).

## Versioning Convention

- Constitution: semantic versioning (e.g., BKGC 2.0.0).
- Governance baseline: `GB-N` (e.g., GB-1).
- Reference standard: `RS-N` (e.g., RS-1).

## Transition Criteria

| Transition | Criteria |
|---|---|
| Draft → GBC | Content complete; cross-volume consistency review passed; audit clean. |
| GBC → GB | Ratification authority approves; ratification package complete; no unresolved critical findings. |
| GB → RS | Library exercised in real development; at least one independent review cycle confirms operational fitness; CDRs capture lessons learned. |

## Current State

GB-1 ratified on 2026-07-27.
