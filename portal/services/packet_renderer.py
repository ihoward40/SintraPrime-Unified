"""
Packet Renderer — renders immutable evidence snapshots into packets.

Engineering Doctrines:
  ED-003: Immutable evidence ≠ mutable presentation.
    - A Packet is a RENDERING of a Snapshot, NOT the source of truth.
    - The Snapshot (with its Evidence Hash) is canonical.
    - The Packet is a presentation artifact that may change across renderings.
  ED-005: Single source of truth.
    - The Evidence Hash in the Packet references the Snapshot's hash.
    - The Packet Hash covers the rendered output, which MAY differ.

Architecture (user-confirmed):
  EvidenceSnapshot (immutable, source of truth)
    ↓
  PacketRenderer (this module)
    ↓
  EvidencePacket (rendered presentation artifact)

Three distinct concepts embedded in every packet:
  1. Evidence Hash — identifies the immutable legal content
  2. Packet Rendered — identifies the presentation event (timestamp)
  3. Packet Version — identifies the renderer output version

Packet Structure:
  ┌─────────────────────────────────────────┐
  │ Evidence Packet                         │
  ├─────────────────────────────────────────┤
  │ Snapshot ID                             │
  │ Evidence Hash                           │
  │ Serialization Version                   │
  │ Snapshot Created                        │
  ├─────────────────────────────────────────┤
  │ Packet Rendered (timestamp)             │
  │ Packet Version (renderer version)       │
  │ Packet Hash (hash of rendered content)  │
  ├─────────────────────────────────────────┤
  │ Evidence Manifest                       │
  │   Exhibits                              │
  │   Facts                                 │
  │   Authorities                           │
  │   Analyses                              │
  │   Requests                              │
  ├─────────────────────────────────────────┤
  │ Audit Receipt Placeholder               │
  └─────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timezone

from .evidence_hash_boundary import (
    SERIALIZATION_VERSION,
    EvidenceCollection,
    EvidenceItem,
    compute_evidence_hash,
    compute_manifest_hash,
)

# ── Renderer Version ─────────────────────────────────────────────────────────
# Incremented when the packet rendering format changes.
# This is a PRESENTATION version, not an evidence version.
RENDERER_VERSION: str = "1.0.0"


class PacketRenderError(Exception):
    """Raised when a packet cannot be rendered."""


class PacketVerificationError(Exception):
    """Raised when packet verification fails."""


@dataclass(frozen=True)
class EvidenceManifestEntry:
    """A single entry in the packet's evidence manifest.

    This is a presentation-layer summary of an evidence item.
    The full content is also included in the packet body.
    """
    item_id: str
    item_type: str
    title: str
    sequence: int


@dataclass(frozen=True)
class EvidencePacket:
    """A rendered evidence packet — a presentation of an immutable snapshot.

    This is NOT the source of truth. The EvidenceSnapshot is.
    The packet is a rendering that:
      - Embeds the Snapshot ID (links back to source of truth)
      - Embeds the Evidence Hash (verifiable against the snapshot)
      - Embeds the Serialization Version (for historical reproducibility)
      - Records when it was rendered (Packet Rendered)
      - Records the renderer version (Packet Version)
      - Computes its own hash (Packet Hash) over the rendered structure
      - Contains the full evidence content organized by type
      - Includes an audit receipt placeholder for future linkage

    ED-003: The Evidence Hash is immutable; the Packet Hash may differ
    across renderings because presentation metadata (rendered_at, etc.)
    is included in the packet but excluded from the evidence hash.
    """

    # ── Snapshot Reference (links to source of truth) ────────────────
    snapshot_id: str
    evidence_hash: str
    manifest_hash: str
    serialization_version: int
    snapshot_created: str  # ISO-8601 UTC string

    # ── Packet Metadata (presentation layer) ─────────────────────────
    packet_rendered: str  # ISO-8601 UTC string — when THIS packet was rendered
    packet_version: str  # Renderer version (e.g., "1.0.0")
    packet_hash: str  # SHA-256 of the rendered packet content

    # ── Evidence Content (organized by type) ─────────────────────────
    case_id: str
    evidence_count: int
    manifest: tuple[EvidenceManifestEntry, ...]
    exhibits: tuple[dict, ...]
    facts: tuple[dict, ...]
    authorities: tuple[dict, ...]
    analyses: tuple[dict, ...]
    requests: tuple[dict, ...]

    # ── Audit (placeholder for Step 4) ───────────────────────────────
    audit_receipt: str = "PENDING"  # Will be linked in Step 4

    def to_dict(self) -> dict:
        """Full packet as a dictionary for serialization/transmission.

        This is the complete rendered packet structure.
        Keys are sorted alphabetically for consistency.
        """
        return {
            "analyses": list(self.analyses),
            "audit_receipt": self.audit_receipt,
            "authorities": list(self.authorities),
            "case_id": self.case_id,
            "evidence_count": self.evidence_count,
            "evidence_hash": self.evidence_hash,
            "exhibits": list(self.exhibits),
            "facts": list(self.facts),
            "manifest": [
                {
                    "item_id": e.item_id,
                    "item_type": e.item_type,
                    "sequence": e.sequence,
                    "title": e.title,
                }
                for e in self.manifest
            ],
            "manifest_hash": self.manifest_hash,
            "packet_hash": self.packet_hash,
            "packet_rendered": self.packet_rendered,
            "packet_version": self.packet_version,
            "requests": list(self.requests),
            "serialization_version": self.serialization_version,
            "snapshot_created": self.snapshot_created,
            "snapshot_id": self.snapshot_id,
        }

    def to_json(self) -> str:
        """Render packet as deterministic JSON string."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def _compute_packet_hash(packet_content: dict) -> str:
    """Compute SHA-256 hash of the rendered packet content.

    This hash covers the ENTIRE rendered packet, including presentation
    metadata. It is distinct from the Evidence Hash, which covers only
    immutable evidence content.

    The packet_hash field itself is excluded from the hash computation
    (it would create a circular dependency).
    """
    # Remove packet_hash from content before hashing (avoid circular ref)
    hashable = {k: v for k, v in packet_content.items() if k != "packet_hash"}
    canonical = json.dumps(
        hashable,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _categorize_items(
    items: tuple[EvidenceItem, ...],
) -> dict[str, list[dict]]:
    """Organize evidence items by type for packet rendering.

    Returns a dict with keys: exhibits, facts, authorities, analyses, requests.
    Each value is a list of dicts with the item's content.
    """
    categories: dict[str, list[dict]] = {
        "exhibits": [],
        "facts": [],
        "authorities": [],
        "analyses": [],
        "requests": [],
    }

    type_map = {
        "exhibit": "exhibits",
        "fact": "facts",
        "authority": "authorities",
        "analysis": "analyses",
        "request": "requests",
        "manifest": "exhibits",  # manifests rendered alongside exhibits
    }

    sorted_items = sorted(items, key=lambda i: (i.sequence, i.item_id))

    for item in sorted_items:
        category = type_map.get(item.item_type, "exhibits")
        categories[category].append({
            "item_id": item.item_id,
            "title": item.title,
            "content": item.content,
            "sequence": item.sequence,
        })

    return categories


def render_packet(
    *,
    snapshot_id: str,
    case_id: str,
    evidence_hash: str,
    manifest_hash: str,
    snapshot_version: int,
    snapshot_created: datetime,
    created_by: str,
    evidence: EvidenceCollection,
    audit_service=None,
) -> EvidencePacket:
    """Render an EvidencePacket from a snapshot and its evidence.

    This is the main entry point for packet rendering. It takes the
    snapshot metadata and the evidence collection, and produces a
    complete rendered packet.

    The rendered packet:
      - Embeds the Snapshot ID and Evidence Hash (traceability)
      - Embeds the Serialization Version (reproducibility)
      - Records the rendering timestamp (presentation metadata)
      - Computes a Packet Hash over the entire rendered content
      - Organizes evidence by type (exhibits, facts, authorities, etc.)
      - Includes an audit receipt placeholder

    If audit_service is provided, creates an audit record linking the
    packet to the snapshot (Step 4: Packet ↔ Audit linkage).

    Args:
        snapshot_id: The EvidenceSnapshot's unique ID.
        case_id: The case this evidence belongs to.
        evidence_hash: The snapshot's Evidence Hash (pre-computed).
        manifest_hash: The snapshot's Manifest Hash (pre-computed).
        snapshot_version: The snapshot's version number.
        snapshot_created: When the snapshot was created.
        created_by: Who created the snapshot.
        evidence: The EvidenceCollection containing all evidence items.
        audit_service: Optional AuditService to link packet to snapshot.
            If provided, creates an audit record after packet rendering.

    Returns:
        A frozen EvidencePacket.

    Raises:
        PacketRenderError: If the packet cannot be rendered.
        PacketVerificationError: If evidence hash doesn't match.
    """
    # ── Verify evidence hash matches ─────────────────────────────────
    # ED-001: No operational capability may depend on an unverified
    # trust primitive. Verify the evidence hash before rendering.
    computed_hash = compute_evidence_hash(evidence)
    if computed_hash != evidence_hash:
        raise PacketVerificationError(
            f"Evidence hash mismatch. Snapshot claims '{evidence_hash}', "
            f"but computed '{computed_hash}'. "
            "Cannot render packet from unverified evidence (ED-001)."
        )

    computed_manifest = compute_manifest_hash(evidence)
    if computed_manifest != manifest_hash:
        raise PacketVerificationError(
            f"Manifest hash mismatch. Snapshot claims '{manifest_hash}', "
            f"but computed '{computed_manifest}'. "
            "Cannot render packet from unverified manifest (ED-001)."
        )

    # ── Build manifest entries ───────────────────────────────────────
    sorted_items = sorted(evidence.items, key=lambda i: (i.sequence, i.item_id))
    manifest_entries = tuple(
        EvidenceManifestEntry(
            item_id=item.item_id,
            item_type=item.item_type,
            title=item.title,
            sequence=item.sequence,
        )
        for item in sorted_items
    )

    # ── Categorize evidence items ────────────────────────────────────
    categorized = _categorize_items(evidence.items)

    # ── Render timestamp (presentation metadata) ─────────────────────
    rendered_at = datetime.now(UTC).isoformat()

    # ── Snapshot created as ISO string ───────────────────────────────
    snapshot_created_str = snapshot_created.isoformat()

    # ── Build packet content for hash computation ────────────────────
    packet_content = {
        "analyses": categorized["analyses"],
        "audit_receipt": "PENDING",
        "authorities": categorized["authorities"],
        "case_id": case_id,
        "evidence_count": len(evidence.items),
        "evidence_hash": evidence_hash,
        "exhibits": categorized["exhibits"],
        "facts": categorized["facts"],
        "manifest": [
            {
                "item_id": e.item_id,
                "item_type": e.item_type,
                "sequence": e.sequence,
                "title": e.title,
            }
            for e in manifest_entries
        ],
        "manifest_hash": manifest_hash,
        "packet_rendered": rendered_at,
        "packet_version": RENDERER_VERSION,
        "requests": categorized["requests"],
        "serialization_version": SERIALIZATION_VERSION,
        "snapshot_created": snapshot_created_str,
        "snapshot_id": snapshot_id,
    }

    # ── Compute packet hash ──────────────────────────────────────────
    packet_hash = _compute_packet_hash(packet_content)

    # ── Assemble frozen packet ───────────────────────────────────────
    packet = EvidencePacket(
        snapshot_id=snapshot_id,
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        serialization_version=SERIALIZATION_VERSION,
        snapshot_created=snapshot_created_str,
        packet_rendered=rendered_at,
        packet_version=RENDERER_VERSION,
        packet_hash=packet_hash,
        case_id=case_id,
        evidence_count=len(evidence.items),
        manifest=manifest_entries,
        exhibits=tuple(categorized["exhibits"]),
        facts=tuple(categorized["facts"]),
        authorities=tuple(categorized["authorities"]),
        analyses=tuple(categorized["analyses"]),
        requests=tuple(categorized["requests"]),
        audit_receipt="PENDING",
    )

    # ── Step 4: Create audit record if service provided ──────────────
    if audit_service is not None:
        audit_service.create(
            snapshot_id=snapshot_id,
            evidence_hash=evidence_hash,
            packet_id=packet.packet_hash,  # Use packet hash as packet ID
            packet_hash=packet.packet_hash,
            packet_version=int(RENDERER_VERSION.split(".")[0]),  # Major version
            serialization_version=SERIALIZATION_VERSION,
            created_by=created_by,
            verify_packet=True,  # Test 4: verify packet hash matches evidence hash
        )

    return packet


def verify_packet(packet: EvidencePacket, evidence: EvidenceCollection) -> dict:
    """Verify a rendered packet against its evidence.

    Checks:
      1. Evidence Hash in packet matches recomputed hash from evidence
      2. Manifest Hash in packet matches recomputed hash from evidence
      3. Packet Hash matches recomputed hash from packet content
      4. Serialization Version matches current version
      5. Evidence count matches

    Returns:
        A verification report dict with pass/fail for each check.
    """
    evidence_hash_ok = compute_evidence_hash(evidence) == packet.evidence_hash
    manifest_hash_ok = compute_manifest_hash(evidence) == packet.manifest_hash

    # Recompute packet hash
    packet_content = packet.to_dict()
    recomputed_packet_hash = _compute_packet_hash(packet_content)
    packet_hash_ok = recomputed_packet_hash == packet.packet_hash

    version_ok = packet.serialization_version == SERIALIZATION_VERSION
    count_ok = packet.evidence_count == len(evidence.items)

    return {
        "evidence_hash_verified": evidence_hash_ok,
        "manifest_hash_verified": manifest_hash_ok,
        "packet_hash_verified": packet_hash_ok,
        "serialization_version_current": version_ok,
        "evidence_count_matches": count_ok,
        "overall": all([
            evidence_hash_ok,
            manifest_hash_ok,
            packet_hash_ok,
            version_ok,
            count_ok,
        ]),
    }