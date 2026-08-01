-- =============================================================================
-- AI-OS migration 0001 — agent registry and version lock
-- Governance: FOUNDATION IMPLEMENTATION, M-001 (authorized). Runner:
--   portal/scripts/migration_runner.py  (root: portal/migrations/ai_os)
-- Authority: docs/adr/ADR-0001-ai-os-migration-framework.md
--
-- Constraints of this migration (M-001 authorization):
--   * simple transactional DDL only
--   * no PL/pgSQL, no DO $$ blocks, no triggers, no functions, no procedures
--   * no seeding, no activation, no runtime behavior
--   * DOWN migration: down.sql (PostgreSQL override: down.postgresql.sql)
--
-- Prerequisite: the legacy portal schema (tenants, users) must already exist.
--   On PostgreSQL it is applied by portal/scripts/postgresql_bootstrap.py.
-- =============================================================================

CREATE TABLE ai_os_agents (
    id                 UUID          PRIMARY KEY,
    tenant_id          UUID          NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    agent_id           VARCHAR(64)   NOT NULL,
    display_name       VARCHAR(128)  NOT NULL,
    role               VARCHAR(128)  NOT NULL,
    status             VARCHAR(16)   NOT NULL DEFAULT 'seed',
    active             BOOLEAN       NOT NULL DEFAULT FALSE,
    current_version_id UUID,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by         UUID          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ai_os_agents_tenant_agent UNIQUE (tenant_id, agent_id),
    CONSTRAINT ck_ai_os_agents_status CHECK (status IN ('seed', 'active', 'retired')),
    CONSTRAINT ck_ai_os_agents_seed_inactive CHECK (status <> 'seed' OR active = FALSE),
    CONSTRAINT ck_ai_os_agents_retired_inactive CHECK (status <> 'retired' OR active = FALSE)
);

CREATE INDEX ix_ai_os_agents_tenant ON ai_os_agents (tenant_id);

CREATE INDEX ix_ai_os_agents_tenant_status ON ai_os_agents (tenant_id, status);

CREATE TABLE ai_os_agent_versions (
    id              UUID          PRIMARY KEY,
    tenant_id       UUID          NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    agent_row_id    UUID          NOT NULL REFERENCES ai_os_agents(id) ON DELETE RESTRICT,
    semver          VARCHAR(32)   NOT NULL,
    definition      TEXT          NOT NULL,
    definition_sha256 VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      UUID          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ai_os_agent_versions_agent_semver UNIQUE (agent_row_id, semver),
    CONSTRAINT uq_ai_os_agent_versions_agent_hash UNIQUE (agent_row_id, definition_sha256)
);

CREATE INDEX ix_ai_os_agent_versions_agent ON ai_os_agent_versions (agent_row_id)
