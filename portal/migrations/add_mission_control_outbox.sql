-- =============================================================================
-- Migration: Add Mission Control transactional outbox
-- R3-D: Resolve ORM-only table — mission_control_outbox
-- R3-G: Tenant security — outbox carries tenant-scoped dispatch records
-- Pattern: transactional outbox for reliable intent dispatch to executors.
-- Ensures command state changes and dispatch records commit atomically.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mission_control_outbox (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    command_id      UUID        REFERENCES mission_control_commands(id) ON DELETE CASCADE,

    -- Dispatch metadata
    executor_type   VARCHAR(60) NOT NULL,   -- e.g. 'nova', 'workflow'
    message_type    VARCHAR(60) NOT NULL,   -- e.g. 'EXECUTE_INTENT', 'CANCEL_INTENT'
    payload         JSONB       NOT NULL DEFAULT '{}',

    -- Reliability and retry state
    state           VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    attempts        INTEGER     NOT NULL DEFAULT 0,
    max_attempts    INTEGER     NOT NULL DEFAULT 5,
    last_attempt_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ,
    last_error      TEXT,

    -- Audit and correlation
    correlation_id  VARCHAR(128) NOT NULL,
    causation_id    VARCHAR(128),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_mission_control_outbox_state CHECK (
        state IN ('PENDING', 'DISPATCHED', 'FAILED', 'DEAD_LETTER')
    )
);

CREATE INDEX IF NOT EXISTS ix_mission_control_outbox_state_next
    ON mission_control_outbox(state, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_mission_control_outbox_tenant
    ON mission_control_outbox(tenant_id);
CREATE INDEX IF NOT EXISTS ix_mission_control_outbox_command
    ON mission_control_outbox(command_id);

-- Row-level security: dispatch records are tenant-owned
ALTER TABLE mission_control_outbox ENABLE ROW LEVEL SECURITY;

CREATE POLICY mission_control_outbox_tenant_isolation ON mission_control_outbox
    AS PERMISSIVE FOR ALL
    USING (
        tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

COMMENT ON TABLE mission_control_outbox IS
    'Transactional outbox for reliable dispatch of Mission Control intents to executors. '
    'Ensures command state changes and dispatch records commit atomically. '
    'PENDING → DISPATCHED (success) or FAILED → DEAD_LETTER (exhausted retries).';

-- =============================================================================
-- DOWN migration notes:
--   DROP TABLE IF EXISTS mission_control_outbox;
-- =============================================================================
