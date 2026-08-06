# ADR-MC-002: Multi-Agent Coordination Protocol

**Status:** DRAFT — NOT YET RATIFIED
**References:** ADR-002 (core authority model); Mission Control Foundation v1; ADR-MC-001 (executor continuation architecture)
**Baseline:** mission-control-foundation-v1 at 97bd539f82ee9099003b0ba5c3729092bf470604; ADR-MC-001 merge at 006748e2f8bd82b527d1c672aa9cbaef47ce648a
**Supersedes:** None
**Superseded by:** None

## 1. Context

This ADR formalizes the operational controls proven necessary during the contested-branch incidents involving PRs #255, #256, #257, #258, and #259. Those incidents demonstrated that multi-agent work on a shared repository requires explicit coordination rules: simultaneous writers collided on the same branch, an agent grabbed the wrong worktree and began repainting a road that was already open to traffic, safety evidence was at risk of being rewritten for convenience, and review/ownership boundaries were ambiguous.

The repository already carries a working PR-handoff protocol (one writer/branch, handoff file per PR, retire contested branches). ADR-MC-002 elevates that operational convenience into a governed, auditable protocol covering ownership, branch claiming, worktree isolation, ownership transfer, handoffs, remote-head movement, contested-branch recovery, force-push governance, evidence preservation, publication authority, review ownership, CI ownership, stale-claim/agent-failure handling, emergency freeze, scope-drift detection, cross-PR contamination, branch retirement, and auditability.

This ADR is a governance and systems-design document. It defines behavior, invariants, protocols, state machines, matrices, and acceptance tests for agent coordination. It does NOT govern executor runtime continuation logic. It does not implement branch-locking software, add GitHub Actions, modify repository settings, create bots, or change runtime code.

## 2. Decision Areas

### 2.A Single-Writer Ownership

- Exactly one active writer exists for any governed branch at any time.
- The writer identity is recorded in the branch handoff file before any write begins.
- All other agents operate read-only on that branch unless ownership is formally transferred via a synchronized handoff (see 2.D).
- Direct GitHub edits (web UI, API, gh CLI outside the declared writer) count as writes and require explicit owner authorization.
- Force-push requires explicit owner authorization and the exact lease SHA of the remote head being overwritten.
- Stale ownership cannot silently remain active: a claim is invalid once its heartbeat expires or it is superseded by a recorded transfer (see 2.M).
- The handoff file is a **coordination record, not a standalone source of truth**. Git object state and independent receipts (CI, review threads, commit history) are always controlling. A writer may update the handoff but must never erase prior committed handoff history; every handoff update appends, it does not rewrite.
- Any mismatch between handoff claims (HEAD, tree SHA, dirty state, remote SHA) and actual Git state, or between the handoff and independent receipts, produces `HANDOFF_INTEGRITY_MISMATCH`. Required behavior: freeze writes, preserve current state on a safety branch, compare committed handoff history against Git objects, treat Git object state and independent receipts as controlling evidence, and require owner or governance review before work resumes.

### 2.B Branch Claiming — Renewable Lease

A branch claim is a **renewable lease**, not permanent ownership. It is a durable record created before implementation begins. Once created it must be committed (or otherwise durably recorded) before implementation begins. A claim without a recorded `starting_sha` and `expected_remote_sha` is invalid.

Required fields:

| Field | Description |
|---|---|
| `claim_id` | Unique identifier for this claim instance |
| `repository` | The governed repository |
| `branch` | The claimed branch name |
| `worktree` | The local worktree path |
| `owner_agent` | The agent identity that holds the claim |
| `authorized_git_identities` | The GitHub/web/API identities permitted to act as the writer |
| `claimed_at` | Timestamp of claim creation |
| `heartbeat_interval` | Period at which the claim must be refreshed |
| `last_heartbeat_at` | Timestamp of the most recent heartbeat |
| `expires_at` | Absolute expiry if not renewed |
| `maximum_claim_lifetime` | Hard ceiling; renewal beyond requires reauthorization |
| `starting_sha` | Exact local starting HEAD |
| `expected_remote_sha` | Exact remote HEAD the writer expects |
| `permitted_paths` | Files the writer may modify |
| `task_scope` | The authorized task description |
| `stop_conditions` | Conditions that trigger an immediate stop |
| `claim_status` | One of the states below |

