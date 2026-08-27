-- =============================================================================
-- Gate 4B: durable restricted external-action sandbox authority
-- Only sandbox.echo-write-v1 is eligible for certification at this gate.
-- No production connector or credential material is represented here.
-- =============================================================================

CREATE TABLE IF NOT EXISTS external_action_intents (
    id                         VARCHAR(36) PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id               UUID NOT NULL REFERENCES users(id),
    service_identity_id        VARCHAR(36) NOT NULL REFERENCES governed_service_identities(id),
    mission_id                 UUID,
    schedule_id                VARCHAR(36),
    adapter_id                 VARCHAR(120) NOT NULL,
    operation_id               VARCHAR(120) NOT NULL,
    environment                VARCHAR(32) NOT NULL,
    destination                TEXT NOT NULL,
    risk_class                 VARCHAR(8) NOT NULL,
    payload                    JSONB NOT NULL,
    canonical_payload_hash     VARCHAR(64) NOT NULL,
    request_hash               VARCHAR(64) NOT NULL,
    payload_summary            TEXT NOT NULL,
    idempotency_key            VARCHAR(128) NOT NULL,
    credential_ref             TEXT,
    status                     VARCHAR(48) NOT NULL,
    preflight_receipt_hash     VARCHAR(64),
    provider_request_hash      VARCHAR(64),
    provider_response_hash     VARCHAR(64),
    provider_confirmation_id   VARCHAR(128),
    claimed_by                 VARCHAR(128),
    claimed_at                 TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_external_action_intent_environment
        CHECK (environment IN ('sandbox')),
    CONSTRAINT ck_external_action_intent_risk
        CHECK (risk_class IN ('E1')),
    CONSTRAINT ck_external_action_intent_status
        CHECK (status IN (
            'DRAFT', 'PREFLIGHTED', 'APPROVAL_REQUIRED', 'APPROVED',
            'CLAIMED', 'EXECUTING', 'SUCCEEDED', 'FAILED',
            'UNKNOWN_REQUIRES_RECONCILIATION', 'CANCELLED', 'BLOCKED',
            'COMPENSATED'
        )),
    CONSTRAINT uq_external_action_intent_idempotency
        UNIQUE (tenant_id, principal_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_external_action_intents_tenant_status
    ON external_action_intents(tenant_id, status, created_at);

CREATE TABLE IF NOT EXISTS external_action_approvals (
    id                         VARCHAR(36) PRIMARY KEY,
    intent_id                  VARCHAR(36) NOT NULL REFERENCES external_action_intents(id) ON DELETE CASCADE,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id               UUID NOT NULL REFERENCES users(id),
    adapter_id                 VARCHAR(120) NOT NULL,
    operation_id               VARCHAR(120) NOT NULL,
    destination                TEXT NOT NULL,
    canonical_payload_hash     VARCHAR(64) NOT NULL,
    approval_nonce             VARCHAR(128) NOT NULL,
    status                     VARCHAR(24) NOT NULL,
    approved_at                TIMESTAMPTZ NOT NULL,
    expires_at                 TIMESTAMPTZ NOT NULL,
    revoked_at                 TIMESTAMPTZ,
    revocation_reason          TEXT,
    CONSTRAINT ck_external_action_approval_status
        CHECK (status IN ('APPROVED', 'REVOKED')),
    CONSTRAINT uq_external_action_approval_nonce
        UNIQUE (tenant_id, principal_id, approval_nonce),
    CONSTRAINT uq_external_action_approval_intent
        UNIQUE (intent_id)
);

CREATE TABLE IF NOT EXISTS external_action_evidence (
    id                         UUID PRIMARY KEY,
    intent_id                  VARCHAR(36) NOT NULL REFERENCES external_action_intents(id) ON DELETE CASCADE,
    sequence_no                INTEGER NOT NULL,
    event_type                 VARCHAR(80) NOT NULL,
    event_payload              JSONB NOT NULL,
    previous_event_hash        VARCHAR(64),
    event_hash                 VARCHAR(64) NOT NULL,
    created_at                 TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_external_action_evidence_sequence
        UNIQUE (intent_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS ix_external_action_evidence_intent_sequence
    ON external_action_evidence(intent_id, sequence_no);

CREATE TABLE IF NOT EXISTS external_execution_kill_switches (
    scope_key                  VARCHAR(180) PRIMARY KEY,
    tenant_id                  UUID REFERENCES tenants(id) ON DELETE CASCADE,
    adapter_id                 VARCHAR(120),
    active                     BOOLEAN NOT NULL DEFAULT FALSE,
    reason                     TEXT,
    updated_by                 UUID REFERENCES users(id),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sandbox_echo_effects (
    id                         UUID PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    destination                TEXT NOT NULL,
    idempotency_key            VARCHAR(128) NOT NULL,
    payload                    JSONB NOT NULL,
    payload_hash               VARCHAR(64) NOT NULL,
    confirmation_id            VARCHAR(128) NOT NULL,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    compensated_at             TIMESTAMPTZ,
    CONSTRAINT uq_sandbox_echo_effect_idempotency
        UNIQUE (tenant_id, idempotency_key)
);

COMMENT ON TABLE external_action_intents IS
    'Gate 4B durable external-action authority envelope. Sandbox E1 only.';
COMMENT ON TABLE sandbox_echo_effects IS
    'Disposable synthetic provider-side effects for sandbox.echo-write-v1 certification only.';
