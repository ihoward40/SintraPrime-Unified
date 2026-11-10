# SP-COMPLETION-MAP-001 — SintraPrime-Unified Completion Map

**Status:** CANONICAL COMPLETION PLAN — evidence-first, fail-closed  
**Repository:** `ihoward40/SintraPrime-Unified`  
**Baseline inspected:** `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`  
**Owner / ratification authority:** Isiah Howard  
**Purpose:** Give any authorized agent one deterministic path from the current repository state to a supportable definition of “complete.”

---

## 0. The definition of COMPLETE

SintraPrime-Unified is **not complete because code exists**. It is complete only when all required release surfaces satisfy the same evidence chain:

`DEFINED -> WIRED -> TESTED -> CERTIFIED -> OBSERVABLE -> RECOVERABLE -> SECURE -> DOCUMENTED -> OPERABLE -> VALUE-PROVEN`

A surface is not complete if it is:
- implemented but unreachable;
- reachable but not governed;
- governed but not tested;
- tested outside the release test universe;
- passing without a SHA-bound receipt;
- certified but unobservable in production;
- observable but unrecoverable after failure;
- technically working but making unsupported legal/financial/product claims;
- deployed without rollback;
- monetized without fulfillment, accounting, privacy, and support controls.

**Global completion gate:** every REQUIRED row in this map must be GREEN, or carry a written, ratified scope exclusion with evidence and rationale.

---

# 1. Agent operating contract

Every agent taking work from this map MUST:

1. Read root `AGENTS.md`, then every applicable child `AGENTS.md`.
2. Record exact starting SHA, branch/worktree, dirty state, runtime versions, and services available.
3. Classify the task as READ-ONLY, LOCAL-REVERSIBLE, EXTERNAL-REVERSIBLE, EXTERNAL-CONSEQUENTIAL, or IRREVERSIBLE.
4. Identify the owning subsystem before editing. Do not create a duplicate engine because an existing one is difficult to understand.
5. Search for existing implementation, tests, schemas, migrations, feature flags, receipts, and prior certification evidence.
6. State the smallest defect being repaired and the acceptance test that proves it.
7. Preserve TRAINING != COMPETENCY != CERTIFICATION != AUTHORIZATION.
8. Preserve evidence provenance. AI output is not independent verification.
9. Run the narrowest relevant tests first, then the owning lane, then release certification when required.
10. Never convert “file exists,” “process runs,” “CI green,” or “agent answered” into “production complete” without the required gates.
11. Update DOX when behavior/contracts/ownership change.
12. Produce a closeout receipt containing: task ID, base SHA, resulting SHA, changed paths, tests, exact results, skipped tests, services, evidence refs, unresolved defects, authority boundary, rollback, and next authorized action.
13. Never merge, deploy, publish, send, spend, move money, file, or contact a third party unless separately authorized.

---

# 2. Truth vocabulary

Use only these states in completion reporting:

- **VERIFIED** — directly supported by current evidence at the exact referenced revision/environment.
- **PARTIAL** — some required elements are proven, others are not.
- **PENDING** — defined work exists but required evidence has not been produced.
- **BLOCKED** — cannot proceed without a named dependency/authorization.
- **STALE** — prior evidence exists but its dependency closure changed.
- **FAILED** — an executed acceptance gate failed.
- **OUT-OF-SCOPE** — explicitly ratified exclusion; never inferred.
- **UNKNOWN** — evidence is absent or insufficient.

Never report percentages as substitutes for gate states.

---

# 3. Current reality anchors

The following repository facts must shape the completion plan:

- `MASTER_STATUS.md` is dated 2026-04-26 and contains broad “complete” claims that are not sufficient release evidence by themselves. Treat it as historical context, not current certification.
- `SP-RC-TEST-UNIVERSE-MANIFEST-001.md` identified serious release-test collection gaps. It recorded that many release-bearing modules had tests on disk but were not exercised by the then-effective automation.
- `scripts/certify.py` now defines expanded lanes: `default`, `portal`, `swarm`, `auth_identity`, `tenant_data`, `execution_correctness`, and `release_cert`. This is progress, but lane existence is not proof that all lanes currently collect and pass.
- The canonical agent runtime already contains typed manifests, capability policy, lifecycle certification, authority provenance, memory scope, and dependency-closure concepts. Extend these rather than building another agent registry.
- Existing governed memory writeback already proves a useful pattern: typed inputs, provenance verification, tenant isolation, idempotency, bounded content, existing memory vault reuse, and approval before authoritative mutation.
- SP-COLLECTIVE-INTELLIGENCE-001 is being developed separately to implement governed organizational learning. Until merged and certified, treat it as proposed integration, not production capability.

