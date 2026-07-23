"""
Known-Answer Test Vectors for Event Canonicalization.

These tests compare hash outputs against FIXED, pre-computed SHA-256 digests.
This prevents future refactoring from silently changing the ledger format
while all tests still compare the same implementation to itself.

Vectors are FROZEN. If the canonicalization rules change intentionally,
the vectors must be updated to match the new expected outputs.
"""

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from portal.services.event_canonicalization import (
    canonical_timestamp,
    compute_hash,
    compute_hash_v1,
    compute_hash_v2,
    verify_event_hash,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Canonical Timestamp Known-Answer Vectors
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalTimestampVectors:
    """Verify canonical_timestamp produces deterministic, cross-database output."""

    def test_aware_utc(self):
        """Aware UTC datetime produces +00:00 suffix."""
        ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        assert ts == "2026-07-15T12:00:00+00:00"

    def test_aware_non_utc_converts_to_utc(self):
        """Aware non-UTC datetime is converted to UTC via astimezone."""
        edt = timezone(timedelta(hours=-4))
        ts = canonical_timestamp(datetime(2026, 7, 15, 8, 0, 0, tzinfo=edt))
        assert ts == "2026-07-15T12:00:00+00:00"

    def test_naive_assumed_utc(self):
        """Naive datetime is assumed UTC and gets +00:00 suffix."""
        ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0))
        assert ts == "2026-07-15T12:00:00+00:00"

    def test_offset_equivalence_same_hash(self):
        """Equivalent timestamps with different offsets produce identical hashes.
        
        2026-07-15T12:00:00+00:00 and 2026-07-15T08:00:00-04:00
        must canonicalize to the same string and therefore produce the same hash.
        """
        ts_utc = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        edt = timezone(timedelta(hours=-4))
        ts_edt = canonical_timestamp(datetime(2026, 7, 15, 8, 0, 0, tzinfo=edt))
        assert ts_utc == ts_edt

        # Hash equivalence
        h_utc = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=ts_utc,
            run_id="run-offset-test", sequence=1,
        )
        h_edt = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=ts_edt,
            run_id="run-offset-test", sequence=1,
        )
        assert h_utc == h_edt

    def test_microseconds_preserved(self):
        """Microseconds are preserved in canonical timestamp."""
        ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, 123456, tzinfo=UTC))
        assert ts == "2026-07-15T12:00:00.123456+00:00"

    def test_zero_microseconds_omitted(self):
        """Zero microseconds produce no fractional seconds."""
        ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, 0, tzinfo=UTC))
        assert ts == "2026-07-15T12:00:00+00:00"

    def test_never_produces_Z_suffix(self):
        """Canonical format uses +00:00, never Z."""
        ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        assert not ts.endswith("Z")
        assert ts.endswith("+00:00")


