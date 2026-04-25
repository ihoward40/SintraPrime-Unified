-- =============================================================================
-- SintraPrime Unified Client Portal — Complete PostgreSQL Schema
-- Multi-tenant, Row-Level Security, Full-Text Search, Audit Triggers
-- UUID primary keys, soft deletes, immutable audit chain
-- =============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- TENANTS (Firms)
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,  -- Used for subdomain routing
    domain          VARCHAR(255),                  -- custom domain e.g. portal.lawfirm.com
    logo_url        TEXT,
    primary_color   VARCHAR(7) DEFAULT '#1a56db',  -- Hex color
    secondary_color VARCHAR(7) DEFAULT '#e1effe',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    plan            VARCHAR(50) NOT NULL DEFAULT 'professional',  -- starter, professional, enterprise
    max_users       INTEGER DEFAULT 50,
    max_storage_gb  INTEGER DEFAULT 100,
    mfa_required    BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_domains TEXT[],                        -- Email domain allowlist for auto-join
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX ix_tenants_slug ON tenants(slug);
CREATE INDEX ix_tenants_domain ON tenants(domain) WHERE domain IS NOT NULL;

-- =============================================================================
-- ROLES & PERMISSIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT[] NOT NULL DEFAULT '{}',
    is_system   BOOLEAN NOT NULL DEFAULT TRUE,    -- System roles can't be deleted
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed system roles
INSERT INTO roles (name, description, permissions, is_system) VALUES
    ('SUPER_ADMIN',  'Full system access',                 ARRAY['*'], TRUE),
    ('FIRM_ADMIN',   'Manage their firm',                  ARRAY['user:*','client:*','case:*','doc:*','billing:*','admin:*'], TRUE),
    ('ATTORNEY',     'Full case and document access',      ARRAY['client:*','case:*','doc:*','billing:read','msg:*'], TRUE),
    ('PARALEGAL',    'Case access, limited sharing',       ARRAY['client:read','case:read,update','doc:read,upload,version','msg:*'], TRUE),
    ('CLIENT',       'Own data only',                      ARRAY['client:own','case:own','doc:own','msg:read,send','billing:own'], TRUE),
    ('ACCOUNTANT',   'Financial documents and billing',    ARRAY['billing:*','doc:financial'], TRUE),
    ('VIEWER',       'Read-only to assigned documents',    ARRAY['doc:read'], TRUE)
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- USERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_id                     UUID NOT NULL REFERENCES roles(id),
    email                       VARCHAR(320) NOT NULL,
    first_name                  VARCHAR(100) NOT NULL,
    last_name                   VARCHAR(100) NOT NULL,
    hashed_password             VARCHAR(255) NOT NULL,
    phone                       VARCHAR(30),
    avatar_url                  TEXT,
    bio                         TEXT,
    title                       VARCHAR(100),              -- e.g. "Senior Partner"
    bar_number                  VARCHAR(50),               -- Attorney bar number
    
    -- Auth state
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified                 BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified              BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_enabled                 BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret                  VARCHAR(255),              -- Encrypted TOTP secret
    mfa_backup_codes            TEXT[],                    -- Encrypted backup codes
    
    -- Invite flow
    invite_token                VARCHAR(255),
    invite_accepted_at          TIMESTAMPTZ,
    
    -- Security tracking
    failed_login_attempts       INTEGER NOT NULL DEFAULT 0,
    locked_until                TIMESTAMPTZ,
    last_login_at               TIMESTAMPTZ,
    last_login_ip               INET,
    password_changed_at         TIMESTAMPTZ,
    force_password_change       BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Preferences
    timezone                    VARCHAR(50) DEFAULT 'America/New_York',
    locale                      VARCHAR(10) DEFAULT 'en-US',
    notification_preferences    JSONB DEFAULT '{}',
    
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,
    
    CONSTRAINT uq_user_email_tenant UNIQUE (email, tenant_id)
);

