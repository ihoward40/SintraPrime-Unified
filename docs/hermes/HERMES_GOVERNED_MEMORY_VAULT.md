# Hermes Governed Memory Vault

## Status

Increment 1 — architecture and executable scaffolding.

## Objective

Create a durable, inspectable, Git-versioned knowledge system for Hermes that separates immutable source material from agent-maintained knowledge and continuously checks itself for contradictions, staleness, broken links, and unsupported claims.

The system implements three first-class operations:

1. `ingest` — transform new source material into governed notes and links.
2. `query` — retrieve answers with source citations and confidence labels.
3. `lint` — audit the vault for integrity and trust defects.

## Non-goals

- This is not a replacement for PostgreSQL operational state.
- This is not an ungoverned memory dump.
- This is not permission for Hermes to publish, contact clients, or alter source evidence autonomously.
- This is not a vector-database dependency.

## Trust boundaries

### Layer 1 — Raw sources

Path: `hermes-vault/raw/`

Raw files are append-only source material: transcripts, emails, pleadings, research, decisions, meeting notes, and exported records. Hermes must never rewrite these files.

Every ingested source receives a receipt containing:

- source path
- SHA-256 hash
- byte length
- MIME/type classification
- ingestion timestamp
- tenant/case/client scope
- sensitivity label
- parser version

### Layer 2 — Governed wiki

Path: `hermes-vault/wiki/`

Hermes may create and update Markdown notes here. Every material claim must include at least one source reference using a stable source identifier. Notes must distinguish:

- verified fact
- user assertion
- legal proposition
- inference
- unresolved contradiction
- recommended action

### Layer 3 — Governance schema

Path: `hermes-vault/schema/`

The schema defines allowed note types, required front matter, link rules, source citation rules, retention rules, and lint checks.

## Directory layout

```text
hermes-vault/
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
  schema/
    vault.schema.json
    note-types.md
    link-policy.md
  receipts/
    ingest/
    query/
    lint/
  indexes/
    source-index.jsonl
    entity-index.jsonl
    contradiction-index.jsonl
  quarantine/
  templates/
  README.md
```

## Required front matter

Every wiki note must begin with YAML front matter containing:

```yaml
id: note_<uuid>
title: Human-readable title
note_type: client|matter|project|decision|person|organization|law|procedure|content
status: active|superseded|archived|quarantined
created_at: 2026-07-26T00:00:00Z
updated_at: 2026-07-26T00:00:00Z
source_ids: []
related_notes: []
claims:
  - id: claim_<uuid>
    classification: verified_fact|user_assertion|legal_proposition|inference|unresolved
    source_ids: []
    confidence: high|medium|low
sensitivity: public|internal|confidential|restricted
owner_profile: hermes-librarian
```

## Operation contract: ingest

### Inputs

- one or more files under `raw/inbox/`
- explicit tenant/client/matter scope
- invoking profile identity

### Processing

1. Hash the source before parsing.
2. Reject executable files and unsupported archives.
3. Extract text without modifying the source.
4. Detect entities, dates, decisions, commitments, deadlines, and claims.
5. Locate candidate existing notes.
6. Update or create notes using source-grounded claims only.
7. Record contradictions instead of silently overwriting earlier claims.
8. Move the raw file to `raw/processed/` only after a valid receipt is written.
9. Write an append-only JSON receipt.

### Failure behavior

- Parser failure: move to `raw/rejected/` and issue a refusal receipt.
- Scope ambiguity: quarantine; do not guess the client or matter.
- Restricted data with insufficient profile permissions: deny and log.
- Contradictory source: preserve both claims and mark unresolved.

## Operation contract: query

Every answer must return:

- concise answer
- supporting note IDs
- raw source IDs
- confidence assessment
- unresolved contradictions
- freshness timestamp
- recommended next action, when requested

Hermes must never present an inference as a verified fact. For legal research, jurisdiction, effective date, and source authority must be included when available.

## Operation contract: lint

Lint is mandatory and must run on a schedule.

Checks:

- claims with no source IDs
- broken note links
- orphan notes
- duplicate entities
- stale active notes
- superseded claims still presented as current
- contradictory active claims
- over-connected notes caused by weak keyword matching
- invalid front matter
- missing sensitivity labels
- restricted notes readable by unauthorized profiles
- source hash mismatch
- processed source missing an ingest receipt

Lint may auto-fix only mechanical defects such as deterministic formatting or index regeneration. It must not silently resolve substantive contradictions.

## Profiles and permissions

### `hermes-librarian`

- read raw
- write wiki
- write receipts and indexes
- run ingest/query/lint
- no external publication authority

### `hermes-research`

- read permitted raw and wiki
- query only
- no note mutation

### `hermes-content`

- read public/internal content and approved voice notes
- query only
- no client-confidential access
- no autonomous publication without a separate approval gate

### `hermes-client-ops`

- read scoped client/matter notes
- generate briefs and follow-up drafts
- no cross-client retrieval
- no ingest or lint authority

## Scheduling recommendation

Windows Task Scheduler or the existing Hermes scheduler should invoke repository scripts:

- 08:00 daily — Git status, receipt validation, private remote backup
- 10:00 daily — ingest raw inbox
- 02:00 Sunday — full lint
- hourly — optional lightweight inbox detection only; no autonomous mutation unless the full ingest gate passes

## Security requirements

- Private repository for any vault containing confidential data.
- Secret scanning enabled.
- `.gitignore` must exclude temporary parser output, credentials, and local model caches.
- Raw sources containing SSNs, account numbers, health data, or privileged material must be labeled `restricted`.
- Cross-tenant retrieval is a hard deny.
- Query receipts must record the profile, scope, source IDs, and output hash.

## Acceptance criteria — Increment 1

1. Vault scaffold can be created deterministically.
2. Schema validates a compliant note and rejects an unsupported note type.
3. Raw files are never overwritten by ingest tooling.
4. Every processed source has a SHA-256-based receipt.
5. Query output contains source IDs and confidence.
6. Lint reports unsupported claims, broken links, orphans, stale notes, contradictions, and hash mismatches.
7. Profile policy prevents content and client-ops profiles from mutating the wiki.
8. The subsystem is additive and does not alter existing PostgreSQL authority.

## Increment 2

- Production parser adapters for TXT, Markdown, PDF, DOCX, email, and transcript formats.
- Case/client scope resolver integrated with SintraPrime tenant authority.
- Cryptographically chained receipts.
- Portal API endpoints and Operations Floor telemetry.
- Human review queue for contradictions and restricted-source ingestion.