---

# 4. Completion architecture — 16 workstreams

## WS-00 — Repository truth and scope convergence
**Objective:** establish one machine-readable inventory of what SintraPrime actually ships.

Required:
- Enumerate all top-level packages/apps/services.
- Classify each as REQUIRED-RUNTIME, REQUIRED-TOOLING, EXPERIMENTAL, LEGACY, ARCHIVED, GENERATED, or OUT-OF-SCOPE.
- Identify canonical implementation when duplicate/parallel systems exist.
- Map owner, entrypoint, dependencies, tests, CI lane, runtime, data stores, APIs, UI consumers, feature flag, deployment target, and rollback.
- Reconcile README, MASTER_STATUS, architecture docs, compose files, CI, and code.
- Remove or explicitly mark unsupported “complete,” “production-ready,” legal, financial, security, performance, and integration claims.
- Create a machine-readable `release_surface_manifest`.

Exit gate:
- No release-bearing surface is absent from the manifest.
- No two systems silently claim the same canonical responsibility.
- Claims validator passes.
- Principal ratifies release scope.

## WS-01 — Test-universe closure
**Objective:** every release-bearing surface is exercised by an intentional certification lane.

Required:
- Re-run static collection inventory against current HEAD.
- Run `--collect-only` for every certification target.
- Prove all target paths exist.
- Detect zero-test targets and silent ignores.
- Reconcile `pytest.ini`, `pyproject.toml`, `conftest.py`, `scripts/certify.py`, and CI.
- Add lane coverage for frontend, mobile, TypeScript/JavaScript, migration, container, API-contract, and deployment tests; Python pytest cannot certify those alone.
- Make skipped tests visible by reason and policy. Critical tests must not silently skip because a service is unavailable.
- Add mutation/negative/failure-injection tests for governance and high-consequence paths.
- Require exact-SHA receipts.

Exit gate:
- AUTH_IDENTITY = PASS
- TENANT_DATA = PASS
- EXECUTION_CORRECTNESS = PASS
- RELEASE_CERT = PASS
- frontend/mobile/build lanes = PASS
- zero unexplained skips in mandatory gates
- all receipts bind to same candidate SHA.

## WS-02 — API/router and end-to-end wiring
**Objective:** code that exists is reachable only when intentionally mounted, authorized, documented, and tested.

Required:
- Inventory every FastAPI/APIRouter/router registration.
- Compare defined routers to mounted routers.
- Detect orphaned endpoints and duplicate route prefixes.
- Resolve API-prefix disagreement across web/mobile/services.
- Generate OpenAPI from runtime and compare to declared clients.
- Contract-test every UI/API client against the canonical schema.
- Add startup test proving expected router count and named critical routes.
- Remove dead navigation and dead API clients.
- Verify auth/tenant context propagates across HTTP, WebSocket, background work, and agent calls.

Exit gate:
- route manifest generated from runtime;
- every REQUIRED endpoint has consumer + auth policy + test;
- no unapproved orphan routes;
- web/mobile use canonical versioned API contract.

## WS-03 — Identity, authorization, tenancy, secrets
**Objective:** fail closed across human, service, agent, tenant, and tool identities.

Required:
- One canonical identity model.
- RBAC/ABAC/capability policies mapped to sensitive operations.
- Tenant isolation at application and database layers where applicable.
- Service-to-service identity and short-lived credentials.
- Secret manager integration; no production secrets in repo/logs/prompts.
- Key rotation and revocation.
- Agent identity bound to canonical registry manifest.
- Tool permissions least-privilege and deny-overrides-allow.
- Human approval identity recorded for consequential actions.
- Session/token/JTI/revocation and WebSocket auth tested.
- Add break-glass procedure with audit.

