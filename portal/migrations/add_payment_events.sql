-- =============================================================================
-- Migration: Add payment_events table
-- Payment Webhook Increment One: Authoritative webhook acknowledgment and idempotency record
-- =============================================================================

CREATE TABLE IF NOT EXISTS payment_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    provider            VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL DEFAULT '__platform__',
    provider_event_id   VARCHAR(255) NOT NULL,
    operation           VARCHAR(100) NOT NULL,
    payload_digest      VARCHAR(64) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'reserved',
    correlation_id      VARCHAR(255),
    result_reference    TEXT,
    processing_owner    VARCHAR(255),
    lease_expires_at    TIMESTAMP WITH TIME ZONE,
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    last_error_code     VARCHAR(100),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expiry_at           TIMESTAMP WITH TIME ZONE,
    version             INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX uq_provider_event
ON payment_events (provider, provider_account_id, provider_event_id);