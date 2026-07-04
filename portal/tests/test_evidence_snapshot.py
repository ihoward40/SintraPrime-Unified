"""
Tests for EvidenceSnapshot model and service.

Phase 1 — Step 1: Immutable EvidenceSnapshot Model

Engineering Doctrines tested:
  ED-003: Immutable evidence ≠ mutable presentation
  ED-005: Single source of truth

Acceptance criteria verified:
  - Immutable after creation
  - Append-only (no delete)
  - Reproducible serialization
  - Unique Snapshot IDs
  - Version monotonicity
  - Supersession behavior
"""

import json
import uuid

import pytest

# Import the service directly (no database dependency for Step 1)
# The service module is self-contained with no external imports beyond stdlib
import sys
import os

# Add the repo root to path so we can import the service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portal.services.evidence_snapshot_service import (
    EvidenceSnapshotService,
    ImmutableSnapshotError,
    SnapshotNotFoundError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    """Fresh EvidenceSnapshotService for each test."""
    return EvidenceSnapshotService()


@pytest.fixture
def sample_case_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_evidence_hash():
    """A deterministic sample hash for testing."""
    return "a" * 64  # 64-char hex string (valid SHA-256 length)


@pytest.fixture
def sample_manifest_hash():
    return "b" * 64


# ── Test: Creation ────────────────────────────────────────────────────────────