Exit gate:
- cross-tenant negative matrix PASS;
- forged identity/authority tests PASS;
- secret scan PASS;
- privilege escalation tests PASS;
- revocation works across processes.

## WS-04 — Agent runtime convergence
**Objective:** one governed substrate for every production agent.

Required:
- Register every production agent in canonical `agent_runtime`.
- Eliminate shadow registries or mark them adapters/read models.
- Every agent declares stable ID/version/owner/capabilities/forbidden capabilities/memory scope/provider policy/tool policy/budget/approval policy.
- Startup fails closed on unknown capabilities or invalid manifests.
- Certification dependency closure includes prompt/instruction version, model/provider policy, tool schemas, memory policy, authority, runtime, and relevant skills.
- Separate model selection from agent identity.
- Add graceful degradation when preferred model/provider is unavailable.
- Add per-run token/cost/time/tool budgets.
- Add deterministic idempotency keys for consequential tool calls.
- Add agent quarantine/revoke controls.
- Require trace/receipt linkage for every production run.

Exit gate:
- 100% of production agents registered and startup-valid;
- no consequential agent bypasses approval gateway;
- provider failover tested;
- quarantine tested;
- certification receipts current.

## WS-05 — Collective intelligence / Academy / competency
**Objective:** turn experience into verified institutional capability.

Required lifecycle:
`OBSERVE -> CHALLENGE -> VERIFY -> DISTRIBUTE -> TRAIN -> EXAMINE -> CERTIFY COMPETENCY -> USE -> MEASURE -> RELEARN`

Required:
- Persist lessons through existing governed evidence/memory architecture.
- Require independent challenge and independent verification.
- Scope lesson inheritance to relevant agents/tenants/domains.
- Build Academy curricula from verified knowledge only.
- Exams use adversarial, scenario, tool-use, refusal, and uncertainty cases.
- Competency receipts bind to lesson fingerprints and agent version.
- Superseded knowledge automatically stales dependent competency.
- Authorization remains separate from competency.
- Outcome receipts can create new OBSERVED lessons but can never self-verify.
- Human experts may ratify high-risk domain curricula.

Exit gate:
- no unverified lesson enters production retrieval;
- stale knowledge triggers recertification;
- competency matrix available for every production agent;
- challenge/verifier independence mechanically enforced.

## WS-06 — Memory, RAG, provenance, and knowledge lifecycle
**Objective:** one trustworthy organizational memory instead of many contradictory stores.

Required:
- Inventory every memory/vector/RAG/knowledge store.
- Designate canonical systems of record and derived indexes.
- Every durable memory carries provenance, tenant, classification, source time, effective time where relevant, confidence/integrity status, and retention policy.
- AI-generated material is labeled and independently verified before promotion to authoritative knowledge.
- Implement supersession/deprecation, not silent overwrite.
- Add deletion/retention/privacy workflows.
- Retrieval must honor tenant, authority, jurisdiction, freshness, and classification.
- Add citation/evidence linkage from answer -> knowledge -> source.
- Benchmark retrieval precision/recall on domain datasets.
- Defend against prompt injection and poisoned documents.
- Add re-index/rebuild reproducibility test.

Exit gate:
- source-to-answer provenance demonstrable;
- poisoned/untrusted content cannot promote itself;
- tenant leakage tests PASS;
- stale/superseded knowledge handled correctly.

## WS-07 — Durable orchestration and scheduling
**Objective:** long-running work survives crashes, retries, approvals, and provider outages.

Required:
- Choose one canonical durable workflow substrate for production long-running workflows; adapt existing orchestration rather than layering multiple authorities.
- Persist workflow state and idempotency keys.
- Define retry/backoff/timeouts/circuit breakers.
- Human approval can pause for hours/days and resume safely.
- Replays do not repeat consequential side effects.
- Scheduled jobs have ownership, concurrency policy, missed-run policy, timezone, dedupe, and cancellation.
- Dead-letter/reconciliation path for permanently failed tasks.
- Crash/restart matrix.
- Provider/tool outage simulation.
- Version workflows safely across deployments.