Claim states:

| State | Meaning |
|---|---|
| PENDING | Claim created, not yet verified |
| ACTIVE | Verified, writer may write |
| RENEWING | Heartbeat renewal in progress |
| STALE | Heartbeat missed but within grace; classified, not auto-free |
| EXPIRED | Past `expires_at`; branch frozen, no auto-takeover |
| RELEASED | Owner voluntarily released |
| REVOKED | Explicitly revoked by governance authority |
| TRANSFER_PENDING | Ownership transfer initiated, awaiting verification |

Renewal rules:

- A heartbeat renews the claim only while within `maximum_claim_lifetime`.
- Renewal updates `last_heartbeat_at` and `expires_at`; it never broadens `task_scope` or `permitted_paths`.
- Renewal beyond `maximum_claim_lifetime` requires explicit reauthorization.
- Expiration freezes the branch; it never grants automatic takeover.
- Takeover requires independent verification and explicit authority (see 2.D, 2.M).

### 2.C Worktree Isolation

- One governed workstream per worktree.
- No use of dirty or conflicted worktrees for unrelated tasks.
- No stashing unrelated work to "make room."
- No resets, conflict resolution, or mutation of another agent's worktree.
- Every worktree must have an inventory and owner; an unowned worktree is not a valid work target.

### 2.D Ownership Transfer

A formal handoff sequence is mandatory:

1. Outgoing agent freezes writes.
2. Outgoing agent updates the handoff with exact HEAD, tree SHA, dirty state, tests, CI, and next action.
3. Outgoing agent records the transfer as PENDING.
4. Incoming agent independently verifies the evidence (HEAD, tree, dirty state, remote state).
5. Incoming agent records CLAIMED and becomes the owner.
6. Only then may writes resume.

No verbal or chat-only ownership transfer is sufficient. The handoff file is the controlling source of truth.

### 2.E Handoff Record Requirements

A handoff is a coordination record, not a standalone source of truth. Every handoff must be **corroborated** by:

- committed handoff content (immutable in git history);
- actual git HEAD;
- actual tree SHA;
- local and remote branch references;
- worktree status (staged/modified/untracked/conflicted);
- CI receipts;
- review-thread state;
- an append-only external or repository evidence record where available.

Every handoff record must carry:

- `handoff_commit_sha` — the commit that introduced/updated this handoff;
- `handoff_content_hash` — hash of the handoff file content at that commit;
- `prior_handoff_commit` — reference to the previous handoff commit (chain, never erased);
- `author_agent` identity;
- `timestamp`;
- `verification_agent` — the incoming agent's identity who independently verified before claiming.

A writer may update the handoff but must not erase prior committed handoff history; the handoff is append-only in effect. Any mismatch between handoff claims and Git state, or between the handoff and independent receipts, produces `HANDOFF_INTEGRITY_MISMATCH` (see 2.A).

Every governed handoff must additionally include:

- branch and worktree;
- local HEAD and remote HEAD;
- tree SHA;
- base SHA;
- dirty/clean state;
- staged, modified, untracked, and conflicted file inventory;
- current task;
- files claimed;
- commits created;
- test matrix;
- CI state;
- review-thread state;
- known limitations;
- prohibited actions;
- required next action;
- evidence links;
- agent identity.

### 2.F Remote-Head Movement

When the remote moves unexpectedly, the agent must:

1. Return `REMOTE_HEAD_CHANGED`.
2. Stop all writes.
3. Fetch the new remote state.
4. Preserve local work on a safety branch.
5. Compare histories.
6. Classify the change (fast-forward, divergence, rewrite, unknown).
7. Do not force over unknown work.
8. Require explicit reconciliation authority before publishing.

