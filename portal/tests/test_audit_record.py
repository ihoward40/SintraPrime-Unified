"""
Tests for AuditService and AuditRecord.

Engineering Doctrines:
  ED-001: Trust Prerequisite — every claim backed by reproducible evidence
  ED-002: Reproducible Evidence — every test verifiable by running pytest
  ED-003: Immutable evidence ≠ mutable presentation
  ED-007: Regression protection — prior tests remain valid

Test 4: packet↔snapshot consistency verification.
"""

from datetime import UTC, datetime

import pytest

from portal.services.evidence_audit_service import (
    AuditRecordNotFoundError,
    AuditRecordValue,
    AuditService,
    AuditVerificationError,
    ImmutableAuditError,
)


class TestAuditRecordValue:
    """Test the AuditRecordValue frozen dataclass."""

    def test_audit_record_value_is_frozen(self):
        """Verify that AuditRecordValue instances are immutable."""
        record = AuditRecordValue(
            audit_id="audit-1",
            snapshot_id="snap-1",
            evidence_hash="hash-evidence-1",
            packet_id="packet-1",
            packet_hash="hash-packet-1",
            packet_version=1,
            serialization_version=1,
            created_at=datetime.now(UTC),
            created_by="user-1",
            verification_status="verified",
            verification_details=None,
        )
        with pytest.raises(AttributeError):
            record.audit_id = "audit-2"

    def test_audit_record_value_to_dict(self):
        """Verify to_dict serialization is deterministic."""
        now = datetime.now(UTC)
        record = AuditRecordValue(
            audit_id="audit-1",
            snapshot_id="snap-1",
            evidence_hash="hash-evidence-1",
            packet_id="packet-1",
            packet_hash="hash-packet-1",
            packet_version=1,
            serialization_version=1,
            created_at=now,
            created_by="user-1",
            verification_status="verified",
            verification_details=None,
        )
        d = record.to_dict()
        assert d["audit_id"] == "audit-1"
        assert d["snapshot_id"] == "snap-1"
        assert d["evidence_hash"] == "hash-evidence-1"
        assert d["packet_id"] == "packet-1"
        assert d["packet_hash"] == "hash-packet-1"
        assert d["packet_version"] == 1
        assert d["serialization_version"] == 1
        assert d["created_by"] == "user-1"
        assert d["verification_status"] == "verified"
        assert d["verification_details"] is None
        # Verify timestamp is ISO format
        assert isinstance(d["created_at"], str)
        assert "T" in d["created_at"]

    def test_audit_record_value_to_dict_alphabetical_keys(self):
        """Verify to_dict keys are in alphabetical order for reproducibility."""
        record = AuditRecordValue(
            audit_id="audit-1",
            snapshot_id="snap-1",
            evidence_hash="hash-evidence",
            packet_id="packet-1",
            packet_hash="hash-packet",
            packet_version=1,
            serialization_version=1,
            created_at=datetime.now(UTC),
            created_by="user-1",
            verification_status="verified",
            verification_details=None,
        )
        d = record.to_dict()
        keys = list(d.keys())
        assert keys == sorted(keys), f"Keys not alphabetical: {keys}"

    def test_audit_record_value_with_verification_details(self):
        """Verify that verification_details are preserved."""
        record = AuditRecordValue(
            audit_id="audit-1",
            snapshot_id="snap-1",
            evidence_hash="hash-evidence",
            packet_id="packet-1",
            packet_hash="hash-packet-wrong",
            packet_version=1,
            serialization_version=1,
            created_at=datetime.now(UTC),
            created_by="user-1",
            verification_status="failed",
            verification_details="Packet hash mismatch: packet_hash=abc, evidence_hash=def",
        )
        d = record.to_dict()
        assert d["verification_status"] == "failed"
        assert "hash mismatch" in d["verification_details"]


