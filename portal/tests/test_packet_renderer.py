"""
Tests for Packet Renderer — Phase 1, Step 3.

Engineering Doctrines tested:
  ED-003: Packet is a rendering; Evidence Hash unchanged across renderings.
  ED-005: Evidence Hash is the single authoritative integrity marker.
  ED-001: Renderer verifies evidence before rendering (trust prerequisite).

Step 3 Acceptance Criteria (user-confirmed):
  A. Render packet from immutable EvidenceSnapshot
  B. Packet embeds Snapshot ID, Evidence Hash, Serialization Version
  C. Packet Hash may differ across renderings; Evidence Hash UNCHANGED
  D. Deterministic packet structure (same rendering → same packet)
  E. Packet verification against evidence succeeds
  F. Tampered evidence fails verification

Key architectural property:
  Two renderings of the same snapshot may produce different Packet Hashes
  (because rendered_at timestamp differs), but the Evidence Hash embedded
  in both packets MUST be identical. This is ED-003 in action.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import UTC

from portal.services.evidence_hash_boundary import (
    SERIALIZATION_VERSION,
    EvidenceCollection,
    EvidenceItem,
    compute_evidence_hash,
    compute_manifest_hash,
)
from portal.services.evidence_snapshot_service import (
    EvidenceSnapshotService,
)
from portal.services.packet_renderer import (
    RENDERER_VERSION,
    EvidencePacket,
    PacketVerificationError,
    render_packet,
    verify_packet,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_items():
    """Standard evidence items for testing."""
    return (
        EvidenceItem(
            item_id="EX-001", item_type="exhibit",
            title="Device Purchase Receipt",
            content="Receipt showing purchase of iPhone 15 Pro on 2025-01-15 for $1,199.00",
            sequence=1,
        ),
        EvidenceItem(
            item_id="FACT-001", item_type="fact",
            title="Device Conversion Date",
            content="On 2025-03-20, defendant refused to return device despite written demand.",
            sequence=2,
        ),
        EvidenceItem(
            item_id="AUTH-001", item_type="authority",
            title="NJ Conversion Statute",
            content="N.J.S.A. 2C:20-3 defines conversion as unauthorized exercise of control.",
            sequence=3,
        ),
        EvidenceItem(
            item_id="ANALYSIS-001", item_type="analysis",
            title="Damages Calculation",
            content="FMV at conversion: $1,050. Consequential damages: $200. Total: $1,250.",
            sequence=4,
        ),
        EvidenceItem(
            item_id="REQ-001", item_type="request",
            title="Prayer for Relief",
            content="Plaintiff requests return of device or FMV plus consequential damages.",
            sequence=5,
        ),
    )


@pytest.fixture
def sample_collection(sample_items):
    return EvidenceCollection(case_id="CASE-001", items=sample_items)


@pytest.fixture
def snapshot_with_evidence(sample_items, sample_collection):
    """Create a snapshot and return (snapshot_record, evidence_collection)."""
    service = EvidenceSnapshotService()
    evidence_hash = compute_evidence_hash(sample_collection)
    manifest_hash = compute_manifest_hash(sample_collection)

    snapshot = service.create(
        case_id="CASE-001",
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        created_by="user-001",
        evidence_count=len(sample_items),
    )
    return snapshot, sample_collection


@pytest.fixture
def rendered_packet(snapshot_with_evidence):
    """Render a packet from the snapshot."""
    snapshot, evidence = snapshot_with_evidence
    return render_packet(
        snapshot_id=snapshot.snapshot_id,
        case_id=snapshot.case_id,
        evidence_hash=snapshot.evidence_hash,
        manifest_hash=snapshot.manifest_hash,
        snapshot_version=snapshot.snapshot_version,
        snapshot_created=snapshot.created_at,
        created_by=snapshot.created_by,
        evidence=evidence,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEST A: Render packet from immutable EvidenceSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestPacketRendering:
    """Verify that packets can be rendered from snapshots."""

    def test_render_produces_evidence_packet(self, rendered_packet):
        """render_packet returns an EvidencePacket."""
        assert isinstance(rendered_packet, EvidencePacket)

    def test_packet_is_frozen(self, rendered_packet):
        """EvidencePacket is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            rendered_packet.evidence_hash = "tampered"
        with pytest.raises(AttributeError):
            rendered_packet.packet_hash = "tampered"

    def test_render_populates_all_fields(self, rendered_packet):
        """All required fields are populated."""
        assert rendered_packet.snapshot_id
        assert rendered_packet.evidence_hash
        assert rendered_packet.manifest_hash
        assert rendered_packet.serialization_version == SERIALIZATION_VERSION
        assert rendered_packet.snapshot_created
        assert rendered_packet.packet_rendered
        assert rendered_packet.packet_version == RENDERER_VERSION
        assert rendered_packet.packet_hash
        assert rendered_packet.case_id == "CASE-001"
        assert rendered_packet.evidence_count == 5
        assert len(rendered_packet.manifest) == 5
        assert rendered_packet.audit_receipt == "PENDING"

    def test_packet_contains_evidence_by_type(self, rendered_packet):
        """Evidence is organized into exhibits, facts, authorities, etc."""
        assert len(rendered_packet.exhibits) == 1  # EX-001
        assert len(rendered_packet.facts) == 1  # FACT-001
        assert len(rendered_packet.authorities) == 1  # AUTH-001
        assert len(rendered_packet.analyses) == 1  # ANALYSIS-001
        assert len(rendered_packet.requests) == 1  # REQ-001

    def test_packet_exhibit_content_matches(self, rendered_packet):
        """Exhibit content in packet matches the evidence item."""
        exhibit = rendered_packet.exhibits[0]
        assert exhibit["item_id"] == "EX-001"
        assert "iPhone 15 Pro" in exhibit["content"]

    def test_packet_manifest_entries(self, rendered_packet):
        """Manifest entries match evidence items."""
        manifest = rendered_packet.manifest
        assert len(manifest) == 5
        ids = [e.item_id for e in manifest]
        assert "EX-001" in ids
        assert "FACT-001" in ids
        assert "AUTH-001" in ids
        assert "ANALYSIS-001" in ids
        assert "REQ-001" in ids


