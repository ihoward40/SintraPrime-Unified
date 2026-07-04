"""
Evidence Hash Boundary — deterministic evidence hashing.

Engineering Doctrines:
  ED-003: Immutable evidence ≠ mutable presentation.
    - The hash boundary defines EXACTLY what is evidence (immutable)
      vs. what is presentation (mutable).
  ED-005: Single source of truth.
    - The Evidence Hash is the single authoritative integrity marker.

GI-B-2026-001 Root Cause:
  Previous implementation included timestamps, version increments, and
  rendering metadata in the hash input. This caused 3 different hashes
  on consecutive runs of identical evidence.

Resolution:
  This module hashes ONLY immutable evidence content. Metadata that
  changes between renderings (timestamps, packet numbers, footer text,
  download info) is EXCLUDED from the hash boundary.

═══════════════════════════════════════════════════════════════════════
Canonical Serialization Specification v1
═══════════════════════════════════════════════════════════════════════

Version: 1
Identifier: CANONICAL_SERIALIZATION_V1

This specification defines how evidence is serialized for hashing.
Future changes to the serialization format MUST increment the version
number. Old evidence remains reproducible because the version is
embedded in the canonical form.

Rules:
  1. Keys are sorted alphabetically at every nesting level.
  2. No whitespace between tokens (separators = (',', ':')).
  3. Unicode is NOT escaped (ensure_ascii=False).
  4. Encoding: UTF-8.
  5. Items are ordered by (sequence, item_id) — deterministic.
  6. Only evidence content enters the canonical form.
  7. Serialization version is embedded in the canonical form.

INCLUDED in hash boundary:
  - serialization_version (integer — THIS field)
  - case_id (string)
  - items (array of evidence items, each with:)
    - item_id (string)
    - item_type (string: "exhibit", "fact", "authority", "analysis",
                 "request", "manifest")
    - title (string)
    - content (string)
    - sequence (integer)

EXCLUDED from hash boundary:
  - Timestamps (created_at, rendered_at, etc.)
  - Rendering metadata (packet_number, footer, download_info)
  - Packet version / renderer version
  - Snapshot version (snapshot_version is a lifecycle concept,
    NOT evidence content)

Canonical Form (JSON):
  {
    "case_id": "...",
    "items": [
      {"content": "...", "item_id": "...", "item_type": "...",
       "sequence": N, "title": "..."},
      ...
    ],
    "serialization_version": 1
  }

Reproducibility Guarantee:
  Given the same evidence items, case_id, and serialization_version,
  this specification produces byte-identical JSON on every invocation,
  across time, across machines, across Python versions.

If canonicalization evolves (e.g., Unicode normalization, numeric
normalization), the version increments to 2. Version 1 evidence
remains reproducible by selecting the v1 canonicalizer.

═══════════════════════════════════════════════════════════════════════

Hash Boundary (user-confirmed):
  INCLUDED:
    - Evidence manifests
    - Exhibits
    - Facts
    - Authorities
    - Legal analyses
    - Requests
    - Serialization version

  EXCLUDED:
    - Timestamps (created_at, rendered_at, etc.)
    - Rendering metadata
    - Packet numbers / version increments
    - Footer text
    - Download information
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

# ── Serialization Version ────────────────────────────────────────────────────
# This is a PERMANENT architectural constant. If the canonical serialization
# format changes, increment this and keep the old canonicalizer available
# for historical hash reproduction.

SERIALIZATION_VERSION: int = 1


class HashBoundaryError(Exception):
    """Raised when evidence cannot be canonicalized or hashed."""


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of evidence within a snapshot.

    Only the fields that constitute immutable evidence content are included.
    Metadata (timestamps, rendering info) is deliberately excluded.
    """
    item_id: str
    item_type: str  # "exhibit", "fact", "authority", "analysis", "request", "manifest"
    title: str
    content: str  # The actual evidence content
    sequence: int  # Order within the evidence collection

    def to_canonical(self) -> dict:
        """Canonical representation for hashing.

        Returns a dict with exactly the fields that enter the hash boundary.
        Keys are sorted alphabetically for determinism.
        """
        return {
            "content": self.content,
            "item_id": self.item_id,
            "item_type": self.item_type,
            "sequence": self.sequence,
            "title": self.title,
        }


