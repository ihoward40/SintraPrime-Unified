-- Phase 2C-2 persistent matter intelligence tables.
-- Scope intentionally excludes deadline calculation and evidence-graph edges.

CREATE TABLE IF NOT EXISTS matter_parties (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    role VARCHAR(40) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    contact_summary TEXT,
    identifier_redacted VARCHAR(64),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_accounts (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    account_type VARCHAR(50) NOT NULL,
    account_reference_redacted VARCHAR(128),
    creditor_party_id UUID REFERENCES matter_parties(id),
    collector_party_id UUID REFERENCES matter_parties(id),
    furnisher_party_id UUID REFERENCES matter_parties(id),
    servicer_party_id UUID REFERENCES matter_parties(id),
    assignee_party_id UUID REFERENCES matter_parties(id),
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    details JSONB NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_filings (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    filing_kind VARCHAR(50) NOT NULL,
    filing_number_redacted VARCHAR(128),
    filing_office VARCHAR(255),
    filing_jurisdiction VARCHAR(32),
    filed_on TIMESTAMPTZ,
    debtor_name_redacted VARCHAR(255),
    secured_party_id UUID REFERENCES matter_parties(id),
    status VARCHAR(30) NOT NULL DEFAULT 'reported',
    details JSONB NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_communications (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    communication_type VARCHAR(40) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    sender_party_id UUID REFERENCES matter_parties(id),
    recipient_party_id UUID REFERENCES matter_parties(id),
    subject_redacted VARCHAR(500),
    content_redacted TEXT,
    source_document_id UUID REFERENCES documents(id),
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_disputes (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    account_id UUID REFERENCES matter_accounts(id),
    dispute_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    submitted_on TIMESTAMPTZ,
    responded_on TIMESTAMPTZ,
    summary_redacted TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_attachments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id),
    label_redacted VARCHAR(255) NOT NULL,
    attachment_kind VARCHAR(40) NOT NULL,
    checksum_sha256 VARCHAR(64),
    classification VARCHAR(40) NOT NULL DEFAULT 'UNCLASSIFIED',
    redaction_status VARCHAR(30) NOT NULL DEFAULT 'REDACTION_REQUIRED',
    metadata JSONB NOT NULL DEFAULT '{}',
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_assessments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    assessment_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    review_status VARCHAR(40) NOT NULL DEFAULT 'NOT_SUBMITTED',
    reviewer_role VARCHAR(40),
    reviewer_identity VARCHAR(255),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matter_assessment_versions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES matter_assessments(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    facts_redacted JSONB NOT NULL DEFAULT '{}',
    conclusions_redacted JSONB NOT NULL DEFAULT '{}',
    limitations JSONB NOT NULL DEFAULT '[]',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (assessment_id, version_number)
);

CREATE TABLE IF NOT EXISTS matter_audit_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matter_id UUID NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(80) NOT NULL,
    object_type VARCHAR(60) NOT NULL,
    object_id UUID NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    previous_hash VARCHAR(64),
    entry_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_matter_parties_scope ON matter_parties(tenant_id, matter_id, role);
CREATE INDEX IF NOT EXISTS ix_matter_accounts_scope ON matter_accounts(tenant_id, matter_id, status);
CREATE INDEX IF NOT EXISTS ix_matter_filings_scope ON matter_filings(tenant_id, matter_id, filed_on);
CREATE INDEX IF NOT EXISTS ix_matter_communications_scope ON matter_communications(tenant_id, matter_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_matter_disputes_scope ON matter_disputes(tenant_id, matter_id, status);
CREATE INDEX IF NOT EXISTS ix_matter_attachments_scope ON matter_attachments(tenant_id, matter_id, classification);
CREATE INDEX IF NOT EXISTS ix_matter_assessments_scope ON matter_assessments(tenant_id, matter_id, review_status);
CREATE INDEX IF NOT EXISTS ix_matter_assessment_versions_scope ON matter_assessment_versions(tenant_id, matter_id, assessment_id, version_number);
CREATE INDEX IF NOT EXISTS ix_matter_audit_events_scope ON matter_audit_events(tenant_id, matter_id, created_at);

-- DOWN MIGRATION:
-- DROP TABLE IF EXISTS matter_audit_events;
-- DROP TABLE IF EXISTS matter_assessment_versions;
-- DROP TABLE IF EXISTS matter_assessments;
-- DROP TABLE IF EXISTS matter_attachments;
-- DROP TABLE IF EXISTS matter_disputes;
-- DROP TABLE IF EXISTS matter_communications;
-- DROP TABLE IF EXISTS matter_filings;
-- DROP TABLE IF EXISTS matter_accounts;
-- DROP TABLE IF EXISTS matter_parties;