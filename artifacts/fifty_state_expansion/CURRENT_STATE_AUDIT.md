# Fifty-State Trust Intelligence Current-State Audit

Status: Phase 0 audit and containment
Worktree: `C:\Users\admin\SintraPrime-Unified-fifty-state`
Branch: `feat/fifty-state-trust-intelligence`
Base HEAD: `6e3d2740faac4e9a46dd1943ad35ef339cc088ad`
Audit date: 2026-08-03

## Scope Boundary

This audit treats current repository content as implementation evidence, not legal authority. Static rule tables, templates, workbooks, manuals, examples, and UI copy are not accepted as verified law. Claims about accepted-for-value, birth-certificate securities, secret Treasury accounts, automatic acquiescence, private-law immunity, or UCC filings against persons or unrelated assets must be handled as `UNVERIFIED_PRIVATE_LAW_CLAIM` unless independently verified against controlling primary authority.

No deployment, workflow, merge, or production infrastructure change was performed.

## Repository Baseline

| Item | Finding |
|---|---|
| Repository root | `C:\Users\admin\SintraPrime-Unified-fifty-state` |
| Current branch | `feat/fifty-state-trust-intelligence` |
| Current HEAD SHA | `6e3d2740faac4e9a46dd1943ad35ef339cc088ad` |
| Source checkout status | Isolated worktree created from existing `feat/hermes-personal-assistant-core` HEAD to avoid disturbing active Hermes work |
| Relevant package managers | Python project metadata in `pyproject.toml`; Node/npm root `package.json`; web package in `web/package.json` |
| Backend framework | FastAPI async app in `portal/main.py` |
| ORM/database | SQLAlchemy ORM in `portal/models`; PostgreSQL/asyncpg runtime; SQLite used by many tests; raw SQL migrations in `portal/migrations`; architecture doc says no Alembic authority despite Alembic dependency |
| Frontend framework | React 18 + TypeScript + Vite in `web/` |
| Python test commands | `pytest`; project default excludes `experimental`; focused portal tests under `portal/tests` |
| Frontend commands | root: `npm run dev/build/lint/type-check`; web: `npm run build`, `npm run lint`, `npm run type-check` |
| Python formatting/lint | `python -m black ...`; `python -m ruff check ...`; Ruff excludes many legacy domains including `trust_law`, `parl`, `agent_protocol`, `artifacts`, `financial_mastery`, `legal_intelligence`, and others |
| CI/certification references | `docs/ARCHITECTURE.md`, `docs/ci/*`, portal certification tests for auth/RBAC, audit/correlation, WebSocket hardening, PostgreSQL bootstrap |

## Governing Repository Instructions Read

- `AGENTS.md`: DOX hierarchy, read-before-edit, update-after-edit, child scope requirements.
- `CONTRIBUTING.md`: legal/financial accuracy, jurisdiction caveats, test expectations, PR process.
- `docs/ARCHITECTURE.md`: authoritative app boundaries, portal as API/identity boundary, web as frontend, raw SQL migrations, no single agent runtime authority.
- `portal/AGENTS.md`: FastAPI portal contracts, PostgreSQL/Redis/MinIO assumptions, RBAC/RLS, AES-256, immutable audit log, soft deletes, raw SQL migration requirements.
- `governance/blackstone/AGENTS.md`: Blackstone governance subtree is framework-only; no product code or operational schema belongs there.

## Existing Capabilities

### Jurisdictions and Legal Authority

- `trust_law/jurisdiction_analyzer.py` contains static scoring for selected high-profile trust jurisdictions such as South Dakota, Nevada, Alaska, Delaware, Wyoming, Tennessee, New Hampshire, Florida, Texas, New York, California, and offshore jurisdictions.
- `trust_law/__init__.py` advertises "All 50 US States + 7 International Jurisdictions", but the implementation reviewed is not backed by primary-authority records, verification states, effective dates, source URLs, or tests for fifty-state completeness.
- `blackstone/models.py` defines useful concepts for `Source`, `Jurisdiction`, `Claim`, `EvidenceItem`, confidence, source classification, conflicts, and provenance. These are in-memory/dataclass models, not normalized portal legal-rule persistence.
- `blackstone/engines/authority_engine.py` can select primary legal sources from a claim's evidence and detect same-jurisdiction primary conflicts, but it does not store enacted state-law rule logic or comprehensive supersession history.
- `governance/blackstone/volume-*` contains strong conceptual governance materials for evidence confidence, source taxonomy, review protocol, hallucinated citation tests, conflicting authority, and provenance failures. These are governance references, not live product schema.