Exit gate:
- crash at every critical boundary and recover without duplicate action;
- approval wait/resume PASS;
- scheduler duplicate/missed-run tests PASS;
- recovery receipts prove state continuity.

## WS-08 — Tool/MCP/integration fabric
**Objective:** every external capability is discoverable, typed, least-privilege, observable, and revocable.

Required:
- Inventory MCP servers, plugins/connectors, internal tools, web/browser, email, finance, GitHub, cloud, payment, and document tools.
- Canonical tool schema registry with versioning.
- Prefer stateless/sessionless interfaces where supported; explicit state handles where state is required.
- Capability negotiation and compatibility tests.
- Network allowlists/SSRF protections.
- Tool input/output validation.
- Per-tool approval classification.
- Timeouts, retries, rate limits, circuit breakers.
- Credential scopes per integration.
- Sandbox risky code/computer-use workloads.
- Conformance tests for MCP/tool adapters.
- Record tool-call provenance in traces/receipts.

Exit gate:
- no unregistered production tool;
- tool schema compatibility gate PASS;
- SSRF/exfiltration negatives PASS;
- revoked credential/tool fails closed.

## WS-09 — Observability, receipts, evaluation, and SRE
**Objective:** know what every agent/system did, why it failed, what it cost, and whether it was correct.

Required:
- Adopt OpenTelemetry-compatible traces/metrics/logs across API, agent, model, tool, DB, queue, and workflow boundaries.
- Standardize correlation IDs: tenant, mission, request, agent, trace, approval, receipt, workflow.
- GenAI telemetry records provider/model, latency, token usage, tool/handoff events, errors, and cost where available.
- Sensitive prompt/output capture is opt-in/redacted, never blindly logged.
- SLOs for availability, latency, correctness, cost, recovery, and approval wait.
- Golden dashboards and alerts.
- Trace-based regression grading.
- Dataset-driven evals for repeatable behaviors.
- Security/adversarial eval corpus.
- Cost-quality frontier tests per model/provider.
- Receipt hash/linkage integrity.

Exit gate:
- one trace can reconstruct an end-to-end mission;
- alerts fire in injected failures;
- regression suite blocks known bad behavior;
- per-agent/provider cost and quality are measurable.

## WS-10 — Data, database, migrations, and event integrity
**Objective:** durable, reproducible, isolated data with safe schema evolution.

Required:
- Canonical DB ownership map.
- PostgreSQL production schema authority defined.
- Migrations are ordered, idempotent where appropriate, and tested from empty + previous release.
- Remove runtime `create_all` as a substitute for governed production migrations where applicable.
- Transaction boundaries for ledgers/payments/approvals.
- Unique constraints/idempotency keys for exactly-once business effects.
- Backup/restore drills.
- RPO/RTO targets.
- Event/outbox pattern where cross-service side effects require reliability.
- PII classification/encryption/retention.
- Test data isolation.

Exit gate:
- empty bootstrap PASS;
- N-1 upgrade PASS;
- rollback/forward-fix procedure proven;
- backup restore drill PASS;
- concurrency race suite PASS.

## WS-11 — Security and safety engineering
**Objective:** production threat model, not security by assertion.

Required:
- Threat model: prompt injection, tool injection, SSRF, command injection, path traversal, secrets leakage, tenant escape, auth bypass, supply chain, poisoned memory/RAG, unsafe deserialization, webhook spoofing, replay, privilege escalation, browser/computer-use attacks.
- SAST, dependency/SBOM scanning, secret scanning, container scanning.
- Pinned/verified dependencies and provenance where practical.
- Sandboxes for untrusted code/documents/browser actions.
- Egress controls.
- Webhook signatures and replay protection.
- Rate limiting/abuse controls.
- Security incident runbook and evidence preservation.
- High-consequence domain guardrails for legal/financial/health-adjacent workflows.
- Red-team test corpus integrated into CI.

Exit gate:
- critical/high findings dispositioned;
- supply-chain artifacts produced;
- red-team mandatory suite PASS;
- incident drill completed.

## WS-12 — Web, mobile, voice, accessibility, and UX
**Objective:** every promised user surface works against the same governed backend.

