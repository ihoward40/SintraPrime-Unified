# ADR-MC-002 MULTI-AGENT COORDINATION — HANDOFF RECORD

## Branch Claim

- Repository: ihoward40/SintraPrime-Unified
- Branch: docs/adr-mc-002-multi-agent-coordination
- Worktree: C:/Users/admin/SintraPrime-Unified-adr-mc-002
- Base: main at 006748e2f8bd82b527d1c672aa9cbaef47ce648a
- Base tag: mission-control-foundation-v1 + ADR-MC-001 merge (006748e2)
- Owner agent: Hermes
- Authorized GitHub identities: Hermes (orchestrator); all direct GitHub/web/API edits must be performed by or explicitly authorized by the owner
- Claim ID: CLAIM-MC002-001
- Claimed at: 2026-08-05
- Heartbeat interval: 24h
- Last heartbeat at: 2026-08-05
- Expires at: 2026-08-12 (unless renewed within maximum claim lifetime)
- Maximum claim lifetime: 30d (renewal beyond requires explicit reauthorization)
- Claim status: ACTIVE
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
  - scope drift detected (return SCOPE_DRIFT_DETECTED);
  - external edit fingerprint mismatch (return HANDOFF_INTEGRITY_MISMATCH).

## Branch Owner

- Branch owner: Hermes
- Agent identity: Hermes (orchestrator agent)
- Single-writer status: EXCLUSIVE — all other agents, bots, automation, and CI-authored commits operate read-only unless they hold an explicit claim or narrowly scoped publication authority.
- Writer model: "one writer" spans local Git, GitHub web UI, GitHub API/gh CLI, API-driven agents, bots (e.g., Dependabot), and CI-authored commits. Automated writers must hold an explicit claim or scoped authority and are recorded in the evidence log with their acting identity.

## Claimed Files

- docs/mission-control/ADR_MC_002_MULTI_AGENT_COORDINATION.md (created)
- artifacts/agent_handoffs/ADR_MC_002_HANDOFF.md (this file)

## Evidence Log

- Handoff commit SHA: (recorded on each commit that updates this file)
- Handoff content hash: (recorded on each commit)
- Prior handoff commit: (chain reference, never erased)
- External edits / bots / APIs / automation:
  - None recorded to date. Any direct GitHub edit, bot action, API call, or automation run must be appended here with the acting identity and timestamp.

## Authorized Scope

This branch is architecture and governance documentation only.

- Multi-agent coordination protocol: single-writer ownership, branch claiming (renewable lease), worktree isolation, ownership transfer, handoff requirements (corroborated, append-only), remote-head movement, GitHub-unavailable/offline mode, contested-branch recovery, force-push governance, evidence preservation, safety-branch retention/deletion, publication authority, review ownership, thread-resolution governance, CI ownership, stale-claim/agent-failure handling, emergency freeze, scope-drift detection, cross-PR contamination, branch retirement, writer model (bots/automation), auditability.
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

Apply REQUEST_CHANGES corrections to ADR-MC-002 (handoff tamper resistance, offline mode, renewable claim lease, safety-branch deletion, state-to-permission matrix, thread-resolution governance, consistency fixes). Commit locally. Do not push or open a PR.

## Governance Baseline (controlling)

- ADR-002: ACCEPTED and merged
- Mission Control Foundation: merged and tagged
- ADR-MC-001: ACCEPTED and merged
- Phase 1 implementation planning: APPROVED locally at 1632fbd92ddb80e4e3739fac7cfd97e530a183c2 (frozen, not based upon)
- ADR-MC-002: DRAFT — correction cycle in progress
- Sigma continuation gate: BLOCKED
- Cancellation: DISABLED
- Runtime implementation: NOT AUTHORIZED
- Phase 3B: BLOCKED
- Deployment: NOT AUTHORIZED

## Timestamp

2026-08-05

## Single-Writer Status

EXCLUSIVE. Hermes owns this branch until a synchronized handoff records CLAIMED for an incoming agent. No verbal or chat-only transfer is valid. The handoff is a coordination record, not standalone source of truth: Git object state and independent receipts (CI, review threads, commit history) are controlling; any mismatch triggers HANDOFF_INTEGRITY_MISMATCH. Direct GitHub edits, bot actions, API calls, and automation by any party other than the recorded owner count as writes and must be recorded with acting identity; automated writers require an explicit claim or scoped authority.
