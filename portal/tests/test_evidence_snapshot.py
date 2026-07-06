"""
Tests for EvidenceSnapshot model and service.

Phase 1 — Step 1 (refined) + Step 2 (Hash Boundary)

Engineering Doctrines tested:
  ED-003: Immutable evidence ≠ mutable presentation
  ED-005: Single source of truth

Step 1 Acceptance criteria verified:
  - Immutable after creation
  - Append-only (no delete)
  - Reproducible serialization
  - Unique Snapshot IDs
  - Version monotonicity
  - Supersession behavior
  - SnapshotState transitions (ACTIVE, SUPERSEDED, ARCHIVED)
  - Persistence-level immutability (new session → still enforced)
"""

import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portal.services.evidence_audit_service import AuditService
from portal.services.evidence_hash_boundary import (
    EvidenceCollection,
    EvidenceItem,
    compute_evidence_hash,
    compute_manifest_hash,
)
from portal.services.evidence_snapshot_service import (
    EvidenceSnapshotService,
    ImmutableSnapshotError,
    InvalidStateTransitionError,
    SnapshotNotFoundError,
    SnapshotStatus,
)
from portal.services.packet_renderer import render_packet

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    """Fresh EvidenceSnapshotService for each test."""
    return EvidenceSnapshotService()


@pytest.fixture
def audit_service():
    """Fresh AuditService for each test."""
    return AuditService()


@pytest.fixture
def sample_case_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_evidence_hash():
    return "a" * 64


@pytest.fixture
def sample_manifest_hash():
    return "b" * 64


# ── Test: Creation ────────────────────────────────────────────────────────────