# ══════════════════════════════════════════════════════════════════════════════
# TEST B: Packet embeds Snapshot ID, Evidence Hash, Serialization Version
# ══════════════════════════════════════════════════════════════════════════════

class TestPacketEmbedding:
    """Verify that the packet correctly embeds snapshot references."""

    def test_packet_embeds_snapshot_id(self, snapshot_with_evidence, rendered_packet):
        snapshot, _ = snapshot_with_evidence
        assert rendered_packet.snapshot_id == snapshot.snapshot_id

    def test_packet_embeds_evidence_hash(self, snapshot_with_evidence, rendered_packet):
        snapshot, _ = snapshot_with_evidence
        assert rendered_packet.evidence_hash == snapshot.evidence_hash

    def test_packet_embeds_manifest_hash(self, snapshot_with_evidence, rendered_packet):
        snapshot, _ = snapshot_with_evidence
        assert rendered_packet.manifest_hash == snapshot.manifest_hash

    def test_packet_embeds_serialization_version(self, rendered_packet):
        assert rendered_packet.serialization_version == SERIALIZATION_VERSION
        assert rendered_packet.serialization_version == 1

    def test_packet_embeds_snapshot_created(self, snapshot_with_evidence, rendered_packet):
        snapshot, _ = snapshot_with_evidence
        assert rendered_packet.snapshot_created == snapshot.created_at.isoformat()

    def test_packet_embeds_renderer_version(self, rendered_packet):
        assert rendered_packet.packet_version == RENDERER_VERSION


