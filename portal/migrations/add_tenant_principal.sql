-- Tenant Principal identity authority
--
-- One constitutional Principal per tenant, established through a trusted
-- bootstrap/migration/administrative ceremony. Not self-service writable.

CREATE TABLE IF NOT EXISTS tenant_principals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    established_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    establishment_source VARCHAR(100) NOT NULL DEFAULT 'bootstrap',
    CONSTRAINT uq_tenant_principals_tenant_id UNIQUE (tenant_id),
    CONSTRAINT uq_tenant_principals_user_tenant UNIQUE (principal_user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_principals_tenant
    ON tenant_principals(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_principals_user
    ON tenant_principals(principal_user_id);

-- Inline DOWN migration for fresh-bootstrap rollback.
-- DROP TABLE IF EXISTS tenant_principals;
