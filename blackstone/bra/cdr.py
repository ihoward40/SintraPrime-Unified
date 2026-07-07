"""
BRA — CDR Filer
===============
Constitutional Decision Record (CDR) filing and retrieval.

BKGC v2.0 Art. XXXIII; BGS v1.0 BGS-22; BKR-11.

CDR rules encoded here:
  1. CDRs are IMMUTABLE after filing — no modification, ever (BKGC Art. XXXIII).
  2. CDR numbers are sequential and never reused (BKR-02).
  3. Corrections require a NEW CDR referencing the corrected record.
  4. CDR-00001, CDR-00002, CDR-00003 are seeded at initialization (the founding CDRs).

Usage:
    filer = CDRFiler()
    cdr_num = filer.file(
        title="Adoption of Future Volume VI",
        filed_by="Isiah Howard, Founder/CEO, IKE Solutions LLC",
        trigger="Volume VI completion",
        decision="Volume VI is adopted...",
        scope="All agents...",
    )
    record = filer.get(cdr_num)
    print(filer.register())  # Full CDR register as list of dicts
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


@dataclass(frozen=True)
class CDRRecord:
    """
    An immutable CDR record. frozen=True enforces immutability at the Python level.
    Any attempt to modify a field after creation raises FrozenInstanceError.
    """
    cdr_number: str
    title: str
    status: str                    # Approved | Superseded | Withdrawn
    filed_at: str                  # ISO 8601 date
    filed_by: str
    trigger: str
    decision: str
    scope: str
    subordinate_standards_activated: str = ""
    implementation_note: str = ""
    supersedes_cdr: str = ""
    superseded_by_cdr: str = ""
    effective_date: str = ""
    expiry_date: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cdr_number": self.cdr_number,
            "title": self.title,
            "status": self.status,
            "filed_at": self.filed_at,
            "filed_by": self.filed_by,
            "trigger": self.trigger,
            "decision": self.decision,
            "scope": self.scope,
            "subordinate_standards_activated": self.subordinate_standards_activated,
            "implementation_note": self.implementation_note,
            "supersedes_cdr": self.supersedes_cdr,
            "superseded_by_cdr": self.superseded_by_cdr,
            "effective_date": self.effective_date or self.filed_at,
            "expiry_date": self.expiry_date,
            "notes": self.notes,
        }


class CDRFilingError(Exception):
    """Raised on invalid CDR filing attempts."""


class CDRFiler:
    """
    File and retrieve Constitutional Decision Records.

    On initialization, seeds the three founding CDRs (CDR-00001 through CDR-00003)
    per BKR-11. Additional CDRs are filed via .file().
    """

    def __init__(self, seed_founding_cdrs: bool = True) -> None:
        self._records: dict[str, CDRRecord] = {}
        self._sequence: int = 0

        if seed_founding_cdrs:
            self._seed_founding_cdrs()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def file(
        self,
        title: str,
        filed_by: str,
        trigger: str,
        decision: str,
        scope: str,
        *,
        subordinate_standards_activated: str = "",
        implementation_note: str = "",
        supersedes_cdr: str = "",
        effective_date: str = "",
        expiry_date: str = "",
        notes: str = "",
        filed_at: str | None = None,
    ) -> str:
        """
        File a new CDR. Returns the assigned CDR number (e.g. 'CDR-00004').

        CDRs are immutable after filing. If you need to correct a CDR,
        file a new one referencing the corrected record.

        Args:
            title: Short descriptive title.
            filed_by: Governance Board member filing the CDR.
            trigger: What event or milestone triggered this CDR.
            decision: The full text of the decision (immutable after filing).
            scope: Which agents, documents, or processes this applies to.
            supersedes_cdr: CDR number being superseded, if any.

        Returns:
            CDR number string (e.g. 'CDR-00004').
        """
        self._sequence += 1
        cdr_number = f"CDR-{self._sequence:05d}"
        today = filed_at or _today()

        # Mark the superseded CDR
        if supersedes_cdr:
            if supersedes_cdr not in self._records:
                raise CDRFilingError(f"Cannot supersede {supersedes_cdr!r} — not found in register.")
            old = self._records[supersedes_cdr]
            # CDRs are frozen — we must replace the record with an updated one
            updated = CDRRecord(
                cdr_number=old.cdr_number,
                title=old.title,
                status="Superseded",
                filed_at=old.filed_at,
                filed_by=old.filed_by,
                trigger=old.trigger,
                decision=old.decision,
                scope=old.scope,
                subordinate_standards_activated=old.subordinate_standards_activated,
                implementation_note=old.implementation_note,
                supersedes_cdr=old.supersedes_cdr,
                superseded_by_cdr=cdr_number,
                effective_date=old.effective_date,
                expiry_date=old.expiry_date,
                notes=old.notes,
            )
            self._records[supersedes_cdr] = updated

        record = CDRRecord(
            cdr_number=cdr_number,
            title=title,
            status="Approved",
            filed_at=today,
            filed_by=filed_by,
            trigger=trigger,
            decision=decision,
            scope=scope,
            subordinate_standards_activated=subordinate_standards_activated,
            implementation_note=implementation_note,
            supersedes_cdr=supersedes_cdr,
            effective_date=effective_date or today,
            expiry_date=expiry_date,
            notes=notes,
        )
        self._records[cdr_number] = record
        return cdr_number

    def get(self, cdr_number: str) -> CDRRecord:
        """Retrieve a CDR by number. Raises KeyError if not found."""
        record = self._records.get(cdr_number)
        if record is None:
            raise KeyError(f"CDR {cdr_number!r} not found in register.")
        return record

    def exists(self, cdr_number: str) -> bool:
        return cdr_number in self._records

    def register(self) -> list[dict[str, Any]]:
        """Return the full CDR register as a list of dicts, ordered by CDR number."""
        return [r.to_dict() for r in sorted(self._records.values(), key=lambda r: r.cdr_number)]

    def latest(self) -> CDRRecord | None:
        """Return the most recently filed CDR."""
        if not self._records:
            return None
        return max(self._records.values(), key=lambda r: r.cdr_number)

    def next_number(self) -> str:
        """Return what the next CDR number will be (preview, does not file)."""
        return f"CDR-{self._sequence + 1:05d}"

    # ------------------------------------------------------------------
    # Founding CDR seed — BKR-11
    # ------------------------------------------------------------------

    def _seed_founding_cdrs(self) -> None:
        """Seed the three founding CDRs (CDR-00001 through CDR-00003)."""
        founding_cdrs = [
            {
                "title": "AI-Generated Summaries Shall Not Be Treated as Primary Authority",
                "filed_at": "2026-07-06",
                "filed_by": "Governance Board — Isiah Howard, Founder/CEO, IKE Solutions LLC",
                "trigger": "BKGC v2.0 adoption. Constitutional requirement to establish a CDR on adoption per BKGC Art. XXXIII § 33.4.",
                "decision": (
                    "AI-generated summaries, paraphrases, and syntheses of source material shall not be treated as primary authority "
                    "for any claim in the Blackstone Ecosystem. AI-generated content may be used as a research aid to identify potential "
                    "sources, but all claims must be supported by authenticated primary or secondary sources logged in the CEL. "
                    "An AI summary of a case is not the case. An AI paraphrase of a statute is not the statute. "
                    "The underlying source must be independently authenticated per BGS-05 before it may serve as evidentiary support."
                ),
                "scope": (
                    "All agents, all knowledge objects, all maturity stages. No exception. "
                    "Applies to outputs produced by any agent including Viktor, Hermes, Blackstone, and future admitted agents."
                ),
                "implementation_note": "AI-generated summaries are classified SC-06 per BKR-03. They may not serve as primary evidentiary support for claims at Corroborated stage (STG-3) or above.",
            },
            {
                "title": "Adoption of Blackstone Governance Standards (BGS) v1.0 as Volume II",
                "filed_at": "2026-07-06",
                "filed_by": "Governance Board — Isiah Howard, Founder/CEO, IKE Solutions LLC",
                "trigger": "BGS v1.0 completion and adoption as Volume II of the Blackstone Governance Library.",
                "decision": (
                    "The Blackstone Governance Standards (BGS), Version 1.0, dated 2026-07-06, is formally adopted as Volume II "
                    "of the Blackstone Governance Library. BGS v1.0 is operative immediately upon adoption. All agents are governed by "
                    "its 23 standards. BGS may be updated without amending BKGC v2.0, provided no change conflicts with a BKGC v2.0 "
                    "constitutional provision. All future updates to BGS require a new CDR."
                ),
                "scope": "All agents operating in the Ecosystem. BGS v1.0 governs all CCS scoring, evidence authentication, maturity stage transitions, human review triggers, escalation, security, and constitutional administration from the adoption date forward.",
                "subordinate_standards_activated": "BGS-01 through BGS-23. All standards operative simultaneously. No phase-in — full compliance required from adoption date.",
                "implementation_note": "Supersedes any prior informal governance standard regarding CCS scoring, evidence handling, or human review thresholds.",
            },
            {
                "title": "Adoption of Blackstone Certification & Compliance Manual (BCCM) v1.0 as Volume IV",
                "filed_at": "2026-07-06",
                "filed_by": "Governance Board — Isiah Howard, Founder/CEO, IKE Solutions LLC",
                "trigger": "BCCM v1.0 completion and adoption as Volume IV of the Blackstone Governance Library.",
                "decision": (
                    "The Blackstone Certification & Compliance Manual (BCCM), Version 1.0, dated 2026-07-06, is formally adopted as "
                    "Volume IV of the Blackstone Governance Library. BCCM v1.0 is operative immediately upon adoption. BCCM defines "
                    "how compliance with BKGC v2.0 and BGS v1.0 is measured, tested, and verified. It creates no new substantive "
                    "obligations — all obligations originate in BKGC v2.0. Agent certification pursuant to BCCM-01 through BCCM-03 "
                    "is required before any agent performs operations above Research stage on knowledge objects."
                ),
                "scope": "All agents operating in the Ecosystem.",
                "implementation_note": (
                    "Existing agents operating prior to BCCM adoption are granted a 30-day grace period to complete Tier 1 and Tier 2 "
                    "examinations. During the grace period, existing operational activities may continue under Governance Board supervision. "
                    "After 30 days (by 2026-08-05), certification is mandatory for all operational activities above Observer level."
                ),
            },
        ]

        for cdr_data in founding_cdrs:
            self._sequence += 1
            cdr_number = f"CDR-{self._sequence:05d}"
            record = CDRRecord(
                cdr_number=cdr_number,
                title=cdr_data["title"],
                status="Approved",
                filed_at=cdr_data["filed_at"],
                filed_by=cdr_data["filed_by"],
                trigger=cdr_data["trigger"],
                decision=cdr_data["decision"],
                scope=cdr_data["scope"],
                subordinate_standards_activated=cdr_data.get("subordinate_standards_activated", ""),
                implementation_note=cdr_data.get("implementation_note", ""),
            )
            self._records[cdr_number] = record
