# SP-LIVE-001 swarm contract

## Purpose

Use multiple specialists to improve analysis without distributing or expanding consequential authority. Specialists produce evidence-bound advisory outputs; only the mission authority can propose an action, and only the canonical external-action authority can execute an approved capability.

## Mission decomposition

The orchestrator derives a DAG from the frozen mission scope. Every task binds mission/request hashes, role, allowed inputs, expected outputs, budgets, deadline, model policy, tool allowlist, data classification, memory scope, and delegated authority. Decomposition cannot add objectives or consequences.

The first mission requires at least two independent roles, such as status analyst and authority/risk reviewer. The verification role is separate from execution and cannot consume an executor’s unverifiable claim as proof.

## Specialist isolation

- Fresh context and workspace per specialist.
- No builder history, hidden cross-lane state, shared mutable scratchpad, or direct specialist-to-specialist channel.
- Inputs are enumerated and hashed; outputs are append-only and sealed.
- Cross-specialist evidence is shared only by the orchestrator as an explicit new input with provenance.
- Credentials, approval tokens, and side-effect capability handles are never delegated to reasoning specialists.

## Delegated authority

A task grant is non-transitive, least-privilege, read/advisory by default, and bounded by mission authority. A specialist may decline or return `INCOMPLETE`; it cannot widen tools, destination, memory scope, budgets, consequence class, or action count. Tool requests outside the grant are blocked and evidenced.

## Governed model routing

Routing records candidate models, required capabilities, data policy, cost/latency budgets, provider independence, selected model/version, rationale, fallback chain, and request/response identities. Fallback cannot weaken privacy, identity, isolation, or evidence requirements. A model change after proposal requires reconciliation and may invalidate the proposal.

## Tool budgets

Per-task ceilings cover calls, tokens, wall time, data bytes, retry count, and allowed tool classes. Network and external action tools require separate capability authority; no specialist receives consequential execution authority in SP-LIVE-001.

## Contradiction and confidence handling

Each output includes claims, evidence references, assumptions, confidence, uncertainty, blockers, and requested follow-up. The reconciler preserves disagreements; it does not average away blockers. Material contradiction triggers an independent tie-break task or `INCOMPLETE`. Confidence is advisory and never substitutes for required evidence or authority.

## Reconciliation

The orchestrator validates seals and task contracts, constructs a claim/evidence matrix, identifies agreement and contradiction, applies frozen mechanical rules, and emits a reconciled report. Any usable authority/security blocker dominates. Missing required specialist output yields `INCOMPLETE`. The proposed action must be derivable from the reconciled report and remain within mission scope.

## Prohibitions

Specialists cannot authenticate the Principal, approve actions, mint capabilities, access raw credentials, execute consequential actions, mark external state verified, alter mission state directly, suppress conflicting findings, or authorize another specialist.

## Required evidence

Mission/task IDs and hashes; specialist role/context/workspace IDs; model/provider identity; input/output hashes; tool calls and budgets; delegated scope; isolation attestation; claim/evidence matrix; contradictions; confidence; reconciliation rule trace; final report hash.
