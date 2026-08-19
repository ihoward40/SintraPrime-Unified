# SP-IKE-002 — Governed Top Features Program

**Date:** 2026-08-19  
**Target:** IKE-Bot as a first-class workforce interface inside SintraPrime-Unified  
**Authority:** SintraPrime remains the single authority, evidence, memory, mission, and execution control plane.  
**Rule:** No second orchestrator, hidden JSON authority store, parallel scheduler authority, or independent long-term memory system.

## Objective

Bring the strongest capabilities demonstrated in Hermes Bot Mode, Hermes + Obsidian second-brain workflows, Jarvis-style computer use, and multi-provider/local-model agent workflows into IKE-Bot while preserving Principal sovereignty, auditability, bounded autonomy, and reversible execution.

## Feature Set

### 1. Persistent named specialist agents
- Named agents with title, role, description, avatar metadata, soul/personality, tool scope, memory scope, and model policy.
- Clone/duplicate agent profiles without silently copying credentials or private memory.
- One primary chat per named agent plus mission-linked subthreads.
- Agent health, last run, last error, current mission, cost, and permission status visible from Mission Control.

### 2. Per-agent memory isolation with controlled sharing
- Default private memory namespace per agent.
- Explicit promotion paths: private -> team -> Principal/shared.
- No silent cross-agent memory bleed.
- Every shared memory item retains provenance, source, authoring agent, confidence, and timestamp.

### 3. Agent-to-agent communication
- @mention handoffs.
- Automatic delegation when policy permits.
- Causation-preserving envelopes: mission ID, parent action, sender, receiver, context refs, requested capabilities.
- Loop detection, bounded fan-out, delegation depth ceilings, and time/cost budgets.

### 4. Routines and event-driven missions
- Human-readable recurring schedules.
- Event-triggered work from authenticated webhooks/connectors.
- Canonical scheduler/outbox only; no parallel cron authority inside IKE-Bot.
- Pause, resume, cancel, dry-run, missed-run recovery, and execution receipts.

### 5. Multi-model routing
- Per-agent provider preferences.
- Local-first option for privacy/cost.
- Cloud escalation for vision, tool use, long context, or difficult reasoning.
- Task-based routing by privacy, latency, model capability, confidence, and budget.
- Explicit fallback chain; no silent provider switching for restricted data.

### 6. Local model support
- Treat Ollama/local providers as replaceable execution adapters.
- Track actual context capacity instead of configured capacity claims.
- Health checks and acceptance tests before a local model can receive production missions.
- Automatic downgrade to smaller context or cloud only when policy explicitly allows it.

### 7. Living-file / second-brain integration
- Markdown/Obsidian-compatible knowledge as human-readable governed context.
- On-demand retrieval; never load an entire vault by default.
- Source URI, hash, classification, last-reviewed timestamp, and ownership metadata.
- Support Git, Drive, Notion, local folders, and Obsidian vaults through adapters.
- Changes to authoritative records must flow through the canonical SintraPrime persistence layer; the vault is a projection/work surface, not a competing source of truth.

### 8. Skill library
- Versioned skills with owner, purpose, required tools, permissions, compatibility, tests, last-used timestamp, and review status.
- Detect stale, redundant, unused, or conflicting skills.
- Promote frequently successful ad-hoc workflows into candidate skills only after review.
- No autonomous mutation of governance or authority skills.

### 9. Git/coding delegation
- Coding agents work on isolated branches/worktrees.
- Tests and static checks required before a completion claim.
- No direct push to protected branches.
- PR/evidence bundle generated automatically.
- Model/agent selection based on language, repo area, task type, and risk.

### 10. Voice interface
- Interruptible full-duplex conversation.
- Voice commands become explicit mission intents with visible state.
- “Stop”, “pause”, and “take over” act as high-priority cancellation/control commands.
- Voice alone never lowers an approval requirement.

### 11. Screen guidance
- Visual pointing/arrow guidance without taking control.
- Explain where to click and why.
- Lowest-risk computer-use mode and default starting mode for unfamiliar interfaces.

### 12. Governed computer takeover
- Mouse/keyboard/browser control through an execution adapter.
- Narrate actions in real time.
- Checkpoint before meaningful side effects.
- Draft-first default for forms, campaigns, messages, filings, purchases, posts, and submissions.
- Immediate Principal interrupt/kill switch.

### 13. Draft-first external actions
- Prepare the complete action.
- Stop before final send/publish/submit/purchase/file unless the mission contains explicit authority for that side effect.
- Approval must identify the exact target, amount/scope, and action.
- Materially changed drafts invalidate prior approvals.

### 14. Connectors
- Gmail, Google Calendar, Drive, Slack, GitHub, MCP/plugins, telephony, and other services through scoped service identities.
- Authentication, authorization, rate limiting, correlation IDs, structured errors, audit, and revocation are mandatory.
- Principal credentials are never repurposed as general agent credentials.

### 15. Phone calls
- Approved telephony adapter only.
- Clear agent identity and disclosure policy.
- Transcript, call metadata, outcome, and follow-up tasks become evidence artifacts.
- No financial commitment, legal admission, cancellation, purchase, or other consequential agreement without specific authority.

