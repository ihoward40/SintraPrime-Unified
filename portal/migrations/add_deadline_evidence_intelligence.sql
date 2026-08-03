-- Phase 2C-3 deadline and evidence graph persistence.
-- Scope excludes frontend matter workspace and export generation.

CREATE TABLE IF NOT EXISTS matter_deadlines (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id VARCHAR(36) NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    deadline_type VARCHAR(40) NOT NULL,
    source_kind VARCHAR(40) NOT NULL,
    trigger_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    timezone_name VARCHAR(64) NOT NULL,
    calendar_type VARCHAR(24) NOT NULL,
    calculation_status VARCHAR(40) NOT NULL,
    calculation_rule_id VARCHAR(128),
    authority_ids JSONB NOT NULL DEFAULT '[]',
    trigger_basis JSONB NOT NULL DEFAULT '{}',
    assumptions JSONB NOT NULL DEFAULT '[]',
    limitations JSONB NOT NULL DEFAULT '[]',
    review_status VARCHAR(40) NOT NULL DEFAULT 'NOT_SUBMITTED',
    current_version INTEGER NOT NULL DEFAULT 1,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_deadline_versions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id VARCHAR(36) NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    deadline_id VARCHAR(36) NOT NULL REFERENCES matter_deadlines(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    trigger_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    calculation_status VARCHAR(40) NOT NULL,
    calculation_inputs_redacted JSONB NOT NULL DEFAULT '{}',
    assumptions JSONB NOT NULL DEFAULT '[]',
    limitations JSONB NOT NULL DEFAULT '[]',
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (deadline_id, version_number)
);

CREATE TABLE IF NOT EXISTS matter_evidence_nodes (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id VARCHAR(36) NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    node_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    statement_redacted TEXT,
    evidence_status VARCHAR(32) NOT NULL,
    source_document_id VARCHAR(36) REFERENCES documents(id),
    source_authority_id VARCHAR(128),
    source_rule_id VARCHAR(128),
    provenance JSONB NOT NULL DEFAULT '{}',
    review_status VARCHAR(40) NOT NULL DEFAULT 'NOT_SUBMITTED',
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_evidence_links (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id VARCHAR(36) NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    source_node_id VARCHAR(36) NOT NULL REFERENCES matter_evidence_nodes(id) ON DELETE CASCADE,
    target_node_id VARCHAR(36) NOT NULL REFERENCES matter_evidence_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(32) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes_redacted TEXT,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matter_evidence_findings (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id VARCHAR(36) NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    finding_type VARCHAR(32) NOT NULL,
    node_id VARCHAR(36) REFERENCES matter_evidence_nodes(id) ON DELETE CASCADE,
    related_node_id VARCHAR(36) REFERENCES matter_evidence_nodes(id) ON DELETE CASCADE,
    summary_redacted TEXT NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'OPEN',
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_matter_deadlines_scope ON matter_deadlines(tenant_id, matter_id, due_at);
CREATE INDEX IF NOT EXISTS ix_matter_deadline_versions_scope ON matter_deadline_versions(tenant_id, matter_id, deadline_id, version_number);
CREATE INDEX IF NOT EXISTS ix_matter_evidence_nodes_scope ON matter_evidence_nodes(tenant_id, matter_id, evidence_status);
CREATE INDEX IF NOT EXISTS ix_matter_evidence_links_scope ON matter_evidence_links(tenant_id, matter_id, relationship_type);
CREATE INDEX IF NOT EXISTS ix_matter_evidence_findings_scope ON matter_evidence_findings(tenant_id, matter_id, status);

-- DOWN MIGRATION:
-- DROP TABLE IF EXISTS matter_evidence_findings;
-- DROP TABLE IF EXISTS matter_evidence_links;
-- DROP TABLE IF EXISTS matter_evidence_nodes;
-- DROP TABLE IF EXISTS matter_deadline_versions;
-- DROP TABLE IF EXISTS matter_deadlines;