# ══════════════════════════════════════════════════════════════════════════════
# TEST C: Packet Hash may differ; Evidence Hash UNCHANGED (ED-003)
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceHashImmutableAcrossRenderings:
    """THE KEY ARCHITECTURAL PROPERTY.

    Two renderings of the same snapshot produce:
      - SAME Evidence Hash (immutable evidence content)
      - POSSIBLY DIFFERENT Packet Hash (presentation metadata differs)

    This is ED-003 in action.
    """

    def test_evidence_hash_identical_across_two_renderings(
        self, snapshot_with_evidence,
    ):
        """Render twice → Evidence Hash identical in both packets."""
        snapshot, evidence = snapshot_with_evidence

        packet_1 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=evidence,
        )
        time.sleep(0.05)  # Ensure different timestamp
        packet_2 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=evidence,
        )

        # Evidence Hash: MUST be identical
        assert packet_1.evidence_hash == packet_2.evidence_hash

        # Manifest Hash: MUST be identical
        assert packet_1.manifest_hash == packet_2.manifest_hash

    def test_packet_hash_may_differ_across_renderings(
        self, snapshot_with_evidence,
    ):
        """Render twice with time gap → Packet Hash may differ.

        This is EXPECTED and CORRECT behavior per ED-003.
        The Packet Hash includes the rendering timestamp.
        """
        snapshot, evidence = snapshot_with_evidence

        packet_1 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=evidence,
        )
        time.sleep(0.05)
        packet_2 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=evidence,
        )

        # Packet rendered timestamps differ
        assert packet_1.packet_rendered != packet_2.packet_rendered

        # Packet hashes MAY differ (they include rendered_at)
        # We don't assert they MUST differ (might run in same microsecond)
        # But we DO assert the evidence hash is the same
        assert packet_1.evidence_hash == packet_2.evidence_hash

    def test_five_renderings_same_evidence_hash(self, snapshot_with_evidence):
        """5 renderings → 5 identical evidence hashes."""
        snapshot, evidence = snapshot_with_evidence
        evidence_hashes = set()

        for _ in range(5):
            packet = render_packet(
                snapshot_id=snapshot.snapshot_id,
                case_id=snapshot.case_id,
                evidence_hash=snapshot.evidence_hash,
                manifest_hash=snapshot.manifest_hash,
                snapshot_version=snapshot.snapshot_version,
                snapshot_created=snapshot.created_at,
                created_by=snapshot.created_by,
                evidence=evidence,
            )
            evidence_hashes.add(packet.evidence_hash)

        assert len(evidence_hashes) == 1, (
            f"Evidence hash should be identical across 5 renderings, "
            f"got {len(evidence_hashes)} distinct hashes"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TEST D: Deterministic packet structure
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicPacketStructure:
    """Same rendering inputs → same packet structure."""

    def test_packet_to_dict_has_all_required_keys(self, rendered_packet):
        d = rendered_packet.to_dict()
        required_keys = {
            "analyses", "audit_receipt", "authorities", "case_id",
            "evidence_count", "evidence_hash", "exhibits", "facts",
            "manifest", "manifest_hash", "packet_hash", "packet_rendered",
            "packet_version", "requests", "serialization_version",
            "snapshot_created", "snapshot_id",
        }
        assert set(d.keys()) == required_keys

    def test_packet_to_json_is_valid_json(self, rendered_packet):
        j = rendered_packet.to_json()
        parsed = json.loads(j)
        assert isinstance(parsed, dict)

    def test_packet_to_json_keys_sorted(self, rendered_packet):
        j = rendered_packet.to_json()
        parsed = json.loads(j)
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_packet_to_dict_is_json_roundtrippable(self, rendered_packet):
        d = rendered_packet.to_dict()
        j = json.dumps(d, sort_keys=True)
        roundtrip = json.loads(j)
        assert roundtrip == d

    def test_packet_hash_is_valid_sha256(self, rendered_packet):
        h = rendered_packet.packet_hash
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ══════════════════════════════════════════════════════════════════════════════
# TEST E: Packet verification against evidence
# ══════════════════════════════════════════════════════════════════════════════

class TestPacketVerification:
    """Verify rendered packets against their evidence."""

    def test_verify_valid_packet(self, rendered_packet, sample_collection):
        """Verification of a valid packet should pass all checks."""
        result = verify_packet(rendered_packet, sample_collection)
        assert result["evidence_hash_verified"] is True
        assert result["manifest_hash_verified"] is True
        assert result["packet_hash_verified"] is True
        assert result["serialization_version_current"] is True
        assert result["evidence_count_matches"] is True
        assert result["overall"] is True

    def test_verify_packet_five_times(self, rendered_packet, sample_collection):
        """5 consecutive verifications all pass."""
        for _ in range(5):
            result = verify_packet(rendered_packet, sample_collection)
            assert result["overall"] is True

    def test_verify_against_different_evidence_fails(
        self, rendered_packet,
    ):
        """Verification against different evidence fails."""
        different = EvidenceCollection(
            case_id="CASE-001",
            items=(EvidenceItem(
                item_id="DIFF-001", item_type="exhibit",
                title="Different", content="Different content", sequence=1,
            ),),
        )
        result = verify_packet(rendered_packet, different)
        assert result["evidence_hash_verified"] is False
        assert result["overall"] is False


# ══════════════════════════════════════════════════════════════════════════════
# TEST F: Tampered evidence fails rendering
# ══════════════════════════════════════════════════════════════════════════════

class TestTamperedEvidencePrevented:
    """ED-001: No capability depends on unverified trust primitive."""

    def test_render_with_wrong_evidence_hash_raises(self, sample_collection):
        """If evidence hash doesn't match, rendering is refused."""
        from datetime import datetime, timezone

        with pytest.raises(PacketVerificationError, match="Evidence hash mismatch"):
            render_packet(
                snapshot_id="snap-001",
                case_id="CASE-001",
                evidence_hash="wrong" * 13,  # Wrong hash
                manifest_hash=compute_manifest_hash(sample_collection),
                snapshot_version=1,
                snapshot_created=datetime.now(UTC),
                created_by="user-001",
                evidence=sample_collection,
            )

    def test_render_with_wrong_manifest_hash_raises(self, sample_collection):
        """If manifest hash doesn't match, rendering is refused."""
        from datetime import datetime, timezone

        with pytest.raises(PacketVerificationError, match="Manifest hash mismatch"):
            render_packet(
                snapshot_id="snap-001",
                case_id="CASE-001",
                evidence_hash=compute_evidence_hash(sample_collection),
                manifest_hash="wrong" * 13,  # Wrong hash
                snapshot_version=1,
                snapshot_created=datetime.now(UTC),
                created_by="user-001",
                evidence=sample_collection,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Integration: Full flow (Snapshot → Hash → Render → Verify)
# ══════════════════════════════════════════════════════════════════════════════

class TestFullRenderFlow:
    """End-to-end: create snapshot → compute hashes → render packet → verify."""

    def test_full_flow_succeeds(self, sample_items):
        """Complete happy path."""
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

        packet = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=collection,
        )

        result = verify_packet(packet, collection)
        assert result["overall"] is True

    def test_full_flow_two_renderings_same_evidence_hash(self, sample_items):
        """Phase 1 Acceptance Test 3: Two renderings → Packet Hash may differ,
        Evidence Hash identical."""
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

        packet_1 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=collection,
        )
        time.sleep(0.05)
        packet_2 = render_packet(
            snapshot_id=snapshot.snapshot_id,
            case_id=snapshot.case_id,
            evidence_hash=snapshot.evidence_hash,
            manifest_hash=snapshot.manifest_hash,
            snapshot_version=snapshot.snapshot_version,
            snapshot_created=snapshot.created_at,
            created_by=snapshot.created_by,
            evidence=collection,
        )

        # THE ASSERTION: Evidence Hash identical, Packet Hash may differ
        assert packet_1.evidence_hash == packet_2.evidence_hash
        assert packet_1.manifest_hash == packet_2.manifest_hash

        # Both verify successfully
        assert verify_packet(packet_1, collection)["overall"] is True
        assert verify_packet(packet_2, collection)["overall"] is True