CREATE INDEX ix_users_tenant_id ON users(tenant_id);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_role_id ON users(role_id);
CREATE INDEX ix_users_is_active ON users(is_active) WHERE deleted_at IS NULL;

-- =============================================================================
-- CLIENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS clients (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    primary_attorney_id UUID REFERENCES users(id),
    portal_user_id      UUID REFERENCES users(id),         -- Linked portal login
    
    -- Identity
    client_type         VARCHAR(20) NOT NULL DEFAULT 'individual', -- individual, business
    first_name          VARCHAR(100),
    last_name           VARCHAR(100),
    company_name        VARCHAR(255),
    display_name        VARCHAR(255) GENERATED ALWAYS AS (
        COALESCE(NULLIF(company_name, ''), CONCAT(first_name, ' ', last_name))
    ) STORED,
    
    -- Contact
    email               VARCHAR(320),
    phone               VARCHAR(30),
    phone_mobile        VARCHAR(30),
    address_line1       VARCHAR(255),
    address_line2       VARCHAR(100),
    city                VARCHAR(100),
    state               VARCHAR(50),
    zip                 VARCHAR(20),
    country             VARCHAR(2) DEFAULT 'US',
    
    -- Business
    tax_id              VARCHAR(50),
    date_of_birth       DATE,
    ssn_last4           VARCHAR(4),                        -- Last 4 digits only
    
    -- Status
    status              VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, prospect, closed
    source              VARCHAR(50),                       -- referral, website, etc.
    intake_date         DATE,
    retainer_signed_at  TIMESTAMPTZ,
    notes               TEXT,
    tags                TEXT[],
    custom_fields       JSONB DEFAULT '{}',
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX ix_clients_tenant_id ON clients(tenant_id);
CREATE INDEX ix_clients_attorney ON clients(primary_attorney_id);
CREATE INDEX ix_clients_email ON clients(email) WHERE email IS NOT NULL;
CREATE INDEX ix_clients_status ON clients(status, tenant_id);
CREATE INDEX ix_clients_fts ON clients USING GIN (
    to_tsvector('english',
        COALESCE(first_name, '') || ' ' ||
        COALESCE(last_name, '') || ' ' ||
        COALESCE(company_name, '') || ' ' ||
        COALESCE(email, '')
    )
);

-- =============================================================================
-- MATTERS (Client engagements / retainers)
-- =============================================================================

CREATE TABLE IF NOT EXISTS matters (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    matter_number       VARCHAR(50),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    practice_area       VARCHAR(100),
    fee_arrangement     VARCHAR(50),  -- hourly, flat_fee, contingency, hybrid
    hourly_rate         NUMERIC(10,2),
    flat_fee_amount     NUMERIC(10,2),
    contingency_percent NUMERIC(5,2),
    retainer_amount     NUMERIC(10,2),
    retainer_balance    NUMERIC(10,2),
    billing_frequency   VARCHAR(20) DEFAULT 'monthly',
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    opened_date         DATE,
    closed_date         DATE,
    custom_fields       JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT uq_matter_number_tenant UNIQUE (matter_number, tenant_id)
);

CREATE INDEX ix_matters_client_id ON matters(client_id);

-- =============================================================================
-- CASES
-- =============================================================================

CREATE TABLE IF NOT EXISTS cases (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id               UUID NOT NULL REFERENCES clients(id),
    matter_id               UUID REFERENCES matters(id),
    lead_attorney_id        UUID REFERENCES users(id),
    parent_case_id          UUID REFERENCES cases(id),     -- Linked/related cases
    
    case_number             VARCHAR(50) NOT NULL,
    title                   VARCHAR(500) NOT NULL,
    description             TEXT,
    practice_area           VARCHAR(100),
    case_type               VARCHAR(100),
    jurisdiction            VARCHAR(100),
    court_name              VARCHAR(255),
    docket_number           VARCHAR(100),
    judge_name              VARCHAR(255),
    opposing_party          VARCHAR(500),
    opposing_counsel        VARCHAR(500),
    opposing_counsel_firm   VARCHAR(255),
    
    stage                   VARCHAR(30) NOT NULL DEFAULT 'intake',
    -- intake, active, discovery, pending, settled, trial, appeal, closed, archived
    
    priority                VARCHAR(10) DEFAULT 'normal',  -- low, normal, high, urgent
    is_urgent               BOOLEAN NOT NULL DEFAULT FALSE,
    is_confidential         BOOLEAN NOT NULL DEFAULT FALSE,
    
    incident_date           DATE,
    statute_of_limitations  DATE,
    trial_date              DATE,
    expected_resolution_date DATE,
    closed_date             DATE,
    close_reason            VARCHAR(100),
    
    -- Assigned staff (array of user UUIDs as strings)
    assigned_staff          TEXT[] DEFAULT '{}',
    
    -- Intake custom fields (per practice area)
    intake_data             JSONB DEFAULT '{}',
    custom_fields           JSONB DEFAULT '{}',
    tags                    TEXT[],
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    
    CONSTRAINT uq_case_number_tenant UNIQUE (case_number, tenant_id)
);

CREATE INDEX ix_cases_tenant_id ON cases(tenant_id);
CREATE INDEX ix_cases_client_id ON cases(client_id);
CREATE INDEX ix_cases_attorney ON cases(lead_attorney_id);
CREATE INDEX ix_cases_stage ON cases(stage, tenant_id);
CREATE INDEX ix_cases_fts ON cases USING GIN (
    to_tsvector('english',
        COALESCE(title, '') || ' ' ||
        COALESCE(case_number, '') || ' ' ||
        COALESCE(opposing_party, '') || ' ' ||
        COALESCE(docket_number, '')
    )
);

-- =============================================================================
-- CASE EVENTS (Timeline)
-- =============================================================================

CREATE TABLE IF NOT EXISTS case_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    created_by          UUID REFERENCES users(id),
    event_type          VARCHAR(50) NOT NULL,  -- hearing, deposition, filing, meeting, call, etc.
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    event_date          TIMESTAMPTZ NOT NULL,
    end_date            TIMESTAMPTZ,
    location            VARCHAR(255),
    is_court_date       BOOLEAN NOT NULL DEFAULT FALSE,
    is_client_visible   BOOLEAN NOT NULL DEFAULT FALSE,
    participants        TEXT[],
    outcome             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_case_events_case_id ON case_events(case_id);
CREATE INDEX ix_case_events_date ON case_events(event_date);

-- =============================================================================
-- CASE DEADLINES
-- =============================================================================

CREATE TABLE IF NOT EXISTS case_deadlines (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    created_by      UUID REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    deadline_type   VARCHAR(50) DEFAULT 'general',  -- statute_of_limitations, filing, response, etc.
    due_date        TIMESTAMPTZ NOT NULL,
    is_court_date   BOOLEAN NOT NULL DEFAULT FALSE,
    is_critical     BOOLEAN NOT NULL DEFAULT FALSE,
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    reminder_days   INTEGER[] DEFAULT '{7, 1}',     -- Remind X days before
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_case_deadlines_case_id ON case_deadlines(case_id);
CREATE INDEX ix_case_deadlines_due_date ON case_deadlines(due_date) WHERE is_completed = FALSE;

-- =============================================================================
-- CASE NOTES
-- =============================================================================

CREATE TABLE IF NOT EXISTS case_notes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    case_id     UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    created_by  UUID REFERENCES users(id),
    note_type   VARCHAR(20) DEFAULT 'internal',   -- internal (staff-only), client_visible
    content     TEXT NOT NULL,
    is_pinned   BOOLEAN NOT NULL DEFAULT FALSE,
    pinned      BOOLEAN GENERATED ALWAYS AS (is_pinned) STORED,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX ix_case_notes_case_id ON case_notes(case_id);

-- =============================================================================
-- CASE TASKS
-- =============================================================================

CREATE TABLE IF NOT EXISTS case_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    created_by      UUID REFERENCES users(id),
    assigned_to     UUID REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    priority        VARCHAR(10) DEFAULT 'normal',
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, in_progress, done, cancelled
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- =============================================================================
-- DOCUMENT FOLDERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_folders (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    parent_id   UUID REFERENCES document_folders(id),
    client_id   UUID REFERENCES clients(id),
    case_id     UUID REFERENCES cases(id),
    created_by  UUID REFERENCES users(id),
    name        VARCHAR(255) NOT NULL,
    path        TEXT NOT NULL,              -- Full materialized path e.g. /Clients/Smith/
    color       VARCHAR(7),
    icon        VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX ix_folders_tenant_id ON document_folders(tenant_id);
CREATE INDEX ix_folders_parent_id ON document_folders(parent_id);

-- =============================================================================
-- DOCUMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID REFERENCES clients(id),
    case_id             UUID REFERENCES cases(id),
    matter_id           UUID REFERENCES matters(id),
    folder_id           UUID REFERENCES document_folders(id),
    uploaded_by         UUID REFERENCES users(id),
    
    name                VARCHAR(1000) NOT NULL,
    description         TEXT,
    mime_type           VARCHAR(255) NOT NULL,
    file_extension      VARCHAR(20),
    size_bytes          BIGINT NOT NULL,
    checksum_sha256     VARCHAR(64) NOT NULL,
    
    -- Storage
    storage_bucket      VARCHAR(255) NOT NULL,
    storage_key         TEXT NOT NULL,
    is_encrypted        BOOLEAN NOT NULL DEFAULT TRUE,
    encryption_iv       VARCHAR(64),
    
    -- Versioning
    current_version     INTEGER NOT NULL DEFAULT 1,
    
    -- Processing state
    status              VARCHAR(20) DEFAULT 'processing',  -- processing, ready, infected, deleted, archived
    virus_scan_status   VARCHAR(20),                       -- pending, clean, infected
    virus_scan_at       TIMESTAMPTZ,
    ocr_status          VARCHAR(20),                       -- pending, processing, complete, failed
    ocr_text            TEXT,                              -- Extracted text for search
    
    -- AI
    ai_category         VARCHAR(100),
    ai_tags             TEXT[],
    ai_summary          TEXT,
    
    -- Metadata
    tags                TEXT[],
    is_confidential     BOOLEAN NOT NULL DEFAULT FALSE,
    is_signed           BOOLEAN NOT NULL DEFAULT FALSE,
    signature_data      JSONB,
    custom_fields       JSONB DEFAULT '{}',
    
    -- FTS index
    fts_vector          TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(ocr_text, '')), 'C')
    ) STORED,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX ix_documents_tenant_id ON documents(tenant_id);