### 2.G Contested-Branch Recovery

Codifies the governed exit pattern used for PR #255:

- Preserve certified state on a safety branch.
- Create safety branches for valid local work.
- Selectively reconcile valid changes onto a fresh branch.
- Reject regressions.
- Publish to a fresh branch.
- Open a replacement PR that states `Supersedes PR #<number>` in its body.
- Close the contaminated PR as superseded; the superseded PR must link back to the replacement PR.
- Retire the contested branch.
- Prohibit future publication from the contested branch.

### 2.H Force-Push Governance

Force-push is prohibited by default. Where expressly authorized, require:

- exact expected remote SHA (the lease);
- force-with-lease only (never unconditional `--force`);
- a safety branch preserving pre-push state;
- local certification passing;
- recorded justification;
- no active competing writer;
- immediate post-push verification;
- halt if the lease fails.

### 2.I Evidence Preservation

Evidence classes:

| Class | Example |
|---|---|
| source commit | the commit a change derives from |
| tree SHA | the exact tree object of a state |
| CI receipt | the CI run URL and terminal result |
| local certification | pytest/mypy/local evidence |
| review disposition | the recorded review decision |
| handoff record | the authoritative handoff file |
| safety branch | branch preserving pre-rewrite work |
| supersession notice | notice that a branch/PR is superseded |
| merge receipt | the merge commit SHA and PR link |
| tag receipt | the created tag and SHA |

Evidence must never be rewritten merely to simplify history.

### 2.J Publication Authority

Separate authorities:

- implementation authority;
- commit authority;
- push authority;
- PR creation authority;
- ready-for-review authority;
- review authority;
- thread-resolution authority;
- merge authority;
- deployment authority.

Possession of one authority does not imply another.

### 2.K Review Ownership

- Reviewers must review exact published heads.
- Findings must distinguish confirmed defect, requirement ambiguity, and future hardening.
- Review comments must be tied to evidence.
- Unresolved threads block merge.
- Self-approval limitations must be documented.
- Comment-based owner approval must not be misrepresented as GitHub review approval.
- Review and thread resolution must be pinned to an exact published head.

Thread-resolution governance:

- Permitted resolvers: the original reviewer; a designated independent reviewer; the project owner or a delegated review authority.
- A writer may not resolve a substantive defect thread solely because code changed, unless the governance policy explicitly permits it and evidence is attached.
- Resolution requires: the exact current PR head; a reference to the corrective commit; evidence showing the finding is addressed; CI state; the resolver identity; and confirmation that the thread applies to the reviewed head.
- If the PR head changes after resolution and the correction is materially affected, the thread must be reopened or re-reviewed.
- All resolutions are recorded as auditable events tied to the exact head they resolved against.

### 2.L CI Ownership

- Define who starts or polls CI.
- Terminal state = all required checks pass, fail, or are cancelled.
- Classify failures (environment, test, lint, security, flaky).
- Corrective commits allowed only within authorized scope.
- Prohibit declaring green from local tests alone.
- No merge while required checks are pending or failing.

### 2.M Stale-Claim and Agent-Failure Handling

- Claim heartbeat marks liveness.
- Maximum inactivity window defines staleness.
- Stale claim is classified, not silently assumed free.
- Owner recovery process preserves the safety branch.
- Takeover requires explicit authorization after verification.
- No automatic takeover merely because an agent is silent.

### 2.N Emergency Freeze

A repository/workstream freeze command:

- stops all writers;
- prohibits push, merge, and deployment;
- records reason and scope;
- identifies the controlling SHA;
- requires explicit release authority;
- preserves all worktrees and evidence.

### 2.O Scope-Drift Detection

Agents must stop when:

- task name changes unexpectedly;
- unrelated feature areas appear;
- wrong branch/worktree is detected;
- prohibited files are touched;
- implementation begins during architecture-only work;
- a previous phase is reopened without authorization.

