# memory — OmniBrain Memory Boundary

## Purpose

Owns SintraPrime persistent memory, scoped context packaging, provenance relationships, and read-only human projections.

## Ownership

- Existing semantic, episodic, working-memory, profile, and memory API modules
- Scoped context packages used by governed agent orchestration
- Provenance/knowledge graph storage for memory relationships
- One-way Obsidian-compatible Markdown projection

## Local Contracts

- Memory retrieval must be scope-filtered before content is exposed to an agent.
- Legacy unscoped memories may only be included when bound to the requesting `user_id`; anonymous unscoped memories are not globally visible.
- Provenance is additive: derived context must retain the source memory ID and available source metadata.
- Obsidian is a projection only. Markdown files generated from memory must never become trusted canonical memory through an automatic reverse sync.
- Credentials, OAuth tokens, secret values, and raw authentication material must not be projected into Markdown.
- `memory/` supplies context; it does not grant action authority.

## Work Guidance

- Extend existing memory primitives rather than creating a parallel store.
- Keep APIs backward compatible where practical.
- Prefer deterministic, inspectable Python/SQLite/Markdown representations.

## Verification

- `pytest memory/tests`
- Governed integration coverage also lives under `parl/tests/`.

## Child DOX Index

*(No child DOX boundaries yet.)*