Required:
- Canonical design/navigation map.
- Build web in CI; lint/typecheck/unit/component/E2E.
- Build mobile in CI; route manifest and deep-link tests.
- PWA/offline behavior explicitly scoped and tested.
- Voice: latency, interruption, confirmation, accessibility, error recovery, privacy.
- No orphan settings/screens/routes.
- API contract generated/shared rather than hand-diverged.
- WCAG-oriented accessibility checks for critical flows.
- Empty/loading/error/offline states.
- Human approval UX clearly distinguishes proposal from executed action.
- Evidence/receipt UX lets user see what happened.

Exit gate:
- production builds reproducible;
- critical E2E journeys PASS desktop/mobile;
- accessibility gate PASS;
- no dead navigation;
- consequential action confirmation/receipt flow PASS.

## WS-13 — Domain engines: legal, financial, trust, consumer, evidence
**Objective:** high-value domain intelligence that is grounded, scoped, and safe.

Required:
- Every legal proposition carries authority, jurisdiction, effective date, proposition support, and applicability analysis.
- “Source exists” must never equal “claim supported.”
- Separate education/drafting from legal representation claims.
- Financial outputs distinguish account facts, calculations, assumptions, and strategy.
- Trust/UCC modules reject unsupported redemption/strawman/secret-account/debt-elimination theories.
- Tax outputs require verified entity/year/classification facts before conclusions.
- Evidence workflows preserve originals, hashes, chronology, source, and uncertainty.
- Domain benchmark sets contain correct, incorrect, ambiguous, outdated, cross-jurisdiction, adversarial, and insufficient-evidence cases.
- Escalate high-risk uncertainty to human review.

Exit gate:
- SP-CLAIM-INTEGRITY benchmark PASS;
- jurisdiction/effective-date negatives PASS;
- unsupported-theory refusal tests PASS;
- evidence chain reproducible.

## WS-14 — IKE revenue and customer operations
**Objective:** turn verified capability into legitimate repeatable revenue.

Required:
- Product catalog with buyer/problem/deliverable/scope/price/cost/fulfillment/refund/privacy/compliance.
- Stripe/product/payment links mapped to live offers only.
- Post-payment intake and fulfillment workflow.
- Customer identity/order/consent/evidence/receipt linkage.
- No misleading legal-service, credit-repair, certification, guaranteed-result, or unsupported security claims.
- Revenue telemetry: traffic -> lead -> intake -> checkout -> payment -> fulfillment -> outcome -> refund/complaint -> repeat.
- Experiment registry ties marketing/product hypotheses to verified lessons.
- Spending/publishing/customer contact/pricing mutations remain approval-gated.
- Unit economics and cost-per-agent-run.
- Customer support/escalation and refund process.

Exit gate:
- one complete paid journey works end-to-end in controlled production;
- fulfillment receipt exists;
- accounting reconciles payment to product/customer;
- experiment outcomes feed governed learning.

## WS-15 — Deployment, operations, disaster recovery
**Objective:** boring, reproducible, reversible production.

Required:
- Explicit environments: dev/test/staging/prod.
- Infrastructure and configuration source of truth.
- Reproducible containers/builds.
- Health/readiness checks.
- Database/Redis/external dependency readiness.
- Blue/green, canary, or equivalent controlled rollout for material changes.
- Automated rollback trigger criteria.
- Feature flags with owner/expiry.
- Production secrets outside source.
- Backup/restore and disaster recovery.
- Runbooks: deploy, rollback, outage, provider outage, DB issue, queue backlog, security incident, compromised credential.
- Capacity/cost limits.
- Post-deploy smoke and synthetic journeys.
- Release receipt binds artifact digest + git SHA + migrations + config generation.

Exit gate:
- staging certification PASS;
- restore drill PASS;
- rollback drill PASS;
- production canary PASS;
- post-deploy synthetic PASS;
- release receipt complete.

---

# 5. Modernization track — use current technology wisely

These are adoption candidates, not automatic rewrites. Every adoption requires a problem statement, benchmark, security review, migration/rollback plan, and measurable improvement.

