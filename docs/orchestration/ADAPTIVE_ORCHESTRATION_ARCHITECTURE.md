# SintraPrime Adaptive Orchestration Layer

## Status

Milestone One architecture contract. Deterministic mock providers only. External providers, paid APIs, deployment, merging, and external actions are blocked pending certification and Principal approval.

## Objective

Provide one governed execution interface that receives a complex task, classifies it, decomposes it into bounded work units, assigns specialized roles, routes each unit according to declared provider capabilities and policy, verifies outputs independently, reconciles disagreement, and returns one auditable result while preserving Principal authority.

This design is inspired by general multi-model orchestration patterns: one interface over specialized models, explicit role assignment, focused handoffs, independent checking, and policy-driven routing. It is not an implementation of Sakana Fugu and must not copy proprietary Sakana code, prompts, weights, trademarks, or undocumented behavior.

## Authority boundary

The orchestrator may plan, recommend, simulate, and request approval. It may not independently merge code, deploy, spend money, publish public content, send external communications, change legal positions, modify payment settings, access restricted evidence, or approve its own high-risk result. Those actions require Principal approval and remain disabled in Milestone One.

## Domain components

The backend service boundary is `portal/services/orchestration/` and contains:

- `orchestrator.py` — run coordination and state transitions
- `task_classifier.py` — task type, sensitivity, and policy classification
- `task_decomposer.py` — bounded work-unit generation
- `role_assignment.py` — role selection and assignment
- `model_router.py` — policy-based provider selection
- `instruction_compiler.py` — least-context role instructions
- `execution_graph.py` — directed acyclic execution graph
- `result_reconciler.py` — disagreement analysis and final synthesis
- `verifier.py` — independent validation contracts
- `confidence.py` — confidence, evidence quality, and uncertainty
- `budget_policy.py` — token, cost, node, retry, and duration limits
- `failure_policy.py` — retry, partial, blocked, and cancellation behavior
- `audit_recorder.py` — immutable run and decision evidence
- `provider_registry.py` — provider declarations and availability
- `schemas.py` — governed request and response schemas

API surface:

- `POST /api/orchestration/plan`
- `POST /api/orchestration/execute`
- `GET /api/orchestration/runs/{run_id}`
- `GET /api/orchestration/runs/{run_id}/events`
- `POST /api/orchestration/runs/{run_id}/cancel`
- `POST /api/orchestration/runs/{run_id}/approve`

Frontend surface:

- `/orchestration`
- `/orchestration/runs`
- `/orchestration/runs/:runId`
- `/orchestration/providers`
- `/orchestration/policies`

## Governed roles

- **PLANNER** — interprets objective and constraints and creates the plan.
- **THINKER** — proposes approaches and identifies uncertainty.
- **RESEARCHER** — gathers permitted evidence and separates facts from inference.
- **WORKER** — performs the bounded implementation or drafting task.
- **CHECKER** — independently validates correctness and unsupported claims.
- **SECURITY_REVIEWER** — reviews secrets, permissions, unsafe actions, and exposure.
- **GOVERNANCE_REVIEWER** — checks authority, policy, and approval requirements.
- **RECONCILER** — compares outputs, preserves disagreement, and produces the final recommendation.
- **PRINCIPAL** — human authority for gated actions; never replaced by a model.

## Task classification

Supported task types:

- coding
- research
- legal-information
- financial-analysis
- document-generation
- operations
- customer-support
- marketing
- security
- mixed

Classification records task type, sensitivity, required roles, recommended providers, expected cost and latency, approval requirement, evidence requirement, and prohibited actions.

## Provider registry and routing

Providers declare capabilities; the router does not infer them. A provider definition includes identity, supported task types, context window, structured-output and tool support, task strengths, latency class, input and output costs, availability, data policy, permitted sensitivity, and enabled status.

Routing considers task fit, sensitivity, cost ceiling, latency ceiling, availability, data policy, required tools, confidence history, and governance restrictions. Benchmark score alone is never sufficient.

Every routing decision records candidate providers, rejected providers, selection reason, applied policy, estimated cost, and actual cost when available.

## Execution modes

