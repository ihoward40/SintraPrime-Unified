# Deferred Architecture Item: Runtime Schema vs. Portal Schema Reconciliation

**Item ID:** DAI-2026-07-27-01
**Status:** DEFERRED — not part of Phase Two
**Opened:** 2026-07-27
**Owner:** TBD (requires architectural decision by repository owner)

---

## Summary

The repository contains two materially different relational schemas:

1. **Live runtime schema** in the `sintraprime-postgres` container — 8 tables focused on agents, skills, swarms, execution history, knowledge, sessions, messages, and users.
2. **Declared portal schema** in `portal/migrations/portal_schema.sql` — 25 tables for a multi-tenant legal/client portal (firms, cases, clients, billing, documents, trust accounts, etc.).

These schemas do not share tables, foreign keys, or ownership semantics. Phase Two is explicitly scoped to stabilize the live runtime schema only; this item captures the need for a future reconciliation initiative.

---

## Affected Files and Components

| File/Component | Role |
|---|---|
| `portal/migrations/portal_schema.sql` | Declared 25-table portal schema |
| `portal/migrations/add_evidence_snapshots.sql` | Portal: evidence snapshots |
| `portal/migrations/add_audit_records.sql` | Portal: audit records |
| `portal/migrations/add_mission_control_command_ledger.sql` | Portal: command ledger |
| `portal/migrations/add_mission_control_run_control_projection.sql` | Portal: run-control projection |
| `portal/scripts/postgresql_bootstrap.py` | Bootstrap runner for portal SQL |
| `portal/database.py` | SQLAlchemy async engine (`postgresql+asyncpg`) |
| `portal/config.py` | Default `DATABASE_URL` points to `sintra_portal` |
| `portal/models/*.py` | ORM models for portal schema |
| `core/universe/db_migrations.sql` | Alternative/unrelated migration file |
| `apps/ike-bot/main/supabase/migrations/*.sql` | ike-bot Supabase migrations |
| `shared/schemas/unified_schema.sql` | Another schema file with unclear ownership |
| Live `sintraprime-postgres` container | 8-table runtime schema |
| `agents/`, `memory/`, `skill_evolution/`, `workflow_builder/` | Likely consumers of runtime schema |

---

## Deployment Implications

- The portal schema has no known deployed instance matching its full definition.
- The runtime schema is actively deployed and likely used by agent/skill subsystems.
- `DATABASE_URL` defaults to `sintra_portal`, but the container running on port 5433 is named `sintraprime-postgres` and contains the runtime schema.
- CI workflows exercise PostgreSQL but test different subsystems; no single CI job validates the portal schema end-to-end on a fresh database.

---

## Migration Strategy Options

### Option 1 — Replace Runtime Schema with Portal Schema
- Drop/recreate database using `portal_schema.sql`.
- Migrate runtime data into portal tables where concepts overlap (users, messages).
- Update all runtime code to use portal schema.
- **Risks:** High blast radius; requires coordinated rewrite of agent/skill code.

### Option 2 — Coexist Separate Schemas
- Keep runtime schema in `sintraprime_unified` (or rename).
- Deploy portal schema in a separate database (`sintra_portal`).
- Maintain two connection strings and migration tracks.
- **Risks:** Operational complexity; cross-schema joins become cross-database.

### Option 3 — Merge Selectively
- Adopt portal concepts (tenants, roles, RBAC) into runtime schema.
- Evolve runtime tables incrementally toward a unified model.
- **Risks:** Long-running redesign; intermediate states must remain functional.

### Option 4 — Deprecate Portal Schema
- Treat `portal_schema.sql` and related models as historical or separate product.
- Formalize the runtime schema as the single source of truth.
- **Risks:** Requires product decision; may discard intended portal functionality.

---

## Estimated Effort (Rough)

| Strategy | Engineering Effort | Migration Risk | Decision Complexity |
|---|---|---|---|
| Replace | 2–4 weeks | High | High |
| Coexist | 1–2 weeks | Medium | Medium |
| Merge | 4–8 weeks | High | Very High |
| Deprecate | 1 week (documentation + cleanup) | Low | High (product) |

---

## Risks

- **Data loss:** Any reconciliation involving `users` or `messages` must preserve identity and history.
- **Downtime:** Replacing the runtime schema requires a cutover window.
- **Code breakage:** Subsystems using the runtime schema will fail if table shapes change.
- **Test gaps:** No migration regression tests currently exist for either schema.
- **Ownership ambiguity:** It is unclear which subsystem owns the live container and its schema.

---

## Unanswered Architectural Questions

1. Which subsystem (`portal/`, `core/`, `agents/`, etc.) owns the live PostgreSQL container?
2. Is the portal schema a future target, a deprecated design, or a separate product line?
3. Does the runtime need multi-tenancy, or is it single-tenant by design?
4. Should the project adopt Alembic, keep raw SQL, or use both in separate tracks?
5. How should `users` and `messages` be reconciled given their incompatible definitions?
6. What is the production deployment topology: one database or multiple?
7. Are `portal/models/*.py` actively used, or are they aligned only with the declared schema?

---

## Next Steps (Future Architecture Phase)

1. Assign an architecture owner.
2. Decide which reconciliation strategy to pursue.
3. Produce an Architecture Decision Record (ADR).
4. Define data-migration and cutover plans.
5. Add migration regression tests before executing any reconciliation.
6. Schedule the work outside normal feature phases.

---

## References

- `artifacts/phase_2_1_database_baseline_report.md`
- `artifacts/schema_drift_register.md`
- `governance/blackstone/checkpoints/phase-1.5-ci-certification.md`