class TestAuditServiceCreate:
    """Test AuditService.create() — append-only audit record creation."""

    def test_create_audit_record_basic(self):
        """Create a basic audit record."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-evidence-1",
            packet_id="packet-1",
            packet_hash="hash-evidence-1",  # Match for verification
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=True,
        )
        assert record.audit_id is not None
        assert record.snapshot_id == "snap-1"
        assert record.evidence_hash == "hash-evidence-1"
        assert record.packet_id == "packet-1"
        assert record.packet_hash == "hash-evidence-1"
        assert record.verification_status == "verified"
        assert record.verification_details is None

    def test_create_audit_record_unique_ids(self):
        """Verify each audit record gets a unique ID."""
        service = AuditService()
        r1 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        r2 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-2",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        assert r1.audit_id != r2.audit_id

    def test_create_audit_record_timestamp_set(self):
        """Verify created_at timestamp is set."""
        before = datetime.now(UTC)
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        after = datetime.now(UTC)
        assert before <= record.created_at <= after

    def test_create_audit_record_verify_packet_true_match(self):
        """When verify_packet=True and hashes match, status is 'verified'."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="abc123",
            packet_id="packet-1",
            packet_hash="abc123",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=True,
        )
        assert record.verification_status == "verified"
        assert record.verification_details is None

    def test_create_audit_record_verify_packet_true_mismatch_raises(self):
        """When verify_packet=True and hashes don't match, raises AuditVerificationError."""
        service = AuditService()
        with pytest.raises(AuditVerificationError) as exc:
            service.create(
                snapshot_id="snap-1",
                evidence_hash="hash-evidence",
                packet_id="packet-1",
                packet_hash="hash-packet-different",
                packet_version=1,
                serialization_version=1,
                created_by="user-1",
                verify_packet=True,
            )
        assert "mismatch" in str(exc.value).lower()

    def test_create_audit_record_verify_packet_false_mismatch(self):
        """When verify_packet=False, record is created even if hashes don't match."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-evidence",
            packet_id="packet-1",
            packet_hash="hash-packet-different",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=False,
        )
        assert record.verification_status == "verified"  # Still created
        assert record.packet_hash == "hash-packet-different"

    def test_create_increments_count(self):
        """Verify count increments with each create."""
        service = AuditService()
        assert service.count == 0
        service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        assert service.count == 1
        service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-2",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        assert service.count == 2


class TestAuditServiceRetrieval:
    """Test AuditService.get*() — retrieval operations."""

    def test_get_audit_record_by_id(self):
        """Retrieve an audit record by audit_id."""
        service = AuditService()
        created = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        retrieved = service.get(created.audit_id)
        assert retrieved.audit_id == created.audit_id
        assert retrieved.snapshot_id == "snap-1"

    def test_get_audit_record_not_found(self):
        """Raise AuditRecordNotFoundError for nonexistent record."""
        service = AuditService()
        with pytest.raises(AuditRecordNotFoundError):
            service.get("nonexistent-id")

    def test_get_by_packet_id(self):
        """Retrieve an audit record by packet_id."""
        service = AuditService()
        service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        retrieved = service.get_by_packet_id("packet-1")
        assert retrieved is not None
        assert retrieved.packet_id == "packet-1"

    def test_get_by_packet_id_not_found(self):
        """Return None for nonexistent packet_id."""
        service = AuditService()
        retrieved = service.get_by_packet_id("nonexistent-packet")
        assert retrieved is None

    def test_get_by_snapshot_id(self):
        """Retrieve all audit records for a snapshot."""
        service = AuditService()
        r1 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        r2 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-2",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        records = service.get_by_snapshot_id("snap-1")
        assert len(records) == 2
        assert records[0].audit_id in [r1.audit_id, r2.audit_id]
        assert records[1].audit_id in [r1.audit_id, r2.audit_id]

    def test_get_by_snapshot_id_empty(self):
        """Return empty list for snapshot with no audit records."""
        service = AuditService()
        records = service.get_by_snapshot_id("snap-nonexistent")
        assert records == []

    def test_get_by_snapshot_id_ordered_by_time(self):
        """Verify records are ordered by creation time."""
        service = AuditService()
        service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-2",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        records = service.get_by_snapshot_id("snap-1")
        assert records[0].created_at <= records[1].created_at


class TestAuditServiceVerification:
    """Test AuditService verification — Test 4: packet↔snapshot consistency."""

    def test_verify_packet_against_evidence_match(self):
        """Test 4.1: Verify packet hash matches evidence hash."""
        service = AuditService()
        evidence_hash = "abc123def456"
        packet_hash = "abc123def456"
        assert service.verify_packet_against_evidence(packet_hash, evidence_hash) is True

    def test_verify_packet_against_evidence_mismatch(self):
        """Test 4.2: Detect packet hash mismatch against evidence hash."""
        service = AuditService()
        evidence_hash = "abc123def456"
        packet_hash = "xyz789uvw123"
        assert service.verify_packet_against_evidence(packet_hash, evidence_hash) is False

    def test_verify_packet_against_evidence_case_sensitive(self):
        """Test 4.3: Hash verification is case-sensitive."""
        service = AuditService()
        # SHA-256 hashes are lowercase hex; verify case matters
        evidence_hash = "abc123"
        packet_hash = "ABC123"
        assert service.verify_packet_against_evidence(packet_hash, evidence_hash) is False

    def test_verify_packet_against_evidence_empty_hashes(self):
        """Test 4.4: Empty hashes are equal (edge case)."""
        service = AuditService()
        assert service.verify_packet_against_evidence("", "") is True

    def test_create_with_verification_creates_verified_record(self):
        """Test 4.5: Create with matching hashes creates 'verified' record."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-abc123",
            packet_id="packet-1",
            packet_hash="hash-abc123",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=True,
        )
        assert record.verification_status == "verified"
        # Verify consistency
        assert service.verify_packet_against_evidence(
            record.packet_hash, record.evidence_hash
        ) is True

    def test_create_with_verification_raises_on_mismatch(self):
        """Test 4.6: Create with mismatched hashes raises verification error."""
        service = AuditService()
        with pytest.raises(AuditVerificationError):
            service.create(
                snapshot_id="snap-1",
                evidence_hash="hash-evidence",
                packet_id="packet-1",
                packet_hash="hash-packet-mismatch",
                packet_version=1,
                serialization_version=1,
                created_by="user-1",
                verify_packet=True,
            )

    def test_packet_snapshot_roundtrip_verification(self):
        """Test 4.7: Full roundtrip: create packet, create audit, verify."""
        service = AuditService()
        # Simulate packet rendering
        evidence_hash = "sha256_evidence_abc123"
        packet_id = "packet_rendering_id"
        packet_hash = evidence_hash  # Ideally they match

        # Create audit record linking packet to snapshot
        service.create(
            snapshot_id="snap-1",
            evidence_hash=evidence_hash,
            packet_id=packet_id,
            packet_hash=packet_hash,
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=True,
        )

        # Retrieve and verify
        retrieved = service.get_by_packet_id(packet_id)
        assert retrieved is not None
        assert retrieved.verification_status == "verified"
        assert (
            service.verify_packet_against_evidence(
                retrieved.packet_hash, retrieved.evidence_hash
            )
            is True
        )