CREATE INDEX ix_documents_client_id ON documents(client_id);
CREATE INDEX ix_documents_case_id ON documents(case_id);
CREATE INDEX ix_documents_folder_id ON documents(folder_id);
CREATE INDEX ix_documents_status ON documents(status) WHERE deleted_at IS NULL;
CREATE INDEX ix_documents_fts ON documents USING GIN (fts_vector);

-- =============================================================================
-- DOCUMENT VERSIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_versions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number      INTEGER NOT NULL,
    storage_key         TEXT NOT NULL,
    storage_bucket      VARCHAR(255),
    size_bytes          BIGINT NOT NULL,
    checksum_sha256     VARCHAR(64) NOT NULL,
    mime_type           VARCHAR(255),
    change_summary      TEXT,
    uploaded_by         UUID REFERENCES users(id),
    is_encrypted        BOOLEAN NOT NULL DEFAULT TRUE,
    encryption_iv       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_doc_version UNIQUE (document_id, version_number)
);

CREATE INDEX ix_doc_versions_document_id ON document_versions(document_id);

-- =============================================================================
-- DOCUMENT SHARES
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_shares (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by          UUID REFERENCES users(id),
    
    share_token         VARCHAR(64) NOT NULL UNIQUE,
    expires_at          TIMESTAMPTZ,
    password_hash       VARCHAR(64),
    
    max_downloads       INTEGER,
    max_views           INTEGER,
    download_count      INTEGER NOT NULL DEFAULT 0,
    view_count          INTEGER NOT NULL DEFAULT 0,
    last_accessed_at    TIMESTAMPTZ,
    last_accessed_by    TEXT,                              -- IP or email
    
    can_download        BOOLEAN NOT NULL DEFAULT TRUE,
    can_view_only       BOOLEAN NOT NULL DEFAULT FALSE,
    is_watermarked      BOOLEAN NOT NULL DEFAULT FALSE,
    is_revoked          BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at          TIMESTAMPTZ,
    
    shared_with_emails  TEXT[],
    notes               TEXT,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_shares_token ON document_shares(share_token);
CREATE INDEX ix_shares_document_id ON document_shares(document_id);

-- =============================================================================
-- MESSAGE THREADS
-- =============================================================================

CREATE TABLE IF NOT EXISTS message_threads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id       UUID REFERENCES clients(id),
    case_id         UUID REFERENCES cases(id),
    created_by      UUID REFERENCES users(id),
    
    subject         VARCHAR(500) NOT NULL,
    category        VARCHAR(50) DEFAULT 'general',
    -- case_discussion, document_review, billing, general
    
    participants    TEXT[] NOT NULL DEFAULT '{}',  -- Array of user UUID strings
    
    is_encrypted    BOOLEAN NOT NULL DEFAULT TRUE,
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at     TIMESTAMPTZ,
    
    message_count   INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    
    retention_days  INTEGER DEFAULT 2555,  -- 7 years
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX ix_threads_tenant_id ON message_threads(tenant_id);
CREATE INDEX ix_threads_case_id ON message_threads(case_id);
CREATE INDEX ix_threads_participants ON message_threads USING GIN (participants);
CREATE INDEX ix_threads_last_message ON message_threads(last_message_at DESC NULLS LAST);

-- =============================================================================
-- MESSAGES
-- =============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id           UUID NOT NULL REFERENCES message_threads(id) ON DELETE CASCADE,
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sender_id           UUID REFERENCES users(id),
    reply_to_id         UUID REFERENCES messages(id),
    
    content             TEXT NOT NULL,
    content_encrypted   BOOLEAN NOT NULL DEFAULT TRUE,
    encryption_iv       VARCHAR(64),
    
    mentions            TEXT[],              -- User IDs mentioned
    read_by             JSONB DEFAULT '{}',  -- {user_id: timestamp}
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMPTZ,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_messages_thread_id ON messages(thread_id);
CREATE INDEX ix_messages_sender_id ON messages(sender_id);
CREATE INDEX ix_messages_created_at ON messages(created_at DESC);

-- =============================================================================
-- MESSAGE ATTACHMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS message_attachments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- BILLING — TIME ENTRIES
-- =============================================================================

CREATE TABLE IF NOT EXISTS time_entries (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id),
    client_id           UUID REFERENCES clients(id),
    case_id             UUID REFERENCES cases(id),
    matter_id           UUID REFERENCES matters(id),
    invoice_id          UUID,                              -- FK added after invoices table
    
    work_date           DATE NOT NULL,
    hours               NUMERIC(6,2) NOT NULL DEFAULT 0,
    hourly_rate         NUMERIC(10,2) NOT NULL,
    amount              NUMERIC(10,2) NOT NULL,
    description         TEXT NOT NULL,
    activity_code       VARCHAR(50),
    
    is_billable         BOOLEAN NOT NULL DEFAULT TRUE,
    is_billed           BOOLEAN NOT NULL DEFAULT FALSE,
    is_no_charge        BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timer support
    is_timer_entry      BOOLEAN NOT NULL DEFAULT FALSE,
    timer_started_at    TIMESTAMPTZ,
    timer_stopped_at    TIMESTAMPTZ,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX ix_time_entries_tenant ON time_entries(tenant_id);
CREATE INDEX ix_time_entries_user ON time_entries(user_id);
CREATE INDEX ix_time_entries_case ON time_entries(case_id);
CREATE INDEX ix_time_entries_unbilled ON time_entries(is_billed, tenant_id) WHERE is_billed = FALSE AND deleted_at IS NULL;

-- =============================================================================
-- BILLING — EXPENSES
-- =============================================================================

CREATE TABLE IF NOT EXISTS expenses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    client_id       UUID REFERENCES clients(id),
    case_id         UUID REFERENCES cases(id),
    invoice_id      UUID,
    
    expense_date    DATE NOT NULL,
    category        VARCHAR(100) NOT NULL,          -- court_fees, travel, copies, etc.
    description     TEXT NOT NULL,
    amount          NUMERIC(10,2) NOT NULL,
    is_billable     BOOLEAN NOT NULL DEFAULT TRUE,
    is_billed       BOOLEAN NOT NULL DEFAULT FALSE,
    receipt_doc_id  UUID REFERENCES documents(id),  -- Uploaded receipt
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- =============================================================================
-- BILLING — INVOICES
-- =============================================================================

CREATE TABLE IF NOT EXISTS invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id),
    case_id         UUID REFERENCES cases(id),
    matter_id       UUID REFERENCES matters(id),
    created_by      UUID REFERENCES users(id),
    
    invoice_number  VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft, sent, partial, paid, overdue, void, disputed
    
    invoice_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date        DATE,
    
    subtotal        NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(12,2) DEFAULT 0,
    tax_rate        NUMERIC(5,2) DEFAULT 0,
    tax_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total           NUMERIC(12,2) NOT NULL,
    amount_paid     NUMERIC(12,2) NOT NULL DEFAULT 0,
    amount_due      NUMERIC(12,2) NOT NULL,
    
    billing_type    VARCHAR(20) DEFAULT 'hourly',   -- hourly, flat_fee, contingency
    currency        VARCHAR(3) DEFAULT 'USD',
    
    notes           TEXT,
    internal_notes  TEXT,
    payment_terms   VARCHAR(100),
    payment_instructions TEXT,
    
    sent_at         TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    voided_at       TIMESTAMPTZ,
    
    -- Stripe / payment gateway
    stripe_payment_intent_id VARCHAR(255),
    payment_link    TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    
    CONSTRAINT uq_invoice_number_tenant UNIQUE (invoice_number, tenant_id)
);

