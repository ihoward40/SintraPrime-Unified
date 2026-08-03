-- Phase 1 legal authority and jurisdiction rule persistence path.
-- Runtime Phase 1 APIs are read-only and JSON-backed; these tables are for governed persistence migration.

CREATE TABLE IF NOT EXISTS legal_authorities (
    id VARCHAR(128) PRIMARY KEY,
    jurisdiction VARCHAR(16) NOT NULL,
    authority_type VARCHAR(64) NOT NULL,
    source_classification VARCHAR(64) NOT NULL,
    citation VARCHAR(512) NOT NULL,
    title VARCHAR(512) NOT NULL,
    court_or_agency VARCHAR(256),
    docket_or_bill_number VARCHAR(128),
    source_url TEXT,
    source_document_id VARCHAR(256),
    publication_date VARCHAR(32),
    effective_date VARCHAR(32),
    repeal_date VARCHAR(32),
    last_verified_at TIMESTAMPTZ,
    verified_by VARCHAR(128),
    verification_status VARCHAR(64) NOT NULL,
    authority_weight INTEGER NOT NULL,
    summary TEXT NOT NULL,
    quoted_text TEXT,
    limitations JSONB NOT NULL DEFAULT '[]',
    tags JSONB NOT NULL DEFAULT '[]',
    content_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_legal_authorities_jurisdiction_type ON legal_authorities(jurisdiction, authority_type);
CREATE INDEX IF NOT EXISTS ix_legal_authorities_source_classification ON legal_authorities(source_classification);
CREATE INDEX IF NOT EXISTS ix_legal_authorities_verification_status ON legal_authorities(verification_status);

CREATE TABLE IF NOT EXISTS jurisdiction_rules (
    id VARCHAR(128) PRIMARY KEY,
    jurisdiction VARCHAR(16) NOT NULL,
    domain VARCHAR(64) NOT NULL,
    topic VARCHAR(256) NOT NULL,
    rule_statement TEXT NOT NULL,
    rule_logic JSONB NOT NULL,
    authority_ids JSONB NOT NULL,
    status VARCHAR(64) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from VARCHAR(32),
    effective_to VARCHAR(32),
    exceptions JSONB NOT NULL DEFAULT '[]',
    conflicting_rule_ids JSONB NOT NULL DEFAULT '[]',
    supersedes_rule_ids JSONB NOT NULL DEFAULT '[]',
    superseded_by_rule_ids JSONB NOT NULL DEFAULT '[]',
    version VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_jurisdiction_rules_lookup ON jurisdiction_rules(jurisdiction, domain, topic);
CREATE INDEX IF NOT EXISTS ix_jurisdiction_rules_status ON jurisdiction_rules(status);

CREATE TABLE IF NOT EXISTS professional_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    object_type VARCHAR(64) NOT NULL,
    object_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(128) NOT NULL,
    reviewer_identity VARCHAR(256),
    review_status VARCHAR(64) NOT NULL,
    findings TEXT NOT NULL,
    conditions JSONB NOT NULL DEFAULT '[]',
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_professional_reviews_object ON professional_reviews(object_type, object_id);
CREATE INDEX IF NOT EXISTS ix_professional_reviews_status ON professional_reviews(review_status);

-- DOWN MIGRATION:
-- DROP TABLE IF EXISTS professional_reviews;
-- DROP TABLE IF EXISTS jurisdiction_rules;
-- DROP TABLE IF EXISTS legal_authorities;
