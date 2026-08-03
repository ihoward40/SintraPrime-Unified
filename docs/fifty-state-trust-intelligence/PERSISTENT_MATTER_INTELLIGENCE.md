# Persistent Matter Intelligence

Phase 2C-2 adds tenant- and matter-scoped persistence for creditor and UCC case records. The service layer stores parties, accounts, filings, communications, disputes, attachment metadata, assessments, immutable assessment versions, and a matter-local hash-chained audit history.

## Scope

- Party roles include client, creditor, collector, furnisher, servicer, assignee, secured party, debtor, and other.
- Sensitive identifiers are recursively redacted before persistence and audit logging.
- Every query is constrained by tenant, matter, and soft-delete state.
- Assessments are append-versioned. A new version resets review status.
- Legal assessment approval requires an attorney role. Tax/accounting approval requires an accountant role. Administrators cannot bypass these gates.

## API surface

The authenticated `/api/v1/matters/{matter_id}/intelligence` routes provide create/list operations for parties, accounts, filings, communications, disputes, attachment metadata, assessments, versions, reviews, and audit events.

The migration is `portal/migrations/add_matter_intelligence.sql`. It includes a documented down migration. Deadlines, evidence-graph edges, export generation, and frontend matter workspace are explicitly deferred.

## Limitations

Attachments register existing document references and metadata; binary upload and evidence graph semantics are out of scope. Audit records are append-only by service contract and use both a matter-local hash chain and the existing global audit service.
