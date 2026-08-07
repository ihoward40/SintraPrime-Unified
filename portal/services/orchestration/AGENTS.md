# portal/services/orchestration - Adaptive Orchestration Services

## Purpose

Owns governed adaptive orchestration service contracts and execution logic for Milestone One mock-provider orchestration.

## Ownership

- Orchestration service schemas, policies, execution graph, routing, verification, reconciliation, and audit helpers
- Deterministic mock-provider behavior for Milestone One
- Provider-neutral contracts used by API routes and Operations Floor projections

## Local Contracts

- Milestone One may use deterministic mock providers only.
- External providers, paid APIs, deployment, merging, and external actions remain blocked.
- Principal authority, checker independence, least-context instructions, budget ceilings, disagreement preservation, tenant-scoped run access, and audit records are mandatory.
- Provider capabilities must be declared before routing; do not infer provider powers from names or benchmarks alone.

## Work Guidance

- Keep service code provider-neutral and deterministic until certification explicitly unlocks live providers.
- Redact secrets, credentials, protected evidence, and restricted identifiers recursively before provider-facing records or audit payloads.
- Preserve separate worker and checker invocations for high-assurance flows.

## Verification

- Run focused orchestration unit tests after policy, graph, routing, verification, reconciliation, or budget changes.
- Run API and frontend certification tests before claiming Milestone One completion.

## Child DOX Index

