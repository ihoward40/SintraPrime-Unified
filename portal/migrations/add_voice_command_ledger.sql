-- =============================================================================
-- Migration: Add SP-VOICE-001 governed voice command ledger (Increment Two)
-- Tenant-scoped voice command projection, append-only hash-chained events,
-- and immutable terminal receipts. Execution recorded here is ALWAYS a mock/
-- sandboxed provider outcome — no real telephony, calendar, messaging,
-- filing, or payment side effect is ever represented by this ledger.
-- =============================================================================

CREATE TABLE IF NOT EXISTS voice_commands (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id),
    principal_id           UUID NOT NULL REFERENCES users(id),
    command_id             VARCHAR(80) NOT NULL,
    voice_session_id       VARCHAR(80) NOT NULL,
    correlation_id         VARCHAR(80) NOT NULL,
    source                 VARCHAR(40) NOT NULL,
    raw_transcript_hash    VARCHAR(80) NOT NULL,
    raw_transcript         TEXT,
    normalized_intent      TEXT NOT NULL,
    requested_capability   VARCHAR(40),
    resolved_capability    VARCHAR(40) NOT NULL,
    target_resource        VARCHAR(255),
    risk_class             VARCHAR(40) NOT NULL,
    policy_decision        VARCHAR(40) NOT NULL,
    confirmation_state     VARCHAR(40) NOT NULL,
    session_state          VARCHAR(40) NOT NULL,
    result                 VARCHAR(40) NOT NULL,
    reason                 TEXT,
    provider_capability     VARCHAR(40),
    provider_resource_id    VARCHAR(120),
    provider_mock           BOOLEAN,
    artifacts               JSONB NOT NULL DEFAULT '[]',
    audit_log_id            UUID REFERENCES audit_logs(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    CONSTRAINT ck_voice_commands_risk_class CHECK (
        risk_class IN ('read', 'draft', 'write', 'sensitive_write', 'prohibited')
    ),
    CONSTRAINT ck_voice_commands_session_state CHECK (
        session_state IN (
            'idle', 'listening', 'transcribing', 'classifying', 'planning',
            'awaiting_confirmation', 'executing', 'completed', 'refused',
            'cancelled', 'failed'
        )
    ),
    -- Mock-first guardrail: provider_mock must never be recorded as false.
    CONSTRAINT ck_voice_commands_provider_mock_only CHECK (
        provider_mock IS NULL OR provider_mock = TRUE
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_voice_command_tenant_command_id
    ON voice_commands(tenant_id, command_id);

CREATE INDEX IF NOT EXISTS ix_voice_commands_tenant_state_created
    ON voice_commands(tenant_id, session_state, created_at);

CREATE INDEX IF NOT EXISTS ix_voice_commands_tenant_session
    ON voice_commands(tenant_id, voice_session_id);

CREATE INDEX IF NOT EXISTS ix_voice_commands_tenant_principal
    ON voice_commands(tenant_id, principal_id);

CREATE TABLE IF NOT EXISTS voice_command_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id      UUID NOT NULL REFERENCES voice_commands(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    event_type      VARCHAR(60) NOT NULL,
    state           VARCHAR(40) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    previous_hash   VARCHAR(64),
    event_hash      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_voice_command_event_seq UNIQUE (command_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_voice_command_events_command
    ON voice_command_events(command_id);

CREATE TABLE IF NOT EXISTS voice_command_receipts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id      UUID NOT NULL REFERENCES voice_commands(id) ON DELETE CASCADE,
    receipt_type    VARCHAR(40) NOT NULL,
    receipt_hash    VARCHAR(64) NOT NULL,
    result          VARCHAR(40) NOT NULL,
    audit_log_id    UUID REFERENCES audit_logs(id),
    evidence_refs   JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_voice_command_receipt UNIQUE (command_id, receipt_type)
);

CREATE INDEX IF NOT EXISTS ix_voice_command_receipts_command
    ON voice_command_receipts(command_id);

CREATE OR REPLACE FUNCTION prevent_voice_command_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'voice_command_events rows are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_voice_command_event_immutable ON voice_command_events;
CREATE TRIGGER trg_voice_command_event_immutable
    BEFORE UPDATE OR DELETE ON voice_command_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_voice_command_event_mutation();

CREATE OR REPLACE FUNCTION prevent_voice_command_receipt_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'voice_command_receipts rows are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_voice_command_receipt_immutable ON voice_command_receipts;
CREATE TRIGGER trg_voice_command_receipt_immutable
    BEFORE UPDATE OR DELETE ON voice_command_receipts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_voice_command_receipt_mutation();

COMMENT ON TABLE voice_commands IS
    'SP-VOICE-001 Increment Two governed voice command projection. Execution recorded here is always a mock/sandboxed provider outcome.';

COMMENT ON TABLE voice_command_events IS
    'Append-only SP-VOICE-001 voice command event hash chain.';

COMMENT ON TABLE voice_command_receipts IS
    'Immutable receipts for terminal SP-VOICE-001 voice command outcomes.';

-- DOWN migration notes:
--   DROP TRIGGER IF EXISTS trg_voice_command_receipt_immutable ON voice_command_receipts;
--   DROP FUNCTION IF EXISTS prevent_voice_command_receipt_mutation();
--   DROP TRIGGER IF EXISTS trg_voice_command_event_immutable ON voice_command_events;
--   DROP FUNCTION IF EXISTS prevent_voice_command_event_mutation();
--   DROP TABLE IF EXISTS voice_command_receipts;
--   DROP TABLE IF EXISTS voice_command_events;
--   DROP TABLE IF EXISTS voice_commands;
