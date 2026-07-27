# Schema Drift Register

**Register ID:** SDR-2026-07-27-01
**Generated:** 2026-07-27T03:21:00+00:00
**Status:** Descriptive — no reconciliation action authorized
**Scope:** `portal/migrations/portal_schema.sql` (declared) vs. live `sintraprime-postgres` runtime schema

---

## Summary

The repository declares a 25-table multi-tenant client-portal schema in `portal/migrations/portal_schema.sql`. The live PostgreSQL container (`sintraprime-postgres`, PostgreSQL 15.17) currently hosts an unrelated 8-table agent/skill runtime schema. This register documents the divergence descriptively; reconciliation is explicitly deferred to a future architecture phase.

---

## Objects Existing Only in Declared Schema (`portal_schema.sql`)

| Object Type | Name |
|---|---|
| Table | tenants |
| Table | roles |
| Table | clients |
| Table | matters |
| Table | cases |
| Table | case_events |
| Table | case_deadlines |
| Table | case_notes |
| Table | case_tasks |
| Table | document_folders |
| Table | documents |
| Table | document_versions |
| Table | document_shares |
| Table | message_threads |
| Table | message_attachments |
| Table | time_entries |
| Table | expenses |
| Table | invoices |
| Table | invoice_line_items |
| Table | payments |
| Table | trust_accounts |
| Table | notifications |
| Table | audit_logs |

Total: 22 tables present only in declared schema.

---

## Objects Existing Only in Live Runtime Schema

| Object Type | Name |
|---|---|
| Table | agents |
| Table | execution_history |
| Table | knowledge_entries |
| Table | sessions |
| Table | skills |
| Table | swarms |

Note: both schemas define a `messages` table and a `users` table, but with incompatible definitions.

Total: 6 tables present only in live schema.

---

## Matching Objects with Incompatible Definitions

### `users`

| Aspect | Declared Schema | Live Schema |
|---|---|---|
| Primary key type | UUID (`uuid_generate_v4()`) | UUID (`uuid_generate_v4()`) |
| Tenant scoping | `tenant_id` FK to `tenants` | None |
| Role model | `role_id` FK to `roles` | None |
| Email uniqueness | `uq_user_email_tenant` (tenant + email) | `users_email_key` (email only) |
| Columns | 30+ (profile, auth state, invite, security, preferences) | 7 (id, email, username, hashed_password, is_active, created_at, updated_at) |
| Soft delete | `deleted_at` | None |

### `messages`

| Aspect | Declared Schema | Live Schema |
|---|---|---|
| Context | `message_threads`, tenant-scoped conversations | Standalone message queue |
| Columns | thread_id, sender_id, recipient_id, body, status, etc. | type, priority, sender_id, recipient_id, content (jsonb), processed |
| Threading | Yes | No |
| Tenant scoping | Yes (`tenant_id`) | No |
| Content storage | `body TEXT` | `content JSONB` |

---

## Areas Requiring Future Reconciliation

| Area | Description | Open Questions |
|---|---|---|
| Database ownership | Which subsystem owns the live container? | Is `sintraprime-postgres` for `core/`, `agents/`, or `portal/`? |
| Tenant model | Declared schema is multi-tenant; live schema is not. | Does the runtime need multi-tenancy? |
| Identity model | `users` definitions differ fundamentally. | Which user model is authoritative? |
| Message semantics | Declared: threaded tenant conversations; Live: event queue. | Are these the same concept or separate services? |
| Migration path | Raw SQL vs. potential Alembic adoption. | Should both schemas share tooling or remain separate? |
| Deployment target | Portal schema has no known deployed instance. | Is it a future target, a stale artifact, or a separate product? |
| Foreign-key compatibility | No overlap in FK graphs. | Can the two schemas coexist in one database? |

---

## Reconciliation Strategy Options (Deferred)

| Strategy | Description | Risk |
|---|---|---|
| Replace runtime schema | Deploy portal schema and migrate runtime data into it. | High — breaks existing runtime code until reconciled. |
| Coexist separate schemas | Keep runtime schema in one DB/namespace and portal schema in another. | Medium — requires separate connection management and migration tracks. |
| Merge selectively | Adopt portal patterns (tenants, roles) into the runtime schema incrementally. | High — architectural redesign beyond current phase. |
| Deprecate portal schema | Treat `portal_schema.sql` as historical documentation or separate product. | Low/Medium — requires formal deprecation decision. |

---

## Status

**Deferred.** No reconciliation action is authorized under Phase Two. This register is updated descriptively only.

**Reference architecture item:** `docs/architecture/deferred/runtime-portal-schema-reconciliation.md`