- **SINGLE** — one provider handles the task.
- **PLAN_AND_EXECUTE** — planner decomposes; workers execute.
- **THINK_WORK_CHECK** — thinker proposes, worker executes, checker validates.
- **PARALLEL_COMPARE** — independent outputs are compared by a reconciler.
- **RESEARCH_SYNTHESIS** — researcher gathers evidence, checker validates, synthesizer produces the result.
- **CODE_REVIEW_LOOP** — planner, implementer, test runner, reviewer, and bounded correction.
- **HIGH_ASSURANCE** — independent outputs, security review, governance review, and Principal approval.

## Execution graph

Each run is a directed acyclic graph. Every node records:

- `node_id`
- role and objective
- focused instructions
- dependencies
- assigned provider
- status and retry count
- input and output artifacts
- confidence and evidence
- start and completion timestamps
- error state

Node states:

`PLANNED`, `WAITING`, `READY`, `RUNNING`, `REVIEW_REQUIRED`, `APPROVAL_REQUIRED`, `COMPLETED`, `FAILED`, `CANCELLED`, `BLOCKED`.

## Instruction minimization

Each role receives only the context required for its objective. Instructions include the exact objective, permitted inputs, output schema, constraints, prohibited actions, evidence requirements, completion criteria, and escalation conditions. Restricted or irrelevant context is not forwarded.

## Verification and checker independence

Each output records confidence, evidence quality, assumptions, contradictions, unresolved uncertainty, and verification result. In `HIGH_ASSURANCE`, the same model invocation may not serve as both worker and independent checker. Where practical, checker inputs exclude hidden worker reasoning and include only the work product, evidence, and verification contract.

## Reconciliation

When outputs disagree, the system identifies disputed claims, compares evidence, ranks evidence quality, requests targeted follow-up when allowed, and preserves unresolved disagreement. The final result separates:

- verified result
- supported inference
- unresolved issue
- Principal decision required

The system must never fabricate consensus.

## Budget and failure controls

Per-run limits cover input tokens, output tokens, provider cost, node count, retries, execution duration, approved providers, and approved task types. Hard-limit exhaustion returns `BLOCKED` or `PARTIAL`; limits are never silently exceeded.

Provider failure follows bounded retry policy and may produce reassignment, partial completion, blocked status, or cancellation. Every retry and route change is audited.

## Security controls

Milestone One requires:

- deterministic mock providers
- provider allowlists
- sensitivity-aware routing
- prompt-injection filtering
- input redaction before provider calls
- output sanitization
- denial rules for unauthorized actions
- immutable audit records
- no secrets in source or evidence

API keys, passwords, tokens, cookies, banking data, tax identifiers, private credentials, and protected evidence must not be exposed.

## Data model

Governed records:

- `OrchestrationRun`
- `OrchestrationNode`
- `OrchestrationEvent`
- `ProviderDefinition`
- `RoutingDecision`
- `VerificationResult`
- `ReconciliationResult`
- `ApprovalRequest`
- `BudgetUsage`
- `EvidenceReference`

Records are tenant-scoped where applicable, redact sensitive data before persistence and audit, preserve soft-delete and immutable-audit expectations, and use SQLAlchemy ORM rather than raw SQL.

## Operations Floor integration

Role mapping:

- Hermes — planner and coding coordinator
- Sintra Sentinel — monitoring, security, and failure review
- Justice Scribe — legal-information and document review
- Dispatch Marshal — customer and communication workflows

The Operations Floor displays current run, graph, active role, provider, status, budget usage, confidence, checker result, approvals, failures, and final outcome. Live provider execution remains blocked until deterministic mock lifecycle, tests, and visual evidence pass.

## Milestone One mock providers

- `reasoning_model`
- `coding_model`
- `research_model`
- `checker_model`
- `security_model`

Required deterministic scenarios:

- successful plan
- parallel work
- checker disagreement
- reconciliation
- approval requirement
- provider failure and retry
- budget exhaustion
- cancellation
- final completion

## Certification contract

Milestone One is complete only when architecture documentation, deterministic mock providers, classification, execution graph, five or more executing roles, recorded routing decisions, budget controls, provider-failure handling, disagreement preservation, Principal approval, cancellation, complete audit trail, Operations Floor mock activity, backend tests, frontend tests, visual tests, and inspected screenshots all pass.

No paid provider may be connected. No deployment, merge, or external action may occur.