# ══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestPacketEdgeCases:
    def test_empty_evidence_renders(self):
        """Empty evidence collection produces a valid packet."""
        from datetime import datetime, timezone

        empty = EvidenceCollection(case_id="CASE-EMPTY", items=())
        eh = compute_evidence_hash(empty)
        mh = compute_manifest_hash(empty)

        packet = render_packet(
            snapshot_id="snap-empty",
            case_id="CASE-EMPTY",
            evidence_hash=eh,
            manifest_hash=mh,
            snapshot_version=1,
            snapshot_created=datetime.now(UTC),
            created_by="user-001",
            evidence=empty,
        )
        assert packet.evidence_count == 0
        assert len(packet.manifest) == 0
        result = verify_packet(packet, empty)
        assert result["overall"] is True

    def test_single_item_renders(self):
        """Single-item evidence produces a valid packet."""
        from datetime import datetime, timezone

        single = EvidenceCollection(
            case_id="CASE-SINGLE",
            items=(EvidenceItem(
                item_id="ITEM-1", item_type="exhibit",
                title="Sole Exhibit", content="Only evidence.", sequence=1,
            ),),
        )
        eh = compute_evidence_hash(single)
        mh = compute_manifest_hash(single)

        packet = render_packet(
            snapshot_id="snap-single",
            case_id="CASE-SINGLE",
            evidence_hash=eh,
            manifest_hash=mh,
            snapshot_version=1,
            snapshot_created=datetime.now(UTC),
            created_by="user-001",
            evidence=single,
        )
        assert packet.evidence_count == 1
        assert len(packet.exhibits) == 1
        result = verify_packet(packet, single)
        assert result["overall"] is True

    def test_serialization_version_in_packet_json(self, rendered_packet):
        """Serialization version appears in JSON output."""
        j = rendered_packet.to_json()
        parsed = json.loads(j)
        assert parsed["serialization_version"] == 1