### Trust Law

- `trust_law/trust_knowledge_base.py` contains a large static doctrine dictionary covering spendthrift trusts, discretionary trusts, purpose trusts, charitable remainder trusts, asset-protection trusts, blind trusts, and many other concepts.
- The trust knowledge tables include legal-basis strings and case names, but they do not encode authority type, source URL, source document ID, effective date, last verified date, verifier, verification status, confidence score per authority, or human-review status.
- `trust_law/trust_reasoning_engine.py` performs keyword-based trust review: it detects trust type, missing elements, spendthrift text, successor trustees, retained control signals, and jurisdiction clauses. It gives issue-spotting recommendations but is not a verified legal-rule engine.
- `trust_law/trust_document_generator.py` appears to generate templates. Existing contributor guidance requires bracketed fields and disclaimers, but no evidence was found that templates are jurisdiction-verified or attorney-approved.
- `web/src/pages/TrustLaw.tsx` exposes a static "Trust Law Explorer" with 30 doctrines, UCC tracking examples, and 19 jurisdictions. The UI does not display legal support status, primary-authority completeness, verification date, or human-review status.

### UCC and Financing Statements

- `trust_law/ucc_filing_assistant.py` has static Article 1/2/3/8/9 summaries, collateral analysis, UCC-1/UCC-3 form text generation, priority analysis, and limited state filing requirements.
- The UCC assistant includes generally accurate Article 9 concepts such as attachment, debtor name exactness, first-to-file-or-perfect, continuation windows, and distinctions between financing-statement collateral descriptions and security agreements.
- The assistant currently produces filing instructions and estimated fees without controlling state authority records, filing-office verification dates, official form versioning, or filing-office rejection-ground modeling.
- The module must be treated as an educational/workflow draft until state law and official filing office rules are verified.

### Creditor Response and Consumer Evidence

- `portal/routers/trust_compliance.py` is an evidence-intake safety gate. It detects high-risk language such as "accepted for value", "birth certificate", "cusip", "self-executing", "silence equals agreement", "automatic default", public-law exemption language, and unsupported accusations.
- The same router maps risky language to safer evidence-review wording and enforces an "external action locked" policy in its returned policy pack.
- `agents/howard_*` agents are evidence-intake/template/recovery helpers. `agents/AGENTS.md` explicitly limits Howard agents to evidence intake and local drafts; they may not send, file, email, mail, serve, post, delete, or contact third parties.
- `blackstone/cases/*` contains case-oriented consumer/creditor examples for LVNV, PayPal, Self Financial, UACC repossession, and related matters.
- No normalized creditor evidence model was found for claimant identity, debt owner, servicer/collector split, notices, deadlines, assignment chain, statute of limitations, arbitration, court status, exhibit indexes, or evidence-readiness scoring.

### Financial, Accounting, Tax, and Audit Readiness

- `portal/models/billing.py` and `portal/routers/billing.py` support invoices, expenses, payments, time entries, and trust-account-oriented billing endpoints.
- `web/src/components/financial/*`, `web/src/pages/FinancialEmpire.tsx`, and `web/src/api/financial.ts` support dashboard-style personal/financial UI projections.
- `app_builder` can generate financial dashboard schemas and app templates, but this is a builder/prototype domain and is excluded from Ruff's active lint scope.
- Search results show no production-grade general ledger, journal-entry, trial-balance, fiduciary principal-and-income, audit assertion, sampling/materiality, workpaper, or audit-readiness binder engine in the authoritative `portal/` backend.
- Existing audit terminology primarily means application audit logs and evidence/audit records, not CPA-style audit procedures.

### Evidence, Provenance, Citations, and Audit Trails

- `portal/services/evidence_hash_boundary.py` defines a deterministic evidence hash boundary with canonical serialization. This is a strong reuse candidate.
- `portal/services/evidence_snapshot_service.py`, `portal/services/evidence_audit_service.py`, and `portal/services/packet_renderer.py` support immutable evidence snapshots, audit records, packet rendering, and evidence hash verification.
- `portal/models/evidence_snapshot.py` and `portal/models/audit_record.py` are portal persistence anchors for evidence and audit records.
- `portal/services/audit_service.py` writes hash-chained audit logs.
- `blackstone` engines and models include source classification, provenance, evidence, authority, and risk concepts, but they are not yet integrated as a portal-native legal-rule store.

