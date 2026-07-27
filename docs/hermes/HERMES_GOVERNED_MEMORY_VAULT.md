# Hermes Governed Memory Vault

## Status

Increment 1 — governed architecture, schemas, and deterministic scaffolding.

## Objective

Create a durable, inspectable, Git-versioned knowledge system for Hermes that separates immutable source material from agent-maintained knowledge and continuously checks itself for contradictions, staleness, broken links, unsupported claims, access-policy defects, and provenance failures.

The system implements three first-class operations:

1. `ingest` — transform new source material into governed notes and links.
2. `query` — retrieve scope-filtered answers with source citations and confidence labels.
3. `lint` — audit the vault for integrity, isolation, and trust defects.

## Non-goals

- This is not a replacement for PostgreSQL operational state or tenant authority.
- This is not an ungoverned memory dump.
- This is not permission for Hermes to publish, contact clients, or alter source evidence autonomously.
- This is not a vector-database dependency.
- This is not a substitute for a jurisdiction-specific legal retention policy.

## Normative terms

- **Raw source**: original ingested bytes plus immutable provenance metadata.
- **Note**: a versioned, agent-maintained representation of source-grounded knowledge.
- **Claim**: the smallest governed assertion inside a note.
- **Receipt**: append-only evidence of an attempted or completed operation.
- **Quarantine**: isolated storage for material that cannot safely enter or remain in the active wiki.
- **Tenant scope**: the authoritative tenant identifier supplied by SintraPrime, never inferred from document text.
- **Matter scope**: an optional case or project identifier subordinate to a tenant.
- **Profile**: one active permission role attached to an invocation.

## Trust boundaries

### Layer 1 — Raw sources

Logical path: `hermes-vault/tenants/<tenant_id>/raw/`

Raw sources are write-once. Hermes must never rewrite or silently replace source bytes. A corrected or updated document is a new source with a new content-derived source ID. Deletion is prohibited through Hermes runtime operations. Retention or legal-hold deletion requires a separately authorized administrative process and a deletion receipt.

Every ingested source receives a receipt containing:

- receipt and operation IDs
- actor/profile and runtime version
- source path and stable source ID
- SHA-256 hash and byte length
- MIME/type classification
- timestamp in UTC with millisecond precision
- tenant and optional matter scope
- sensitivity label
- parser name/version
- prior receipt hash and receipt hash
- outcome and diagnostic codes

### Layer 2 — Governed wiki

Logical path: `hermes-vault/tenants/<tenant_id>/wiki/`

Hermes may create new note versions here. Existing note versions are never destructively replaced. A material update creates a new `version`, points to `previous_version_id`, and may set the prior note status to `superseded`. A verified claim may be downgraded to `unresolved` only by creating a successor version with the retraction or contradiction source cited.

Every material claim must distinguish:

- verified fact
- user assertion
- legal proposition
- inference
- unresolved claim
- recommended action

### Layer 3 — Governance schemas

Path: `hermes-vault/schema/`

Schemas define allowed note and receipt structures, required fields, link rules, source citation rules, lifecycle states, profile restrictions, migration rules, and lint checks.

## Physical segregation

Tenant data is physically segregated by directory and logically guarded by inline `tenant_id` fields. The directory tenant and inline tenant must match. Label-only tenancy is forbidden.

```text
hermes-vault/
  tenants/
    <tenant_id>/
      raw/
        inbox/
        processed/
        rejected/
      wiki/
        clients/
        matters/
        projects/
        decisions/
        people/
        organizations/
        law/
        procedures/
        content/
      receipts/
        ingest/
        query/
        lint/
        quarantine/
        resolution/
        access/
      indexes/
        source-index.jsonl
        entity-index.jsonl
        contradiction-index.jsonl
      quarantine/
  schema/
  templates/
  parser-cache/
  README.md
  .vault-version
```

Indexes and parser caches are rebuildable and are never sources of truth.

## Note lifecycle

Allowed states:

- `active`: current and queryable subject to profile/sensitivity policy.
- `superseded`: retained for history but excluded from current-answer synthesis by default.
- `archived`: retained and normally excluded from active queries.
- `quarantined`: unavailable to ordinary query profiles.
- `deleted_by_authority`: tombstone only; permitted solely through an external retention/legal-hold authority.

Lifecycle transitions are append-only events recorded by receipts. No transition may erase the earlier note version.

## Contradictions

A contradiction is a first-class indexed governance record, not merely free-text note metadata. It records:

- contradiction ID
- keyed claim identity
- participating note and claim IDs
- source IDs
- detecting lint run ID
- status: `open|resolved|accepted_variance|false_positive`
- resolution authority and timestamp
- resolution rationale and receipt ID

Lint may detect and open contradictions but may never substantively resolve them. Resolution requires `hermes-librarian` plus an explicit human-review authority identifier.

## Quarantine policy

Material enters quarantine when scope is ambiguous, schema validation fails after safe parsing, a source hash changes, restricted data lacks permission, malware/executable content is detected, or required provenance is missing.

