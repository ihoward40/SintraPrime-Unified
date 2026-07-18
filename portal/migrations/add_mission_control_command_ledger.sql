-- =============================================================================
-- Migration: Add Mission Control governed command ledger
-- Phase Two, Increment One: command persistence, events, receipts, idempotency
-- No run, scheduler, agent, mission, or assignment mutation state is introduced.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mission_control_commands (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id),
    requested_by      UUID NOT NULL REFERENCES users(id),
    command_type      VARCHAR(40) NOT NULL,
    target_type       VARCHAR(40) NOT NULL,
    target_id         VARCHAR(128) NOT NULL,
    idempotency_key   VARCHAR(128) NOT NULL,
    request_hash      VARCHAR(64) NOT NULL,
    state             VARCHAR(40) NOT NULL,
    reason_code       VARCHAR(80),
    reason            TEXT,
    payload           JSONB NOT NULL DEFAULT '{}',
    metadata          JSONB NOT NULL DEFAULT '{}',
    audit_log_id      UUID REFERENCES audit_logs(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    CONSTRAINT ck_mission_control_commands_command_type CHECK (
        command_type IN (
            'START_GOVERNED_RUN',
            'PAUSE_RUN',
            'RESUME_RUN',
            'CANCEL_RUN',
            'ASSIGN_AGENT',
            'REASSIGN_AGENT'
        )
    ),
    CONSTRAINT ck_mission_control_commands_state CHECK (
        state IN (
            'RECEIVED',
            'VALIDATING',
            'REFUSED',
            'DUPLICATE_REPLAYED',
            'DUPLICATE_CONFLICT'
        )
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_mission_control_command_idempotency
    ON mission_control_commands(tenant_id, requested_by, idempotency_key);

CREATE INDEX IF NOT EXISTS ix_mission_control_commands_tenant_state_created
    ON mission_control_commands(tenant_id, state, created_at);

CREATE INDEX IF NOT EXISTS ix_mission_control_commands_target
    ON mission_control_commands(tenant_id, target_type, target_id);

CREATE TABLE IF NOT EXISTS mission_control_command_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id      UUID NOT NULL REFERENCES mission_control_commands(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    event_type      VARCHAR(60) NOT NULL,
    state           VARCHAR(40) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    previous_hash   VARCHAR(64),
    event_hash      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mission_control_command_event_seq UNIQUE (command_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_mission_control_command_events_command
    ON mission_control_command_events(command_id);

CREATE TABLE IF NOT EXISTS mission_control_command_receipts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id      UUID NOT NULL REFERENCES mission_control_commands(id) ON DELETE CASCADE,
    receipt_type    VARCHAR(40) NOT NULL,
    receipt_hash    VARCHAR(64) NOT NULL,
    audit_log_id    UUID REFERENCES audit_logs(id),
    evidence_refs   JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mission_control_command_receipt UNIQUE (command_id, receipt_type)
);

CREATE INDEX IF NOT EXISTS ix_mission_control_command_receipts_command
    ON mission_control_command_receipts(command_id);

CREATE OR REPLACE FUNCTION prevent_mission_control_command_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'mission_control_command_events rows are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mission_control_command_event_immutable
    ON mission_control_command_events;
CREATE TRIGGER trg_mission_control_command_event_immutable
    BEFORE UPDATE OR DELETE ON mission_control_command_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_mission_control_command_event_mutation();

CREATE OR REPLACE FUNCTION prevent_mission_control_command_receipt_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'mission_control_command_receipts rows are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mission_control_command_receipt_immutable
    ON mission_control_command_receipts;
CREATE TRIGGER trg_mission_control_command_receipt_immutable
    BEFORE UPDATE OR DELETE ON mission_control_command_receipts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_mission_control_command_receipt_mutation();

COMMENT ON TABLE mission_control_commands IS
    'Mission Control governed command ledger projection. Increment One records and refuses only; no operational mutation path exists.';

COMMENT ON TABLE mission_control_command_events IS
    'Append-only Mission Control command event hash chain.';

COMMENT ON TABLE mission_control_command_receipts IS
    'Immutable receipts for governed Mission Control command outcomes.';

-- DOWN migration notes:
--   DROP TRIGGER IF EXISTS trg_mission_control_command_receipt_immutable ON mission_control_command_receipts;
--   DROP FUNCTION IF EXISTS prevent_mission_control_command_receipt_mutation();
--   DROP TRIGGER IF EXISTS trg_mission_control_command_event_immutable ON mission_control_command_events;
--   DROP FUNCTION IF EXISTS prevent_mission_control_command_event_mutation();
--   DROP TABLE IF EXISTS mission_control_command_receipts;
--   DROP TABLE IF EXISTS mission_control_command_events;
--   DROP TABLE IF EXISTS mission_control_commands;