### AI Agents, Parliament, Consensus, and Large-Batch Review

- `trust_law/trust_parliament.py` implements a six-agent trust-law deliberation simulation using static roles and generated opinions. It uses majority recommendation and confidence-style outputs, not durable jobs or weighted evidence voting.
- `web/src/pages/AIParliament.tsx` is a static front-end demo of six agents, votes, confidence, and debate messages. It does not connect to a durable backend job system.
- `parl/` contains policy/adaptation/reward-oriented experiments and tests, but it is excluded from Ruff active scope.
- `agent_protocol/` includes agent discovery, shared memory, message bus, and swarm orchestration with tests. It is not the architecture authority for production execution.
- `docs/ARCHITECTURE.md` explicitly says there is no single agent runtime authority and that convergence is unresolved.

### Privacy, Security, RBAC, and Tenant Isolation

- `portal/auth/rbac.py` is the current RBAC authority. It validates JWT claims, role hierarchy, permissions, and trusted tenant/user identity propagation into correlation context.
- `portal/models/user.py`, `portal/services/permission_provisioning.py`, and portal auth certification tests cover roles/permissions and tenant/RBAC certification.
- `portal/services/encryption_service.py` exists; portal DOX requires AES-256 encryption, immutable audit logs, and soft deletes.
- `portal/services/storage_service.py`, `document_export_service.py`, `share_service.py`, and `document_processor.py` provide document storage/export/share processing primitives.
- `portal/auth/ws_hardening.py`, session/SSO modules, and certification tests cover WebSocket hardening and session behavior.
- No complete data-classification taxonomy, privacy budget, honeytoken, selective-disclosure, purpose-bound access, watermarking, metadata stripping, legal hold, or field-level encryption policy model was found as an integrated product capability.

### Document Storage, Generation, and Processing

- `portal/models/document.py`, `portal/routers/documents.py`, `portal/services/document_processor.py`, `storage_service.py`, `share_service.py`, and `document_export_service.py` provide document vault foundations.
- `artifacts/legal_document_library.py` and `trust_law/trust_document_generator.py` contain template-generation style capabilities.
- No source-ingestion pipeline was found that classifies documents into the directive's classes, extracts citations, verifies citations, identifies stale/unsupported claims, stores copyright/permitted-use metadata, and quarantines pseudo-legal material.

### Dashboards, Scoring, Simulation, and Timeline

- `web/src/pages/TrustLaw.tsx`, `FinancialEmpire.tsx`, `EntityGovernance.tsx`, `AIParliament.tsx`, `DocumentVault.tsx`, and `mission-control/*` provide visual surfaces.
- `app_builder/digital_twin.py` contains life-event and risk-modeling concepts, but this is not a portal-native trust digital twin.
- `trust_law/asset_protection_planner.py` and `jurisdiction_analyzer.py` provide strategy/ranking concepts. They are static and not evidence-linked.
- No production trust-health score, jurisdiction-change workflow, simulation lab, trust evolution tracker, or beneficiary education portal was found in authoritative portal models/routes.

## Incomplete or Duplicated Logic

- Trust-law concepts are duplicated across `trust_law/*`, `web/src/pages/TrustLaw.tsx`, `developer_experience/cookbook.py`, `developer_experience/openapi_spec.py`, `app_builder`, and governance/Blackstone references.
- Evidence and provenance concepts exist in both `portal/services/evidence_*` and `blackstone/models.py`; the former is production-adjacent, while the latter is a governance/engine model.
- Agent/parliament concepts exist in `trust_law/trust_parliament.py`, `web/src/pages/AIParliament.tsx`, `parl/`, `agent_protocol/`, and `agents/*`; architecture marks execution authority unresolved.
- Financial dashboard and accounting concepts exist in `web`, `app_builder`, and billing modules, but there is no unified accounting ledger/workpaper authority.

## Security Concerns

- Many legacy or prototype packages are excluded from Ruff and may contain unreviewed code paths.
- Existing static legal/trust/UCC modules can produce confident-sounding legal outputs without verified primary authority.
- `trust_law/ucc_filing_assistant.py` can generate filing instructions, which is high risk unless constrained to draft/educational outputs and gated by professional review.
- `web/src/pages/TrustLaw.tsx` displays doctrine and UCC content without support-level or legal-review warnings.
- No explicit unsupported-claim quarantine persistence/interface exists; the trust-compliance router only detects some phrases at request time.
- No fully integrated privacy classification/access-purpose/privacy-budget model exists for sensitive legal/financial documents.

