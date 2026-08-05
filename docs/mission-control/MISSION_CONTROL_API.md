# Mission Control API Reference

**Version:** 1
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
  "items": [ { "command_id": "...", "state": "...", "command_type": "...", ... } ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

---

### 1.3 GET /api/v1/mission-control/intents/{command_id}

**Status:** NEW, tenant-scoped.

Returns a single intent by command id. Cross-tenant access returns 404.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| command_id | string | Command ledger entry id |

**Response 200:** Intent object.
**Response 404:** Not found (including cross-tenant).

---

### 1.4 GET /api/v1/mission-control/run-controls

**Status:** NEW, tenant-scoped.

Lists projected run-control entries for the current tenant.

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
  "items": [ { "run_control_id": "...", "state": "...", "workflow_id": "...", ... } ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

---

### 1.5 GET /api/v1/mission-control/run-controls/{run_control_id}

**Status:** NEW, tenant-scoped.

Returns a single run-control entry by id. Cross-tenant access returns 404.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| run_control_id | string | Run-control entry id |

**Response 200:** Run-control object.
**Response 404:** Not found (including cross-tenant).

---

### 1.6 GET /api/v1/mission-control/intents/{command_id}/causation-chain

**Status:** NEW, tenant-scoped.

Returns the causation chain for a command — the lineage of commands that caused or were caused by the given command id.

**Path parameters:**

| Param | Type | Description |
|-------|------|-------------|
| command_id | string | Command ledger entry id |

**Response 200:**

```json
{
  "command_id": "...",
  "chain": [ { "command_id": "...", "cause": "...", "effect": "..." } ]
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
  "gate": "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE",
  "blocked": true,
  "cancellation_controls_disabled": true
}
```

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