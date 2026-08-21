-- =============================================================================
-- Gate 4C: provider-owned non-production HTTP authority extensions
-- Extends the single Gate 4B external-action envelope. No live production
-- connector or credential secret material is authorized or stored here.
-- =============================================================================

ALTER TABLE external_action_intents
    DROP CONSTRAINT IF EXISTS ck_external_action_intent_environment;

ALTER TABLE external_action_intents
    ADD CONSTRAINT ck_external_action_intent_environment
        CHECK (environment IN ('sandbox', 'provider_test'));

CREATE TABLE IF NOT EXISTS external_provider_credential_leases (
    id                         VARCHAR(36) PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id               UUID NOT NULL REFERENCES users(id),
    service_identity_id        VARCHAR(36) NOT NULL REFERENCES governed_service_identities(id),
    adapter_id                 VARCHAR(120) NOT NULL,
    environment                VARCHAR(32) NOT NULL,
    destination               TEXT NOT NULL,
    credential_ref             TEXT NOT NULL,
    credential_fingerprint     VARCHAR(64) NOT NULL,
    status                     VARCHAR(24) NOT NULL,
    issued_at                  TIMESTAMPTZ NOT NULL,
    expires_at                 TIMESTAMPTZ NOT NULL,
    revoked_at                 TIMESTAMPTZ,
    revocation_reason          TEXT,
    rate_limit_per_minute      INTEGER NOT NULL DEFAULT 5,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_external_provider_lease_environment
        CHECK (environment IN ('provider_test')),
    CONSTRAINT ck_external_provider_lease_status
        CHECK (status IN ('ACTIVE', 'REVOKED')),
    CONSTRAINT ck_external_provider_lease_rate_limit
        CHECK (rate_limit_per_minute > 0 AND rate_limit_per_minute <= 60)
);

CREATE INDEX IF NOT EXISTS ix_external_provider_credential_leases_tenant_adapter
    ON external_provider_credential_leases(tenant_id, adapter_id, status, expires_at);

CREATE TABLE IF NOT EXISTS external_provider_rate_buckets (
    scope_key                  VARCHAR(240) PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    adapter_id                 VARCHAR(120) NOT NULL,
    window_started_at          TIMESTAMPTZ NOT NULL,
    request_count              INTEGER NOT NULL DEFAULT 0,
    limit_count                INTEGER NOT NULL,
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_external_provider_rate_bucket_counts
        CHECK (request_count >= 0 AND limit_count > 0)
);

CREATE TABLE IF NOT EXISTS external_provider_attempts (
    id                         UUID PRIMARY KEY,
    intent_id                  VARCHAR(36) NOT NULL REFERENCES external_action_intents(id) ON DELETE CASCADE,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    adapter_id                 VARCHAR(120) NOT NULL,
    credential_lease_id        VARCHAR(36) REFERENCES external_provider_credential_leases(id),
    attempt_no                 INTEGER NOT NULL,
    request_hash               VARCHAR(64) NOT NULL,
    response_hash              VARCHAR(64),
    provider_status            INTEGER,
    provider_url               TEXT,
    resolved_ips               JSONB,
    outcome                    VARCHAR(32) NOT NULL,
    started_at                 TIMESTAMPTZ NOT NULL,
    completed_at               TIMESTAMPTZ,
    CONSTRAINT uq_external_provider_attempt_sequence
        UNIQUE (intent_id, attempt_no),
    CONSTRAINT ck_external_provider_attempt_outcome
        CHECK (outcome IN ('ATTEMPTED', 'SUCCEEDED', 'AMBIGUOUS', 'FAILED', 'RATE_LIMITED'))
);

CREATE INDEX IF NOT EXISTS ix_external_provider_attempts_intent
    ON external_provider_attempts(intent_id, attempt_no);

COMMENT ON TABLE external_provider_credential_leases IS
    'Gate 4C durable credential descriptors only; secrets remain outside PostgreSQL.';
COMMENT ON TABLE external_provider_attempts IS
    'Gate 4C provider request/result ledger for the existing external-action authority envelope.';