## Legal-Risk Concerns

- `trust_law/__init__.py` claims all-50-state coverage, but audited implementation does not satisfy primary-authority verification requirements.
- Static doctrine descriptions state broad creditor-protection effects and jurisdiction strengths. These could be mistaken for legal conclusions if surfaced without review.
- UCC filing guidance could be misused for filing assertions unsupported by attachment, security agreement, value, debtor rights, and applicable state rules.
- Existing consumer evidence routing is better bounded than the older trust-law modules, but it still lacks full deadline and statute-of-limitations modeling.
- Financial outputs and dashboards are not audit opinions and should be labeled accordingly if expanded.

## Missing Tests

- No tests demonstrate fifty-state jurisdiction coverage with support levels.
- No tests for LegalAuthority/JurisdictionRule schemas, effective dates, repeals, supersession, conflicts, or incomplete research states.
- No tests for unsupported private-law document quarantine as a durable product feature.
- No tests for creditor evidence-readiness scoring, FDCPA/FCRA/TILA/ECOA/EFTA/FCBA overlays, or collector/original-creditor classification.
- No tests for trust health scoring explainability or jurisdiction-change simulation.
- No tests for 1,000-document parliament processing, durable queues, resumability, dead-letter handling, dissent preservation, or weighted evidence voting.
- No security tests specific to legal-rule lookup authorization, privacy export, sensitive field exposure, or document-ingestion prompt injection.

## Stale or Unverified Citations

- `trust_law/trust_knowledge_base.py` and `trust_law/ucc_filing_assistant.py` include citations and case names without source URLs, official source IDs, verification dates, verifier identity, or supersession state.
- `web/src/pages/TrustLaw.tsx` contains case/doctrine references directly in UI source without source metadata.
- Governance Blackstone test cases intentionally include fabricated/stale/conflicting citation scenarios; they are useful for future tests but not live authority.

## State Coverage Count and Matrix

Production-eligible state legal-rule coverage count: `0`.

Current repository has static mentions for selected states and broad all-state claims, but no jurisdiction satisfies the directive's requirements for primary-authority completeness, encoded rules, tests, human review, and production eligibility.

| Jurisdiction | Current support status | Notes |
|---|---|---|
| Alabama | NOT_STARTED | No verified portal-native rule set found |
| Alaska | NOT_STARTED | Static DAPT/trust references only |
| Arizona | NOT_STARTED | No verified portal-native rule set found |
| Arkansas | NOT_STARTED | No verified portal-native rule set found |
| California | NOT_STARTED | Static UI/trust references only |
| Colorado | NOT_STARTED | Static references only |
| Connecticut | NOT_STARTED | No verified portal-native rule set found |
| Delaware | NOT_STARTED | Static trust-jurisdiction references only |
| District of Columbia | NOT_STARTED | No verified portal-native rule set found |
| Florida | NOT_STARTED | Static trust-jurisdiction references only |
| Georgia | NOT_STARTED | No verified portal-native rule set found |
| Hawaii | NOT_STARTED | No verified portal-native rule set found |
| Idaho | NOT_STARTED | No verified portal-native rule set found |
| Illinois | NOT_STARTED | Static land-trust/UI references only |
| Indiana | NOT_STARTED | No verified portal-native rule set found |
| Iowa | NOT_STARTED | No verified portal-native rule set found |
| Kansas | NOT_STARTED | No verified portal-native rule set found |
| Kentucky | NOT_STARTED | No verified portal-native rule set found |
| Louisiana | NOT_STARTED | No verified portal-native rule set found |
| Maine | NOT_STARTED | No verified portal-native rule set found |
| Maryland | NOT_STARTED | No verified portal-native rule set found |
| Massachusetts | NOT_STARTED | Static UI case reference only |
| Michigan | NOT_STARTED | No verified portal-native rule set found |
| Minnesota | NOT_STARTED | No verified portal-native rule set found |
| Mississippi | NOT_STARTED | Static case reference only |
| Missouri | NOT_STARTED | Static case/reference examples only |
| Montana | NOT_STARTED | No verified portal-native rule set found |
| Nebraska | NOT_STARTED | No verified portal-native rule set found |
| Nevada | NOT_STARTED | Static DAPT/UCC/trust references only |
| New Hampshire | NOT_STARTED | Static trust-jurisdiction references only |
| New Jersey | NOT_STARTED | No verified portal-native rule set found; should be first research pilot |
| New Mexico | NOT_STARTED | No verified portal-native rule set found |
| New York | NOT_STARTED | Static UI/case references only |
| North Carolina | NOT_STARTED | No verified portal-native rule set found |
| North Dakota | NOT_STARTED | No verified portal-native rule set found |
| Ohio | NOT_STARTED | Static UI reference only |
| Oklahoma | NOT_STARTED | No verified portal-native rule set found |
| Oregon | NOT_STARTED | Static case reference only |
| Pennsylvania | NOT_STARTED | No verified portal-native rule set found |
| Rhode Island | NOT_STARTED | No verified portal-native rule set found |
| South Carolina | NOT_STARTED | No verified portal-native rule set found |
| South Dakota | NOT_STARTED | Static trust-jurisdiction references only |
| Tennessee | NOT_STARTED | Static trust-jurisdiction references only |
| Texas | NOT_STARTED | Static UI/trust references only |
| Utah | NOT_STARTED | Static UI reference only |
| Vermont | NOT_STARTED | No verified portal-native rule set found |
| Virginia | NOT_STARTED | Static UI reference only |
| Washington | NOT_STARTED | Static bankruptcy case reference only |
| West Virginia | NOT_STARTED | No verified portal-native rule set found |
| Wisconsin | NOT_STARTED | No verified portal-native rule set found |
| Wyoming | NOT_STARTED | Static trust-jurisdiction references only |
| Federal overlays | NOT_STARTED | Static IRC/UCC/federal references only; no verified overlay engine |