## M-01 — Agent SDK / Responses-style orchestration
Use modern typed agent definitions, structured outputs, tool schemas, handoffs, guardrails, tracing, and MCP integration where they simplify existing adapters. Do not replace working governed SintraPrime authority merely to follow a framework trend.

## M-02 — Trace-first agent evaluation
Make traces first-class evidence. Grade tool choice, handoff correctness, policy compliance, evidence use, refusal behavior, latency, and cost. Convert recurring trace failures into regression datasets.

## M-03 — OpenTelemetry GenAI observability
Use current OpenTelemetry semantic conventions where stable enough; version-pin experimental GenAI conventions. Instrument model/tool/workflow spans without leaking secrets or private prompts.

## M-04 — Durable agent execution
Evaluate Temporal or equivalent durable execution for long-lived workflows only if it reduces custom recovery complexity. Preserve SintraPrime approval/authority semantics above the workflow engine.

## M-05 — Current MCP architecture
Track the current MCP specification and SDK conformance. Favor stateless/sessionless transport and explicit state handles where supported. Build conformance tests rather than assuming SDK interoperability.

## M-06 — Model routing as an optimization problem
Maintain provider-neutral interfaces. Route by capability, risk, latency, privacy, availability, and cost. Use canaries/evals before changing production routing. Local models may handle low-risk/private workloads; frontier models handle tasks only when evidence shows benefit.

## M-07 — Sandboxed computer/code agents
Run browser/computer/code execution in isolated ephemeral environments with restricted credentials, filesystem boundaries, egress policy, and full receipts.

## M-08 — Structured context engineering
Treat context as compiled input: identity + authority + task + relevant memory + evidence + tool schemas + policy + budget. Measure context quality and avoid dumping entire histories into every agent.

## M-09 — Continuous organizational learning
Complete SP-COLLECTIVE-INTELLIGENCE-001 and wire verified lessons into memory, Academy, competency, mission retrieval, outcomes, and revenue experiments.

## M-10 — Supply-chain provenance
Generate SBOMs, pin dependencies, scan containers, and attach build provenance/artifact digests to release receipts.

---

# 6. Dependency order — do not violate

```
GATE A  TRUTH
  WS-00 Repository truth/scope
      |
GATE B  TESTABILITY
  WS-01 Test-universe closure
      |
GATE C  CORE CONTROL PLANE
  WS-03 Identity/Auth/Tenancy
  WS-04 Agent Runtime
  WS-10 Data/Migrations
      |
GATE D  CONNECTIVITY
  WS-02 API/Wiring
  WS-08 Tool/MCP Fabric
      |
GATE E  RELIABILITY
  WS-07 Durable Orchestration
  WS-09 Observability/Evals
  WS-11 Security
      |
GATE F  INTELLIGENCE
  WS-06 Memory/RAG
  WS-05 Collective Intelligence/Academy
  WS-13 Domain Engines
      |
GATE G  EXPERIENCE
  WS-12 Web/Mobile/Voice
      |
GATE H  VALUE
  WS-14 IKE Revenue/Customer Ops
      |
GATE I  PRODUCTION
  WS-15 Deployment/DR
```

Parallel work is allowed inside a gate only when interfaces and ownership are frozen enough to prevent rework.

---

# 7. Priority execution waves

## Wave 0 — Reality freeze
1. Freeze exact baseline SHA.
2. Generate release-surface inventory.
3. Reconcile stale status claims.
4. Enumerate current PRs/worktrees/dirty branches.
5. Produce “known good / known broken / unknown” register.

**Do not begin broad feature work before Wave 0 closes.**

## Wave 1 — Certification foundation
1. Prove every `scripts/certify.py` lane collects intended tests.
2. Add missing non-Python CI/build lanes.
3. Eliminate silent skips in critical suites.
4. Generate SHA-bound receipts.
5. Make release gate consume all mandatory lane receipts.

## Wave 2 — Wiring and control-plane convergence
1. Router/API mount audit.
2. Canonical API prefix/schema.
3. Canonical agent registry.
4. Identity/tenant/authority propagation.
5. Database migration authority.

## Wave 3 — Reliability/security
1. Durable execution crash matrix.
2. Tool/MCP conformance.
3. OpenTelemetry trace spine.
4. Threat model and red-team corpus.
5. Backup/restore + incident drills.

