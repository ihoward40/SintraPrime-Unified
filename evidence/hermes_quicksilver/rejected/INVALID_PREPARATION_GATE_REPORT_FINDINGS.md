# HERMES PREPARATION GATE — INVALID REPORT CONFLICT FINDINGS

| Field | Invalid report | Verified evidence | Status |
| ----- | -------------- | ----------------- | ------ |
| Hermes version | `v0.1.0` | `0.18.2` from Hermes `pyproject.toml` | Conflict |
| Authority repository | `C:\Repositories\SintraPrime-Unified` | Not previously observed | Unsupported |
| Known primary repository | omitted | `C:\SintraPrime-Unified` | Omitted |
| Known Desktop Projects clone | omitted | `C:\Users\admin\Desktop\Projects\SintraPrime-Unified` | Omitted |
| Commit | `a1b2c3d4` | Placeholder-like; not verified | Invalid |
| Report date | `2023-10-05` | Current work occurred in July 2026 | Conflict |
| AGENTS.md files | Invented `docs\agents\agent_*` entries | Actual repository paths differ | Conflict |
| Coverage claims | 95%, 98%, 15%, 100%, 40% | No test output or coverage report | Unsupported |
| Capability versions | Fleet v2.1, Mesh v1.3, Policy v3.0, etc. | No source evidence | Unsupported |
| Compliance bot | v2.1 | No runtime evidence | Unsupported |
| Production changes | Claimed none | Not independently verified | Unknown |
| Worktree existence | Claimed created | Not independently verified | Unknown |
| Branch existence | Claimed `feat/hermes-quicksilver-governed-fleet-increment-1` | Not independently verified | Unknown |

## Summary

The rejected report is not a credible preparation gate output. It appears to contain fabricated or placeholder values, unsupported percentages, and repository locations not documented in prior discovery. No implementation should proceed until each field is replaced with a command-backed finding.

## Preservation

The original report is preserved unchanged at `evidence/hermes_quicksilver/rejected/INVALID_PREPARATION_GATE_REPORT.md`. This findings file documents the conflicts without altering the original.