class TestSnapshotCreation:
    def test_create_snapshot_returns_record(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
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

    def test_create_snapshot_first_version_is_1(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
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
        record = service.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
        )
        assert record.evidence_count == 0


# ── Test: Unique IDs ─────────────────────────────────────────────────────────

class TestUniqueSnapshotIDs:
    def test_two_snapshots_have_different_ids(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        r1 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r2 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert r1.snapshot_id != r2.snapshot_id

    def test_ten_snapshots_all_unique(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        ids = set()
        for _ in range(10):
            record = service.create(case_id=str(uuid.uuid4()), evidence_hash=sample_evidence_hash,
                                    manifest_hash=sample_manifest_hash, created_by=sample_user_id)
            ids.add(record.snapshot_id)
        assert len(ids) == 10


# ── Test: Immutability ────────────────────────────────────────────────────────

class TestSnapshotImmutability:
    def test_update_raises_immutable_error(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        with pytest.raises(ImmutableSnapshotError, match="Cannot modify"):
            service.update(record.snapshot_id, evidence_hash="changed")

    def test_delete_raises_immutable_error(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        with pytest.raises(ImmutableSnapshotError, match="Cannot delete"):
            service.delete(record.snapshot_id)

    def test_frozen_dataclass_prevents_field_mutation(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
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
        original = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                  manifest_hash=sample_manifest_hash, created_by=sample_user_id,
                                  evidence_count=7)
        reloaded = service.get(original.snapshot_id)
        assert reloaded.snapshot_id == original.snapshot_id
        assert reloaded.evidence_hash == original.evidence_hash
        assert reloaded.created_at == original.created_at
        assert reloaded.status == original.status


# ── Test: Persistence-Level Immutability ──────────────────────────────────────
# User-requested: Migration → Insert → Restart Session → Reload → Still Immutable

class TestPersistenceLevelImmutability:
    """Verify immutability survives across service instances (simulating restart).

    This simulates: create in Service A → destroy A → create Service B → reload → immutable.
    The SQL trigger provides database-level enforcement; this test proves the
    application-level invariant is structural, not dependent on a single session.
    """

    def test_immutability_survives_service_restart(
        self, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Create snapshot in one service, export state, import into fresh service."""
        # Session 1: Create a snapshot
        service_a = EvidenceSnapshotService()
        original = service_a.create(
            case_id=sample_case_id,
            evidence_hash=sample_evidence_hash,
            manifest_hash=sample_manifest_hash,
            created_by=sample_user_id,
            evidence_count=3,
        )
        original_id = original.snapshot_id
        original_hash = original.evidence_hash
        original_version = original.snapshot_version
        original_dict = original.to_dict()

        # Export state (simulate what a database would persist)
        exported_state = {
            sid: record.to_dict()
            for sid, record in service_a._store.items()
        }

        # "Restart": Destroy service_a, create service_b
        del service_a

        # Session 2: Reconstruct from persisted state
        service_b = EvidenceSnapshotService()
        from datetime import datetime

        from portal.services.evidence_snapshot_service import SnapshotRecord

        for sid, data in exported_state.items():
            restored = SnapshotRecord(
                snapshot_id=data["snapshot_id"],
                case_id=data["case_id"],
                evidence_hash=data["evidence_hash"],
                manifest_hash=data["manifest_hash"],
                snapshot_version=data["snapshot_version"],
                created_at=datetime.fromisoformat(data["created_at"]),
                created_by=data["created_by"],
                evidence_count=data["evidence_count"],
                status=data["status"],
            )
            service_b._store[sid] = restored
            current_v = service_b._case_versions.get(data["case_id"], 0)
            service_b._case_versions[data["case_id"]] = max(current_v, data["snapshot_version"])

        # Verify: reload from new session
        reloaded = service_b.get(original_id)
        assert reloaded.evidence_hash == original_hash
        assert reloaded.snapshot_version == original_version
        assert reloaded.to_dict() == original_dict

        # Verify: immutability still enforced in new session
        with pytest.raises(ImmutableSnapshotError, match="Cannot modify"):
            service_b.update(original_id, evidence_hash="tampered")

        with pytest.raises(ImmutableSnapshotError, match="Cannot delete"):
            service_b.delete(original_id)

        with pytest.raises(AttributeError):
            reloaded.evidence_hash = "tampered"

    def test_supersession_works_across_sessions(
        self, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        """Snapshot created in session 1, superseded in session 2."""
        from datetime import datetime

        from portal.services.evidence_snapshot_service import SnapshotRecord

        # Session 1
        svc1 = EvidenceSnapshotService()
        r1 = svc1.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                         manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        exported = {sid: r.to_dict() for sid, r in svc1._store.items()}
        del svc1

        # Session 2: restore and create new snapshot
        svc2 = EvidenceSnapshotService()
        for sid, data in exported.items():
            restored = SnapshotRecord(
                snapshot_id=data["snapshot_id"], case_id=data["case_id"],
                evidence_hash=data["evidence_hash"], manifest_hash=data["manifest_hash"],
                snapshot_version=data["snapshot_version"],
                created_at=datetime.fromisoformat(data["created_at"]),
                created_by=data["created_by"], evidence_count=data["evidence_count"],
                status=data["status"],
            )
            svc2._store[sid] = restored
            svc2._case_versions[data["case_id"]] = max(
                svc2._case_versions.get(data["case_id"], 0), data["snapshot_version"]
            )

        # Create new snapshot in session 2
        r2 = svc2.create(case_id=sample_case_id, evidence_hash="c" * 64,
                         manifest_hash="d" * 64, created_by=sample_user_id)

        assert r2.snapshot_version == 2
        assert r2.status == "active"

        old = svc2.get(r1.snapshot_id)
        assert old.status == "superseded"
        assert old.evidence_hash == sample_evidence_hash  # original data preserved


# ── Test: SnapshotState Transitions ───────────────────────────────────────────

class TestSnapshotStateTransitions:
    """Verify the SnapshotStatus state machine (ACTIVE, SUPERSEDED, ARCHIVED)."""

    def test_active_to_archived(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert record.status == "active"

        archived = service.archive(record.snapshot_id)
        assert archived.status == "archived"
        assert archived.evidence_hash == sample_evidence_hash  # data preserved

    def test_superseded_to_archived(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        r1 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        service.create(case_id=sample_case_id, evidence_hash="c" * 64,
                       manifest_hash="d" * 64, created_by=sample_user_id)

        old = service.get(r1.snapshot_id)
        assert old.status == "superseded"

        archived = service.archive(r1.snapshot_id)
        assert archived.status == "archived"

    def test_archived_is_terminal(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        service.archive(record.snapshot_id)

        with pytest.raises(InvalidStateTransitionError):
            service.archive(record.snapshot_id)

    def test_valid_transitions_matrix(self):
        assert SnapshotStatus.is_valid_transition("active", "superseded") is True
        assert SnapshotStatus.is_valid_transition("active", "archived") is True
        assert SnapshotStatus.is_valid_transition("superseded", "archived") is True
        assert SnapshotStatus.is_valid_transition("archived", "active") is False
        assert SnapshotStatus.is_valid_transition("archived", "superseded") is False
        assert SnapshotStatus.is_valid_transition("superseded", "active") is False


# ── Test: Append-Only ─────────────────────────────────────────────────────────

class TestAppendOnly:
    def test_store_grows_on_create(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        assert service.count == 0
        service.create(case_id=str(uuid.uuid4()), evidence_hash=sample_evidence_hash,
                       manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert service.count == 1
        service.create(case_id=str(uuid.uuid4()), evidence_hash=sample_evidence_hash,
                       manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert service.count == 2

    def test_superseded_snapshot_still_exists(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        r1 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r2 = service.create(case_id=sample_case_id, evidence_hash="c" * 64,
                            manifest_hash="d" * 64, created_by=sample_user_id)
        old = service.get(r1.snapshot_id)
        new = service.get(r2.snapshot_id)
        assert old.status == "superseded"
        assert new.status == "active"
        assert service.count == 2

    def test_all_versions_retrievable_for_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        for i in range(5):
            service.create(case_id=sample_case_id, evidence_hash=f"{i:064x}",
                           manifest_hash=f"{i:064x}", created_by=sample_user_id, evidence_count=i)
        all_snapshots = service.get_all_for_case(sample_case_id)
        assert len(all_snapshots) == 5
        assert [s.snapshot_version for s in all_snapshots] == [1, 2, 3, 4, 5]


# ── Test: Version Monotonicity ────────────────────────────────────────────────

class TestVersionMonotonicity:
    def test_versions_increment_per_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        r1 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r2 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r3 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert (r1.snapshot_version, r2.snapshot_version, r3.snapshot_version) == (1, 2, 3)

    def test_different_cases_have_independent_versions(
        self, service, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        case_a, case_b = str(uuid.uuid4()), str(uuid.uuid4())
        ra = service.create(case_id=case_a, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        rb = service.create(case_id=case_b, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        assert ra.snapshot_version == 1
        assert rb.snapshot_version == 1


# ── Test: Supersession ────────────────────────────────────────────────────────

class TestSupersession:
    def test_old_snapshot_becomes_superseded(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        r1 = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                            manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r2 = service.create(case_id=sample_case_id, evidence_hash="f" * 64,
                            manifest_hash="e" * 64, created_by=sample_user_id)
        old = service.get(r1.snapshot_id)
        assert old.status == "superseded"
        assert r2.status == "active"

    def test_only_one_active_per_case(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        for i in range(5):
            service.create(case_id=sample_case_id, evidence_hash=f"{i:064x}",
                           manifest_hash=f"{i:064x}", created_by=sample_user_id)
        active_count = sum(1 for s in service.get_all_for_case(sample_case_id) if s.status == "active")
        assert active_count == 1

    def test_get_active_for_case_returns_latest(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                       manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        r2 = service.create(case_id=sample_case_id, evidence_hash="f" * 64,
                            manifest_hash="e" * 64, created_by=sample_user_id)
        active = service.get_active_for_case(sample_case_id)
        assert active.snapshot_id == r2.snapshot_id


# ── Test: Serialization ──────────────────────────────────────────────────────

class TestReproducibleSerialization:
    def test_to_dict_contains_all_fields(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id, evidence_count=3)
        d = record.to_dict()
        expected_keys = {"case_id", "created_at", "created_by", "evidence_count",
                         "evidence_hash", "manifest_hash", "snapshot_id", "snapshot_version", "status"}
        assert set(d.keys()) == expected_keys

    def test_to_dict_is_json_serializable(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        d = record.to_dict()
        roundtrip = json.loads(json.dumps(d, sort_keys=True))
        assert roundtrip == d

    def test_to_dict_is_reproducible(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        record = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                manifest_hash=sample_manifest_hash, created_by=sample_user_id)
        j1 = json.dumps(record.to_dict(), sort_keys=True)
        j2 = json.dumps(record.to_dict(), sort_keys=True)
        assert j1 == j2


# ── Test: Retrieval ───────────────────────────────────────────────────────────

class TestRetrieval:
    def test_get_nonexistent_raises_not_found(self, service):
        with pytest.raises(SnapshotNotFoundError):
            service.get(str(uuid.uuid4()))

    def test_get_active_for_empty_case_returns_none(self, service):
        assert service.get_active_for_case(str(uuid.uuid4())) is None

    def test_get_all_for_empty_case_returns_empty_list(self, service):
        assert service.get_all_for_case(str(uuid.uuid4())) == []


# ── Test: Step 1 Acceptance Sequence ──────────────────────────────────────────

class TestStep1AcceptanceSequence:
    def test_full_acceptance_sequence(
        self, service, sample_case_id, sample_user_id,
        sample_evidence_hash, sample_manifest_hash,
    ):
        # Create
        original = service.create(case_id=sample_case_id, evidence_hash=sample_evidence_hash,
                                  manifest_hash=sample_manifest_hash, created_by=sample_user_id, evidence_count=3)
        assert original.status == "active"
        assert original.snapshot_version == 1

        # Reload
        reloaded = service.get(original.snapshot_id)
        assert reloaded.evidence_hash == original.evidence_hash

        # Attempt Modification → Rejected
        with pytest.raises(ImmutableSnapshotError):
            service.update(original.snapshot_id, evidence_hash="tampered")
        with pytest.raises(ImmutableSnapshotError):
            service.delete(original.snapshot_id)
        with pytest.raises(AttributeError):
            reloaded.evidence_hash = "tampered"

        # Data unchanged
        still_same = service.get(original.snapshot_id)
        assert still_same.evidence_hash == sample_evidence_hash

        # Create New → New ID
        new_snapshot = service.create(case_id=sample_case_id, evidence_hash="c" * 64,
                                      manifest_hash="d" * 64, created_by=sample_user_id, evidence_count=4)
        assert new_snapshot.snapshot_id != original.snapshot_id
        assert new_snapshot.snapshot_version == 2
        assert service.get(original.snapshot_id).status == "superseded"

# ── Test: Step 5 Provenance Replay (AT-5) ─────────────────────────────────────

class TestProvenanceReplay:
    """Verify the complete evidence → snapshot → packet → audit chain.

    Step 5 Acceptance Test (AT-5): the entire provenance chain can be
    created, persisted in-memory, retrieved, and verified end-to-end.

    Engineering Doctrines:
      ED-003: Immutable evidence ≠ mutable presentation
      ED-005: Single source of truth — snapshots are authoritative
      ED-007: Regression protection through immutable audit trail
    """

    def test_05_provenance_replay_chain_is_complete_and_verifiable(
        self,
        service,
        audit_service,
        sample_case_id,
        sample_user_id,
    ):
        # 1. Build immutable evidence collection
        items = (
            EvidenceItem(
                item_id="exhibit-001",
                item_type="exhibit",
                title="Bank Statement",
                content="Account ending 4242, balance $1,234.56 as of 2026-07-01.",
                sequence=1,
            ),
            EvidenceItem(
                item_id="fact-001",
                item_type="fact",
                title="Residence Status",
                content="Taxpayer is currently homeless and receiving Medicaid.",
                sequence=2,
            ),
            EvidenceItem(
                item_id="request-001",
                item_type="request",
                title="CNC Relief Request",
                content="Request currently-not-collectible hardship status.",
                sequence=3,
            ),
        )
        evidence = EvidenceCollection(case_id=sample_case_id, items=items)
        evidence_hash = compute_evidence_hash(evidence)
        manifest_hash = compute_manifest_hash(evidence)

        # 2. Create immutable EvidenceSnapshot
        snapshot = service.create(
            case_id=sample_case_id,
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            created_by=sample_user_id,
            evidence_count=len(items),
        )
        assert snapshot.status == "active"
        assert snapshot.evidence_hash == evidence_hash
        assert snapshot.manifest_hash == manifest_hash

        # 3. Render packet from snapshot
        packet = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=sample_case_id,
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=sample_user_id,
            evidence=evidence,
        )
        assert packet.snapshot_id == snapshot.snapshot_id
        assert packet.evidence_hash == snapshot.evidence_hash
        assert packet.case_id == sample_case_id
        assert packet.evidence_count == len(items)

        # 4. Create audit record linking packet to snapshot
        # Packet hash and evidence hash are intentionally different (ED-003:
        # immutable evidence vs. mutable presentation), so we link without
        # requiring them to match.
        audit = audit_service.create(
            snapshot_id=snapshot.snapshot_id,
            evidence_hash=snapshot.evidence_hash,
            packet_id=packet.packet_hash,
            packet_hash=packet.packet_hash,
            packet_version=int(packet.packet_version.split(".")[0]),
            serialization_version=packet.serialization_version,
            created_by=sample_user_id,
            verify_packet=False,
        )

        # 5. Simulate replay: retrieve all records from the in-memory store
        retrieved_audit = audit_service.get(audit.audit_id)
        retrieved_snapshot = service.get(retrieved_audit.snapshot_id)
        retrieved_packet_by_audit = audit_service.get_by_packet_id(
            retrieved_audit.packet_id
        )

        # 6. Verify chain integrity
        assert retrieved_audit.snapshot_id == snapshot.snapshot_id
        assert retrieved_audit.packet_id == packet.packet_hash
        assert retrieved_snapshot.evidence_hash == evidence_hash
        assert retrieved_snapshot.snapshot_id == snapshot.snapshot_id
        assert retrieved_packet_by_audit.audit_id == retrieved_audit.audit_id

        # 7. Verify hashes match end-to-end
        assert retrieved_audit.evidence_hash == retrieved_snapshot.evidence_hash
        assert retrieved_audit.packet_hash == packet.packet_hash
        assert retrieved_snapshot.evidence_hash == packet.evidence_hash
        assert retrieved_snapshot.manifest_hash == manifest_hash

    def test_05_replay_fails_when_snapshot_is_missing(
        self, audit_service, sample_user_id, sample_case_id,
    ):
        fresh_service = EvidenceSnapshotService()
        with pytest.raises(SnapshotNotFoundError):
            fresh_service.get("nonexistent-snapshot-id")

    def test_05_audit_traceability_by_snapshot_id(
        self,
        service,
        audit_service,
        sample_case_id,
        sample_user_id,
    ):
        items = (
            EvidenceItem(
                item_id="auth-001",
                item_type="authority",
                title="IRC 6702 Penalty",
                content="Frivolous submission penalty of $5,000 per return.",
                sequence=1,
            ),
        )
        evidence = EvidenceCollection(case_id=sample_case_id, items=items)
        evidence_hash = compute_evidence_hash(evidence)
        manifest_hash = compute_manifest_hash(evidence)

        snapshot = service.create(
            case_id=sample_case_id,
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            created_by=sample_user_id,
            evidence_count=1,
        )
        packet = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=sample_case_id,
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=sample_user_id,
            evidence=evidence,
        )
        audit_service.create(
            snapshot_id=snapshot.snapshot_id,
            evidence_hash=snapshot.evidence_hash,
            packet_id=packet.packet_hash,
            packet_hash=packet.packet_hash,
            packet_version=int(packet.packet_version.split(".")[0]),
            serialization_version=packet.serialization_version,
            created_by=sample_user_id,
            verify_packet=False,
        )

        audits = audit_service.get_by_snapshot_id(snapshot.snapshot_id)
        assert len(audits) == 1
        assert audits[0].packet_id == packet.packet_hash
        assert audits[0].evidence_hash == evidence_hash