## Wave 4 — Intelligence quality
1. Canonical memory/RAG map.
2. Claim integrity and provenance.
3. Collective intelligence integration.
4. Academy/competency certification.
5. Model/provider eval and routing matrix.

## Wave 5 — Product surfaces
1. Web CI/build/E2E.
2. Mobile CI/build/E2E.
3. Voice governed E2E.
4. Approval/receipt UX.
5. Accessibility/offline/error paths.

## Wave 6 — Revenue proof
1. Select one IKE offer.
2. Verify claims/scope.
3. Complete payment -> intake -> fulfillment -> receipt.
4. Measure unit economics/customer outcome.
5. Feed results into collective learning.

## Wave 7 — Production certification
1. Staging exact candidate.
2. Full certification universe.
3. Security + DR + rollback drills.
4. Canary.
5. Production release receipt.
6. 24/72-hour observation.
7. Principal closeout.

---

# 8. Work-item template for any agent

Every work item should be created in this form:

```text
TASK_ID:
WORKSTREAM:
OBJECTIVE:
BASE_SHA:
BRANCH_WORKTREE:
AUTHORIZATION:
SIDE_EFFECT_CLASS:
OWNER:
DEPENDENCIES:
IN_SCOPE:
OUT_OF_SCOPE:
DO_NOT_TOUCH:
CURRENT_EVIDENCE:
DEFECT:
HYPOTHESIS:
IMPLEMENTATION:
ACCEPTANCE_TESTS:
NEGATIVE_TESTS:
FAILURE_INJECTION:
SECURITY_IMPACT:
DATA_MIGRATION_IMPACT:
OBSERVABILITY:
ROLLBACK:
DOX_UPDATES:
RECEIPT_PATH:
RESULT: VERIFIED | PARTIAL | PENDING | BLOCKED | STALE | FAILED
UNRESOLVED:
NEXT_AUTHORIZED_ACTION:
```

A task is not complete until the acceptance evidence exists.

---

# 9. Definition-of-done matrix for each feature

Every production feature must answer YES to all applicable questions:

| Gate | Required question |
|---|---|
| Scope | Is it explicitly in the release manifest? |
| Ownership | Is one subsystem authoritative? |
| Contract | Are inputs/outputs/errors/version semantics defined? |
| Authority | Who/what may invoke it? |
| Tenant | Is tenant boundary explicit? |
| Privacy | Is data classification/retention defined? |
| Wiring | Is it reachable from intended callers only? |
| Tests | Are positive, negative, edge, concurrency tests present? |
| Failure | Are timeout/retry/crash/restart semantics tested? |
| Security | Has threat model coverage been added? |
| Evidence | Does execution produce trace/receipt linkage? |
| Observability | Are latency/errors/cost/usage measurable? |
| Recovery | Can failure be reconciled without duplicate effects? |
| UX | Can user distinguish proposed/pending/executed/failed? |
| Docs | Are DOX/operator docs current? |
| CI | Does mandatory automation execute the tests? |
| Cert | Is evidence bound to exact SHA/config/dependencies? |
| Deploy | Is rollout reversible? |
| Value | Is the feature used, required, or explicitly experimental? |

---

# 10. Release candidate law

A release candidate is certifiable only when:

1. Candidate SHA is frozen.
2. Working tree is clean except declared evidence output.
3. Release-surface manifest is current.
4. All mandatory test lanes collect and pass.
5. Mandatory frontend/mobile/build/contract tests pass.
6. Required Postgres/Redis/external-service test modes actually execute rather than skip.
7. Migrations pass empty bootstrap and supported upgrade path.
8. Security gates pass.
9. Agent certification dependency closures are current.
10. Critical Academy competencies are current.
11. End-to-end trace/receipt chain passes.
12. Backup/restore and rollback evidence are current for material infrastructure changes.
13. Documentation/claims validator passes.
14. Known defects are zero at release-blocking severity or explicitly dispositioned by Principal.
15. Release receipt binds git SHA, artifact digest, migration set, config generation, test receipts, approvals, deployment ID, and rollback target.
16. Any code/config/prompt/tool-schema/model-policy change after certification invalidates affected certification according to dependency closure.