Required return: `SCOPE_DRIFT_DETECTED`.

### 2.P Cross-PR Contamination

Prohibit:

- handoff files from unrelated PRs;
- files from another workstream;
- shared scratch files;
- changes copied without provenance;
- branch reuse after supersession.

### 2.Q Branch Retirement

States:

| State | Meaning |
|---|---|
| ACTIVE | normal feature work allowed |
| FROZEN | writes stopped, evidence preserved |
| SUPERSEDED | replaced by another branch/PR |
| RETIRED | closed, no further publication |
| ARCHIVED | preserved read-only for history |
| CONTESTED | under governed recovery; no merge |

Only ACTIVE branches may receive normal feature work.

### 2.R Auditability

Every ownership, publication, review, supersession, recovery, and merge decision must be auditable: recorded with agent identity, exact SHAs, timestamps, and justification.

### 2.S GitHub-Unavailable / Offline Mode

When GitHub or the canonical remote is unreachable, the agent must:

1. Return `REMOTE_AUTHORITY_UNAVAILABLE`.
2. Enter degraded mode. Publication remains frozen.

Permitted in degraded mode:

- inspect the local worktree;
- run local tests;
- preserve work on a local safety branch;
- update an uncommitted local recovery note;
- create local evidence bundles.

Prohibited in degraded mode:

- acquire a new publication claim;
- transfer ownership;
- push;
- open or update a PR;
- resolve review threads;
- claim remote-head equivalence;
- mark ready;
- merge;
- deploy;
- force-push.

Publication must remain frozen until:

- remote connectivity returns;
- remote HEAD is fetched;
- local and remote histories are reconciled;
- claim ownership is revalidated against the fetched remote state.

### 2.S.1 Offline Claim Expiry

A claim may expire while remote authority is unavailable. Expiry during outage:

- immediately freezes local writes beyond preservation and testing;
- does **not** grant takeover to any other agent;
- the prior owner retains no publication authority after expiry;
- ownership and claim status must be revalidated after remote connectivity returns (see claim revalidation in 2.B / 2.M);
- any work created after claim expiry is preservation-only and cannot be published until explicitly authorized and reconciled.

This is a known limitation: the protocol depends on the canonical remote as the source of truth for claims, PRs, review, and merge. Offline operation is restricted to local preservation and verification only.

### 2.T Safety-Branch Retention and Deletion

Safety branches preserve pre-rewrite and contested work and must not be deleted before governance closure.

- **Minimum retention period:** a safety branch is retained for at least the governance-closure retention window (default: 90 days from closure) or until explicitly authorized for deletion.
- **Governance closure event:** the governing PR is merged or formally abandoned; supersession evidence is preserved; no unresolved review or incident exists; final merge/tag receipt is recorded.
- **Deletion authority:** only the project owner or a delegated repository governance authority may authorize deletion, and only after all closure conditions are met.
- **Required evidence before deletion:** merge or abandonment receipt, supersession notice, retained CI receipt, and the recorded deletion authorization.
- **Prohibition:** deletion is prohibited during open review, contested recovery, active audit, incident response, or unresolved merge verification.

Deletion itself must be recorded as an auditable event (who, when, which branch, which authorization, which retention evidence).

### 2.U Writer Model: Bots and Automation

"One writer" spans all mutation paths: local Git, the GitHub web UI, the GitHub API/gh CLI, API-driven agents, bots (e.g., Dependabot), and CI-authored commits.

- Automated writers (bots, automation, CI) must hold an explicit claim or a narrowly scoped publication authority before mutating a governed branch.
- Every direct GitHub edit, bot action, API call, and automation run must be recorded in the handoff and the evidence log with the acting identity.
- An automated writer's scope is bounded by its claim's `permitted_paths` and `authorized_git_identities`; exceeding it triggers `SCOPE_DRIFT_DETECTED`.