### 16. Mission Control / Principal Command
- One command surface for active agents, schedules, handoffs, approvals, memory changes, evidence, costs, and failures.
- Principal can pause or cancel any active mission.
- Full causation graph from Principal intent to every side effect.
- Freshness and confidence shown for all important status claims.

## Unscripted improvements

These are intentionally beyond the source demos.

### A. Authority Envelope
Each mission receives a machine-readable authority envelope:
- allowed capabilities
- allowed targets/domains
- maximum risk tier
- maximum spend
- maximum token/API/telephony cost
- deadline
- maximum delegation depth
- allowed data classifications
- whether irreversible actions are allowed

Anything outside the envelope stops and requests approval.

### B. Action Ledger + Evidence Receipts
Every material action emits a durable receipt containing:
- mission ID
- causation ID
- agent/model/tool identity
- timestamp
- input/output hashes
- approval reference
- side-effect reference
- cost
- result

Receipts should be cryptographically hashed and available in the Mission Control causation graph.

### C. Simulation Mode
Every consequential workflow should support dry-run/simulation mode. The agent completes planning and drafts the side effects but produces a preview instead of executing them.

### D. Replay and forensic reconstruction
A mission can be replayed from receipts and source hashes to answer:
- What did the agent know?
- Which model/tool made the decision?
- What approval existed?
- Which side effect occurred?
- Which later changes altered the result?

### E. Memory promotion workflow
Agents may suggest memory, but durable/shared memory follows:
1. candidate
2. deduplicate
3. source/provenance check
4. confidence/classification
5. Principal or policy approval when needed
6. commit to canonical memory

This prevents “AI gossip” from becoming institutional truth.

### F. Skill health scoring
Score every skill on:
- recency
- success rate
- failure rate
- average cost
- average latency
- security scope
- dependency health
- test coverage
- last human review

Flag stale or dangerous skills automatically.

### G. Contradiction detector
When new research conflicts with existing memory, do not overwrite. Create a contradiction object linking both claims, sources, dates, and confidence until resolved.

### H. Privacy zones
Classify data as public/internal/confidential/restricted and enforce provider routing. Restricted data can be local-only when configured, preventing accidental cloud exposure.

### I. Cost governor
Use cheapest sufficient model, not cheapest model blindly. Enforce mission budgets and provide a cost receipt by model/tool/connector.

### J. Confidence-aware escalation
Agents attach confidence to important conclusions. Low confidence, source conflict, or failed verification automatically escalates to research/review instead of being presented as fact.

### K. Swarm manager
Parallel specialist agents are supported, but with:
- bounded fan-out
- delegation depth limits
- shared mission budget
- duplicate-work detection
- independent verifier role for high-risk conclusions
- deterministic merge policy for final synthesis

### L. Approval diffing
When a draft changes after approval, compute a semantic diff. Material changes revoke the approval automatically. Cosmetic changes do not.

### M. Capability leases
Grant temporary, mission-scoped permissions that expire automatically. Avoid permanent broad tool access for agents that only need a connector once.

### N. Dead-man / stuck-agent detection
Detect loops, repeated tool failures, stalled browser actions, escalating spend, repeated delegation, and context thrashing. Pause before the agent burns time or money.

### O. Principal Brief
Every completed mission ends with a compact brief:
- requested objective
- what was done
- what changed
- evidence
- approvals used
- cost/time
- unresolved risks
- next best actions

## Implementation state created by this branch

`apps/ike-bot/main/src/runtime/governedRuntime.ts`
- capability registry for the full feature set
- risk tiers
- authenticated Principal requirements
- approval evaluation
- draft-only downgrade behavior for consequential actions
- model policy and model-selection helper
- agent profile contract
- handoff envelope
- living-file reference contract
- evidence receipt contract
- canonical runtime adapter interface

`apps/ike-bot/main/src/routes/runtime.routes.ts`
- `GET /api/runtime/capabilities`
- `POST /api/runtime/evaluate-authority`
- `POST /api/runtime/select-model`

The discovery endpoint explicitly reports `executionEnabled: false` until the canonical Principal gateway, approval service, evidence layer, scheduler/outbox, memory retrieval, and cancellation adapters are wired.

## Non-negotiable activation gates

No consequential runtime execution may be enabled until all are true:

1. Authenticated Principal gateway is implemented and tested.
2. Service identities exist for agent/connector access.
3. Canonical mission/intent authority is wired.
4. Canonical approval/HITL authority is wired.
5. Canonical evidence receipt layer is wired.
6. Canonical scheduler/outbox is wired.
7. Canonical cancellation/kill-switch path is wired.
8. Rate limiting and connector revocation are implemented.
9. Clean-database migration verification passes for any schema changes.
10. Cross-agent memory isolation and permission tests pass.
11. Computer-use sandbox and irreversible-action approval tests pass.
12. Full causation/evidence chain is demonstrated in an end-to-end acceptance mission.

## Acceptance mission

A single Principal request should be able to:

1. create/select a specialist team;
2. retrieve only relevant living-file context;
3. delegate research and drafting across agents;
4. choose appropriate local/cloud models;
5. prepare an external action in draft;
6. narrate computer-use steps;
7. stop at the consequential boundary;
8. request Principal approval;
9. execute only the approved side effect;
10. emit cryptographic receipts and a complete causation graph;
11. allow immediate cancellation;
12. return a Principal Brief.

Until that mission passes with evidence, the feature set is not production-certified.
