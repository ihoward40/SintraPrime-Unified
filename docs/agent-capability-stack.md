# Governed Agent Capability Stack

## Decision

SintraPrime will integrate **capabilities**, not surrender orchestration authority to a second agent framework.

The platform already has agent protocols, Mission Control, tenant boundaries, audit requirements, and governance authority. CrewAI, AutoGen/Microsoft Agent Framework, and Langflow therefore remain evaluation references rather than runtime dependencies.

## Selected capabilities

| Capability | Preferred integration posture | Reason |
|---|---|---|
| Durable memory | Mem0-compatible adapter behind `MemoryStore` | Useful token reduction and cross-session recall, but only after tenant isolation, deletion, expiry, provenance, and sensitivity controls are certified. |
| Private-document retrieval | RAGFlow-compatible adapter behind `KnowledgeRetriever` | Strong document structure and citation model; retrieval results must always carry source locators. |
| Self-hosted web reading | Crawl4AI-compatible adapter behind `WebReader` | Privacy and cost control. Firecrawl may be an optional managed fallback, not the authority layer. |
| Browser action | browser-use-compatible adapter behind `BrowserActor` | Only for sites without suitable APIs. Every consequential action passes an explicit SintraPrime policy and approval gate. |
| Private model endpoint | LocalAI-compatible OpenAI endpoint | Useful deployment option, but model routing stays in SintraPrime's provider boundary. |

## Explicitly deferred

- **AnythingLLM:** overlaps the existing SintraPrime portal and would create a second user/permission surface.
- **CrewAI / AutoGen / Langflow:** overlap orchestration and would create competing execution semantics.
- **Direct vendor SDK imports in domain code:** prohibited. Only adapters may depend on third-party packages.
- **Autonomous filing, purchasing, signing, sending, or deletion:** prohibited without recorded human approval.

## Authority model

1. Domain agents request a capability through a SintraPrime contract.
2. Tenant and actor identity are mandatory.
3. Read-only operations may proceed under policy.
4. State-changing browser actions require approval or are denied.
5. Adapters return normalized results, citations, and metadata.
6. Mission Control will record request, policy decision, provider, result, and correlation identifiers.

## Certification increments

### Increment 1 — contracts and reference controls

Delivered in this branch:

- provider-neutral contracts for web reading, browser action, memory, and retrieval;
- dependency-free governed memory reference implementation;
- fail-closed browser-action policy;
- tests for tenant isolation, subject isolation, expiry, deletion, approval, and denial.

### Increment 2 — persistence and audit

- PostgreSQL-backed memory records with migration authority;
- encryption classification and redaction boundary;
- Mission Control receipts for memory and browser decisions;
- retention and user-directed deletion tests;
- persistence restart tests.

### Increment 3 — provider adapters

- Crawl4AI read-only adapter first;
- Mem0 adapter second;
- RAGFlow adapter third;
- browser-use adapter only after approval receipts exist;
- LocalAI endpoint certification through the existing model-provider layer.

## Non-negotiable acceptance criteria

- no cross-tenant or cross-subject memory retrieval;
- no memory without provenance and sensitivity classification in persistent implementations;
- no citation-free private-knowledge answer represented as grounded;
- no consequential browser mutation without a valid approval receipt;
- no provider can bypass SintraPrime policy, RBAC, audit, or redaction boundaries;
- all external integrations remain optional and fail closed.
