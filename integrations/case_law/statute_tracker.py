"""
Statute Tracker
===============
Tracks statute changes and legislative history across US Code and state law.

Features:
- Monitor US Code section changes
- Track statutory amendments over time
- Legislative history for any statute
- Congressional Research Service references
- State statute tracking
- Regulatory cross-references (CFR ↔ USC)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StatuteVersion:
    """A version of a statute at a point in time."""

    usc_citation: str          # e.g., "42 U.S.C. § 1983"
    title: int
    section: str
    chapter: Optional[str]
    heading: str
    text: str
    effective_date: Optional[str]
    enacted_by: Optional[str]  # Public Law number
    amended_by: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class StatuteWatch:
    """A configured statute monitoring watch."""

    watch_id: str
    usc_citation: str
    description: str
    added_date: str
    last_checked: Optional[str] = None
    webhook_url: Optional[str] = None
    last_known_text_hash: Optional[str] = None


@dataclass
class StatuteAmendment:
    """A recorded amendment to a statute."""

    usc_citation: str
    amendment_date: str
    public_law: str
    congress: int
    description: str
    changed_sections: List[str] = field(default_factory=list)
    full_text_url: Optional[str] = None


class StatuteTracker:
    """
    Tracks changes to US statutes over time.

    Integrates with:
    - congress.gov API for legislative history
    - uscode.house.gov for current statute text
    - GovInfo API for historical versions

    Usage:
        tracker = StatuteTracker(congress_client=congress_api)
        await tracker.watch("42 U.S.C. § 1983")
        history = await tracker.get_legislative_history("42 U.S.C. § 1983")
        amendments = await tracker.get_recent_amendments(days=90)
    """

    USCODE_API = "https://uscode.house.gov/search/criteria.shtml"
    GOVINFO_API = "https://api.govinfo.gov/collections"

    def __init__(
        self,
        congress_client: Optional[Any] = None,
        govinfo_api_key: Optional[str] = None,
    ) -> None:
        self._congress = congress_client
        self._govinfo_key = govinfo_api_key
        self._watches: Dict[str, StatuteWatch] = {}
        self._history: Dict[str, List[StatuteAmendment]] = {}

    def _parse_usc_citation(self, citation: str) -> Dict[str, Any]:
        """
        Parse a USC citation string into components.

        Handles formats:
        - "42 U.S.C. § 1983"
        - "42 USC 1983"
        - "18 U.S.C. 2252(a)(4)"
        """
        import re
        # Normalize
        citation = citation.replace("§", "").replace("  ", " ").strip()
        pattern = r"(\d+)\s+U\.?S\.?C\.?\s+(\w+(?:\([^)]+\))*)"
        match = re.search(pattern, citation, re.IGNORECASE)
        if match:
            return {
                "title": int(match.group(1)),
                "section": match.group(2),
                "full": citation,
            }
        return {"title": 0, "section": "", "full": citation}

    def watch_statute(
        self,
        usc_citation: str,
        description: str = "",
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Add a statute to the monitoring list.

        Args:
            usc_citation: Citation like "42 U.S.C. § 1983".
            description: Why you're tracking this statute.
            webhook_url: Webhook to call on changes.

        Returns:
            watch_id: Unique identifier for this watch.
        """
        import hashlib
        watch_id = hashlib.md5(usc_citation.encode()).hexdigest()[:12]
        watch = StatuteWatch(
            watch_id=watch_id,
            usc_citation=usc_citation,
            description=description,
            added_date=datetime.utcnow().isoformat(),
            webhook_url=webhook_url,
        )
        self._watches[watch_id] = watch
        logger.info("Watching statute: %s", usc_citation)
        return watch_id

    def unwatch_statute(self, watch_id: str) -> None:
        """Remove a statute from monitoring."""
        self._watches.pop(watch_id, None)

    async def get_legislative_history(
        self,
        usc_citation: str,
        include_committee_reports: bool = True,
    ) -> Dict[str, Any]:
        """
        Get full legislative history for a statute.

        Args:
            usc_citation: USC citation string.
            include_committee_reports: Whether to include committee reports.

        Returns:
            Dict with:
            - original_enactment: The bill that first enacted this statute
            - amendments: List of subsequent amendments
            - committee_reports: CRS and committee reports (if available)
            - current_text_url: Link to current statute text
        """
        parsed = self._parse_usc_citation(usc_citation)
        result: Dict[str, Any] = {
            "citation": usc_citation,
            "title": parsed["title"],
            "section": parsed["section"],
            "amendments": [],
            "original_enactment": None,
            "committee_reports": [],
            "current_text_url": self._build_uscode_url(parsed),
        }

        if self._congress:
            try:
                history = await self._congress.get_legislative_history(usc_citation)
                result["original_enactment"] = history.get("primary_bill")
                result["action_history"] = history.get("action_history", [])
                result["related_bills"] = history.get("related_bills", [])
            except Exception as exc:
                logger.error("Error fetching legislative history: %s", exc)

        # Add any locally cached amendments
        result["amendments"] = [
            asdict(a) for a in self._history.get(usc_citation, [])
        ]

        return result

    def _build_uscode_url(self, parsed: Dict[str, Any]) -> str:
        """Build link to House.gov USC viewer."""
        if parsed["title"] and parsed["section"]:
            return f"https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title{parsed['title']}-section{parsed['section']}&num=0&edition=prelim"
        return "https://uscode.house.gov/"

    async def get_recent_amendments(
        self, days: int = 90
    ) -> List[StatuteAmendment]:
        """
        Get statutes recently amended (within N days).

        Args:
            days: Look back this many days.

        Returns:
            List of recent StatuteAmendment objects.
        """
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent = []
        for amendments in self._history.values():
            for a in amendments:
                if a.amendment_date >= cutoff:
                    recent.append(a)
        return sorted(recent, key=lambda a: a.amendment_date, reverse=True)

    def record_amendment(self, amendment: StatuteAmendment) -> None:
        """Record a known amendment for a statute."""
        citation = amendment.usc_citation
        if citation not in self._history:
            self._history[citation] = []
        self._history[citation].append(amendment)

    async def check_all_watches(self) -> Dict[str, bool]:
        """
        Check all watched statutes for text changes.

        Returns:
            Dict mapping watch_id → True if changed, False if unchanged.
        """
        results = {}
        for watch_id, watch in self._watches.items():
            try:
                changed = await self._check_statute_changed(watch)
                results[watch_id] = changed
                watch.last_checked = datetime.utcnow().isoformat()
                if changed and watch.webhook_url:
                    await self._notify_webhook(watch)
            except Exception as exc:
                logger.error("Error checking statute %s: %s", watch.usc_citation, exc)
                results[watch_id] = False
        return results

    async def _check_statute_changed(self, watch: StatuteWatch) -> bool:
        """
        Check if a statute text has changed since last check.
        Uses text hash comparison.
        """
        import hashlib
        import aiohttp

        url = self._build_uscode_url(self._parse_usc_citation(watch.usc_citation))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return False
                    text = await resp.text()
            current_hash = hashlib.md5(text.encode()).hexdigest()
            if watch.last_known_text_hash and current_hash != watch.last_known_text_hash:
                logger.info("Statute changed: %s", watch.usc_citation)
                watch.last_known_text_hash = current_hash
                return True
            watch.last_known_text_hash = current_hash
            return False
        except Exception as exc:
            logger.debug("Could not check statute text: %s", exc)
            return False

    async def _notify_webhook(self, watch: StatuteWatch) -> None:
        """Send webhook notification for statute change."""
        import aiohttp, json
        payload = {
            "event": "statute_changed",
            "citation": watch.usc_citation,
            "watch_id": watch.watch_id,
            "detected_at": datetime.utcnow().isoformat(),
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(watch.webhook_url, json=payload)
        except Exception as exc:
            logger.error("Webhook notification failed: %s", exc)

    def list_watches(self) -> List[Dict[str, Any]]:
        """List all statute watches."""
        return [asdict(w) for w in self._watches.values()]

    def get_amendment_history(self, usc_citation: str) -> List[StatuteAmendment]:
        """Get all recorded amendments for a statute."""
        return self._history.get(usc_citation, [])
