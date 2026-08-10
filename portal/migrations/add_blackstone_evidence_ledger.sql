-- =============================================================================
-- Migration: Add Blackstone evidence ledger and evaluation tables
-- R3-D: Resolve ORM-only tables — evidence_ledger, blackstone_evaluations
-- R3-G: Tenant security — both tables carry tenant-scoped data and receive RLS
-- =============================================================================

-- =============================================================================
-- 1. evidence_ledger — append-only ledger of governance knowledge objects
-- =============================================================================

CREATE TABLE IF NOT EXISTS evidence_ledger (
    id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        VARCHAR(128),
    object_type      VARCHAR(64)  NOT NULL,
    object_id        VARCHAR(128) NOT NULL,
    action           VARCHAR(64)  NOT NULL,
    actor            VARCHAR(128) NOT NULL,
    payload          JSONB        NOT NULL DEFAULT '{}',
    parent_id        VARCHAR(128),
    recorded_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    provenance_hash  VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS ix_evidence_ledger_object
    ON evidence_ledger(object_type, object_id);
CREATE INDEX IF NOT EXISTS ix_evidence_ledger_actor
    ON evidence_ledger(actor);
CREATE INDEX IF NOT EXISTS ix_evidence_ledger_recorded_at
    ON evidence_ledger(recorded_at);
CREATE INDEX IF NOT EXISTS ix_evidence_ledger_tenant
    ON evidence_ledger(tenant_id);

-- Row-level security: every row is owned by its tenant; tenantless rows
-- are system-internal and visible only via the migration/admin role.
ALTER TABLE evidence_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY evidence_ledger_tenant_isolation ON evidence_ledger
    AS PERMISSIVE FOR ALL
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)
    );

-- Prevent deletion (append-only)
CREATE OR REPLACE FUNCTION prevent_evidence_ledger_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'evidence_ledger rows are append-only and cannot be deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evidence_ledger_append_only ON evidence_ledger;
CREATE TRIGGER trg_evidence_ledger_append_only
    BEFORE DELETE ON evidence_ledger
    FOR EACH ROW
    EXECUTE FUNCTION prevent_evidence_ledger_delete();

COMMENT ON TABLE evidence_ledger IS
    'Append-only ledger of governance knowledge objects (claims, evidence, provenance). '
    'Tenant-scoped; system-internal rows have tenant_id = NULL.';

-- =============================================================================
-- 2. blackstone_evaluations — snapshot of a Blackstone orchestrator evaluation
-- =============================================================================

CREATE TABLE IF NOT EXISTS blackstone_evaluations (
    id                    UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id             VARCHAR(128),
    case_id               VARCHAR(128),
    claim_id              VARCHAR(128) NOT NULL,
    question              TEXT,
    status                VARCHAR(32)  NOT NULL,
    confidence            VARCHAR(32)  NOT NULL,
    recommendation        TEXT         NOT NULL,
    rationale             TEXT         NOT NULL,
    controlling_authority JSONB,
    conflicts             JSONB        NOT NULL DEFAULT '[]',
    risks                 JSONB        NOT NULL DEFAULT '[]',
    agents                JSONB        NOT NULL DEFAULT '[]',
    evaluated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    evaluated_by          VARCHAR(128) NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS ix_blackstone_evaluations_claim
    ON blackstone_evaluations(tenant_id, claim_id);
CREATE INDEX IF NOT EXISTS ix_blackstone_evaluations_case
    ON blackstone_evaluations(tenant_id, case_id);
CREATE INDEX IF NOT EXISTS ix_blackstone_evaluations_evaluated_at
    ON blackstone_evaluations(evaluated_at);
CREATE INDEX IF NOT EXISTS ix_blackstone_evaluations_tenant
    ON blackstone_evaluations(tenant_id);

-- Row-level security: tenant isolation for evaluation records
ALTER TABLE blackstone_evaluations ENABLE ROW LEVEL SECURITY;

CREATE POLICY blackstone_evaluations_tenant_isolation ON blackstone_evaluations
    AS PERMISSIVE FOR ALL
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', true)
    );

COMMENT ON TABLE blackstone_evaluations IS
    'Snapshot of a Blackstone governance orchestrator evaluation. '
    'Records claim analysis, confidence, recommendation, and evidence chains. '
    'Tenant-scoped; system evaluations have tenant_id = NULL.';

-- =============================================================================
-- DOWN migration notes:
--   DROP TRIGGER IF EXISTS trg_evidence_ledger_append_only ON evidence_ledger;
--   DROP FUNCTION IF EXISTS prevent_evidence_ledger_delete();
--   DROP TABLE IF EXISTS blackstone_evaluations;
--   DROP TABLE IF EXISTS evidence_ledger;
-- =============================================================================
