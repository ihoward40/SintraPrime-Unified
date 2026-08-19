-- =============================================================================
-- Migration: Durable governed service-identity descriptors
-- Stores authority metadata only. No credential material is stored here.
-- =============================================================================

CREATE TABLE IF NOT EXISTS governed_service_identities (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by            UUID NOT NULL REFERENCES users(id),
    display_name          VARCHAR(120) NOT NULL,
    agent_id              VARCHAR(128),
    credential_ref        TEXT,
    scopes                JSONB NOT NULL DEFAULT '[]'::jsonb,
    scoped_folders        JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_capabilities  JSONB NOT NULL DEFAULT '[]'::jsonb,
    status                VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    idempotency_key       VARCHAR(128),
    request_hash          VARCHAR(64) NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at            TIMESTAMPTZ NOT NULL,
    revoked_at            TIMESTAMPTZ,
    revocation_reason     TEXT,
    CONSTRAINT ck_governed_service_identity_status
        CHECK (status IN ('ACTIVE', 'REVOKED')),
    CONSTRAINT uq_governed_service_identity_idempotency
        UNIQUE (tenant_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_governed_service_identities_tenant_status_expires
    ON governed_service_identities(tenant_id, status, expires_at);

CREATE INDEX IF NOT EXISTS ix_governed_service_identities_tenant_agent
    ON governed_service_identities(tenant_id, agent_id);

COMMENT ON TABLE governed_service_identities IS
    'Durable non-secret service identity descriptors for governed SintraPrime execution.';

COMMENT ON COLUMN governed_service_identities.credential_ref IS
    'Opaque reference to canonical secret/connector identity; never credential material.';
