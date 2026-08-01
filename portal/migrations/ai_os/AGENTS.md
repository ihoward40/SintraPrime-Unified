# portal/migrations/ai_os — AI-OS versioned migrations

## Purpose

Owns the AI-OS versioned migration root used by `portal/scripts/migration_runner.py`.

## Ownership

- AI-OS migration directories and SQL scripts under `portal/migrations/ai_os/`
- Schema changes for the AI-OS registry, receipts, approvals, memory, provider policy, and related foundation objects when authorized
- Migration naming, ordering, and reversible DDL for the AI-OS subtree

## Local Contracts

- Each migration lives in `NNNN_slug/` with mandatory `up.sql` and `down.sql`
- Optional `<direction>.<dialect>.sql` overrides may exist only when the neutral script cannot express a portable equivalent
- Keep migrations reversible and ledger-safe; checksum drift must fail closed
- Use simple transactional DDL only unless a later authorization explicitly expands parser support
- Do not add runtime application logic, API routes, or seeding behavior here
- Preserve the scope boundary: this root governs only AI-OS versioned migrations, not the legacy flat `portal/migrations/*.sql` corpus

## Work Guidance

- Prefer small, independently reviewable migration increments
- Keep SQL comments explicit about prerequisites, down behavior, and any dialect-specific divergence
- Add or update focused migration tests when the schema or parity contract changes

## Verification

- Run the targeted migration framework tests and, when available, PostgreSQL parity checks against a disposable database
- Confirm upgrade, downgrade, idempotence, and residue-free rollback behavior for each change

## Child DOX Index

*(No child AGENTS.md files yet.)
