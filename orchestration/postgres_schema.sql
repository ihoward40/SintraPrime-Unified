-- A2A C10-R2 PostgreSQL schema draft
-- Design only: not an executable migration and does not enable external actions.
-- PostgreSQL 15+ recommended. Apply tenant RLS policies in deployment migrations.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE a2a_approval_status AS ENUM ('issued', 'used', 'revoked', 'expired');
CREATE TYPE a2a_outbox_status AS ENUM ('pending', 'validated', 'claimed', 'blocked', 'dispatched', 'failed', 'expired', 'dlq');
CREATE TYPE a2a_delivery_status AS ENUM ('sent', 'received', 'acked', 'reclaimed', 'retried', 'dlq');

CREATE TABLE a2a_audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    sequence BIGINT GENERATED ALWAYS AS IDENTITY,
    event_type TEXT NOT NULL,
    mission_id TEXT,
    actor_agent_id TEXT,
    recipient_agent_id TEXT,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    reason_code TEXT,
    reason_detail TEXT,
    user_approval TEXT,
    external_action_taken BOOLEAN NOT NULL DEFAULT FALSE CHECK (external_action_taken = FALSE),
    payload_hash TEXT,
    attachment_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_output_hash TEXT,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    idempotency_key TEXT,
    UNIQUE (tenant_id, idempotency_key),
    UNIQUE (tenant_id, sequence)
);

CREATE TABLE a2a_approval_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    event_type a2a_approval_status NOT NULL,
    approved_by TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    approved_output_id TEXT NOT NULL,
    final_content_hash TEXT NOT NULL,
    attachment_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    signature TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    reason TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, receipt_id, event_id)
);

CREATE TABLE a2a_approval_current_state (
    tenant_id TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    status a2a_approval_status NOT NULL,
    approved_by TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    approved_output_id TEXT NOT NULL,
    final_content_hash TEXT NOT NULL,
    attachment_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    signature TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_by TEXT,
    consumed_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, receipt_id)
);

CREATE TABLE a2a_outbox_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    outbox_id UUID NOT NULL,
    event_type a2a_outbox_status NOT NULL,
    receipt_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    attachment_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    worker_id TEXT,
    claim_version BIGINT,
    reason TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, outbox_id, event_id)
);

CREATE TABLE a2a_outbox_current_state (
    tenant_id TEXT NOT NULL,
    outbox_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    status a2a_outbox_status NOT NULL,
    receipt_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    attachment_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    lease_owner TEXT,
    lease_until TIMESTAMPTZ,
    claim_version BIGINT NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, outbox_id),
    UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE a2a_delivery_attempts (
    delivery_id UUID NOT NULL,
    tenant_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    status a2a_delivery_status NOT NULL,
    payload_hash TEXT NOT NULL,
    redis_namespace TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, delivery_id, attempt_number),
    UNIQUE (tenant_id, delivery_id, status, attempt_number)
);

CREATE TABLE a2a_dlq_records (
    dlq_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    delivery_id UUID NOT NULL,
    message_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    retry_count INTEGER NOT NULL CHECK (retry_count >= 0),
    payload_hash TEXT NOT NULL,
    reason TEXT NOT NULL,
    redis_namespace TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, delivery_id)
);

CREATE INDEX a2a_audit_tenant_time_idx ON a2a_audit_events (tenant_id, occurred_at);
CREATE INDEX a2a_approval_expiry_idx ON a2a_approval_current_state (tenant_id, expires_at) WHERE status = 'issued';
CREATE INDEX a2a_outbox_claim_idx ON a2a_outbox_current_state (tenant_id, status, lease_until, created_at);
CREATE INDEX a2a_delivery_message_idx ON a2a_delivery_attempts (tenant_id, message_id);

-- Production migrations must enable RLS and create policies using app.tenant_id.
-- Example policy shape (adapt per deployment role):
-- ALTER TABLE a2a_audit_events ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_audit_policy ON a2a_audit_events
--   USING (tenant_id = current_setting('app.tenant_id', true));

-- Required application transaction patterns:
-- 1. Approval consume: SELECT ... FROM a2a_approval_current_state
--    WHERE tenant_id = :tenant AND receipt_id = :receipt FOR UPDATE;
-- 2. Outbox claim: SELECT ... FROM a2a_outbox_current_state
--    WHERE tenant_id = :tenant AND status IN ('pending','validated')
--      AND (lease_until IS NULL OR lease_until < now())
--    ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT :n;
-- 3. All projection changes must insert the corresponding immutable event row
--    and audit row in the same transaction.