## 3. Formal Invariants

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | At most one authorized writer exists for a governed branch. | Handoff claim; CI ownership checks |
| 2 | No agent writes before recording a valid claim. | Claim-before-write rule |
| 3 | No ownership transfer is valid without a synchronized handoff. | Handoff PENDING -> CLAIMED sequence |
| 4 | Unknown remote changes always stop publication. | `REMOTE_HEAD_CHANGED` protocol |
| 5 | No force-push occurs without an exact lease SHA. | Force-with-lease + lease verification |
| 6 | No contested branch is merged. | CONTESTED state blocks merge |
| 7 | No superseded branch returns to ACTIVE status. | Retirement rule |
| 8 | Every published state has an exact HEAD and tree SHA. | Handoff records both |
| 9 | Review is always performed against an exact published head. | Reviewer must pin head |
| 10 | Unresolved review threads block merge. | PR merge gate |
| 11 | Passing local tests do not substitute for required CI. | CI gate |
| 12 | Merge authority does not imply deployment authority. | Separated authorities (2.J) |
| 13 | Architecture-only branches contain no runtime changes. | Changed-file inventory check |
| 14 | Safety branches are never deleted before governance closure. | Retirement sequence |
| 15 | Handoff evidence must match actual Git state. | Incoming agent verifies independently |
| 16 | An agent may never rewrite another agent's unknown work. | No mutation of other worktrees |
| 17 | Scope drift triggers an immediate stop. | `SCOPE_DRIFT_DETECTED` |
| 18 | The default response to uncertainty is freeze, preserve, and verify. | Emergency freeze + safety branch |
| 19 | Handoff claims must be corroborated by committed Git state and independent receipts; a mismatch triggers freeze. | `HANDOFF_INTEGRITY_MISMATCH` protocol (2.A, 2.E) |
| 20 | A claim is a renewable lease, not permanent ownership; expiry freezes, never grants takeover. | Heartbeat + `maximum_claim_lifetime` (2.B, 2.M) |
| 21 | Automated writers (bots, CI, API agents) require an explicit claim or scoped authority. | Writer model (2.U) |

## 4. State Machines

### 4.1 Branch Lifecycle

```text
UNCLAIMED -- claim --> CLAIMED -- activate --> ACTIVE
ACTIVE -- freeze --> FROZEN -- release --> ACTIVE
ACTIVE -- open PR --> REVIEW -- merge --> MERGED -- archive --> ARCHIVED
ACTIVE -- contest --> CONTESTED -- supersede --> SUPERSEDED -- retire --> RETIRED -- archive --> ARCHIVED
ACTIVE -- abandon --> ABANDONED -- archive --> ARCHIVED
CONTESTED -- supersede --> SUPERSEDED
FROZEN -- supersede --> SUPERSEDED
```

### 4.2 Ownership Claim Lifecycle

```text
EMPTY -- create --> PENDING -- verify --> CLAIMED (ACTIVE WRITER)
CLAIMED -- heartbeat --> CLAIMED
CLAIMED -- expire --> STALE
CLAIMED -- transfer-init --> TRANSFER_PENDING -- verify --> CLAIMED (new owner)
CLAIMED -- release --> RELEASED
STALE -- recover --> CLAIMED
STALE -- takeover-auth --> CLAIMED (new owner)
```

### 4.3 Handoff Lifecycle

```text
NONE -- outgoing freezes --> OUTGOING_UPDATED
OUTGOING_UPDATED -- mark PENDING --> TRANSFER_PENDING
TRANSFER_PENDING -- incoming verifies --> INCOMING_CLAIMED
INCOMING_CLAIMED -- resume writes --> ACTIVE_WRITER
```

### 4.4 Remote-Head Conflict

```text
SYNCED -- detect remote move --> REMOTE_HEAD_CHANGED
REMOTE_HEAD_CHANGED -- stop writes --> PRESERVE_SAFETY
PRESERVE_SAFETY -- fetch --> COMPARE
COMPARE -- fast-forward --> RESYNC -- SYNCED
COMPARE -- divergence --> CLASSIFY
CLASSIFY -- unknown --> REQUIRE_RECONCILE_AUTH
CLASSIFY -- rewrite --> REQUIRE_RECONCILE_AUTH
```

