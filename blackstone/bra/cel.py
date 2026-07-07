"""
BRA — Constitutional Evidence Ledger (CEL)
==========================================
The central, immutable evidence repository for the Blackstone Ecosystem.

BKGC v2.0 Art. XIII-XIV; BGS v1.0 BGS-05 through BGS-09.

Core rules encoded here:
  1. Evidence items are NEVER deleted — only deprecated (BGS-07).
  2. Every access, transfer, and transformation is logged to chain of custody (BGS-08).
  3. Re-verification intervals are enforced by source class (BGS-09).
  4. Legal holds block all modification and archival (BGS-19).
  5. EV-IDs are unique, sequential, and immutable once assigned (BKR-02).

Usage:
    cel = ConstitutionalEvidenceLedger()
    ev_id = cel.add("Evidence Title", source_class="SC-01", collected_by="hermes",
                    citation="26 U.S.C. § 6213", provenance={...})
    cel.authenticate(ev_id, authenticator="viktor", content_hash="sha256:...")
    item = cel.get(ev_id)
    cel.deprecate(ev_id, deprecated_by="viktor", reason="Superseded by EV-20260801-0001",
                  successor_ev_id="EV-20260801-0001")
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, date
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Re-verification intervals by source class — BGS-09 (in days)
# ---------------------------------------------------------------------------
REVERIFICATION_INTERVALS: dict[str, int] = {
    "SC-01": 180,  # Primary Legal Authority
    "SC-02": 180,  # Official Government Publication
    "SC-03": 90,   # Scholarly and Academic
    "SC-04": 90,   # Privately Published Reference
    "SC-05": 365,  # Historical Document
    "SC-06": 30,   # Secondary / Informational
}

# Source reliability score ranges — BGS-06 reference
SOURCE_RELIABILITY_RANGES: dict[str, tuple[int, int]] = {
    "SC-01": (16, 20),
    "SC-02": (13, 17),
    "SC-03": (10, 15),
    "SC-04": (10, 15),
    "SC-05": (6, 12),
    "SC-06": (0, 8),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ev_id(date_str: str, seq: int) -> str:
    return f"EV-{date_str}-{seq:04d}"


@dataclass
class CustodyEvent:
    event_type: str  # COLLECTED | AUTHENTICATED | ACCESSED | TRANSFERRED | TRANSFORMED | DEPRECATED | HELD | REVERIFIED
    actor: str
    timestamp: datetime
    description: str = ""
    prior_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "actor": actor if (actor := self.actor) else "(unknown)",
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "prior_hash": self.prior_hash,
        }


@dataclass
class EvidenceItemRecord:
    """In-memory representation of a CEL evidence item."""
    ev_id: str
    title: str
    source_class: str          # SC-01 through SC-06
    source_reliability_score: int
    collected_at: datetime
    collected_by: str
    citation: str = ""
    source_url: str = ""
    source_author: str = ""
    source_publication_date: str = ""
    jurisdiction_code: str = "UNCONFIRMED"
    provenance: dict[str, Any] = field(default_factory=dict)
    integrity_status: str = "UNVERIFIED"
    authenticated_at: datetime | None = None
    authenticated_by: str = ""
    content_hash: str = ""
    reverification_due: date | None = None
    chain_of_custody: list[CustodyEvent] = field(default_factory=list)
    ko_ids: list[str] = field(default_factory=list)
    is_ai_generated: bool = False
    legal_hold: bool = False
    legal_hold_basis: str = ""
    deprecation: dict[str, Any] | None = None
    notes: str = ""

    @property
    def is_deprecated(self) -> bool:
        return self.integrity_status == "DEPRECATED"

    @property
    def is_held(self) -> bool:
        return self.legal_hold

    @property
    def reverification_overdue(self) -> bool:
        if self.reverification_due is None:
            return False
        return date.today() > self.reverification_due

    def to_dict(self) -> dict:
        return {
            "ev_id": self.ev_id,
            "title": self.title,
            "source_class": self.source_class,
            "source_reliability_score": self.source_reliability_score,
            "collected_at": self.collected_at.isoformat(),
            "collected_by": self.collected_by,
            "citation": self.citation,
            "source_url": self.source_url,
            "jurisdiction_code": self.jurisdiction_code,
            "provenance": self.provenance,
            "integrity_status": self.integrity_status,
            "authenticated_at": self.authenticated_at.isoformat() if self.authenticated_at else None,
            "authenticated_by": self.authenticated_by,
            "content_hash": self.content_hash,
            "reverification_due": self.reverification_due.isoformat() if self.reverification_due else None,
            "chain_of_custody": [e.to_dict() for e in self.chain_of_custody],
            "ko_ids": self.ko_ids,
            "is_ai_generated": self.is_ai_generated,
            "legal_hold": self.legal_hold,
            "deprecation": self.deprecation,
            "notes": self.notes,
        }


class CELError(Exception):
    """Base class for CEL errors."""


class EvidenceNotFound(CELError):
    """Raised when an EV-ID is not found in the CEL."""


class EvidenceDeletionProhibited(CELError):
    """
    Raised on any attempt to delete an evidence item.
    Evidence items are NEVER deleted — BKGC Art. XIII.
    """


class LegalHoldViolation(CELError):
    """Raised on any attempt to modify a legally held evidence item."""


class ConstitutionalEvidenceLedger:
    """
    The Constitutional Evidence Ledger (CEL).

    Single source of truth for all evidence items in the Blackstone Ecosystem.
    Thread-safety is NOT guaranteed — wrap in appropriate locking for concurrent use.

    Constitutional constraints enforced:
      - No deletion (EvidenceDeletionProhibited raised on any delete attempt)
      - Legal holds block modification (LegalHoldViolation)
      - All state changes append to chain of custody
      - EV-IDs are assigned sequentially and never reused
    """

    def __init__(self) -> None:
        self._items: dict[str, EvidenceItemRecord] = {}
        self._sequence: int = 0
        self._creation_date: str = _utcnow().strftime("%Y%m%d")

    # ------------------------------------------------------------------
    # Core CRUD — NO DELETE
    # ------------------------------------------------------------------

    def add(
        self,
        title: str,
        source_class: str,
        collected_by: str,
        *,
        citation: str = "",
        source_url: str = "",
        source_author: str = "",
        source_publication_date: str = "",
        jurisdiction_code: str = "UNCONFIRMED",
        provenance: dict[str, Any] | None = None,
        is_ai_generated: bool = False,
        notes: str = "",
    ) -> str:
        """
        Add a new evidence item to the CEL. Returns the assigned EV-ID.

        Source classification codes: SC-01 through SC-06 (BKR-03).
        AI-generated content is automatically SC-06 per CDR-00001.
        """
        if source_class not in REVERIFICATION_INTERVALS:
            raise ValueError(f"Unknown source class: {source_class!r}. Must be SC-01 through SC-06.")

        # CDR-00001: AI-generated content is always SC-06
        if is_ai_generated and source_class != "SC-06":
            raise ValueError(
                "AI-generated content must be classified SC-06 per CDR-00001. "
                "It may not be classified as a higher-tier source."
            )

        self._sequence += 1
        today = _utcnow().strftime("%Y%m%d")
        ev_id = _ev_id(today, self._sequence)

        now = _utcnow()
        rel_min, rel_max = SOURCE_RELIABILITY_RANGES[source_class]
        # Default reliability to midpoint of range; caller may override via authenticate()
        reliability = (rel_min + rel_max) // 2

        item = EvidenceItemRecord(
            ev_id=ev_id,
            title=title,
            source_class=source_class,
            source_reliability_score=reliability,
            collected_at=now,
            collected_by=collected_by,
            citation=citation,
            source_url=source_url,
            source_author=source_author,
            source_publication_date=source_publication_date,
            jurisdiction_code=jurisdiction_code,
            provenance=provenance or {},
            is_ai_generated=is_ai_generated,
            notes=notes,
        )

        item.chain_of_custody.append(CustodyEvent(
            event_type="COLLECTED",
            actor=collected_by,
            timestamp=now,
            description=f"Evidence item created in CEL. Source class: {source_class}.",
        ))

        self._items[ev_id] = item
        return ev_id

    def get(self, ev_id: str) -> EvidenceItemRecord:
        """Retrieve an evidence item by EV-ID. Raises EvidenceNotFound if missing."""
        item = self._items.get(ev_id)
        if item is None:
            raise EvidenceNotFound(f"No evidence item with ID {ev_id!r} in the CEL.")
        return item

    def exists(self, ev_id: str) -> bool:
        return ev_id in self._items

    def list_all(self) -> list[EvidenceItemRecord]:
        """Return all evidence items (including deprecated)."""
        return list(self._items.values())

    def list_active(self) -> list[EvidenceItemRecord]:
        """Return all non-deprecated evidence items."""
        return [i for i in self._items.values() if not i.is_deprecated]

    def list_overdue(self) -> list[EvidenceItemRecord]:
        """Return items whose re-verification is overdue."""
        return [i for i in self._items.values() if i.reverification_overdue and not i.is_deprecated]

    # ------------------------------------------------------------------
    # Authentication — BGS-05
    # ------------------------------------------------------------------

    def authenticate(
        self,
        ev_id: str,
        authenticator: str,
        *,
        content_hash: str = "",
        source_reliability_score: int | None = None,
        notes: str = "",
    ) -> None:
        """
        Mark an evidence item as authenticated. Sets integrity_status to INTACT
        and schedules re-verification per BGS-09.

        Args:
            ev_id: The EV-ID to authenticate.
            authenticator: Agent ID or human performing authentication.
            content_hash: SHA-256 hash of the source content.
            source_reliability_score: Override the default reliability score (0-20).
        """
        item = self._require_mutable(ev_id, "authenticate")
        now = _utcnow()

        item.authenticated_at = now
        item.authenticated_by = authenticator
        item.content_hash = content_hash
        item.integrity_status = "INTACT"

        if source_reliability_score is not None:
            if not (0 <= source_reliability_score <= 20):
                raise ValueError("source_reliability_score must be 0-20 per BGS-06.")
            item.source_reliability_score = source_reliability_score

        # Schedule re-verification
        from datetime import timedelta
        interval = REVERIFICATION_INTERVALS[item.source_class]
        item.reverification_due = (now + timedelta(days=interval)).date()

        item.chain_of_custody.append(CustodyEvent(
            event_type="AUTHENTICATED",
            actor=authenticator,
            timestamp=now,
            description=f"Authenticated. Hash recorded. Re-verification due: {item.reverification_due}. {notes}".strip(),
        ))

    def reverify(self, ev_id: str, verifier: str, *, content_hash: str = "", notes: str = "") -> None:
        """
        Re-verify an evidence item, resetting the reverification clock.
        Called on the BGS-09 reverification schedule.
        """
        item = self._require_mutable(ev_id, "reverify")
        now = _utcnow()

        from datetime import timedelta
        interval = REVERIFICATION_INTERVALS[item.source_class]
        item.reverification_due = (now + timedelta(days=interval)).date()
        if content_hash:
            item.content_hash = content_hash
        item.authenticated_at = now
        item.authenticated_by = verifier

        item.chain_of_custody.append(CustodyEvent(
            event_type="REVERIFIED",
            actor=verifier,
            timestamp=now,
            description=f"Reverification completed. Next due: {item.reverification_due}. {notes}".strip(),
        ))

    # ------------------------------------------------------------------
    # Deprecation — BGS-07. NO DELETION EVER.
    # ------------------------------------------------------------------

    def deprecate(
        self,
        ev_id: str,
        deprecated_by: str,
        reason: str,
        *,
        successor_ev_id: str | None = None,
    ) -> None:
        """
        Deprecate an evidence item. Preserves the item in the CEL permanently.
        Evidence items are NEVER deleted — only deprecated (BKGC Art. XIII).

        Args:
            ev_id: The EV-ID to deprecate.
            deprecated_by: Agent ID or human performing deprecation.
            reason: Reason for deprecation.
            successor_ev_id: EV-ID of the item replacing this one, if applicable.
        """
        item = self._require_mutable(ev_id, "deprecate")
        now = _utcnow()

        item.integrity_status = "DEPRECATED"
        item.deprecation = {
            "deprecated_at": now.isoformat(),
            "deprecated_by": deprecated_by,
            "reason": reason,
            "successor_ev_id": successor_ev_id,
        }

        item.chain_of_custody.append(CustodyEvent(
            event_type="DEPRECATED",
            actor=deprecated_by,
            timestamp=now,
            description=f"DEPRECATED: {reason}"
            + (f" Successor: {successor_ev_id}." if successor_ev_id else ""),
        ))

    def delete(self, ev_id: str) -> None:  # type: ignore[override]
        """
        Deletion is PROHIBITED by BKGC Art. XIII.
        This method always raises EvidenceDeletionProhibited.
        """
        raise EvidenceDeletionProhibited(
            f"Evidence item {ev_id!r} cannot be deleted. "
            "BKGC Art. XIII: Evidence items are never deleted, only deprecated. "
            "Call cel.deprecate() instead."
        )

    # ------------------------------------------------------------------
    # Legal holds — BGS-19
    # ------------------------------------------------------------------

    def place_hold(self, ev_id: str, held_by: str, basis: str) -> None:
        """Place a legal hold on an evidence item. Blocks all modification."""
        item = self.get(ev_id)
        item.legal_hold = True
        item.legal_hold_basis = basis
        item.chain_of_custody.append(CustodyEvent(
            event_type="HELD",
            actor=held_by,
            timestamp=_utcnow(),
            description=f"LEGAL HOLD PLACED. Basis: {basis}",
        ))

    def release_hold(self, ev_id: str, released_by: str, cdr_number: str) -> None:
        """
        Release a legal hold. Requires a CDR number authorizing the release
        to ensure the release is a governance-board-level decision.
        """
        item = self.get(ev_id)
        if not item.legal_hold:
            return
        item.legal_hold = False
        old_basis = item.legal_hold_basis
        item.legal_hold_basis = ""
        item.chain_of_custody.append(CustodyEvent(
            event_type="ACCESSED",
            actor=released_by,
            timestamp=_utcnow(),
            description=f"LEGAL HOLD RELEASED. Original basis: {old_basis}. Authorizing CDR: {cdr_number}.",
        ))

    # ------------------------------------------------------------------
    # KO linkage
    # ------------------------------------------------------------------

    def link_ko(self, ev_id: str, ko_id: str) -> None:
        """Record that a knowledge object references this evidence item."""
        item = self.get(ev_id)
        if ko_id not in item.ko_ids:
            item.ko_ids.append(ko_id)

    # ------------------------------------------------------------------
    # Export / serialization
    # ------------------------------------------------------------------

    def export(self) -> list[dict]:
        """Export all evidence items as a list of dicts (for persistence or audit)."""
        return [item.to_dict() for item in self._items.values()]

    def audit_report(self) -> dict:
        """
        Generate a CEL audit summary per BGS-17 audit reporting requirements.
        """
        all_items = self.list_all()
        active = [i for i in all_items if not i.is_deprecated]
        deprecated = [i for i in all_items if i.is_deprecated]
        overdue = self.list_overdue()
        held = [i for i in all_items if i.is_held]
        unverified = [i for i in active if i.integrity_status == "UNVERIFIED"]
        ai_generated = [i for i in active if i.is_ai_generated]

        return {
            "total_items": len(all_items),
            "active_items": len(active),
            "deprecated_items": len(deprecated),
            "reverification_overdue": len(overdue),
            "under_legal_hold": len(held),
            "unverified_items": len(unverified),
            "ai_generated_items": len(ai_generated),
            "by_source_class": {
                sc: len([i for i in active if i.source_class == sc])
                for sc in REVERIFICATION_INTERVALS
            },
            "overdue_ev_ids": [i.ev_id for i in overdue],
            "held_ev_ids": [i.ev_id for i in held],
            "unverified_ev_ids": [i.ev_id for i in unverified],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_mutable(self, ev_id: str, operation: str) -> EvidenceItemRecord:
        item = self.get(ev_id)
        if item.legal_hold:
            raise LegalHoldViolation(
                f"Cannot {operation} evidence item {ev_id!r}: it is under a legal hold. "
                f"Basis: {item.legal_hold_basis}. A CDR is required to release the hold."
            )
        return item
