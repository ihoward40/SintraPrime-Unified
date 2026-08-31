# Mission Control API Reference

**Version:** 2
**Base path:** /api/v1/mission-control
**Auth:** All endpoints require authentication and the `MISSION_COMMAND_READ` permission.

## 1. Endpoints

### 1.1 GET /api/v1/mission-control/summary

**Status:** Existing, unchanged.

Returns a high-level summary of the Mission Control surface.

**Response 200:**

```json
{
  "intents": { "total": 0, "by_state": {} },
  "run_controls": { "total": 0, "by_state": {} },
  "sigma_gate": { "blocked": true }
}
```

---

### 1.2 GET /api/v1/mission-control/intents

**Status:** NEW, tenant-scoped.

Lists projected command ledger entries (intents) for the current tenant.
Returns lightweight `CommandSummary` objects — not full projections.
Payloads, events, and receipts are excluded; only `event_count` and
`receipt_count` are surfaced.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| state | string | Filter by intent state |
| command_type | string | Filter by command type |
| limit | integer | Max results (default 50) |
| offset | integer | Pagination offset (default 0) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "requested_by": "...",
      "command_type": "...",
      "target_type": "...",
      "target_id": "...",
      "idempotency_key": "...",
      "request_hash": "...",
      "state": "...",
      "reason_code": null,
      "reason": null,
      "audit_log_id": null,
      "created_at": "...",
      "completed_at": null,
      "event_count": 3,
      "receipt_count": 1
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "freshness": {
    "generated_at": "...",
    "source_updated_at": "...",
    "freshness_seconds": 1.2,
    "state": "LIVE"
  }
}
```

**Freshness semantics:** The `freshness` field measures **record age** — the gap
between `generated_at` (when the projection was assembled) and the latest
timestamp from the underlying source records. It does NOT measure projection
pipeline lag or source synchronization health. A command that completed
yesterday will always be labeled `STALE` even if the projection system is
perfectly current. See section 5 for details.

---

### 1.3 GET /api/v1/mission-control/intents/{command_id}

**Status:** NEW, tenant-scoped.

Returns a single intent by command id. Cross-tenant access returns 404.
Includes full event log and receipts with redacted payloads.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| command_id | string | Command ledger entry id |

**Response 200:** `CommandProjection` with events, receipts, and freshness.
**Response 404:** Not found (including cross-tenant).

---

### 1.4 GET /api/v1/mission-control/run-controls

**Status:** NEW, tenant-scoped.

Lists projected run-control entries for the current tenant.
Returns lightweight `RunControlSummary` objects — not full projections.
Events and `last_error` are excluded; only `event_count` is surfaced.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| state | string | Filter by run-control state |
| workflow_id | string | Filter by workflow id |
| limit | integer | Max results (default 50) |
| offset | integer | Pagination offset (default 0) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "...",
      "tenant_id": "...",
      "workflow_id": "...",
      "command_id": null,
      "state": "...",
      "workflow_status_snapshot": "...",
      "state_version": 1,
      "projection_schema_version": 1,
      "event_count": 2,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "freshness": { "state": "LIVE", "freshness_seconds": 0.5, ... }
}
```

---

### 1.5 GET /api/v1/mission-control/run-controls/{run_control_id}

**Status:** NEW, tenant-scoped.

Returns a single run-control entry by id. Cross-tenant access returns 404.
Sensitive fields (`last_error`, `confirmation_ref`, `recovery_ref`) are redacted.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| run_control_id | string | Run-control entry id |

**Response 200:** `RunControlProjection` with events and freshness.
**Response 404:** Not found (including cross-tenant).

---

### 1.6 GET /api/v1/mission-control/intents/{command_id}/causation-chain

**Status:** NEW, tenant-scoped.

Returns the causation chain for a command — the lineage of events, receipts,
and run-control transitions linked to the given command id.

**Safety metadata:**

| Field | Type | Description |
|-------|------|-------------|
| `truncated` | boolean | True if chain exceeded MAX_CAUSATION_LINKS (500) |
| `total_links` | integer | Total links before truncation |
| `warnings` | string[] | Diagnostic warnings: duplicate hashes, missing parents, cycles |
| `freshness` | object | Record-age freshness metadata |

**Cycle detection:** The chain is traversed following `previous_hash` pointers.
If a cycle is detected (self-cycle, two-node, or longer), a warning is emitted
containing the involved node hashes and source IDs.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| command_id | string | Command ledger entry id |

