"""
PACER Navigator
===============
Interface for public PACER (Public Access to Court Electronic Records) data.

PACER Case Locator: https://pcl.uscourts.gov/pcl/pages/search/findCase.jsf
No login required for basic case location and public docket summaries.

Features:
- Case search by party name, case number, court
- Docket entry listing
- Filing date tracking
- Case status monitoring
- Alert on new filings for tracked cases
- Export case information to structured format
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PACERError(Exception):
    """Base PACER navigator exception."""


class PACERSearchError(PACERError):
    """Error performing a PACER search."""


class PACERParseError(PACERError):
    """Error parsing PACER HTML response."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PACERCase:
    """Represents a case found in PACER."""

    case_id: str
    case_number: str
    case_title: str
    court_id: str
    court_name: str
    date_filed: Optional[str]
    date_closed: Optional[str]
    case_type: str
    cause: str
    nature_of_suit: Optional[str]
    jurisdiction: str
    presiding_judge: Optional[str]
    referred_judge: Optional[str]
    pacer_case_id: Optional[str] = None
    is_active: bool = True


@dataclass
class DocketEntry:
    """A single entry on a PACER docket."""

    entry_number: int
    date_filed: str
    description: str
    documents: List[str] = field(default_factory=list)
    filed_by: Optional[str] = None
    doc_count: int = 0


@dataclass
class TrackedCase:
    """A case being monitored for new filings."""

    case_id: str
    case_number: str
    court_id: str
    last_entry_number: int = 0
    last_checked: Optional[str] = None
    alert_webhook: Optional[str] = None
    notes: str = ""


# ---------------------------------------------------------------------------
# PACER Navigator
# ---------------------------------------------------------------------------


