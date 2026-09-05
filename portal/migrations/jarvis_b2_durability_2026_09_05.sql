-- JARVIS B2 durability/containment additive migration.
-- DOWN: DROP TABLE IF EXISTS jarvis_credential_state, jarvis_operational_memory,
--       jarvis_action_receipts, jarvis_operations, jarvis_authority_leases CASCADE;

CREATE TABLE IF NOT EXISTS jarvis_authority_leases (
    lease_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    principal_id VARCHAR(255) NOT NULL,
    capability_id VARCHAR(255) NOT NULL,
    capability_version VARCHAR(64) NOT NULL,
    capability_contract_hash VARCHAR(64) NOT NULL,
    registry_revision INTEGER NOT NULL,
    action_id VARCHAR(255) NOT NULL,
    approval_id VARCHAR(255) NOT NULL,
    operation TEXT NOT NULL,
    target TEXT NOT NULL,
    params_hash VARCHAR(64) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    lease_state VARCHAR(32) NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_jarvis_lease_state CHECK (lease_state IN ('ISSUED','CLAIMED','CONSUMED','EXPIRED','REVOKED')),
    CONSTRAINT uq_jarvis_lease_scope_revision UNIQUE (lease_id, revision)
);
CREATE INDEX IF NOT EXISTS ix_jarvis_lease_tenant_state ON jarvis_authority_leases (tenant_id, lease_state);

CREATE TABLE IF NOT EXISTS jarvis_operations (
    operation_id VARCHAR(64) PRIMARY KEY,
    action_id VARCHAR(255) NOT NULL,
    attempt_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    capability_contract_hash VARCHAR(64) NOT NULL,
    lease_id VARCHAR(64) NOT NULL,
    credential_grant_id VARCHAR(64) NOT NULL,
    operation TEXT NOT NULL,
    target TEXT NOT NULL,
    params_hash VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    state VARCHAR(32) NOT NULL,
    provider_operation_ref TEXT,
    latest_verification_status VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL,
    attempted_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    reconciled_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revision INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT ck_jarvis_operation_state CHECK (state IN ('PENDING','ATTEMPTING','AWAITING_VERIFICATION','VERIFIED','FAILED_VERIFIED','UNKNOWN','RECONCILING','RECONCILED','MANUAL_REVIEW_REQUIRED'))
);
CREATE INDEX IF NOT EXISTS ix_jarvis_operation_tenant_state ON jarvis_operations (tenant_id, state);

CREATE TABLE IF NOT EXISTS jarvis_action_receipts (
    receipt_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    receipt_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_receipt_hash VARCHAR(64),
    receipt_payload JSONB NOT NULL,
    finalized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_jarvis_receipt_payload_no_secret CHECK (receipt_payload::text !~* '(api[_-]?key|authorization|password|private[_-]?key|FAKE_B2_SECRET)')
);
CREATE INDEX IF NOT EXISTS ix_jarvis_receipt_tenant_predecessor ON jarvis_action_receipts (tenant_id, previous_receipt_hash);

CREATE TABLE IF NOT EXISTS jarvis_operational_memory (
    memory_event_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    mission_id VARCHAR(255) NOT NULL,
    action_id VARCHAR(255) NOT NULL,
    operation_id VARCHAR(64) NOT NULL,
    receipt_id VARCHAR(64),
    receipt_hash VARCHAR(64),
    capability_id VARCHAR(255) NOT NULL,
    capability_version VARCHAR(64) NOT NULL,
    capability_contract_hash VARCHAR(64) NOT NULL,
    event_class VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    reason_code VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    dedup_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_jarvis_memory_tenant_dedup UNIQUE (tenant_id, dedup_key),
    CONSTRAINT ck_jarvis_memory_status CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED'))
);
CREATE INDEX IF NOT EXISTS ix_jarvis_memory_tenant_status ON jarvis_operational_memory (tenant_id, status);

CREATE TABLE IF NOT EXISTS jarvis_credential_state (
    grant_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    lease_id VARCHAR(64) NOT NULL,
    action_id VARCHAR(255) NOT NULL,
    capability_contract_hash VARCHAR(64) NOT NULL,
    nonce_hash VARCHAR(64) NOT NULL UNIQUE,
    grant_status VARCHAR(32) NOT NULL DEFAULT 'ISSUED',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed_at TIMESTAMPTZ,
    CONSTRAINT ck_jarvis_credential_status CHECK (grant_status IN ('ISSUED','CONSUMED','REVOKED','EXPIRED'))
);
