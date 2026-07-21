-- =============================================================================
-- Migration: Add provider_tenant_mappings table
-- Payment Webhook Increment One: Server-side mapping of Stripe provider IDs to tenants
-- =============================================================================

CREATE TABLE IF NOT EXISTS provider_tenant_mappings (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    provider              VARCHAR(50) NOT NULL,
    provider_account_id   VARCHAR(255),
    provider_customer_id  VARCHAR(255),
    mapping_status        VARCHAR(20) NOT NULL DEFAULT 'active',
    created_by            UUID REFERENCES users(id),
    created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by            UUID REFERENCES users(id),
    deactivated_at        TIMESTAMP WITH TIME ZONE,
    deactivated_by        UUID REFERENCES users(id),
    deactivation_reason   TEXT
);

CREATE UNIQUE INDEX uq_active_provider_account
ON provider_tenant_mappings (provider, provider_account_id)
WHERE provider_account_id IS NOT NULL
  AND mapping_status = 'active';

CREATE UNIQUE INDEX uq_active_provider_customer
ON provider_tenant_mappings (provider, provider_customer_id)
WHERE provider_customer_id IS NOT NULL
  AND mapping_status = 'active';