@dataclass(frozen=True)
class EvidenceCollection:
    """An ordered collection of evidence items for a case.

    This is the input to the hash boundary function. It contains ONLY
    the items that should be hashed — no metadata, no timestamps, no
    rendering information.
    """
    case_id: str
    items: tuple[EvidenceItem, ...]  # tuple for immutability

    def to_canonical(self) -> dict:
        """Canonical representation of the entire evidence collection.

        The canonical form is:
        {
            "case_id": "...",
            "items": [
                { canonical item 1 },
                { canonical item 2 },
                ...
            ],
            "serialization_version": 1
        }

        Items are ordered by their 'sequence' field, NOT by insertion order.
        This ensures the same evidence always produces the same canonical form
        regardless of the order in which items were added.

        The serialization_version is embedded so that future format changes
        can be detected and historical hashes reproduced.
        """
        sorted_items = sorted(self.items, key=lambda i: (i.sequence, i.item_id))
        return {
            "case_id": self.case_id,
            "items": [item.to_canonical() for item in sorted_items],
            "serialization_version": SERIALIZATION_VERSION,
        }


def canonicalize(evidence: EvidenceCollection) -> str:
    """Produce the canonical JSON string for evidence hashing.

    Canonical serialization rules (Specification v1):
      1. Keys are sorted alphabetically at every level.
      2. No whitespace (separators = (',', ':')).
      3. Unicode is NOT escaped (ensure_ascii=False).
      4. Encoding target: UTF-8.
      5. Items are ordered by (sequence, item_id).
      6. Only evidence content enters the canonical form.
         NO timestamps, NO rendering metadata, NO packet numbers.
      7. serialization_version is embedded in the canonical form.

    This function is the SINGLE entry point for evidence canonicalization.
    All hash computations MUST use this function.

    Args:
        evidence: The EvidenceCollection to canonicalize.

    Returns:
        A deterministic JSON string suitable for hashing.

    Raises:
        HashBoundaryError: If evidence cannot be canonicalized.
    """
    try:
        canonical_dict = evidence.to_canonical()
        return json.dumps(
            canonical_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as e:
        raise HashBoundaryError(f"Cannot canonicalize evidence: {e}") from e


def compute_evidence_hash(evidence: EvidenceCollection) -> str:
    """Compute the SHA-256 hash of canonicalized evidence.

    This is THE hash boundary function. It computes a hash over ONLY
    immutable evidence content. Everything excluded from the hash
    boundary (timestamps, metadata, etc.) does not affect this hash.

    The same evidence ALWAYS produces the same hash, regardless of:
      - When it was computed (no timestamp dependency)
      - How many times it was computed (no counter/version dependency)
      - What rendering metadata exists (not included)
      - What packet version is being generated (not included)

    Args:
        evidence: The EvidenceCollection to hash.

    Returns:
        SHA-256 hex digest (64 characters, lowercase).

    Raises:
        HashBoundaryError: If evidence cannot be hashed.
    """
    canonical = canonicalize(evidence)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_manifest_hash(evidence: EvidenceCollection) -> str:
    """Compute the SHA-256 hash of the evidence manifest.

    The manifest hash covers the structural metadata of the evidence
    collection: item IDs, types, titles, sequence numbers, and count.
    It does NOT include the full content (that's the evidence hash).

    This allows quick verification that the evidence structure hasn't
    changed without re-hashing all content.

    Args:
        evidence: The EvidenceCollection to hash.

    Returns:
        SHA-256 hex digest (64 characters, lowercase).

    Raises:
        HashBoundaryError: If manifest cannot be hashed.
    """
    try:
        sorted_items = sorted(evidence.items, key=lambda i: (i.sequence, i.item_id))
        manifest = {
            "case_id": evidence.case_id,
            "evidence_count": len(evidence.items),
            "items": [
                {
                    "item_id": item.item_id,
                    "item_type": item.item_type,
                    "sequence": item.sequence,
                    "title": item.title,
                }
                for item in sorted_items
            ],
            "serialization_version": SERIALIZATION_VERSION,
        }
        canonical = json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as e:
        raise HashBoundaryError(f"Cannot compute manifest hash: {e}") from e


def verify_evidence_hash(evidence: EvidenceCollection, expected_hash: str) -> bool:
    """Verify that evidence matches an expected hash.

    Args:
        evidence: The EvidenceCollection to verify.
        expected_hash: The expected SHA-256 hex digest.

    Returns:
        True if the computed hash matches the expected hash.
    """
    computed = compute_evidence_hash(evidence)
    return computed == expected_hash


def verify_manifest_hash(evidence: EvidenceCollection, expected_hash: str) -> bool:
    """Verify that the evidence manifest matches an expected hash.

    Args:
        evidence: The EvidenceCollection to verify.
        expected_hash: The expected SHA-256 hex digest.

    Returns:
        True if the computed manifest hash matches the expected hash.
    """
    computed = compute_manifest_hash(evidence)
    return computed == expected_hash