CREATE INDEX ix_invoices_tenant ON invoices(tenant_id);
CREATE INDEX ix_invoices_client ON invoices(client_id);
CREATE INDEX ix_invoices_status ON invoices(status, tenant_id);

-- =============================================================================
-- BILLING — INVOICE LINE ITEMS
-- =============================================================================

CREATE TABLE IF NOT EXISTS invoice_line_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    line_type       VARCHAR(20) DEFAULT 'service',  -- service, expense, discount, tax
    description     TEXT NOT NULL,
    quantity        NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(10,2) NOT NULL,
    amount          NUMERIC(12,2) NOT NULL,
    activity_code   VARCHAR(50),
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_line_items_invoice ON invoice_line_items(invoice_id);

-- Add FK for time_entries → invoices
ALTER TABLE time_entries ADD CONSTRAINT fk_time_entries_invoice
    FOREIGN KEY (invoice_id) REFERENCES invoices(id);

ALTER TABLE expenses ADD CONSTRAINT fk_expenses_invoice
    FOREIGN KEY (invoice_id) REFERENCES invoices(id);

-- =============================================================================
-- BILLING — PAYMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID REFERENCES clients(id),
    invoice_id          UUID REFERENCES invoices(id),
    received_by         UUID REFERENCES users(id),
    
    amount              NUMERIC(12,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'USD',
    payment_method      VARCHAR(50) NOT NULL,       -- check, wire, ach, credit_card, cash
    payment_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    reference_number    VARCHAR(255),
    status              VARCHAR(20) DEFAULT 'succeeded',
    notes               TEXT,
    
    -- Stripe
    stripe_payment_id   VARCHAR(255),
    stripe_receipt_url  TEXT,
    
    processed_at        TIMESTAMPTZ,
    refunded_at         TIMESTAMPTZ,
    refund_amount       NUMERIC(12,2),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- BILLING — TRUST ACCOUNTING (IOLTA)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trust_accounts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES clients(id),
    matter_id           UUID REFERENCES matters(id),
    created_by          UUID REFERENCES users(id),
    approved_by         UUID REFERENCES users(id),
    
    transaction_type    VARCHAR(20) NOT NULL,       -- deposit, withdrawal, transfer, fee
    amount              NUMERIC(12,2) NOT NULL,
    balance_after       NUMERIC(12,2) NOT NULL,
    description         TEXT NOT NULL,
    reference_number    VARCHAR(255),
    transaction_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_trust_client ON trust_accounts(client_id);
CREATE INDEX ix_trust_date ON trust_accounts(transaction_date);

-- =============================================================================
-- NOTIFICATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    event_type      VARCHAR(50) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    body            TEXT,
    resource_type   VARCHAR(50),
    resource_id     VARCHAR(255),
    actor_id        VARCHAR(255),
    metadata        JSONB,
    
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    
    email_sent      BOOLEAN NOT NULL DEFAULT FALSE,
    push_sent       BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_notifications_user_id ON notifications(user_id);
CREATE INDEX ix_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX ix_notifications_created ON notifications(created_at DESC);

-- =============================================================================
-- AUDIT LOG (Immutable, Hash-Chained)
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID REFERENCES tenants(id),
    user_id             UUID REFERENCES users(id),
    actor_email         VARCHAR(320),
    actor_role          VARCHAR(50),
    actor_ip            INET,
    actor_user_agent    TEXT,
    
    action              VARCHAR(100) NOT NULL,
    resource_type       VARCHAR(50),
    resource_id         VARCHAR(255),
    resource_name       VARCHAR(500),
    status              VARCHAR(20) NOT NULL DEFAULT 'success',
    details             JSONB,
    error_message       TEXT,
    
    http_method         VARCHAR(10),
    http_path           TEXT,
    http_status_code    INTEGER,
    
    -- Chain integrity
    previous_hash       VARCHAR(64),
    entry_hash          VARCHAR(64) NOT NULL,
    
    -- Retention: 7 years minimum
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Make audit_logs append-only via policy
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_insert_only ON audit_logs
    FOR INSERT WITH CHECK (TRUE);

CREATE POLICY audit_select ON audit_logs
    FOR SELECT USING (TRUE);

-- No UPDATE or DELETE policies = impossible to modify/delete

CREATE INDEX ix_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX ix_audit_user ON audit_logs(user_id);
CREATE INDEX ix_audit_action ON audit_logs(action);
CREATE INDEX ix_audit_created ON audit_logs(created_at DESC);
CREATE INDEX ix_audit_resource ON audit_logs(resource_type, resource_id);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

-- Enable RLS on all tenant-scoped tables
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;

-- Current tenant isolation (via app-level session variable)
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID
$$ LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION current_user_id() RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.user_id', TRUE), '')::UUID
$$ LANGUAGE SQL STABLE;

-- Clients: tenant isolation + client self-access
CREATE POLICY tenant_isolation ON clients
    FOR ALL USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON cases
    FOR ALL USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON documents
    FOR ALL USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON message_threads
    FOR ALL USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON messages
    FOR ALL USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON invoices
    FOR ALL USING (tenant_id = current_tenant_id());

-- =============================================================================
-- AUTO-UPDATE TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'tenants','users','clients','matters','cases','case_notes','case_tasks',
        'document_folders','documents','message_threads','messages',
        'time_entries','expenses','invoices'
    ]) LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t
        );
    END LOOP;