Exit requires all applicable conditions:

1. schema-valid replacement or correction,
2. verified tenant/matter scope,
3. source/provenance verification,
4. authorized human review for restricted or contradictory material,
5. a quarantine-resolution receipt.

Quarantined originals remain preserved.

## Operation contract: ingest

### Inputs

- one or more files under a tenant `raw/inbox/`
- authoritative tenant and optional matter scope
- one active invoking profile
- operation ID and runtime version
- optional `read_only` or dry-run mode

### Processing

1. Authorize profile and scope before reading source contents.
2. Canonicalize and verify the tenant-root path; reject traversal and symlink escape.
3. Hash the source before parsing.
4. Reject executables, unsupported archives, and detected secret-bearing material according to policy.
5. Detect duplicate source IDs; return an idempotent result without duplicate notes.
6. Store source bytes write-once.
7. Extract normalized text without modifying the source.
8. Detect entities, dates, decisions, commitments, deadlines, and claims.
9. Locate candidate existing notes within the same tenant only.
10. Validate proposed notes against the declared schema version.
11. Create new note versions using source-grounded claims only.
12. Record contradictions instead of overwriting earlier claims.
13. Write a chained append-only receipt.
14. Move the inbox copy to `processed/` only after source storage and receipt validation succeed.

### Failure behavior

- Authorization failure: deny before touching tenant data and emit an access receipt where safe.
- Parser failure: preserve source, place processing record in `rejected/`, and issue a refusal receipt.
- Schema violation: quarantine the proposed note; do not activate it.
- Scope ambiguity: quarantine; do not guess the tenant or matter.
- Restricted data with insufficient permissions: deny and log.
- Parser cache corruption: discard and rebuild cache from immutable raw source; never promote cache content directly.
- Contradictory source: preserve both claims and open a contradiction record.
- Receipt-write failure: fail closed; no source is marked processed and no note becomes active.

## Operation contract: query

Query returns a structured response, optionally rendered as Markdown, containing:

- concise synthesized answer
- filtered claim records
- supporting note IDs and versions
- raw source IDs
- confidence assessment
- unresolved contradictions
- freshness timestamp
- redaction summary
- recommended next action when requested
- query receipt ID

Queries must apply authorization, tenant scope, lifecycle status, sensitivity, and profile filtering before retrieval and synthesis. Cross-tenant requests are hard-denied, return no data, and emit an access receipt.

Hermes must never present an inference as a verified fact. Legal research must include jurisdiction, effective date, and source authority when available.

## Operation contract: lint

Lint is mandatory and scheduled. A full-vault lint failure blocks promotion/merge certification for this subsystem. A tenant-local defect quarantines affected records and may block queries that depend on them, but does not make unrelated tenants unavailable.

Checks include:

- schema and inline schema-version validity
- directory/inline tenant mismatch
- claims with missing or nonexistent source IDs
- broken note links and orphan notes
- duplicate entities
- stale active notes
- superseded claims presented as current
- contradictory active claims
- over-connected notes caused by weak matching
- missing sensitivity labels
- restricted notes readable by unauthorized profiles
- source hash mismatch
- processed source missing an ingest receipt
- receipt hash-chain discontinuity
- note-version chain discontinuity
- quarantine items lacking diagnostics
- indexes inconsistent with authoritative files

Lint may auto-fix only deterministic formatting and rebuildable indexes/caches. It must not alter source bytes, resolve contradictions, change tenant scope, or promote quarantined material.

## Profile ACL

Exactly one profile is active per operation. Profile switching requires a new invocation context and a new authorization decision. Agents may be configured for multiple eligible profiles, but may not combine permissions inside one invocation.

| Action | librarian | research | content | client-ops |
|---|---:|---:|---:|---:|
| Read permitted raw source | yes | yes | no | scoped only |
| Create source receipt/index | yes | no | no | no |
| Create or version notes | yes | proposal only | no | no |
| Add research claims | yes | proposal only | no | no |
| Run lint/quarantine | yes | no | no | no |
| Query verified facts | yes | yes | yes | scoped only |
| Query assertions/inferences | yes | yes | no | scoped when authorized |
| Read confidential/restricted | policy-bound | policy-bound | no | policy-bound and scoped |
| Resolve contradiction | human-authorized only | no | no | no |
| External publication/contact | no | no | separate approval gate | separate approval gate |

`proposal only` means output is placed in a review queue and cannot mutate the active wiki.

## Sensitivity enforcement

- `public`: all authorized profiles.
- `internal`: librarian and research; content only for explicitly approved voice/content notes.
- `confidential`: librarian/research and specifically authorized client-ops within tenant scope.
- `restricted`: explicit policy grant plus tenant/matter scope; never available to content.

Encryption at rest is a deployment requirement for vaults containing confidential or restricted data. Increment 1 defines the requirement; key management and encrypted storage adapters are Increment 2 hardening work.