## Data-Model Gaps

- Missing `LegalAuthority` persistence with citation, URL/source ID, effective/repeal dates, verification status, verifier, last verified date, quoted text, limitations, and tags.
- Missing `JurisdictionRule` persistence with domain/topic, machine-readable rule logic, authority links, effective range, confidence, exceptions, conflicts, and versioning.
- Missing jurisdiction coverage table with explicit support status and human-review status.
- Missing unsupported-claim quarantine table/document class.
- Missing creditor case/evidence/deadline/assignment/court/arbitration models.
- Missing trust health assessment, score-factor, evidence-link, and professional-review models.
- Missing simulation run/scenario/event-output models.
- Missing privacy classification, purpose-bound access, privacy budget, selective disclosure, and export ledger models.
- Missing durable parliament job/batch/document/chunk/vote/dissent/conclusion models.

## Scalability Bottlenecks

- Trust-law and UCC data are static Python dictionaries; this will not scale to fifty-state verification, source updates, or statutory drift.
- Parliament demos are synchronous/static and not backed by queues, checkpointing, resumability, or batch manifests.
- UI legal content is embedded in component source, making legal updates coupled to frontend deployment.
- Ruff excludes many target domains, so quality gates do not currently cover the modules most relevant to this expansion.
- Existing document processing lacks large-batch ingestion architecture, citation graphing, deduplication, and retry/dead-letter semantics.

## UX Deficiencies

- Trust Law UI lacks support status, verification state, authority links, limitations, professional-review gates, and jurisdiction completeness warnings.
- AI Parliament UI relies on demo data and majority-style visualizations rather than evidence-weighted conclusions and preserved dissent.
- No coverage map, professional review queue, creditor evidence workspace, privacy command center, trust health report, simulation lab, or evolution timeline was found as a complete portal feature.

## Recommended Reuse

- Reuse `portal/` as the authoritative API, identity, RBAC, audit, and persistence boundary.
- Reuse `portal/services/evidence_hash_boundary.py`, `evidence_snapshot_service.py`, `evidence_audit_service.py`, and `packet_renderer.py` for provenance and evidence package integrity.
- Reuse `blackstone/models.py` concepts for source classification, evidence, claim status, confidence, risk, recommendation, and provenance, but implement portal-native persistence for production workflows.
- Reuse `portal/auth/rbac.py`, `audit_service.py`, and certification tests as the baseline for authorization and audit logging.
- Reuse `portal/routers/trust_compliance.py` phrase-detection policy as a starting unsupported-claim quarantine classifier.
- Reuse `web/` visual language and existing pages as prototypes, but move legal content behind verified APIs.

## Recommended Deprecation or Containment

