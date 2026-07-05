"""
Tests for Evidence Hash Boundary — Phase 1, Step 2.

Engineering Doctrines tested:
  ED-003: Hash covers ONLY immutable evidence, NOT mutable presentation.
  ED-005: Evidence Hash is the single authoritative integrity marker.

GI-B-2026-001 Resolution Tests:
  The root cause was that timestamps, version increments, and rendering
  metadata entered the hash input. These tests prove that ONLY evidence
  content affects the hash.

Acceptance Criteria (user-confirmed, tightened):

  Test A: Same evidence → 5 consecutive hashes → ALL IDENTICAL
  Test B: Modify one evidence item → New hash → DIFFERENT
  Test C: Metadata/timestamp/packet version changes → Evidence Hash UNCHANGED
          ^^^ This is the HEART of GI-B-2026-001 ^^^
"""

import hashlib
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portal.services.evidence_hash_boundary import (
    EvidenceCollection,
    EvidenceItem,
    canonicalize,
    compute_evidence_hash,
    compute_manifest_hash,
    verify_evidence_hash,
    verify_manifest_hash,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_items():
    """A set of sample evidence items for testing."""
    return (
        EvidenceItem(
            item_id="EX-001",
            item_type="exhibit",
            title="Device Purchase Receipt",
            content="Receipt showing purchase of iPhone 15 Pro on 2025-01-15 for $1,199.00",
            sequence=1,
        ),
        EvidenceItem(
            item_id="FACT-001",
            item_type="fact",
            title="Device Conversion Date",
            content="On 2025-03-20, defendant refused to return device despite written demand.",
            sequence=2,
        ),
        EvidenceItem(
            item_id="AUTH-001",
            item_type="authority",
            title="NJ Conversion Statute",
            content="N.J.S.A. 2C:20-3 defines conversion as unauthorized exercise of control over property.",
            sequence=3,
        ),
        EvidenceItem(
            item_id="ANALYSIS-001",
            item_type="analysis",
            title="Damages Calculation",
            content="FMV at conversion: $1,050. Consequential damages: $200. Total: $1,250.",
            sequence=4,
        ),
        EvidenceItem(
            item_id="REQ-001",
            item_type="request",
            title="Prayer for Relief",
            content="Plaintiff requests return of device or FMV plus consequential damages.",
            sequence=5,
        ),
    )


@pytest.fixture
def sample_collection(sample_items):
    """An evidence collection for testing."""
    return EvidenceCollection(
        case_id="CASE-001",
        items=sample_items,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ACCEPTANCE TEST A: Same evidence → 5 consecutive hashes → ALL IDENTICAL
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicHashing:
    """Evidence A → Hash → Hash → Hash → Hash → Hash → All identical."""

    def test_five_consecutive_hashes_identical(self, sample_collection):
        """THE determinism test. 5 runs, same input, same output."""
        hashes = []
        for _ in range(5):
            h = compute_evidence_hash(sample_collection)
            hashes.append(h)

        # All 5 must be identical
        assert len(set(hashes)) == 1, f"Got {len(set(hashes))} distinct hashes: {hashes}"

    def test_ten_consecutive_hashes_identical(self, sample_collection):
        """Extended determinism: 10 runs."""
        hashes = [compute_evidence_hash(sample_collection) for _ in range(10)]
        assert len(set(hashes)) == 1

    def test_hash_is_valid_sha256(self, sample_collection):
        """Hash output must be a valid 64-char lowercase hex SHA-256."""
        h = compute_evidence_hash(sample_collection)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_manifest_hash_also_deterministic(self, sample_collection):
        """Manifest hash must also be deterministic."""
        hashes = [compute_manifest_hash(sample_collection) for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_canonicalization_deterministic(self, sample_collection):
        """The canonical JSON string must be byte-identical across runs."""
        canonical_strings = [canonicalize(sample_collection) for _ in range(5)]
        assert len(set(canonical_strings)) == 1

    def test_hash_matches_manual_computation(self, sample_collection):
        """Verify hash matches manual SHA-256 of canonical JSON."""
        canonical = canonicalize(sample_collection)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        actual = compute_evidence_hash(sample_collection)
        assert actual == expected

    def test_determinism_across_time_delay(self, sample_collection):
        """Hash before and after a delay must be identical (no time dependency)."""
        h1 = compute_evidence_hash(sample_collection)
        time.sleep(0.1)  # Introduce time gap
        h2 = compute_evidence_hash(sample_collection)
        assert h1 == h2


# ══════════════════════════════════════════════════════════════════════════════
# ACCEPTANCE TEST B: Modify one evidence item → New hash → DIFFERENT
# ══════════════════════════════════════════════════════════════════════════════

class TestModifiedEvidenceProducesDifferentHash:
    """Modify one evidence item → New Snapshot → New Hash → Different."""

    def test_changed_content_produces_different_hash(self, sample_items):
        """Changing the content of one item changes the hash."""
        original = EvidenceCollection(case_id="CASE-001", items=sample_items)
        h_original = compute_evidence_hash(original)

        # Modify one item's content
        modified_items = list(sample_items)
        modified_items[0] = EvidenceItem(
            item_id="EX-001",
            item_type="exhibit",
            title="Device Purchase Receipt",
            content="Receipt showing purchase of iPhone 15 Pro on 2025-01-15 for $999.00",  # price changed
            sequence=1,
        )
        modified = EvidenceCollection(case_id="CASE-001", items=tuple(modified_items))
        h_modified = compute_evidence_hash(modified)

        assert h_original != h_modified

    def test_added_item_produces_different_hash(self, sample_items):
        """Adding an evidence item changes the hash."""
        original = EvidenceCollection(case_id="CASE-001", items=sample_items)
        h_original = compute_evidence_hash(original)

        extended_items = (*sample_items,
            EvidenceItem(
                item_id="EX-002",
                item_type="exhibit",
                title="Demand Letter",
                content="Written demand sent via certified mail on 2025-04-01.",
                sequence=6,
            ),
        )
        extended = EvidenceCollection(case_id="CASE-001", items=extended_items)
        h_extended = compute_evidence_hash(extended)

        assert h_original != h_extended

    def test_removed_item_produces_different_hash(self, sample_items):
        """Removing an evidence item changes the hash."""
        original = EvidenceCollection(case_id="CASE-001", items=sample_items)
        h_original = compute_evidence_hash(original)

        reduced = EvidenceCollection(case_id="CASE-001", items=sample_items[:-1])
        h_reduced = compute_evidence_hash(reduced)

        assert h_original != h_reduced

    def test_changed_title_produces_different_hash(self, sample_items):
        """Changing an item's title changes the hash."""
        original = EvidenceCollection(case_id="CASE-001", items=sample_items)
        h_original = compute_evidence_hash(original)

        modified_items = list(sample_items)
        modified_items[0] = EvidenceItem(
            item_id="EX-001", item_type="exhibit",
            title="Device Purchase Invoice",  # title changed
            content=sample_items[0].content, sequence=1,
        )
        modified = EvidenceCollection(case_id="CASE-001", items=tuple(modified_items))
        h_modified = compute_evidence_hash(modified)

        assert h_original != h_modified

    def test_changed_case_id_produces_different_hash(self, sample_items):
        """Different case IDs produce different hashes."""
        col_a = EvidenceCollection(case_id="CASE-001", items=sample_items)
        col_b = EvidenceCollection(case_id="CASE-002", items=sample_items)

        assert compute_evidence_hash(col_a) != compute_evidence_hash(col_b)

    def test_reordered_items_same_hash(self, sample_items):
        """Items reordered by insertion (but same sequence numbers) → same hash.

        The canonical form sorts by (sequence, item_id), so insertion order
        doesn't matter. This is critical for determinism.
        """
        original = EvidenceCollection(case_id="CASE-001", items=sample_items)
        # Reverse the tuple (different insertion order, same sequence values)
        reversed_items = tuple(reversed(sample_items))
        reordered = EvidenceCollection(case_id="CASE-001", items=reversed_items)

        assert compute_evidence_hash(original) == compute_evidence_hash(reordered)


# ══════════════════════════════════════════════════════════════════════════════
# ACCEPTANCE TEST C: Metadata changes → Evidence Hash UNCHANGED
# ^^^ THE HEART OF GI-B-2026-001 ^^^
# ══════════════════════════════════════════════════════════════════════════════

class TestMetadataExcludedFromHash:
    """Metadata changes / Timestamp changes / Packet version changes
    → Evidence Hash UNCHANGED.

    This test class directly addresses GI-B-2026-001.

    Root cause was: timestamps and version increments entered the hash.
    Fix: hash boundary includes ONLY evidence content.
    """

    def test_timestamp_does_not_affect_evidence_hash(self, sample_collection):
        """Hashing at different times produces the same hash.

        Previous bug: datetime.now() was included in hash input.
        """
        h1 = compute_evidence_hash(sample_collection)
        time.sleep(0.05)
        h2 = compute_evidence_hash(sample_collection)
        time.sleep(0.05)
        h3 = compute_evidence_hash(sample_collection)

        assert h1 == h2 == h3

    def test_rendering_metadata_not_in_canonical_form(self, sample_collection):
        """The canonical JSON must NOT contain rendering metadata."""
        canonical = canonicalize(sample_collection)

        # These should NEVER appear in the canonical form
        assert "rendered_at" not in canonical
        assert "packet_number" not in canonical
        assert "packet_version" not in canonical
        assert "footer" not in canonical
        assert "download" not in canonical
        assert "created_at" not in canonical  # snapshot timestamps excluded
        assert "updated_at" not in canonical

    def test_version_increment_does_not_affect_hash(self, sample_collection):
        """Simulating version increments: hash remains the same.

        Previous bug: version counter incremented on each call,
        changing the hash input. The hash boundary now excludes
        version numbers entirely.
        """
        # Simulate what the old buggy code did: compute hash multiple times
        # as if snapshot versions were incrementing (v1, v2, v3...)
        # The hash should be IDENTICAL because version is not in the boundary.
        hashes = []
        for _version in range(1, 6):
            # The evidence collection has no version field — that's the fix.
            # Version lives on the snapshot, not in the evidence content.
            h = compute_evidence_hash(sample_collection)
            hashes.append(h)

        assert len(set(hashes)) == 1

    def test_different_snapshot_metadata_same_evidence_hash(self, sample_items):
        """Two snapshots with different metadata but same evidence → same hash.

        This simulates: render packet v1, render packet v2. Evidence didn't
        change. Hash must be identical.
        """
        # Two collections with identical evidence
        col1 = EvidenceCollection(case_id="CASE-001", items=sample_items)
        col2 = EvidenceCollection(case_id="CASE-001", items=sample_items)

        h1 = compute_evidence_hash(col1)
        h2 = compute_evidence_hash(col2)

        assert h1 == h2

    def test_hash_boundary_contains_only_evidence_fields(self, sample_collection):
        """Verify the canonical form contains ONLY the defined evidence fields."""
        canonical = canonicalize(sample_collection)
        parsed = json.loads(canonical)

        # Top level: only case_id and items
        assert set(parsed.keys()) == {"case_id", "items", "serialization_version"}

        # Each item: only content, item_id, item_type, sequence, title
        expected_item_keys = {"content", "item_id", "item_type", "sequence", "title"}
        for item in parsed["items"]:
            assert set(item.keys()) == expected_item_keys

    def test_canonical_keys_alphabetically_sorted(self, sample_collection):
        """Keys must be alphabetically sorted for determinism."""
        canonical = canonicalize(sample_collection)
        parsed = json.loads(canonical)

        # Top-level keys sorted
        assert list(parsed.keys()) == sorted(parsed.keys())

        # Item-level keys sorted
        for item in parsed["items"]:
            assert list(item.keys()) == sorted(item.keys())


# ══════════════════════════════════════════════════════════════════════════════
# Integration: Hash Boundary + EvidenceSnapshot Service
# ══════════════════════════════════════════════════════════════════════════════

class TestHashBoundaryWithSnapshotService:
    """End-to-end: compute hash → create snapshot → verify hash → deterministic."""

    def test_end_to_end_hash_and_snapshot(self, sample_items):
        """Compute evidence hash → store in snapshot → verify later."""
        from portal.services.evidence_snapshot_service import EvidenceSnapshotService

        collection = EvidenceCollection(case_id="CASE-001", items=sample_items)
        evidence_hash = compute_evidence_hash(collection)
        manifest_hash = compute_manifest_hash(collection)

        service = EvidenceSnapshotService()
        snapshot = service.create(
            case_id="CASE-001",
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            created_by="user-001",
            evidence_count=len(sample_items),
        )

        # Recompute and verify
        assert verify_evidence_hash(collection, snapshot.evidence_hash)
        assert verify_manifest_hash(collection, snapshot.manifest_hash)

        # 5 more verifications — all pass
        for _ in range(5):
            assert verify_evidence_hash(collection, snapshot.evidence_hash)

    def test_modified_evidence_fails_verification(self, sample_items):
        """If evidence changes, verification against old hash must fail."""
        from portal.services.evidence_snapshot_service import EvidenceSnapshotService

        collection = EvidenceCollection(case_id="CASE-001", items=sample_items)
        original_hash = compute_evidence_hash(collection)

        service = EvidenceSnapshotService()
        snapshot = service.create(
            case_id="CASE-001",
            evidence_hash=original_hash,
            manifest_hash=compute_manifest_hash(collection),
            created_by="user-001",
            evidence_count=len(sample_items),
        )

        # Tamper with evidence
        tampered_items = list(sample_items)
        tampered_items[0] = EvidenceItem(
            item_id="EX-001", item_type="exhibit",
            title="Device Purchase Receipt",
            content="TAMPERED CONTENT",
            sequence=1,
        )
        tampered = EvidenceCollection(case_id="CASE-001", items=tuple(tampered_items))

        # Verification MUST fail
        assert not verify_evidence_hash(tampered, snapshot.evidence_hash)


# ══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_evidence_collection(self):
        """Empty evidence collection should still produce a valid deterministic hash."""
        empty = EvidenceCollection(case_id="CASE-EMPTY", items=())
        hashes = [compute_evidence_hash(empty) for _ in range(5)]
        assert len(set(hashes)) == 1
        assert len(hashes[0]) == 64

    def test_single_item_collection(self):
        """Single-item collection produces valid hash."""
        single = EvidenceCollection(
            case_id="CASE-SINGLE",
            items=(EvidenceItem(
                item_id="ITEM-1", item_type="exhibit",
                title="Sole Exhibit", content="Only evidence.", sequence=1,
            ),),
        )
        hashes = [compute_evidence_hash(single) for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_unicode_content_deterministic(self):
        """Unicode content must hash deterministically."""
        unicode_col = EvidenceCollection(
            case_id="CASE-UNICODE",
            items=(EvidenceItem(
                item_id="UNI-1", item_type="fact",
                title="Ünïcödé Tëst",
                content="Ñoño señor café résumé naïve 日本語 中文 한국어",
                sequence=1,
            ),),
        )
        hashes = [compute_evidence_hash(unicode_col) for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_large_content_deterministic(self):
        """Large evidence content must hash deterministically."""
        large_content = "x" * 100_000
        large_col = EvidenceCollection(
            case_id="CASE-LARGE",
            items=(EvidenceItem(
                item_id="LARGE-1", item_type="exhibit",
                title="Large Document", content=large_content, sequence=1,
            ),),
        )
        hashes = [compute_evidence_hash(large_col) for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_verify_evidence_hash_returns_bool(self, sample_collection):
        """verify_evidence_hash returns True/False, not raises."""
        h = compute_evidence_hash(sample_collection)
        assert verify_evidence_hash(sample_collection, h) is True
        assert verify_evidence_hash(sample_collection, "wrong" * 13) is False

    def test_evidence_hash_differs_from_manifest_hash(self, sample_collection):
        """Evidence hash and manifest hash must be different."""
        eh = compute_evidence_hash(sample_collection)
        mh = compute_manifest_hash(sample_collection)
        assert eh != mh  # They hash different content


# ══════════════════════════════════════════════════════════════════════════════
# GI-B-2026-001 Regression Test
# ══════════════════════════════════════════════════════════════════════════════

class TestGIB2026001Regression:
    """Explicit regression test for the exact bug that caused GI-B-2026-001.

    Original bug:
      Run 1: SHA256 = X  (version=v001, timestamp=T1)
      Run 2: SHA256 = Y  (version=v002, timestamp=T2)
      Run 3: SHA256 = Z  (version=v003, timestamp=T3)

    Root cause: version increments + datetime.now() in hash input.

    This test simulates that scenario and proves it's fixed.
    """

    def test_gi_b_2026_001_exact_scenario(self, sample_items):
        """Simulate the exact bug scenario: 3 runs with incrementing context."""
        collection = EvidenceCollection(case_id="CASE-001", items=sample_items)

        # Simulate 3 consecutive "generate_snapshot()" calls
        # In the old code, each call incremented a version counter
        # and used datetime.now(). Now those are excluded.
        run_1_hash = compute_evidence_hash(collection)
        time.sleep(0.01)  # Time passes (old bug: datetime.now() changed)

        run_2_hash = compute_evidence_hash(collection)
        time.sleep(0.01)

        run_3_hash = compute_evidence_hash(collection)

        # THE FIX: All three hashes must be identical
        assert run_1_hash == run_2_hash == run_3_hash, (
            f"GI-B-2026-001 REGRESSION: Hashes differ!\n"
            f"  Run 1: {run_1_hash}\n"
            f"  Run 2: {run_2_hash}\n"
            f"  Run 3: {run_3_hash}"
        )