## Receipt policy

Receipts conform to `hermes.memory.receipt.v1.schema.json`. They are immutable JSON records chained per tenant and operation stream using `previous_receipt_hash` and `receipt_hash`. Hash calculation uses canonical JSON excluding `receipt_hash`. Query receipts store an output hash and source/note references, not unrestricted answer bodies.

Retention follows the governing tenant retention/legal-hold policy. In the absence of an approved policy, receipts and source tombstones are retained indefinitely; Hermes itself cannot delete them.

## Scheduling recommendation

- 08:00 daily — receipt-chain validation and private encrypted backup
- 10:00 daily — authorized tenant inbox ingest
- 02:00 Sunday — full lint
- hourly — optional read-only inbox detection; no mutation unless the full ingest gate passes

## Initialization and resilience

The initializer is idempotent and non-destructive:

- creates missing directories and baseline files,
- never overwrites existing files,
- honors PowerShell `-WhatIf`,
- writes a vault format marker,
- rejects a root path that resolves to an existing non-directory,
- does not create tenant directories until a tenant ID is explicitly supplied.

## Schema versioning and migration

Every note and receipt stores `schema_version` inline. New schema versions are additive and coexist with earlier versions. Query runtimes must read all supported versions and normalize output to the current query contract. Migration creates new note versions and migration receipts; it never rewrites historical notes. Dropping support for a schema version requires a separately approved deprecation decision and complete migration evidence.

## Acceptance criteria — Increment 1

1. Vault scaffold is deterministic, idempotent, non-destructive, and `-WhatIf` safe.
2. Note schema validates tenant scope, inline schema version, lifecycle, version chain, sensitivity, and source-grounded verified facts.
3. Receipt schema requires actor, operation, scope, timestamps, outcome, and tamper-evident chain fields.
4. Raw files are write-once and never overwritten by runtime tooling.
5. Query contract is tenant-, lifecycle-, sensitivity-, and profile-filtered.
6. Lint detects unsupported claims, broken links, tenant mismatch, orphans, stale notes, contradictions, hash mismatches, and receipt-chain failures.
7. Profile policy prevents content and client-ops from mutating the wiki.
8. Quarantine entry and exit criteria are explicit and receipt-backed.
9. Schema migration preserves historical versions.
10. The subsystem remains additive and does not alter PostgreSQL authority.

## Merge gate — Increment 1

This architecture increment may merge only after repository-local certification proves:

- both JSON schemas parse and validate known-good and known-bad fixtures,
- the initializer passes fresh-root, existing-root, tenant-root, `-WhatIf`, and non-directory-root tests,
- no initializer test observes overwritten content,
- documentation and schemas agree on status, sensitivity, profile, lifecycle, and identifier enums,
- secret scanning and repository policy checks pass.

Runtime claims such as actual write-once enforcement, chained-receipt verification, tenant-safe query execution, or contradiction resolution are **not certified by Increment 1** and must not be represented as operational until Increment 2 tests pass.

## Increment 2 sequencing

### Phase 1 — Core runtime and isolation

1. Ingest runtime, note versioning, source storage, schema validation, and idempotency.
2. Tenant directory resolver and cross-tenant hard-deny guards.

### Phase 2 — Source processing

3. Pluggable TXT, Markdown, JSON, email, transcript, PDF, and DOCX parsers.
4. Normalized parser output, cache recovery, source linking, and source-ID generation.

### Phase 3 — Governance engine

5. Lint engine, quarantine decisions, deterministic re-runs, and chained lint receipts.
6. Keyed-claim contradiction detection and human resolution queue.

### Phase 4 — Query and profiles

7. Structured query engine with lifecycle, sensitivity, source, type, and profile filters.
8. Runtime ACL enforcement and explicit profile-switch boundaries.

### Phase 5 — API and observability

9. Tenant-scoped CLI/HTTP endpoints with authentication/authorization hook points.
10. Operations Floor telemetry for ingest, lint, quarantine, contradiction, latency, and access-denial events.

### Phase 6 — hardening

11. Encryption adapter and key-management decision.
12. Secret scanning, backup/restore, migration, resilience, and full certification suite.

## Increment 2 acceptance-test catalog

- `AT-INGEST-01..04`: valid ingest, missing provenance, duplicate idempotency, tenant scope.
- `AT-SOURCE-01..03`: write-once sources, controlled deletion/tombstone, source existence.
- `AT-LINT-01..04`: clean lint, quarantine, provenance failure, deterministic rerun.
- `AT-CONTRA-01..03`: conflict detection, lint-run linkage, authorized resolution receipt.
- `AT-QUERY-01..04`: research visibility, content filtering/redaction, client isolation, denied-access receipt.
- `AT-SEC-01..03`: secret quarantine, chained receipts, authorization before data access.
- `AT-INIT-01..02`: idempotent existing vault and complete new scaffold.
- `AT-RES-01`: malformed notes quarantine without crashing lint.