class PACERNavigator:
    """
    Navigates public PACER data sources.

    Uses the PACER Case Locator for case searches (no auth required)
    and CourtListener's PACER mirror data where available.

    Args:
        courtlistener_token: Optional CL token for enhanced PACER data.
        timeout: HTTP timeout in seconds.
    """

    PCL_BASE = "https://pcl.uscourts.gov/pcl/pages/search/findCase.jsf"
    CL_RECAP_BASE = "https://www.courtlistener.com/api/rest/v4/"

    def __init__(
        self,
        courtlistener_token: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self._cl_token = courtlistener_token
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._tracked_cases: Dict[str, TrackedCase] = {}

    async def __aenter__(self) -> "PACERNavigator":
        headers = {
            "User-Agent": "SintraPrime/1.0 Legal Research Bot",
            "Accept": "text/html,application/json",
        }
        if self._cl_token:
            headers["Authorization"] = f"Token {self._cl_token}"
        self._session = aiohttp.ClientSession(
            headers=headers, timeout=self._timeout
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    # ------------------------------------------------------------------
    # Case search (via CourtListener RECAP mirror)
    # ------------------------------------------------------------------

    async def search_cases(
        self,
        party_name: Optional[str] = None,
        case_number: Optional[str] = None,
        court_id: Optional[str] = None,
        nature_of_suit: Optional[str] = None,
        date_filed_min: Optional[str] = None,
        date_filed_max: Optional[str] = None,
        page_size: int = 20,
    ) -> List[PACERCase]:
        """
        Search PACER cases via CourtListener's RECAP mirror.

        Args:
            party_name: Search by party/case name.
            case_number: Specific docket number.
            court_id: CourtListener court identifier (e.g. "dcd", "nysd").
            nature_of_suit: NOS code or description.
            date_filed_min: ISO date lower bound.
            date_filed_max: ISO date upper bound.
            page_size: Number of results.

        Returns:
            List of PACERCase objects.
        """
        params: Dict[str, Any] = {
            "page_size": page_size,
            "type": "r",  # RECAP type
        }
        if party_name:
            params["case_name"] = party_name
        if case_number:
            params["docket_number"] = case_number
        if court_id:
            params["court"] = court_id
        if nature_of_suit:
            params["nature_of_suit"] = nature_of_suit
        if date_filed_min:
            params["filed_after"] = date_filed_min
        if date_filed_max:
            params["filed_before"] = date_filed_max

        session = self._ensure_session()
        url = f"{self.CL_RECAP_BASE}dockets/"
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise PACERSearchError(f"RECAP API returned HTTP {resp.status}")
            data = await resp.json()

        return [self._parse_cl_docket(d) for d in data.get("results", [])]

    def _parse_cl_docket(self, d: Dict[str, Any]) -> PACERCase:
        """Convert CourtListener docket data to PACERCase."""
        return PACERCase(
            case_id=str(d.get("id", "")),
            case_number=d.get("docket_number", ""),
            case_title=d.get("case_name", "Unknown"),
            court_id=d.get("court_id", ""),
            court_name=d.get("court", ""),
            date_filed=d.get("date_filed"),
            date_closed=d.get("date_terminated"),
            case_type=d.get("jurisdiction_type", ""),
            cause=d.get("cause", ""),
            nature_of_suit=d.get("nature_of_suit"),
            jurisdiction=d.get("jurisdiction_type", ""),
            presiding_judge=d.get("assigned_to_str"),
            referred_judge=d.get("referred_to_str"),
            pacer_case_id=d.get("pacer_case_id"),
            is_active=d.get("date_terminated") is None,
        )

    # ------------------------------------------------------------------
    # Docket entries
    # ------------------------------------------------------------------

    async def get_docket_entries(
        self, docket_id: str, page_size: int = 50
    ) -> List[DocketEntry]:
        """
        Retrieve docket entries for a case.

        Args:
            docket_id: CourtListener docket ID.
            page_size: Entries per page.

        Returns:
            List of DocketEntry objects sorted by entry number.
        """
        session = self._ensure_session()
        url = f"{self.CL_RECAP_BASE}docket-entries/"
        params = {"docket": docket_id, "page_size": page_size, "order_by": "entry_number"}

        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise PACERSearchError(f"Docket entries API returned HTTP {resp.status}")
            data = await resp.json()

        entries = []
        for item in data.get("results", []):
            entries.append(
                DocketEntry(
                    entry_number=item.get("entry_number", 0),
                    date_filed=item.get("date_filed", ""),
                    description=item.get("description", ""),
                    documents=[
                        d.get("filepath_local", "")
                        for d in item.get("recap_documents", [])
                    ],
                    doc_count=len(item.get("recap_documents", [])),
                )
            )
        return sorted(entries, key=lambda e: e.entry_number)

    # ------------------------------------------------------------------
    # Case status monitoring
    # ------------------------------------------------------------------

    def track_case(
        self,
        case_id: str,
        case_number: str,
        court_id: str,
        alert_webhook: Optional[str] = None,
        notes: str = "",
    ) -> TrackedCase:
        """
        Begin tracking a case for new filings.

        Args:
            case_id: CourtListener docket ID.
            case_number: Human-readable docket number.
            court_id: Court identifier.
            alert_webhook: Optional URL to POST alerts to.
            notes: Free-form notes about why this case is tracked.

        Returns:
            The TrackedCase instance.
        """
        tracked = TrackedCase(
            case_id=case_id,
            case_number=case_number,
            court_id=court_id,
            last_checked=datetime.utcnow().isoformat(),
            alert_webhook=alert_webhook,
            notes=notes,
        )
        self._tracked_cases[case_id] = tracked
        logger.info("Now tracking case %s (%s)", case_number, court_id)
        return tracked

    def untrack_case(self, case_id: str) -> None:
        """Stop tracking a case."""
        self._tracked_cases.pop(case_id, None)

    async def check_for_new_filings(self) -> Dict[str, List[DocketEntry]]:
        """
        Check all tracked cases for new docket entries since last check.

        Returns:
            Dict mapping case_id → list of new DocketEntry objects.
        """
        new_filings: Dict[str, List[DocketEntry]] = {}

        for case_id, tracked in self._tracked_cases.items():
            try:
                entries = await self.get_docket_entries(case_id)
                new_entries = [
                    e for e in entries if e.entry_number > tracked.last_entry_number
                ]
                if new_entries:
                    new_filings[case_id] = new_entries
                    tracked.last_entry_number = max(e.entry_number for e in entries)
                    logger.info(
                        "Case %s: %d new filing(s)",
                        tracked.case_number,
                        len(new_entries),
                    )
                    if tracked.alert_webhook:
                        await self._send_webhook_alert(tracked, new_entries)
                tracked.last_checked = datetime.utcnow().isoformat()
            except Exception as exc:
                logger.error("Error checking case %s: %s", case_id, exc)

        return new_filings

    async def _send_webhook_alert(
        self, tracked: TrackedCase, new_entries: List[DocketEntry]
    ) -> None:
        """Send a webhook notification for new docket entries."""
        import json

        payload = {
            "case_id": tracked.case_id,
            "case_number": tracked.case_number,
            "court_id": tracked.court_id,
            "new_entry_count": len(new_entries),
            "entries": [
                {
                    "entry_number": e.entry_number,
                    "date_filed": e.date_filed,
                    "description": e.description,
                }
                for e in new_entries
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

        session = self._ensure_session()
        try:
            async with session.post(
                tracked.alert_webhook,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                logger.info("Webhook alert sent for %s: HTTP %d", tracked.case_number, resp.status)
        except Exception as exc:
            logger.error("Failed to send webhook for %s: %s", tracked.case_number, exc)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_case_to_dict(self, case: PACERCase) -> Dict[str, Any]:
        """Export a PACERCase to a serializable dict."""
        return asdict(case)

    def get_tracked_cases_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all tracked cases."""
        return [
            {
                "case_id": t.case_id,
                "case_number": t.case_number,
                "court_id": t.court_id,
                "last_checked": t.last_checked,
                "last_entry_number": t.last_entry_number,
                "notes": t.notes,
            }
            for t in self._tracked_cases.values()
        ]

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