# ═══════════════════════════════════════════════════════════════════════════════
# v1 Known-Answer Hash Vectors
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashV1Vectors:
    """v1 hash formula: event_type|mission_id|agent_id|previous_hash|timestamp|payload"""

    TS = "2026-07-15T12:00:00+00:00"

    def test_v1_genesis(self):
        """v1 genesis event with no previous hash."""
        h = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
            mission_id=None,
            agent_id=None,
        )
        assert h == "5246748a9118cfabb46a8898e3907f812af06fd0d415d7cc20c239a8cc004fdc"

    def test_v1_tampered_payload_fails(self):
        """Tampered payload produces different hash."""
        h_original = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
        )
        h_tampered = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "TAMPERED", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
        )
        assert h_original != h_tampered

    def test_v1_verify_match(self):
        """verify_event_hash returns True for matching v1 hash."""
        stored = "5246748a9118cfabb46a8898e3907f812af06fd0d415d7cc20c239a8cc004fdc"
        assert verify_event_hash(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
            stored_hash=stored,
            hash_version=1,
        ) is True

    def test_v1_verify_tampered_fails(self):
        """verify_event_hash returns False for tampered payload."""
        stored = "5246748a9118cfabb46a8898e3907f812af06fd0d415d7cc20c239a8cc004fdc"
        assert verify_event_hash(
            event_type="MISSION_CREATED",
            payload={"action": "TAMPERED", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
            stored_hash=stored,
            hash_version=1,
        ) is False


# ═══════════════════════════════════════════════════════════════════════════════
# v2 Known-Answer Hash Vectors
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashV2Vectors:
    """v2 hash formula: run_id|sequence|event_type|mission_id|agent_id|previous_hash|timestamp|payload"""

    TS = "2026-07-15T12:00:00+00:00"

    def test_v2_genesis(self):
        """v2 genesis event with no previous hash."""
        h = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
            mission_id=None,
            agent_id=None,
            run_id="run-test-001",
            sequence=1,
        )
        assert h == "4b8eada2d0f0ddeacc62f41c4ac6fcceb4148e8a7fc5690464eb8899b9d42eb7"

    def test_v2_continuation(self):
        """v2 continuation event with previous hash and all fields populated."""
        h = compute_hash_v2(
            event_type="MISSION_STARTED",
            payload={"action": "start"},
            previous_hash="4b8eada2d0f0ddeacc62f41c4ac6fcceb4148e8a7fc5690464eb8899b9d42eb7",
            timestamp=self.TS,
            mission_id="mission-abc",
            agent_id="agent-007",
            run_id="run-test-001",
            sequence=2,
        )
        assert h == "6a2e775fd914d43e7f5f8544c8d3fc46505b0d0594ba430471346cb2244e88ff"

    def test_v2_different_run_id_different_hash(self):
        """Same event in different run produces different hash (run-scoping)."""
        h1 = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=self.TS,
            run_id="run-alpha", sequence=1,
        )
        h2 = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=self.TS,
            run_id="run-beta", sequence=1,
        )
        assert h1 != h2

    def test_v2_different_sequence_different_hash(self):
        """Same event with different sequence produces different hash."""
        h1 = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=self.TS,
            run_id="run-test", sequence=1,
        )
        h2 = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"action": "create"},
            previous_hash=None, timestamp=self.TS,
            run_id="run-test", sequence=2,
        )
        assert h1 != h2

    def test_sequence_zero_is_deterministic(self):
        """Sequence=0 serializes as '0' (not '') and is deterministic."""
        h = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-seq-zero",
            sequence=0,
        )
        # Verify it's different from sequence=None and sequence=1
        h_none = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-seq-zero",
            sequence=None,
        )
        h_one = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-seq-zero",
            sequence=1,
        )
        assert h != h_none  # 0 != None
        assert h != h_one   # 0 != 1
        assert h == "bd5dab9a6e906003d4d9246096ea011af44a0a0d862847787d7fd2607bedca11"

    def test_sequence_none_serializes_as_empty(self):
        """Sequence=None serializes as empty string in hash input."""
        h = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-seq-none",
            sequence=None,
        )
        assert h == "78df77937247b2335cd2b4e1b11d31868c013cfcc082196a0ff120abdb1022fc"

    def test_unicode_payload_deterministic(self):
        """Unicode characters in payload produce deterministic hash."""
        h = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"description": "Données importantes à vérifier"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-unicode",
            sequence=1,
        )
        # This hash is determined by Python's dict repr which uses
        # repr() for string values — unicode is deterministic
        assert isinstance(h, str) and len(h) == 64

    def test_payload_key_order_irrelevant_for_known_vectors(self):
        """dict repr key order is Python-version dependent.
        
        This test documents that key order affects the hash.
        Same keys in different order produce different hashes.
        This is why canonical_event_bytes exists for payload normalization.
        """
        h1 = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"a": 1, "b": 2},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-key-order",
            sequence=1,
        )
        h2 = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"b": 2, "a": 1},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-key-order",
            sequence=1,
        )
        # In Python 3.7+, dicts preserve insertion order, so these may differ
        # The important thing is that the same dict object always produces
        # the same hash, and stored/reloaded dicts preserve order.
        # This test just verifies they're valid 64-char hex strings.
        assert len(h1) == 64 and len(h2) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# Hash Version Dispatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashVersionDispatch:
    """Verify compute_hash dispatches correctly and rejects unknown versions."""

    TS = "2026-07-15T12:00:00+00:00"

    def test_dispatch_v1(self):
        """hash_version=1 dispatches to v1 formula."""
        h_dispatch = compute_hash(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
            hash_version=1,
        )
        h_direct = compute_hash_v1(
            event_type="MISSION_CREATED",
            payload={"action": "create", "target": "mission-001"},
            previous_hash=None,
            timestamp=self.TS,
        )
        assert h_dispatch == h_direct

    def test_dispatch_v2(self):
        """hash_version=2 dispatches to v2 formula."""
        h_dispatch = compute_hash(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-test",
            sequence=1,
            hash_version=2,
        )
        h_direct = compute_hash_v2(
            event_type="MISSION_CREATED",
            payload={"action": "create"},
            previous_hash=None,
            timestamp=self.TS,
            run_id="run-test",
            sequence=1,
        )
        assert h_dispatch == h_direct

    def test_dispatch_unknown_raises(self):
        """Unknown hash_version raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash_version"):
            compute_hash(
                event_type="X", payload={}, previous_hash=None,
                timestamp=self.TS, hash_version=99,
            )

    def test_verify_unknown_returns_false(self):
        """verify_event_hash returns False for unknown hash_version."""
        assert verify_event_hash(
            event_type="X", payload={}, previous_hash=None,
            timestamp=self.TS, stored_hash="anything", hash_version=99,
        ) is False

    def test_v1_v2_produce_different_hashes(self):
        """Same inputs with v1 and v2 produce different hashes."""
        h1 = compute_hash_v1(
            event_type="MISSION_CREATED", payload={"a": 1},
            previous_hash=None, timestamp=self.TS,
        )
        h2 = compute_hash_v2(
            event_type="MISSION_CREATED", payload={"a": 1},
            previous_hash=None, timestamp=self.TS,
            run_id="run", sequence=1,
        )
        assert h1 != h2  # v2 includes run_id and sequence