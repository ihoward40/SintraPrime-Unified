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

Hash Boundary (user-confirmed):
  INCLUDED:
    - Evidence manifests
    - Exhibits
    - Facts
    - Authorities
    - Legal analyses
    - Requests

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


class HashBoundaryError(Exception):
    """Raised when evidence cannot be canonicalized or hashed."""
    pass


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
            ]
        }

        Items are ordered by their 'sequence' field, NOT by insertion order.
        This ensures the same evidence always produces the same canonical form
        regardless of the order in which items were added.
        """
        sorted_items = sorted(self.items, key=lambda i: (i.sequence, i.item_id))
        return {
            "case_id": self.case_id,
            "items": [item.to_canonical() for item in sorted_items],
        }


def canonicalize(evidence: EvidenceCollection) -> str:
    """Produce the canonical JSON string for evidence hashing.

    Canonical serialization rules:
      1. Keys are sorted alphabetically at every level.
      2. No whitespace (separators = (',', ':')).
      3. Unicode is NOT escaped (ensure_ascii=False).
      4. Items are ordered by (sequence, item_id).
      5. Only evidence content enters the canonical form.
         NO timestamps, NO rendering metadata, NO packet numbers.

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