**Response 200:**

```json
{
  "command_id": "...",
  "tenant_id": "...",
  "command_type": "...",
  "command_state": "...",
  "links": [ { "source_type": "...", "source_id": "...", "hash": "...", ... } ],
  "truncated": false,
  "total_links": 3,
  "warnings": [],
  "freshness": { "state": "LIVE", ... }
}
```

**Response 404:** Not found (including cross-tenant).

---

### 1.7 GET /api/v1/mission-control/sigma-gate

**Status:** NEW, read-only gate status.

Returns the current status of the Sigma lease-expiry continuation gate.

**Response 200:**

```json
{
  "execution_scoped": "DISABLED",
  "tenant_scoped": "DISABLED",
  "platform_break_glass": "DISABLED",
  "gate": {
    "gate_id": "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE",
    "state": "BLOCKED",
    "description": "...",
    "criteria": ["..."],
    "cancellation_controls": "DISABLED",
    "blocking_phase_3b": true
  },
  "reason": "..."
}
```

If the Sigma-gate endpoint itself is unavailable, the UI displays
`STATUS UNKNOWN — CONTROLS REMAIN BLOCKED`. The gate banner is never hidden.

---

### 1.8 POST /api/v1/mission-control/commands

**Status:** PRE-EXISTING, refusal-only.

This endpoint predates the Foundation phase. It cannot execute commands. It returns `COMMAND_EXECUTION_NOT_ENABLED` for all requests. It remains **unchanged** by this phase.

**Response:** `COMMAND_EXECUTION_NOT_ENABLED` (refusal).

## 2. Permissions

All new GET endpoints require the `MISSION_COMMAND_READ` permission. Requests without the permission are rejected.

## 3. Mutation Posture

**No new POST, PUT, PATCH, or DELETE route was added** by this phase. The only POST endpoint is the pre-existing refusal-only `/commands` endpoint, which remains unchanged and cannot execute commands.

- No cancellation mutation added.
- No approval mutation added.
- No retry mutation added.
- No replay mutation added.
- No lease mutation added.
- No dispatch mutation added.

## 4. Tenant Scoping

All list and detail endpoints filter on `current_user.tenant_id`. A request for a resource belonging to another tenant returns 404 (not found), never 403, to avoid leaking existence.

## 5. Freshness Semantics

The `freshness` field on projection responses measures **record age** — the
gap between `generated_at` (when the projection was assembled) and
`source_updated_at` (the latest timestamp from the underlying source records).

This is NOT a measure of:

- Projection pipeline lag (how far behind the projection is relative to
  real-time events)
- Source synchronization health (whether the source system is up-to-date)
- Data freshness in the CDC/streaming sense

A command that completed yesterday will always be labeled `STALE` even if the
projection system is perfectly current, because the underlying record's
timestamp is old. This is by design: the field tells operators whether the
displayed data reflects recent source activity.

To distinguish projection lag from record age, a separate source
synchronization watermark would be needed. That is out of scope for the
Foundation phase.

| State | Condition | Meaning |
|-------|-----------|---------|
| `LIVE` | gap <= 5 seconds | Source records are very recent |
| `DELAYED` | gap <= 60 seconds | Source records are slightly old |
| `STALE` | gap > 60 seconds | Source records are old (record age, not pipeline lag) |
| `UNKNOWN` | `source_updated_at` is null | No source timestamp available |

## 6. Operational Identifier Exposure

List summary responses expose the following operational identifiers. These are
not secrets, but they are operational metadata. The exposure decision for each
is documented here:

| Identifier | Exposed in list? | Rationale |
|------------|-----------------|-----------|
| `idempotency_key` | Yes | Required for deduplication verification by operators |
| `request_hash` | Yes | Integrity verification; not a secret (hash of request) |
| `requested_by` | Yes | Principal identity; needed for audit trail in list view |
| `audit_log_id` | Yes | Links to audit trail; null when no audit entry exists |
| `target_id` | Yes | Identifies the target resource; not sensitive |
| `incident_id` | Yes (run-control) | Links to incident tracking; null when no incident |

These identifiers are exposed only to authenticated users with the
`MISSION_COMMAND_READ` permission. Raw payload bodies, evidence references,
error details, and sensitive run-control fields (`last_error`,
`confirmation_ref`, `recovery_ref`) are redacted and available only in
detail views.