class TestAuditServiceImmutability:
    """Test immutability — ED-003: audit records cannot be modified."""

    def test_update_raises_immutable_error(self):
        """Calling update() always raises ImmutableAuditError."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        with pytest.raises(ImmutableAuditError):
            service.update(record.audit_id, verification_status="failed")

    def test_delete_raises_immutable_error(self):
        """Calling delete() always raises ImmutableAuditError."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        with pytest.raises(ImmutableAuditError):
            service.delete(record.audit_id)

    def test_immutable_error_message_clear(self):
        """Verify error messages are clear about immutability."""
        service = AuditService()
        record = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        with pytest.raises(ImmutableAuditError) as exc:
            service.delete(record.audit_id)
        # Message should reference immutability concept (either "immutable" or "append-only")
        msg_lower = str(exc.value).lower()
        assert ("immutable" in msg_lower or "append-only" in msg_lower)
        assert "ED-003" in str(exc.value) or "ED-007" in str(exc.value)


class TestAuditServiceRegressionProtection:
    """Test ED-007: regression protection across steps."""

    def test_created_records_persist(self):
        """ED-007: Previously created records remain valid and accessible."""
        service = AuditService()
        # Create Step 1-3 records (simulate prior work)
        r1 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        # Create Step 4 records (new work)
        r2 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-2",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        # Verify prior work still accessible
        assert service.get(r1.audit_id).audit_id == r1.audit_id
        assert service.get(r2.audit_id).audit_id == r2.audit_id
        assert service.count == 2

    def test_verification_status_stable(self):
        """ED-007: Verification status does not change on retrieval."""
        service = AuditService()
        created = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
            verify_packet=True,
        )
        original_status = created.verification_status
        retrieved = service.get(created.audit_id)
        assert retrieved.verification_status == original_status


class TestAuditServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_many_records_for_one_snapshot(self):
        """Handle multiple audit records for a single snapshot."""
        service = AuditService()
        snapshot_id = "snap-1"
        evidence_hash = "hash-evidence"
        for i in range(10):
            service.create(
                snapshot_id=snapshot_id,
                evidence_hash=evidence_hash,
                packet_id=f"packet-{i}",
                packet_hash=evidence_hash,
                packet_version=1,
                serialization_version=1,
                created_by="user-1",
            )
        records = service.get_by_snapshot_id(snapshot_id)
        assert len(records) == 10

    def test_long_verification_details(self):
        """Handle long verification detail strings."""
        long_details = "x" * 500
        record = AuditRecordValue(
            audit_id="audit-1",
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-2",
            packet_version=1,
            serialization_version=1,
            created_at=datetime.now(UTC),
            created_by="user-1",
            verification_status="failed",
            verification_details=long_details,
        )
        d = record.to_dict()
        assert d["verification_details"] == long_details
        assert len(d["verification_details"]) == 500

    def test_serialization_version_tracking(self):
        """Verify serialization_version is tracked and retrievable."""
        service = AuditService()
        record_v1 = service.create(
            snapshot_id="snap-1",
            evidence_hash="hash-1",
            packet_id="packet-1",
            packet_hash="hash-1",
            packet_version=1,
            serialization_version=1,
            created_by="user-1",
        )
        assert record_v1.serialization_version == 1
        retrieved = service.get(record_v1.audit_id)
        assert retrieved.serialization_version == 1
