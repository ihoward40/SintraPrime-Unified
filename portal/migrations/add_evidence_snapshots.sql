-- =============================================================================
-- Migration: Add evidence_snapshots table
-- Phase 1, Steps 1-2: EvidenceSnapshot immutable model + Hash Boundary
-- Engineering Doctrines: ED-003 (immutable evidence), ED-005 (single source of truth)
-- Governance: Advances GI-B-2026-001
-- =============================================================================

-- UP Migration
CREATE TABLE IF NOT EXISTS evidence_snapshots (
    snapshot_id     UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id         UUID            NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    evidence_hash   VARCHAR(64)     NOT NULL,
    manifest_hash   VARCHAR(64)     NOT NULL,
    snapshot_version INTEGER        NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      UUID            NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    evidence_count  INTEGER         NOT NULL DEFAULT 0,
    status          VARCHAR(20)     NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'superseded', 'archived'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_evidence_snapshots_case_id
    ON evidence_snapshots(case_id);

CREATE INDEX IF NOT EXISTS idx_evidence_snapshots_case_status
    ON evidence_snapshots(case_id, status);

CREATE INDEX IF NOT EXISTS idx_evidence_snapshots_created_at
    ON evidence_snapshots(created_at);

-- Enforce: at most one ACTIVE snapshot per case
CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_snapshots_one_active_per_case
    ON evidence_snapshots(case_id)
    WHERE status = 'active';

-- Immutability enforcement: prevent UPDATE and DELETE via trigger
-- (Defense in depth — the application layer also rejects these operations)

CREATE OR REPLACE FUNCTION prevent_evidence_snapshot_mutation()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow only status transitions: active→superseded, active→archived, superseded→archived
    -- All other modifications are blocked
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'evidence_snapshots rows cannot be deleted (ED-003: immutable evidence)';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Allow only valid forward status transitions
        IF (OLD.status = 'active' AND NEW.status IN ('superseded', 'archived'))
           OR (OLD.status = 'superseded' AND NEW.status = 'archived')
        THEN
            -- Verify no other field changed
            IF NEW.snapshot_id = OLD.snapshot_id
               AND NEW.case_id = OLD.case_id
               AND NEW.evidence_hash = OLD.evidence_hash
               AND NEW.manifest_hash = OLD.manifest_hash
               AND NEW.snapshot_version = OLD.snapshot_version
               AND NEW.created_at = OLD.created_at
               AND NEW.created_by = OLD.created_by
               AND NEW.evidence_count = OLD.evidence_count
            THEN
                RETURN NEW;
            ELSE
                RAISE EXCEPTION 'evidence_snapshots rows are immutable. Only status transitions are allowed (ED-003)';
            END IF;
        ELSE
            RAISE EXCEPTION 'Invalid status transition: % → %. Allowed: active→superseded, active→archived, superseded→archived (ED-003)',
                OLD.status, NEW.status;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evidence_snapshot_immutable ON evidence_snapshots;
CREATE TRIGGER trg_evidence_snapshot_immutable
    BEFORE UPDATE OR DELETE ON evidence_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION prevent_evidence_snapshot_mutation();

-- Comment documenting the immutability contract
COMMENT ON TABLE evidence_snapshots IS
    'Immutable, append-only evidence snapshots. ED-003: immutable evidence ≠ mutable presentation. '
    'Rows are never modified (except forward status transitions) or deleted. '
    'See Engineering Baseline EB-2026-001.';

-- =============================================================================
-- DOWN Migration (for reversibility)
-- =============================================================================
-- To reverse this migration:
--   DROP TRIGGER IF EXISTS trg_evidence_snapshot_immutable ON evidence_snapshots;
--   DROP FUNCTION IF EXISTS prevent_evidence_snapshot_mutation();
--   DROP TABLE IF EXISTS evidence_snapshots;
-- =============================================================================
