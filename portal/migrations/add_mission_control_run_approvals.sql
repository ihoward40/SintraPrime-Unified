-- Run-bound Principal approval artifact
--
-- One durable approval per (tenant_id, run_id). The approval table is the
-- authoritative state for approval; AuditLog is evidence only.
--
-- Inline DOWN migration:
-- DROP TABLE IF EXISTS mission_control_run_approvals;

CREATE TABLE IF NOT EXISTS mission_control_run_approvals (
    approval_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_user_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    run_id             UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,

    decision           VARCHAR(20) NOT NULL,  -- APPROVED | REJECTED
    status             VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING | CONSUMED | REJECTED
    input_data_hash    VARCHAR(64) NOT NULL,

    mission_id         UUID,
    reason_code        VARCHAR(80),

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    consumed_at        TIMESTAMPTZ,
    execution_ref      VARCHAR(128),

    CONSTRAINT uq_run_approvals_tenant_run UNIQUE (tenant_id, run_id),
    CONSTRAINT chk_run_approval_decision CHECK (decision IN ('APPROVED', 'REJECTED')),
    CONSTRAINT chk_run_approval_status CHECK (status IN ('PENDING', 'CONSUMED', 'REJECTED'))
);

CREATE INDEX IF NOT EXISTS ix_run_approvals_tenant_run
    ON mission_control_run_approvals(tenant_id, run_id);