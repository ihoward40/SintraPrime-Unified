# GOD-2A Capability Inventory

**Status:** INVENTORIED / SHADOW-ONLY  
**Admitted capabilities:** 0

| Surface | Capability IDs | Default classification | Current state |
|---|---|---|---|
| A2A messaging | `a2a.read_messages`, `a2a.draft_message` | E0 / E1 | Shadow-only |
| Evidence vault | `evidence_vault.read`, `evidence_vault.draft_index` | E0 / E1 | Shadow-only |
| Repository | `repository.read_state`, `repository.draft_change` | E0 / E1 | Shadow-only |
| Redis | `redis.read_status`, `redis.draft_delivery` | E0 / E1 | Shadow-only |
| PostgreSQL governance | `postgres.read_governance`, `postgres.draft_reconciliation` | E0 / E1 | Shadow-only |
| Dispatch Desk | `dispatch.read_queue`, `dispatch.draft_packet` | E0 / E1 | Shadow-only; no dispatch authority |
| Future connectors | `connector.read_metadata`, `connector.draft_payload` | E0 / E1 | Shadow-only; no connector enabled |

The inventory is intentionally operation-specific. A tool name or installed adapter does not grant authority. Every unknown operation is denied because it is absent from the admission registry.

No entry is `ADMITTED`. E2 remains closed pending separate operation-specific approval. E3–E8 remain closed or revoked.
