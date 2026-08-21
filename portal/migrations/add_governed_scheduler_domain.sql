-- =============================================================================
-- Migration: Canonical governed scheduler authority (Gate 3)
-- PostgreSQL is the system of record. This domain schedules bounded SintraPrime
-- missions only; it does not authorize external adapters or consequential side effects.
-- =============================================================================

CREATE TABLE IF NOT EXISTS governed_schedules (
    id                    UUID PRIMARY KEY,
    tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by            UUID NOT NULL REFERENCES users(id),
    service_identity_id   VARCHAR(36) REFERENCES governed_service_identities(id),
    objective             TEXT NOT NULL,
    constraints           JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_mode        VARCHAR(40) NOT NULL DEFAULT 'THINK_WORK_CHECK',
    budget_limits         JSONB,
    schedule_kind         VARCHAR(20) NOT NULL DEFAULT 'ONCE',
    run_at                TIMESTAMPTZ NOT NULL,
    status                VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    idempotency_key       VARCHAR(128) NOT NULL,
    request_hash          VARCHAR(64) NOT NULL,
    dispatched_run_id     UUID REFERENCES orchestration_runs(id),
    claimed_at            TIMESTAMPTZ,
    claimed_by            VARCHAR(128),
    dispatched_at         TIMESTAMPTZ,
    cancelled_at          TIMESTAMPTZ,
    cancellation_reason   TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_governed_schedule_kind
        CHECK (schedule_kind IN ('ONCE')),
    CONSTRAINT ck_governed_schedule_status
        CHECK (status IN ('SCHEDULED', 'CLAIMED', 'DISPATCHED', 'CANCELLED', 'FAILED')),
    CONSTRAINT uq_governed_schedule_idempotency
        UNIQUE (tenant_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_governed_schedules_due
    ON governed_schedules(tenant_id, status, run_at);

CREATE INDEX IF NOT EXISTS ix_governed_schedules_dispatched_run
    ON governed_schedules(dispatched_run_id);

CREATE TABLE IF NOT EXISTS governed_schedule_events (
    id                    UUID PRIMARY KEY,
    schedule_id           UUID NOT NULL REFERENCES governed_schedules(id) ON DELETE CASCADE,
    sequence              INTEGER NOT NULL,
    event_type            VARCHAR(60) NOT NULL,
    status                VARCHAR(20) NOT NULL,
    payload               JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash         VARCHAR(64),
    event_hash            VARCHAR(64) NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_governed_schedule_event_sequence UNIQUE (schedule_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_governed_schedule_events_schedule_sequence
    ON governed_schedule_events(schedule_id, sequence);

COMMENT ON TABLE governed_schedules IS
    'Canonical PostgreSQL scheduler authority for bounded governed SintraPrime missions.';

COMMENT ON TABLE governed_schedule_events IS
    'Hash-chained scheduler lifecycle events supporting replay and restart certification.';