class TestSnapshotCreation:
    """Verify snapshots can be created with correct fields."""

    def test_create_snapshot_returns_record(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Creating a snapshot returns a SnapshotRecord with all fields set."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
            evidence_count=5,
        )

        assert record.case_id == sample_case_id
        assert record.evidence_hash == sample_evidence_hash
        assert record.manifest_hash == sample_manifest_hash
        assert record.created_by == sample_user_id
        assert record.evidence_count == 5
        assert record.snapshot_version == 1
        assert record.status == "active"
        assert record.snapshot_id is not None
        assert record.created_at is not None

    def test_create_snapshot_first_version_is_1(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """First snapshot for a case should be version 1."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert record.snapshot_version == 1

    def test_create_snapshot_default_evidence_count_is_0(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Default evidence_count should be 0."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert record.evidence_count == 0


# ── Test: Unique IDs ─────────────────────────────────────────────────────────

class TestUniqueSnapshotIDs:
    """Every snapshot must get a unique ID."""

    def test_two_snapshots_have_different_ids(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Two snapshots created for the same case must have different IDs."""
        r1 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        r2 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert r1.snapshot_id != r2.snapshot_id

    def test_ten_snapshots_all_unique(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """10 snapshots across different cases all have unique IDs."""
        ids = set()
        for i in range(10):
            record = service.create(
                case_id=str(uuid.uuid4()),
                evidence_hash=sample_evidence_hash,
                manifest_hash=sample_manifest_hash,
                created_by=sample_user_id,
            )
            ids.add(record.snapshot_id)
        assert len(ids) == 10


# ── Test: Immutability ────────────────────────────────────────────────────────

class TestSnapshotImmutability:
    """EvidenceSnapshots must be immutable after creation (ED-003)."""

    def test_update_raises_immutable_error(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Attempting to update a snapshot must raise ImmutableSnapshotError."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        with pytest.raises(ImmutableSnapshotError, match="Cannot modify"):
            service.update(record.snapshot_id, evidence_hash="changed")

    def test_delete_raises_immutable_error(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Attempting to delete a snapshot must raise ImmutableSnapshotError."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        with pytest.raises(ImmutableSnapshotError, match="Cannot delete"):
            service.delete(record.snapshot_id)

    def test_frozen_dataclass_prevents_field_mutation(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """SnapshotRecord is a frozen dataclass — attribute assignment must fail."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        with pytest.raises(AttributeError):
            record.evidence_hash = "tampered"

        with pytest.raises(AttributeError):
            record.status = "tampered"

        with pytest.raises(AttributeError):
            record.snapshot_version = 999

    def test_snapshot_data_unchanged_after_reload(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Create → reload → verify all fields match exactly."""
        original = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
            evidence_count=7,
        )

        reloaded = service.get(original.snapshot_id)

        assert reloaded.snapshot_id == original.snapshot_id
        assert reloaded.case_id == original.case_id
        assert reloaded.evidence_hash == original.evidence_hash
        assert reloaded.manifest_hash == original.manifest_hash
        assert reloaded.snapshot_version == original.snapshot_version
        assert reloaded.created_at == original.created_at
        assert reloaded.created_by == original.created_by
        assert reloaded.evidence_count == original.evidence_count
        assert reloaded.status == original.status


# ── Test: Append-Only ─────────────────────────────────────────────────────────

class TestAppendOnly:
    """Snapshots can only be added, never removed or replaced."""

    def test_store_grows_on_create(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Each create() increases the total count by 1."""
        assert service.count == 0

        service.create(
            case_id=str(uuid.uuid4()),
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert service.count == 1

        service.create(
            case_id=str(uuid.uuid4()),
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert service.count == 2

    def test_superseded_snapshot_still_exists(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """When a new snapshot supersedes the old, both remain in the store."""
        r1 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        r2 = service.create(
            case_id=sample_case_id,
            evidence_hash="c" * 64,
            manifest_hash="d" * 64,
            created_by=sample_user_id,
        )

        # Both still retrievable
        old = service.get(r1.snapshot_id)
        new = service.get(r2.snapshot_id)

        assert old.status == "superseded"
        assert new.status == "active"
        assert service.count == 2

    def test_all_versions_retrievable_for_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """All historical snapshots for a case are retrievable."""
        for i in range(5):
            service.create(
                case_id=sample_case_id,
                evidence_hash=f"{i:064x}",
                manifest_hash=f"{i:064x}",
                created_by=sample_user_id,
                evidence_count=i,
            )

        all_snapshots = service.get_all_for_case(sample_case_id)
        assert len(all_snapshots) == 5
        versions = [s.snapshot_version for s in all_snapshots]
        assert versions == [1, 2, 3, 4, 5]


# ── Test: Version Monotonicity ────────────────────────────────────────────────

class TestVersionMonotonicity:
    """Versions must increment monotonically per case."""

    def test_versions_increment_per_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """v1, v2, v3 for the same case."""
        r1 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        r2 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        r3 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        assert r1.snapshot_version == 1
        assert r2.snapshot_version == 2
        assert r3.snapshot_version == 3

    def test_different_cases_have_independent_versions(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Two different cases each start at v1."""
        case_a = str(uuid.uuid4())
        case_b = str(uuid.uuid4())

        ra = service.create(
            case_id=case_a,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        rb = service.create(
            case_id=case_b,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        assert ra.snapshot_version == 1
        assert rb.snapshot_version == 1


# ── Test: Supersession ────────────────────────────────────────────────────────

class TestSupersession:
    """Creating a new snapshot for a case supersedes the active one."""

    def test_old_snapshot_becomes_superseded(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Old active → superseded when new snapshot is created."""
        r1 = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert r1.status == "active"

        r2 = service.create(
            case_id=sample_case_id,
            evidence_hash="f" * 64,
            manifest_hash="e" * 64,
            created_by=sample_user_id,
        )

        # Reload r1 to see updated status
        old = service.get(r1.snapshot_id)
        assert old.status == "superseded"
        assert r2.status == "active"

    def test_only_one_active_per_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Only one snapshot per case should be active at any time."""
        for i in range(5):
            service.create(
                case_id=sample_case_id,
                evidence_hash=f"{i:064x}",
                manifest_hash=f"{i:064x}",
                created_by=sample_user_id,
            )

        active_count = sum(
            1 for s in service.get_all_for_case(sample_case_id)
            if s.status == "active"
        )
        assert active_count == 1

    def test_get_active_for_case_returns_latest(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """get_active_for_case returns the most recent active snapshot."""
        service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        r2 = service.create(
            case_id=sample_case_id,
            evidence_hash="f" * 64,
            manifest_hash="e" * 64,
            created_by=sample_user_id,
        )

        active = service.get_active_for_case(sample_case_id)
        assert active is not None
        assert active.snapshot_id == r2.snapshot_id


# ── Test: Serialization ──────────────────────────────────────────────────────

class TestReproducibleSerialization:
    """Serialization must be reproducible (same input → same output)."""

    def test_to_dict_contains_all_fields(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """to_dict() includes all 9 fields."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
            evidence_count=3,
        )

        d = record.to_dict()
        expected_keys = {
            "case_id", "created_at", "created_by", "evidence_count",
            "evidence_hash", "manifest_hash", "snapshot_id",
            "snapshot_version", "status",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_is_json_serializable(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """to_dict() output must be JSON-serializable."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        d = record.to_dict()
        json_str = json.dumps(d, sort_keys=True)
        roundtrip = json.loads(json_str)
        assert roundtrip == d

    def test_to_dict_is_reproducible(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Same snapshot serialized twice produces identical output."""
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )

        d1 = record.to_dict()
        d2 = record.to_dict()
        assert d1 == d2

        j1 = json.dumps(d1, sort_keys=True)
        j2 = json.dumps(d2, sort_keys=True)
        assert j1 == j2


# ── Test: Retrieval ───────────────────────────────────────────────────────────

class TestRetrieval:
    """Snapshot retrieval operations."""

    def test_get_nonexistent_raises_not_found(self, service):
        """Getting a non-existent snapshot raises SnapshotNotFoundError."""
        with pytest.raises(SnapshotNotFoundError):
            service.get(str(uuid.uuid4()))

    def test_get_active_for_empty_case_returns_none(self, service):
        """No snapshots for a case → None."""
        assert service.get_active_for_case(str(uuid.uuid4())) is None

    def test_get_all_for_empty_case_returns_empty_list(self, service):
        """No snapshots for a case → empty list."""
        assert service.get_all_for_case(str(uuid.uuid4())) == []


# ── Test: Step 1 Acceptance Sequence ──────────────────────────────────────────

class TestStep1AcceptanceSequence:
    """
    The complete Step 1 acceptance sequence:
      Create Snapshot → Reload Snapshot → Attempt Modification → Rejected
      → Create New Snapshot → New Snapshot ID

    This is the exact sequence defined in the Phase 1 Step 1 authorization.
    """

    def test_full_acceptance_sequence(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Execute the full Step 1 acceptance sequence end-to-end."""

        # Step 1: Create Snapshot
        original = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
            evidence_count=3,
        )
        assert original.status == "active"
        assert original.snapshot_version == 1

        # Step 2: Reload Snapshot
        reloaded = service.get(original.snapshot_id)
        assert reloaded.snapshot_id == original.snapshot_id
        assert reloaded.evidence_hash == original.evidence_hash
        assert reloaded.created_at == original.created_at

        # Step 3: Attempt Modification → Rejected
        with pytest.raises(ImmutableSnapshotError):
            service.update(original.snapshot_id, evidence_hash="tampered")

        with pytest.raises(ImmutableSnapshotError):
            service.delete(original.snapshot_id)

        with pytest.raises(AttributeError):
            reloaded.evidence_hash = "tampered"

        # Step 4: Verify data unchanged after rejected modification
        still_same = service.get(original.snapshot_id)
        assert still_same.evidence_hash == sample_evidence_hash

        # Step 5: Create New Snapshot → New Snapshot ID
        new_snapshot = service.create(
            case_id=sample_case_id,
            evidence_hash="c" * 64,
            manifest_hash="d" * 64,
            created_by=sample_user_id,
            evidence_count=4,
        )
        assert new_snapshot.snapshot_id != original.snapshot_id
        assert new_snapshot.snapshot_version == 2
        assert new_snapshot.status == "active"

        # Verify original is now superseded
        old = service.get(original.snapshot_id)
        assert old.status == "superseded"

        # PASS: Full sequence verified