CI green by itself does not authorize merge or deployment.

---

# 11. Completion dashboard

Maintain one generated dashboard with these rows:

- Repository Truth
- Test Universe
- API/Wiring
- Identity/Auth/Tenancy
- Agent Runtime
- Collective Intelligence
- Academy/Competency
- Memory/RAG/Provenance
- Durable Execution
- MCP/Tools/Integrations
- Observability/Evals
- Data/Migrations
- Security/Supply Chain
- Web
- Mobile
- Voice
- Legal/Trust/Consumer Intelligence
- Financial Intelligence
- IKE Revenue
- Customer Fulfillment
- Deployment
- Disaster Recovery
- Documentation/Claims
- Cost/Performance

For each row store:
`STATE | OWNER | LAST_VERIFIED_SHA | RECEIPT | BLOCKER | NEXT_ACTION | STALE_IF`

Dashboard state must be generated from evidence where possible, not manually painted green.

---

# 12. Anti-patterns — forbidden completion shortcuts

- Do not count files, lines, agents, routes, or tests as completion.
- Do not create new engines before proving the existing engine cannot satisfy the contract.
- Do not merge dead code because tests pass in isolation.
- Do not make production claims from mocks.
- Do not hide skipped tests.
- Do not certify against a different SHA than the release candidate.
- Do not let an agent self-verify its own learned lesson.
- Do not let competency imply authority.
- Do not let memory retrieval bypass tenant/authority/jurisdiction/freshness rules.
- Do not let a model/provider become a constitutional dependency.
- Do not expose chain-of-thought; record decisions, evidence, tool calls, policy outcomes, and concise rationales instead.
- Do not log secrets or private content merely for observability.
- Do not use AI-generated legal/financial claims as authority.
- Do not monetize unsupported claims.
- Do not deploy without rollback.
- Do not call a project “done” while release-bearing surfaces remain UNKNOWN.

---

# 13. The final target state

SintraPrime-Unified is complete when it operates as one governed system:

**Principal intent**
-> typed mission
-> authority/capability check
-> context/evidence retrieval
-> certified agent selection
-> governed model/tool execution
-> durable workflow
-> human approval where required
-> action
-> immutable/linked receipt
-> telemetry/evaluation
-> outcome
-> verified organizational learning
-> competency update
-> improved next decision

At that point SintraPrime is not merely a large repository. It is a **governed, testable, observable, recoverable, continuously learning operating system for IKE workflows**.

The architectural objective is not maximum autonomy. It is **maximum useful autonomy under explicit authority, evidence, reversibility, and measurable value**.


---

# 14. Wave 0 populated baseline — SP-COMPLETION-BASELINE-001

**Baseline SHA:** `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`  
**Detailed evidence:** `SP-COMPLETION-BASELINE-001.md`

| Workstream | Baseline state |
|---|---|
| WS-00 Repository truth/scope | RED |
| WS-01 Test-universe closure | YELLOW |
| WS-02 API/router wiring | YELLOW |
| WS-03 Identity/auth/tenancy/secrets | YELLOW |
| WS-04 Agent runtime convergence | YELLOW |
| WS-05 Collective intelligence/Academy | RED |
| WS-06 Memory/RAG/provenance | YELLOW |
| WS-07 Durable orchestration/scheduling | YELLOW |
| WS-08 MCP/tools/integrations | YELLOW |
| WS-09 Observability/evals/SRE | RED |
| WS-10 Data/migrations/event integrity | RED |
| WS-11 Security/safety | YELLOW |
| WS-12 Web/mobile/voice UX | RED |
| WS-13 Domain engines | YELLOW |
| WS-14 IKE revenue/customer ops | RED |
| WS-15 Deployment/DR | UNKNOWN |

**Wave 0 count:** GREEN 0 · YELLOW 9 · RED 6 · UNKNOWN 1.  
**Minimum remaining completion gates:** 44 (16 P0, 18 P1, 10 P2).

This baseline does not mean zero functionality works. A workstream turns GREEN only when its entire exit gate is proven against current evidence. See the baseline document for the evidence register, dependency graph, critical path, planning ranges, and authority boundary.
