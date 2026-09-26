# PostgreSQL RLS Validation

## Test topology

- PostgreSQL 16.15, localhost.
- Database: isolated C10-R4 test database.
- Owner role used only for bootstrap.
- Restricted non-owner application role used for runtime queries.
- Tenant context set with `set_config('app.tenant_id', tenant, false)`.
- RLS enabled on all seven A2A tables.

## Policies tested

Each table has a tenant policy of the form:

```sql
USING (tenant_id = current_setting('app.tenant_id', true))
```

The runtime role received table DML privileges but was not the table owner, so RLS was active for the validation queries.

## Evidence

1. A row was inserted under `tenant-a`.
2. A separate transaction set the context to `tenant-b`.
3. The same application role queried the audit table.
4. The cross-tenant query returned zero rows.
5. The C10-R4 harness recorded `RLS cross-tenant read blocked`.

The same policy shape was applied to approval state, approval events, outbox state, outbox events, delivery attempts, and DLQ records.

## Limitations

This proves local PostgreSQL RLS behavior with the tested policy shape. It does not replace production verification of role ownership, migration order, connection-pool context reset, security-definer functions, backup/restore, or failover behavior. Production must ensure application roles do not own tenant tables and cannot bypass RLS through elevated roles.