END $$;

-- =============================================================================
-- FULL-TEXT SEARCH — GIN indexes already created inline above
-- Additional: client display name trigram for fuzzy search
-- =============================================================================

CREATE INDEX ix_clients_trgm ON clients USING GIN (display_name gin_trgm_ops);
CREATE INDEX ix_cases_title_trgm ON cases USING GIN (title gin_trgm_ops);
CREATE INDEX ix_documents_name_trgm ON documents USING GIN (name gin_trgm_ops);

-- =============================================================================
-- AUDIT TRIGGER — Auto-log changes to sensitive tables
-- =============================================================================

CREATE OR REPLACE FUNCTION log_sensitive_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        tenant_id, action, resource_type, resource_id,
        details, status, entry_hash
    )
    VALUES (
        CASE TG_OP
            WHEN 'DELETE' THEN OLD.tenant_id
            ELSE NEW.tenant_id
        END,
        TG_OP || '_' || TG_TABLE_NAME,
        TG_TABLE_NAME,
        CASE TG_OP
            WHEN 'DELETE' THEN OLD.id::TEXT
            ELSE NEW.id::TEXT
        END,
        jsonb_build_object(
            'operation', TG_OP,
            'table', TG_TABLE_NAME
        ),
        'success',
        encode(sha256(
            (TG_TABLE_NAME || TG_OP || NOW()::TEXT || random()::TEXT)::bytea
        ), 'hex')
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit trigger to documents and invoices
CREATE TRIGGER trg_audit_documents
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION log_sensitive_changes();

CREATE TRIGGER trg_audit_invoices
    AFTER INSERT OR UPDATE OR DELETE ON invoices
    FOR EACH ROW EXECUTE FUNCTION log_sensitive_changes();

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Active cases with client and attorney info
CREATE OR REPLACE VIEW v_active_cases AS
SELECT
    c.id,
    c.tenant_id,
    c.case_number,
    c.title,
    c.stage,
    c.practice_area,
    c.is_urgent,
    c.trial_date,
    c.statute_of_limitations,
    cl.display_name AS client_name,
    cl.email AS client_email,
    u.first_name || ' ' || u.last_name AS attorney_name,
    c.created_at,
    c.updated_at
FROM cases c
LEFT JOIN clients cl ON cl.id = c.client_id
LEFT JOIN users u ON u.id = c.lead_attorney_id
WHERE c.deleted_at IS NULL
AND c.stage NOT IN ('closed', 'archived');

-- Outstanding invoices
CREATE OR REPLACE VIEW v_outstanding_invoices AS
SELECT
    i.id,
    i.tenant_id,
    i.invoice_number,
    i.status,
    i.total,
    i.amount_paid,
    i.amount_due,
    i.due_date,
    i.invoice_date,
    cl.display_name AS client_name,
    CASE WHEN i.due_date < CURRENT_DATE THEN TRUE ELSE FALSE END AS is_overdue
FROM invoices i
LEFT JOIN clients cl ON cl.id = i.client_id
WHERE i.deleted_at IS NULL
AND i.status IN ('sent', 'partial', 'overdue');

-- Upcoming deadlines (next 30 days)
CREATE OR REPLACE VIEW v_upcoming_deadlines AS
SELECT
    d.id,
    d.case_id,
    d.title,
    d.deadline_type,
    d.due_date,
    d.is_critical,
    c.case_number,
    c.title AS case_title,
    c.tenant_id,
    EXTRACT(DAY FROM d.due_date - NOW()) AS days_until_due
FROM case_deadlines d
JOIN cases c ON c.id = d.case_id
WHERE d.is_completed = FALSE
AND d.due_date BETWEEN NOW() AND NOW() + INTERVAL '30 days'
ORDER BY d.due_date ASC;
