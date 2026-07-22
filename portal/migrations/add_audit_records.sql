-- =============================================================================
-- Migration: Add audit_records table
-- Phase 1, Step 4: AuditRecord immutable model + Packet ↔ Audit linkage
-- Engineering Doctrines: ED-003 (immutable evidence), ED-005 (single source of truth), ED-007 (regression protection)
-- Governance: Advances GI-B-2026-001, supports Test 4 (packet↔snapshot consistency)
-- =============================================================================

-- UP Migration
CREATE TABLE IF NOT EXISTS audit_records (
    audit_id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_id           UUID            NOT NULL REFERENCES evidence_snapshots(snapshot_id) ON DELETE RESTRICT,
    evidence_hash         VARCHAR(64)     NOT NULL,
    packet_id             UUID            NOT NULL,
    packet_hash           VARCHAR(64)     NOT NULL,
    packet_version        INTEGER         NOT NULL,
    serialization_version INTEGER         NOT NULL DEFAULT 1,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by            UUID            NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    verification_status   VARCHAR(20)     NOT NULL DEFAULT 'verified'
        CHECK (verification_status IN ('verified', 'failed')),
    verification_details  VARCHAR(512)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_records_snapshot_id
    ON audit_records(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_audit_records_packet_id
    ON audit_records(packet_id);

CREATE INDEX IF NOT EXISTS idx_audit_records_created_at
    ON audit_records(created_at);

CREATE INDEX IF NOT EXISTS idx_audit_records_verification_status
    ON audit_records(verification_status);

-- Composite index for tracing packet back to snapshot
CREATE INDEX IF NOT EXISTS idx_audit_records_packet_snapshot
    ON audit_records(packet_id, snapshot_id);

-- Immutability enforcement: prevent UPDATE and DELETE via trigger
-- (Defense in depth — the application layer also rejects these operations)
-- Audit records are append-only. Once created, they are permanent.

CREATE OR REPLACE FUNCTION prevent_audit_record_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_records rows cannot be deleted (ED-003: immutable evidence, ED-007: regression protection)';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'audit_records rows cannot be modified. They are immutable and permanent (ED-003)';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_record_immutable ON audit_records;
CREATE TRIGGER trg_audit_record_immutable
    BEFORE UPDATE OR DELETE ON audit_records
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_record_mutation();

-- Comment documenting the immutability contract
COMMENT ON TABLE audit_records IS
    'Immutable, append-only audit trail linking rendered packets to their source snapshots. '
    'ED-003: immutable evidence ≠ mutable presentation. ED-007: regression protection. '
    'Rows are created once and never modified or deleted. '
    'See Engineering Baseline EB-2026-001 and PHASE_1_SPECIFICATION.md.';

-- =============================================================================
-- DOWN Migration (for reversibility)
-- =============================================================================
-- To reverse this migration:
--   DROP TRIGGER IF EXISTS trg_audit_record_immutable ON audit_records;
--   DROP FUNCTION IF EXISTS prevent_audit_record_mutation();
--   DROP TABLE IF EXISTS audit_records;
-- =============================================================================