### 4.5 Contested-Branch Recovery

```text
ACTIVE -- conflict detected --> CONTESTED
CONTESTED -- preserve certified --> SAFETY_BRANCHES
SAFETY_BRANCHES -- reconcile valid --> FRESH_BRANCH
FRESH_BRANCH -- publish --> REPLACEMENT_PR
REPLACEMENT_PR -- merge --> MERGED
CONTESTED -- supersede --> SUPERSEDED
SUPERSEDED -- close contaminated PR --> RETIRED
RETIRED -- archive --> ARCHIVED
```

### 4.6 PR Lifecycle

```text
NONE -- push --> DRAFT
DRAFT -- ready --> REVIEW
REVIEW -- approve + threads clear --> MERGEABLE
MERGEABLE -- merge --> MERGED
REVIEW -- request changes --> CHANGES_REQUESTED -- fix --> REVIEW
REVIEW -- contest --> CONTESTED (see 4.5)
```

### 4.7 Emergency Freeze Lifecycle

```text
NORMAL -- freeze command --> FROZEN_ALL
FROZEN_ALL -- no push/merge/deploy --> PRESERVED
PRESERVED -- release auth --> RELEASED
RELEASED -- NORMAL
```

## 5. Required Matrices

### 5.1 Authority Matrix

| Authority | Implementation | Commit | Push | PR | Ready | Review | Thread | Merge | Deploy |
|---|---|---|---|---|---|---|---|---|---|
| Impl owner | yes | yes | no | no | no | no | no | no | no |
| Committer | - | yes | no | no | no | no | no | no | no |
| Pusher | - | - | yes | no | no | no | no | no | no |
| PR author | - | - | - | yes | no | no | no | no | no |
| Reviewer | - | - | - | - | - | yes | yes | no | no |
| Merger | - | - | - | - | - | - | - | yes | no |
| Deployer | - | - | - | - | - | - | - | - | yes |

Possession of any column does not grant any other column.

### 5.2 Branch-State Transition Matrix

| From \ To | CLAIMED | ACTIVE | FROZEN | REVIEW | MERGED | CONTESTED | SUPERSEDED | RETIRED | ARCHIVED |
|---|---|---|---|---|---|---|---|---|---|
| UNCLAIMED | claim | - | - | - | - | - | - | - | - |
| CLAIMED | - | activate | - | - | - | - | - | - | - |
| ACTIVE | - | - | freeze | open PR | - | contest | - | abandon | - |
| FROZEN | - | release | - | - | - | - | supersede | - | - |
| REVIEW | - | - | - | - | merge | contest | - | - | - |
| CONTESTED | - | - | - | - | - | - | supersede | - | - |
| SUPERSEDED | - | - | - | - | - | - | - | retire | - |
| RETIRED | - | - | - | - | - | - | - | - | archive |

Claim `STALE` and `EXPIRED` states (see 2.B) transition the branch to `FROZEN`: a stale or expired claim freezes the branch and blocks all publication; it does not grant takeover. Recovery from FROZEN requires explicit reauthorization (see 2.M). The `CONTESTED -- supersede --> SUPERSEDED` edge is the single canonical label used consistently in 4.1, 4.5, and this matrix.

### 5.3 Agent-Action Permission Matrix

| Action | Owner | Other agent | Direct GitHub edit |
|---|---|---|---|
| Write to claimed branch | allowed | denied | denied unless authorized |
| Force-push | lease+auth | denied | denied |
| Transfer ownership | via handoff | verify | n/a |
| Merge | merger | denied | denied |
| Declare review approve | reviewer | n/a | comment != approval |

### 5.4 Remote-Head-Change Decision Matrix