- Contain `trust_law/*` as legacy research/prototype until all legal claims are migrated into verified authority/rule records.
- Do not expose UCC filing instructions as actionable production guidance until official state filing rules and Article 9 authority are verified.
- Do not use `trust_law/trust_parliament.py` as a production decision engine; replace with durable, evidence-weighted parliament jobs.
- Do not rely on static UI doctrine arrays for legal content.
- Quarantine pseudo-legal/private-law manuals and claims under `UNVERIFIED_PRIVATE_LAW_CLAIM`.

## Proposed Migration Sequence

1. Create portal-native authority, jurisdiction coverage, rule, source-ingestion, and unsupported-claim quarantine schemas.
2. Build read-only APIs for coverage, authorities, rules, and quarantined claims with RBAC and audit logging.
3. Migrate current `trust_law` static content as `unverified` research records, not production rules.
4. Implement New Jersey legal research pilot using primary authorities only; encode a narrow rule set with tests.
5. Add support-level UI indicators before exposing any legal rules.
6. Add creditor evidence workspace and evidence-readiness scoring using evidence records, not legal conclusions.
7. Add trust health scoring with explainable factors and professional-review triggers.
8. Add source ingestion, citation extraction, and unsupported-claim quarantine.
9. Add simulation/evolution models and APIs.
10. Replace static parliament demos with durable jobs, weighted evidence review, dissent preservation, and synthetic 1,000-document tests.

## Phase 0 Architecture Proposal

- Authority store: `legal_authorities`, `jurisdiction_rules`, `jurisdiction_coverage`, `legal_source_documents`.
- Quarantine store: `unsupported_claims`, linked to source documents and evidence snapshots.
- Creditor workspace: `creditor_matters`, `creditor_parties`, `creditor_evidence_items`, `creditor_deadlines`, `creditor_events`, `creditor_scores`.
- Trust assessment: `trust_assessments`, `trust_score_factors`, `trust_review_triggers`, `trust_simulation_runs`, `trust_timeline_events`.
- Privacy: `data_classifications`, `purpose_bound_access_requests`, `privacy_exposure_events`, `selective_disclosure_packets`.
- Parliament: `parliament_jobs`, `parliament_documents`, `parliament_chunks`, `parliament_votes`, `parliament_dissents`, `parliament_conclusions`, `parliament_checkpoints`.

All should be tenant-scoped, RBAC-gated, auditable, and explicit about legal-review status.

## Security Review Summary

Immediate required controls before Phase 1:

- Mark all imported legal content `unverified` by default.
- Require `requires_human_review=True` for all legal/accounting/tax rules until professional review.
- Add server-side permissions for legal-rule management, professional review, creditor workspace, financial audit readiness, privacy exports, and parliament jobs.
- Audit all rule reads, source imports, exports, professional challenges, and privacy disclosures.
- Prevent UI from displaying "complete", "valid", "protected", "perfected", or "discharged" without verified authority and review status.

## Scope Boundaries for Next Work

- Start with schemas and tests, not broad UI polish.
- Start New Jersey only after the authority schema and quarantine model exist.
- Do not browse or encode legal rules without recording primary authority source URLs, effective dates, last verified dates, and verification status.
- Do not create final execution-ready documents or filing instructions without licensed professional review workflow.

## Phase 0 Artifact Review Addendum

Review completed after creation of the Phase 0 artifacts.

- `DEFICIENCY_REGISTER.json` entries were expanded so each Phase 0 deficiency has non-empty evidence, affected files, recommended action, acceptance criteria, and open status.
- Severity classifications distinguish critical production blockers, high-risk incomplete capabilities, and medium repository/process gaps.
- `data/jurisdictions/coverage.json` includes all fifty states, District of Columbia, and federal overlays. Every entry remains `NOT_STARTED` with `researched`, `encoded`, `tested`, `human_reviewed`, and `production_eligible` set to `false`.
- Support statuses use only the approved enum values in `coverage.json`.
- Audit conclusions distinguish static material, prototype or demo code, reusable portal primitives, and unsupported private-law claims.
- No uploaded, generated, static, workbook, template, or private manual material is treated as controlling law merely because it exists in the repository.
- The exact ignore rule affecting `data/jurisdictions/coverage.json` is `.gitignore:63:data/`. Phase 0 therefore uses `git add -f data/jurisdictions/coverage.json` instead of broad `.gitignore` exceptions, to avoid unintentionally exposing unrelated ignored `data/` content.
