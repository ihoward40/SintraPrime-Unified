# Gate 4.6 — JSON Portability and Dialect Type Audit

## Audit Date: 2026-07-16

## Summary

All ORM columns using dialect-specific types have been audited. No deliberately PG-only
type usage remains without a portable fallback mechanism.

## Type Matrix

| File | Model | Column | Base Type | PG Variant | SQLite Fallback | Portability | Status |
|------|-------|--------|-----------|------------|-----------------|-------------|--------|
| models/observatory.py | ObservatoryEvent | payload | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryEvent | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryMission | governance_gates_required | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryMission | governance_gates_passed | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryMission | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryAgent | capabilities | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryAgent | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryApproval | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryArtifact | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | ObservatoryIncident | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | KillSwitchState | metadata | JSON | JSONB | JSON | Variant | PASS |
| models/observatory.py | (all id columns) | id | String(36) | UUID | String(36) | PortableUUID | PASS |
| models/observatory.py | (all FK id columns) | *_id | String(36) | UUID | String(36) | PortableUUID | PASS |
| models/blackstone.py | BlackstoneEvaluation | controlling_authority | JSON | JSONB | JSON | Variant | PASS |
| models/blackstone.py | BlackstoneEvaluation | conflicts | JSON | JSONB | JSON | Variant | PASS |
| models/blackstone.py | BlackstoneEvaluation | risks | JSON | JSONB | JSON | Variant | PASS |
| models/blackstone.py | BlackstoneEvaluation | agents | JSON | JSONB | JSON | Variant | PASS |
| routers/notifications.py | Notification | extra_data | JSON | JSONB | JSON | _JSONB variant | PASS |
| routers/notifications.py | Notification | id | String(36) | UUID | String(36) | _PortableUUID | FIXED |
| routers/notifications.py | Notification | tenant_id | String(36) | UUID | String(36) | _PortableUUID | FIXED |
| routers/notifications.py | Notification | user_id | String(36) | UUID | String(36) | _PortableUUID | FIXED |

## Deliberately PG-Only Features

None. All PG-specific types (UUID, JSONB) have portable fallback mechanisms.

## Remediation Actions

1. **FIXED**: `Notification.id`, `Notification.tenant_id`, `Notification.user_id` were using
   `sqlalchemy.dialects.postgresql.UUID(as_uuid=True)` without a portable variant. Replaced
   with `_PortableUUID` TypeDecorator that maps to `UUID(as_uuid=True)` on PostgreSQL and
   `String(36)` on SQLite.

2. `_JSONB` already uses `SaJSON().with_variant(PgJSONB, "postgresql")` — portable.

3. All `PortableUUID` implementations in `models/observatory.py`, `models/blackstone.py`, and
   `alembic/migration_types.py` are consistent.

## Round-Trip Test Evidence

### SQLite JSON Round-Trip

- nested objects: PASS
- lists: PASS
- booleans: PASS
- nulls: PASS
- numbers: PASS
- unicode: PASS
- empty containers: PASS

### PostgreSQL JSONB Column Types

- `notification.extra_data`: data_type=JSONB, udt_name=jsonb (verified in information_schema)
- All JSON columns use JSONB variant on PostgreSQL
- All UUID columns use native UUID on PostgreSQL, String(36) on SQLite

### Alembic Drift Check

- No unintended type drift detected in Notification model
- Observatory tables show expected UUID → String(36) portable type mapping
- Test marker table (`__gate4_test_marker`) is intentionally excluded from migrations

## Test Evidence Hash

- SQLite round-trip: PASS (all 7 data types verified)
- PG DDL types: JSONB for JSON, UUID for UUID columns
- No PG-only types without portable fallback: CONFIRMED