| Change type | Action | Publish? |
|---|---|---|
| Fast-forward | resync | allowed after verify |
| Divergence (known) | reconcile with auth | conditional |
| Divergence (unknown) | stop, require auth | blocked |
| Rewrite of expected head | stop, safety branch | blocked |

### 5.5 Contested-Branch Recovery Matrix

| Step | Action | Gate |
|---|---|---|
| 1 | Preserve certified state | safety branch |
| 2 | Create safety branches | local only |
| 3 | Reconcile valid changes | onto fresh branch |
| 4 | Reject regressions | diff review |
| 5 | Publish fresh branch | new PR |
| 6 | Close contaminated PR | superseded |
| 7 | Retire contested branch | no future publish |
| 8 | Archive | read-only |

### 5.6 CI Failure Classification Matrix

| Class | Example | Action |
|---|---|---|
| Environment | runner down | rerun, no code change |
| Lint | ruff error | corrective commit in scope |
| Test | assertion fail | fix or stop |
| Security | bandit/secret | stop, escalate |
| Flaky | intermittent | rerun, document |

### 5.7 Review Disposition Matrix

| Disposition | Meaning | Merge effect |
|---|---|---|
| Confirmed defect | reproducible bug | block |
| Requirement ambiguity | spec unclear | block until clarified |
| Future hardening | not now | non-blocking note |

### 5.8 Emergency Freeze Matrix

| Trigger | Scope | Release auth |
|---|---|---|
| Suspected contamination | branch | owner+principal |
| CI compromise | repo | principal |
| Unknown remote rewrite | workstream | owner |

### 5.9 Evidence-Retention Matrix

| Evidence | Retain until |
|---|---|
| Safety branch | governance closure |
| Handoff record | archive |
| Merge receipt | permanent |
| CI receipt | permanent |
| Supersession notice | archive |

### 5.10 Scope-Drift Matrix

| Signal | Return | Action |
|---|---|---|
| Task name change | SCOPE_DRIFT_DETECTED | stop |
| Unrelated files | SCOPE_DRIFT_DETECTED | stop |
| Wrong worktree | SCOPE_DRIFT_DETECTED | stop |
| Runtime code in arch branch | SCOPE_DRIFT_DETECTED | stop |

### 5.11 State-to-Permission Matrix

For every branch state, the following actions are allowed (Y), conditionally allowed (C), or denied (N):

| State | local edits | commits | normal push | force-with-lease | PR create | PR meta edit | review | thread resolve | ready | merge | deploy | transfer | safety branch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| UNCLAIMED | N | N | N | N | N | N | N | N | N | N | N | N | N |
| CLAIMED | N | N | N | N | N | N | N | N | N | N | N | N | N |
| ACTIVE | Y | Y | C | N | C | C | Y | Y | C | N | N | C | Y |
| FROZEN | N | N | N | N | N | N | Y | Y | N | N | N | C* | Y |
| REVIEW | N | C | N | N | N | C | Y | Y | C | N | N | C | Y |
| CONTESTED | N | N | N | N | N | N | Y | Y | N | N | N | N | Y |
| SUPERSEDED | N | N | N | N | N | N | Y | Y | N | N | N | N | Y |
| RETIRED | N | N | N | N | N | N | N | N | N | N | N | N | N |
| MERGED | N | N | N | N | N | C | Y | Y | N | N | N | N | Y |
| ARCHIVED | N | N | N | N | N | N | N | N | N | N | N | N | N |
| ABANDONED | N | N | N | N | N | N | N | N | N | N | N | N | Y |

Key rules:

- **FROZEN:** no feature writes or publication; preservation and verification only. `transfer` is allowed only via explicit reauthorization (C*), never automatic.
- **CONTESTED:** no push to the contested branch; no merge; only safety/reconciliation actions.
- **SUPERSEDED:** read-only evidence state; no return to ACTIVE (Inv 7).
- **RETIRED:** no writes or publication.
- **MERGED:** no feature work; post-merge evidence only.
- **ARCHIVED:** immutable/read-only.

