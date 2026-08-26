-- SintraPrime Adaptive Orchestration remediation tables.
--
-- Adds the three ORM-declared tables that were absent from the controlling
-- raw-SQL bootstrap: orchestration_linkages, orchestration_principal_authorities,
-- and memory_vault.  These tables are used by active runtime paths and must
-- be present in the authoritative PostgreSQL fresh-bootstrap sequence.
--
-- All parent tables (tenants, users, orchestration_events, orchestration_nodes)
-- are already authoritative in earlier migrations.

-- ---------------------------------------------------------------------------
-- orchestration_linkages
--   Immutable event-to-node linkage with FK enforcement.
--   Depends on: orchestration_events, orchestration_nodes, tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orchestration_linkages (
    id          UUID PRIMARY KEY,
    event_id    UUID NOT NULL REFERENCES orchestration_events(id) ON DELETE CASCADE,
    node_id     UUID NOT NULL REFERENCES orchestration_nodes(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    linked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_orchestration_linkage_event_node UNIQUE (event_id, node_id)
);

CREATE INDEX IF NOT EXISTS ix_orchestration_linkage_event
    ON orchestration_linkages(event_id);
CREATE INDEX IF NOT EXISTS ix_orchestration_linkage_node
    ON orchestration_linkages(node_id);

-- ---------------------------------------------------------------------------
-- orchestration_principal_authorities
--   Tenant-scoped human principal authority registration.
--   Depends on: tenants, users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orchestration_principal_authorities (
    id             UUID PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(id),
    user_id        UUID NOT NULL REFERENCES users(id),
    scope          VARCHAR(80) NOT NULL DEFAULT 'GLOBAL',
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    authorized_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_orchestration_principal_auth UNIQUE (tenant_id, user_id, scope)
);

CREATE INDEX IF NOT EXISTS ix_orchestration_principal_tenant
    ON orchestration_principal_authorities(tenant_id, is_active);

-- ---------------------------------------------------------------------------
-- memory_vault
--   Durable OmniBrain memory entry for Phase 10 flow.
--   Depends on: tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_vault (
    id             UUID PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type           VARCHAR(80) NOT NULL,
    content        JSONB NOT NULL,
    metadata_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    version        INTEGER NOT NULL DEFAULT 1,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_memory_vault_tenant_type
    ON memory_vault(tenant_id, type);

-- ---------------------------------------------------------------------------
-- Row-Level Security
--   All three tables are tenant-scoped and must enforce tenant isolation
--   consistent with the existing orchestration domain RLS pattern.
-- ---------------------------------------------------------------------------
ALTER TABLE orchestration_linkages ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestration_principal_authorities ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_vault ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS orchestration_linkages_tenant_isolation ON orchestration_linkages;
CREATE POLICY orchestration_linkages_tenant_isolation
    ON orchestration_linkages
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS orchestration_principal_authorities_tenant_isolation ON orchestration_principal_authorities;
CREATE POLICY orchestration_principal_authorities_tenant_isolation
    ON orchestration_principal_authorities
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS memory_vault_tenant_isolation ON memory_vault;
CREATE POLICY memory_vault_tenant_isolation
    ON memory_vault
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

-- DOWN migration notes:
-- Run in reverse dependency order if rollback is required.
--   DROP TABLE IF EXISTS memory_vault;
--   DROP TABLE IF EXISTS orchestration_principal_authorities;
--   DROP TABLE IF EXISTS orchestration_linkages;