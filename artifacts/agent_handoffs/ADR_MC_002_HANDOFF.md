# ADR-MC-002 MULTI-AGENT COORDINATION — HANDOFF RECORD

## Branch Claim

- Repository: ihoward40/SintraPrime-Unified
- Branch: docs/adr-mc-002-multi-agent-coordination
- Worktree: C:/Users/admin/SintraPrime-Unified-adr-mc-002
- Base: main at 006748e2f8bd82b527d1c672aa9cbaef47ce648a
- Base tag: mission-control-foundation-v1 + ADR-MC-001 merge (006748e2)
- Owner agent: Hermes
- Claimed at: 2026-08-05
- Expires at: heartbeat-based; claim is active until explicitly released or superseded
- Starting SHA: 006748e2f8bd82b527d1c672aa9cbaef47ce648a
- Expected remote SHA: 006748e2f8bd82b527d1c672aa9cbaef47ce648a (origin/main)
- Permitted paths:
  - docs/mission-control/ADR_MC_002_MULTI_AGENT_COORDINATION.md
  - artifacts/agent_handoffs/ADR_MC_002_HANDOFF.md
- Task scope: Author ADR-MC-002 (Multi-Agent Coordination Protocol) — architecture-only governance document
- Stop conditions:
  - implementation begins during architecture-only work;
  - wrong branch/worktree detected;
  - prohibited files touched;
  - remote head moves unexpectedly (return REMOTE_HEAD_CHANGED);
  - scope drift detected (return SCOPE_DRIFT_DETECTED).

## Branch Owner

- Branch owner: Hermes
- Agent identity: Hermes (orchestrator agent)
- Single-writer status: EXCLUSIVE — all other agents operate read-only unless ownership is formally transferred

## Claimed Files

- docs/mission-control/ADR_MC_002_MULTI_AGENT_COORDINATION.md (to be created)
- artifacts/agent_handoffs/ADR_MC_002_HANDOFF.md (this file)

## Authorized Scope

This branch is architecture and governance documentation only.

- Multi-agent coordination protocol: single-writer ownership, branch claiming, worktree isolation, ownership transfer, handoff requirements, remote-head movement, contested-branch recovery, force-push governance, evidence preservation, publication authority, review ownership, CI ownership, stale-claim/agent-failure handling, emergency freeze, scope-drift detection, cross-PR contamination, branch retirement, auditability.
- Does NOT govern executor runtime continuation logic.

## Prohibited Actions

- No implementation of branch-locking software.
- No GitHub Actions added.
- No repository settings or branch-protection changes.
- No bots created.
- No runtime code changes.
- No Mission Control modification.
- No executor continuation implementation.
- No cancellation enablement.
- No Phase 3B work.
- No deployment.
- No force-push (default prohibited; authorized force-push requires exact lease SHA and force-with-lease).
- No push, no PR, no mark-ready, no merge, no deploy.

## Current Next Action

Draft ADR-MC-002 per the required decision areas (A–R), invariants (1–18), state machines, matrices (10), threat model (16 items), acceptance criteria, and non-goals. Commit locally in narrow documentation commits. Do not push or open a PR.

## Governance Baseline (controlling)

- ADR-002: ACCEPTED and merged
- Mission Control Foundation: merged and tagged
- ADR-MC-001: ACCEPTED and merged
- Phase 1 implementation planning: APPROVED locally at 1632fbd92ddb80e4e3739fac7cfd97e530a183c2 (frozen, not based upon)
- Sigma continuation gate: BLOCKED
- Cancellation: DISABLED
- Runtime implementation: NOT AUTHORIZED
- Phase 3B: BLOCKED
- Deployment: NOT AUTHORIZED

## Timestamp

2026-08-05

## Single-Writer Status

EXCLUSIVE. Hermes owns this branch until a synchronized handoff records CLAIMED for an incoming agent. No verbal or chat-only transfer is valid. Direct GitHub edits by any party other than the recorded owner count as writes and require explicit authorization.