`normal push` from ACTIVE requires the manuscript to be within `permitted_paths` and the remote to match `expected_remote_sha` (else `REMOTE_HEAD_CHANGED`). `force-with-lease` is denied in all normal states; it is only permitted under the explicit 2.H authorization with an exact lease SHA.

## 6. Threat Model

| # | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| T1 | Two agents writing simultaneously | Medium | Critical | Single-writer claim (2.A, Inv 1) |
| T2 | Malicious or mistaken force-push | Low | Critical | Lease SHA + force-with-lease (2.H, Inv 5) |
| T3 | Stale remote state | Medium | High | REMOTE_HEAD_CHANGED (2.F) |
| T4 | Dirty-worktree contamination | Medium | High | Worktree isolation (2.C) |
| T5 | PR cross-contamination | Medium | High | Cross-PR prohibition (2.P) |
| T6 | False certification | Low | High | CI gate, no local-green (2.L, Inv 11) |
| T7 | Incorrect SHA reporting | Low | Critical | Independent verify (Inv 15) |
| T8 | Handoff tampering | Low | High | Audit trail (2.R) |
| T9 | Self-approval misrepresentation | Medium | High | Comment != approval (2.K) |
| T10 | Branch hijacking | Low | Critical | Claim + ownership transfer (2.D) |
| T11 | Stale ownership claim | Medium | High | Heartbeat + recovery (2.M) |
| T12 | Agent hallucinating file mutation | Medium | High | Changed-file inventory (Inv 13) |
| T13 | Direct GitHub edit outside writer | Medium | High | Counts as write (2.A) |
| T14 | CI result misclassification | Medium | High | Failure classification (5.6) |
| T15 | Compromised agent credentials | Low | Critical | Emergency freeze (2.N) |
| T16 | Deletion of safety evidence | Low | Critical | Retention rule (Inv 14, 2.T) |
| T17 | Bot/automation identity spoofing | Low | Critical | Explicit claim or scoped authority required (2.U); recorded acting identity |
| T18 | Handoff record falsified by current writer | Low | Critical | Corroboration + `HANDOFF_INTEGRITY_MISMATCH` (2.A, 2.E, Inv 19) |

## 7. Acceptance Criteria

ADR-MC-002 may be accepted only when:

1. Single-writer semantics are complete (2.A, Inv 1).
2. Claim and transfer lifecycle is defined (2.B, 2.D, 4.2, 4.3).
3. Contested-branch recovery is deterministic (2.G, 4.5, 5.5).
4. Force-push rules are fail-safe (2.H, Inv 5).
5. Authority roles are separated (2.J, 5.1).
6. CI and review gates are explicit (2.K, 2.L, 5.6, 5.7).
7. Stale claims and emergency freezes are governed (2.M, 2.N, 5.8).
8. Evidence retention is complete (2.I, 5.9).
9. All invariants are testable or auditable (Section 3).
10. No runtime implementation is introduced (Inv 13).
11. Owner and security reviews are recorded.

## 8. Non-Goals

Do not:

- implement branch-locking software;
- add GitHub Actions;
- modify repository settings;
- change branch protection;
- create bots;
- modify runtime code;
- change Mission Control;
- implement executor continuation;
- enable cancellation;
- begin Phase 3B;
- deploy.

## 9. Consequences

Until ADR-MC-002 is ratified and its controls are implemented:

- The existing PR-handoff protocol remains the operational default.
- Single-writer claims are advisory-but-required for governed branches.
- Contested-branch recovery follows the PR #255 pattern.
- Sigma gate, cancellation, Phase 3B, and deployment remain unchanged by this ADR.

## 10. Status

| Item | State |
|------|-------|
| ADR-MC-002 | DRAFT — not ratified |
| Sigma continuation gate | BLOCKED |
| Cancellation controls | DISABLED |
| Runtime implementation | NOT AUTHORIZED |
| Phase 3B | BLOCKED |
| Deployment | NOT AUTHORIZED |
