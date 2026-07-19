-- =============================================================================
-- Migration: Add Mission Control run-control governance projection
-- Phase Two, Increment Two A: additive control-state table and immutable events
-- No workflow execution behavior is modified.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mission_control_run_controls (
    id                         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                  UUID NOT NULL REFERENCES tenants(id),
    workflow_id                VARCHAR(128) NOT NULL,
    command_id                 UUID REFERENCES mission_control_commands(id) ON DELETE SET NULL,
    state                      VARCHAR(40) NOT NULL,
    workflow_status_snapshot   VARCHAR(40) NOT NULL,
    workflow_status_observed_at TIMESTAMPTZ,
    workflow_source            VARCHAR(80),
    workflow_version_snapshot  INTEGER,
    state_version              INTEGER NOT NULL DEFAULT 1,
    projection_schema_version  INTEGER NOT NULL DEFAULT 1,
    pause_reason               TEXT,
    requested_by               UUID REFERENCES users(id),
    requested_at               TIMESTAMPTZ,
    confirmation_ref           VARCHAR(128),
    acknowledged_by            UUID REFERENCES users(id),
    acknowledged_at            TIMESTAMPTZ,
    paused_at                  TIMESTAMPTZ,
    failed_at                  TIMESTAMPTZ,
    timed_out_at               TIMESTAMPTZ,
    superseded_at              TIMESTAMPTZ,
    incident_id                VARCHAR(128),
    recovery_ref               VARCHAR(128),
    terminal_reason_code       VARCHAR(64),
    last_error                 TEXT,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mission_control_run_controls_tenant_workflow UNIQUE (tenant_id, workflow_id),
    CONSTRAINT ck_mission_control_run_controls_state CHECK (
        state IN (
            'RUNNING',
            'PAUSE_REQUESTED',
            'PAUSING',
            'PAUSED',
            'PAUSE_FAILED',
            'PAUSE_TIMED_OUT',
            'SUPERSEDED',
            'COMPLETED',
            'FAILED',
            'CANCELLED',
            'COMPENSATING',
            'COMPENSATED'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_mission_control_run_controls_tenant_state
    ON mission_control_run_controls(tenant_id, state);

CREATE INDEX IF NOT EXISTS ix_mission_control_run_controls_tenant_workflow
    ON mission_control_run_controls(tenant_id, workflow_id);

CREATE INDEX IF NOT EXISTS ix_mission_control_run_controls_command
    ON mission_control_run_controls(command_id);

CREATE INDEX IF NOT EXISTS ix_mission_control_run_controls_state_version
    ON mission_control_run_controls(tenant_id, state_version);

CREATE TABLE IF NOT EXISTS mission_control_run_control_events (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_control_id          UUID NOT NULL REFERENCES mission_control_run_controls(id) ON DELETE CASCADE,
    sequence                INTEGER NOT NULL,
    event_type              VARCHAR(60) NOT NULL,
    previous_state          VARCHAR(40) NOT NULL,
    new_state               VARCHAR(40) NOT NULL,
    previous_version        INTEGER NOT NULL,
    new_version             INTEGER NOT NULL,
    principal_id            UUID REFERENCES users(id),
    command_id              UUID REFERENCES mission_control_commands(id) ON DELETE SET NULL,
    reason                  TEXT,
    payload                 JSONB NOT NULL DEFAULT '{}',
    workflow_status_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previous_event_hash     VARCHAR(64),
    event_hash              VARCHAR(64) NOT NULL,
    event_schema_version    INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mission_control_run_control_event_seq UNIQUE (run_control_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_mission_control_run_control_events_control
    ON mission_control_run_control_events(run_control_id);

CREATE OR REPLACE FUNCTION prevent_mission_control_run_control_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'mission_control_run_control_events rows are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mission_control_run_control_event_immutable
    ON mission_control_run_control_events;
CREATE TRIGGER trg_mission_control_run_control_event_immutable
    BEFORE UPDATE OR DELETE ON mission_control_run_control_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_mission_control_run_control_event_mutation();

COMMENT ON TABLE mission_control_run_controls IS
    'Governance-only Mission Control run projection. Execution runtime remains authoritative.';

COMMENT ON TABLE mission_control_run_control_events IS
    'Append-only Mission Control run-control transition evidence.';
