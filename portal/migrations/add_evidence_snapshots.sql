-- =============================================================================
-- Migration: Add evidence_snapshots table
-- Phase 1, Step 1: EvidenceSnapshot immutable model
-- Engineering Doctrines: ED-003 (immutable evidence), ED-005 (single source of truth)
-- Governance: Advances GI-B-2026-001
-- =============================================================================

-- UP Migration
CREATE TABLE IF NOT EXISTS evidence_snapshots (
    snapshot_id     VARCHAR(36)     PRIMARY KEY,
    case_id         VARCHAR(36)     NOT NULL REFERENCES cases(id),
    evidence_hash   VARCHAR(64)     NOT NULL,
    manifest_hash   VARCHAR(64)     NOT NULL,
    snapshot_version INTEGER        NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(36)     NOT NULL REFERENCES users(id),
    evidence_count  INTEGER         NOT NULL DEFAULT 0,
    status          VARCHAR(20)     NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'superseded'))
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
    -- Allow only status transition from 'active' to 'superseded'
    -- All other modifications are blocked
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'evidence_snapshots rows cannot be deleted (ED-003: immutable evidence)';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Only allow status change active → superseded
        IF NEW.status = 'superseded' AND OLD.status = 'active'
           AND NEW.snapshot_id = OLD.snapshot_id
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
            RAISE EXCEPTION 'evidence_snapshots rows are immutable. Only status active→superseded is allowed (ED-003)';
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
    'Rows are never modified (except status active→superseded) or deleted. '
    'See Engineering Baseline EB-2026-001.';

-- =============================================================================
-- DOWN Migration (for reversibility — required by Step 1 acceptance criteria)
-- =============================================================================
-- To reverse this migration:
--   DROP TRIGGER IF EXISTS trg_evidence_snapshot_immutable ON evidence_snapshots;
--   DROP FUNCTION IF EXISTS prevent_evidence_snapshot_mutation();
--   DROP TABLE IF EXISTS evidence_snapshots;
-- =============================================================================
