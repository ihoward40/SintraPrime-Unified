"""
Regulatory Monitor
==================
Monitors federal agency rules via the Federal Register and CFR.

Features:
- Monitor Federal Register for new proposed/final rules
- Track CFR section changes
- Agency-specific monitoring (EPA, FDA, FTC, SEC, CFPB, etc.)
- Comment period tracking
- Regulatory docket monitoring (regulations.gov)
- Alert on rules affecting specific industries/topics
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RegulatoryAction:
    """A regulatory action in the Federal Register."""

    document_number: str
    title: str
    agency: str
    agency_acronym: str
    action_type: str       # "Proposed Rule", "Final Rule", "Notice", "Rule"
    abstract: str
    publication_date: str
    effective_date: Optional[str]
    comment_deadline: Optional[str]
    cfr_references: List[str]
    docket_id: Optional[str]
    url: str
    full_text_url: Optional[str] = None
    regulations_gov_url: Optional[str] = None


@dataclass
class CFRSection:
    """A CFR section being monitored."""

    title: int          # CFR Title number
    part: str           # CFR Part
    section: Optional[str]
    heading: str
    agency: str
    last_amended: Optional[str]
    text_hash: Optional[str] = None


@dataclass
class RegWatch:
    """A regulatory monitoring watch."""

    watch_id: str
    name: str
    keywords: List[str]
    agencies: List[str]          # agency acronyms: ["EPA", "FDA"]
    action_types: List[str]      # ["Proposed Rule", "Final Rule"]
    cfr_titles: List[int]        # CFR title numbers
    date_added: str
    is_active: bool = True
    webhook_url: Optional[str] = None
    last_checked: Optional[str] = None


# ---------------------------------------------------------------------------
# Known major federal agencies
# ---------------------------------------------------------------------------

FEDERAL_AGENCIES: Dict[str, str] = {
    "EPA": "Environmental Protection Agency",
    "FDA": "Food and Drug Administration",
    "FTC": "Federal Trade Commission",
    "SEC": "Securities and Exchange Commission",
    "CFPB": "Consumer Financial Protection Bureau",
    "DOJ": "Department of Justice",
    "DOL": "Department of Labor",
    "HHS": "Department of Health and Human Services",
    "DOE": "Department of Energy",
    "OSHA": "Occupational Safety and Health Administration",
    "FCC": "Federal Communications Commission",
    "NLRB": "National Labor Relations Board",
    "IRS": "Internal Revenue Service",
    "FinCEN": "Financial Crimes Enforcement Network",
    "OCC": "Office of the Comptroller of the Currency",
    "FDIC": "Federal Deposit Insurance Corporation",
    "FED": "Federal Reserve System",
    "DOT": "Department of Transportation",
    "FAA": "Federal Aviation Administration",
    "FMCSA": "Federal Motor Carrier Safety Administration",
    "DHS": "Department of Homeland Security",
    "CBP": "U.S. Customs and Border Protection",
    "ICE": "Immigration and Customs Enforcement",
    "USCIS": "U.S. Citizenship and Immigration Services",
    "NRC": "Nuclear Regulatory Commission",
    "CFTC": "Commodity Futures Trading Commission",
    "FERC": "Federal Energy Regulatory Commission",
}


class RegulatoryMonitor:
    """
    Monitor federal regulatory activity via Federal Register API.

    Federal Register API: https://www.federalregister.gov/api/v1/
    Regulations.gov API: https://api.regulations.gov/v4/

    Usage:
        monitor = RegulatoryMonitor()
        # Search for new rules
        rules = await monitor.search_federal_register(
            keywords=["data privacy", "artificial intelligence"],
            agencies=["FTC", "SEC"],
            action_types=["Proposed Rule"]
        )
        # Add a watch
        watch_id = monitor.add_watch(
            name="AI Regulation",
            keywords=["artificial intelligence", "machine learning", "algorithm"],
            agencies=["FTC", "SEC", "CFPB"]
        )
        await monitor.check_all_watches()
    """

    FR_API = "https://www.federalregister.gov/api/v1/"
    REGULATIONS_GOV_API = "https://api.regulations.gov/v4/"

    def __init__(
        self,
        regulations_gov_api_key: Optional[str] = None,
        timeout: int = 20,
    ) -> None:
        self._reg_gov_key = regulations_gov_api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._watches: Dict[str, RegWatch] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._alert_history: List[Dict[str, Any]] = []

    async def __aenter__(self) -> "RegulatoryMonitor":
        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            headers={"User-Agent": "SintraPrime Regulatory Monitor/1.0"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    # ------------------------------------------------------------------
    # Federal Register search
    # ------------------------------------------------------------------

    async def search_federal_register(
        self,
        keywords: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None,
        action_types: Optional[List[str]] = None,
        cfr_titles: Optional[List[int]] = None,
        publication_date_gte: Optional[str] = None,
        publication_date_lte: Optional[str] = None,
        per_page: int = 20,
        page: int = 1,
    ) -> List[RegulatoryAction]:
        """
        Search the Federal Register for regulatory actions.

        Args:
            keywords: Search terms.
            agencies: Agency acronym list (e.g., ["EPA", "FDA"]).
            action_types: Document types to include.
            cfr_titles: CFR title numbers to filter by.
            publication_date_gte: Start date (YYYY-MM-DD).
            publication_date_lte: End date (YYYY-MM-DD).
            per_page: Results per page.
            page: Page number.

        Returns:
            List of RegulatoryAction objects.
        """
        params: Dict[str, Any] = {
            "per_page": per_page,
            "page": page,
            "order": "newest",
        }

        if keywords:
            params["conditions[term]"] = " ".join(keywords)

        if agencies:
            # Map acronyms to agency slugs
            agency_slugs = [a.lower().replace(" ", "-") for a in agencies]
            for i, slug in enumerate(agency_slugs):
                params[f"conditions[agencies][]"] = slug

        if action_types:
            type_map = {
                "Proposed Rule": "PRORULE",
                "Final Rule": "RULE",
                "Notice": "NOTICE",
                "Presidential Document": "PRESDOCU",
            }
            for i, at in enumerate(action_types):
                params[f"conditions[type][]"] = type_map.get(at, at.upper())

        if cfr_titles:
            for t in cfr_titles:
                params[f"conditions[cfr][title]"] = t

        if publication_date_gte:
            params["conditions[publication_date][gte]"] = publication_date_gte
        if publication_date_lte:
            params["conditions[publication_date][lte]"] = publication_date_lte

        params["fields[]"] = [
            "document_number", "title", "agencies", "type", "abstract",
            "publication_date", "effective_on", "comment_date",
            "cfr_references", "docket_ids", "html_url", "full_text_xml_url",
        ]

        session = self._ensure_session()
        url = f"{self.FR_API}documents.json"

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Federal Register API returned HTTP %d", resp.status)
                    return []
                data = await resp.json()
        except Exception as exc:
            logger.error("Federal Register search failed: %s", exc)
            return []

        results = []
        for doc in data.get("results", []):
            agencies_list = doc.get("agencies", [])
            agency_name = agencies_list[0].get("name", "") if agencies_list else ""
            agency_acronym = agencies_list[0].get("short_name", "") if agencies_list else ""

            cfr_refs = [
                f"CFR Title {r.get('title')} Part {r.get('part')}"
                for r in doc.get("cfr_references", [])
            ]
            docket_ids = doc.get("docket_ids", [])

            results.append(
                RegulatoryAction(
                    document_number=doc.get("document_number", ""),
                    title=doc.get("title", ""),
                    agency=agency_name,
                    agency_acronym=agency_acronym,
                    action_type=doc.get("type", ""),
                    abstract=doc.get("abstract", "")[:500] if doc.get("abstract") else "",
                    publication_date=doc.get("publication_date", ""),
                    effective_date=doc.get("effective_on"),
                    comment_deadline=doc.get("comment_date"),
                    cfr_references=cfr_refs,
                    docket_id=docket_ids[0] if docket_ids else None,
                    url=doc.get("html_url", ""),
                    full_text_url=doc.get("full_text_xml_url"),
                )
            )

        return results

    async def get_document(self, document_number: str) -> Optional[RegulatoryAction]:
        """Get a specific Federal Register document by number."""
        session = self._ensure_session()
        url = f"{self.FR_API}documents/{document_number}.json"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                doc = await resp.json()
        except Exception:
            return None

        agencies_list = doc.get("agencies", [])
        return RegulatoryAction(
            document_number=doc.get("document_number", ""),
            title=doc.get("title", ""),
            agency=agencies_list[0].get("name", "") if agencies_list else "",
            agency_acronym=agencies_list[0].get("short_name", "") if agencies_list else "",
            action_type=doc.get("type", ""),
            abstract=(doc.get("abstract") or "")[:500],
            publication_date=doc.get("publication_date", ""),
            effective_date=doc.get("effective_on"),
            comment_deadline=doc.get("comment_date"),
            cfr_references=[],
            docket_id=None,
            url=doc.get("html_url", ""),
        )

    async def get_recent_rules(
        self, days: int = 7, agencies: Optional[List[str]] = None
    ) -> List[RegulatoryAction]:
        """Get all rules published in the last N days."""
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        return await self.search_federal_register(
            agencies=agencies,
            action_types=["Final Rule", "Proposed Rule"],
            publication_date_gte=since,
            per_page=50,
        )

    async def get_open_comment_periods(
        self, agencies: Optional[List[str]] = None
    ) -> List[RegulatoryAction]:
        """Get all rules with open comment periods."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        actions = await self.search_federal_register(
            agencies=agencies,
            action_types=["Proposed Rule"],
            per_page=50,
        )
        return [a for a in actions if a.comment_deadline and a.comment_deadline >= today]

    # ------------------------------------------------------------------
    # Regulations.gov docket search
    # ------------------------------------------------------------------

    async def search_regulations_gov(
        self,
        docket_id: Optional[str] = None,
        keyword: Optional[str] = None,
        agency_id: Optional[str] = None,
        document_type: Optional[str] = None,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """
        Search regulations.gov for dockets and documents.

        Requires REGULATIONS_GOV_API_KEY environment variable.
        """
        if not self._reg_gov_key:
            import os
            self._reg_gov_key = os.getenv("REGULATIONS_GOV_API_KEY", "")

        params: Dict[str, Any] = {
            "api_key": self._reg_gov_key,
            "page[size]": page_size,
        }
        if keyword:
            params["filter[searchTerm]"] = keyword
        if agency_id:
            params["filter[agencyId]"] = agency_id
        if document_type:
            params["filter[documentType]"] = document_type

        session = self._ensure_session()
        url = f"{self.REGULATIONS_GOV_API}documents"
        if docket_id:
            params["filter[docketId]"] = docket_id

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Regulations.gov returned HTTP %d", resp.status)
                    return {}
                return await resp.json()
        except Exception as exc:
            logger.error("Regulations.gov search failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Watches
    # ------------------------------------------------------------------

    def add_watch(
        self,
        name: str,
        keywords: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None,
        action_types: Optional[List[str]] = None,
        cfr_titles: Optional[List[int]] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Add a regulatory monitoring watch.

        Args:
            name: Descriptive name for this watch.
            keywords: Terms to watch for.
            agencies: Agency acronyms to monitor.
            action_types: Types of actions to watch.
            cfr_titles: CFR title numbers.
            webhook_url: Webhook for alerts.

        Returns:
            watch_id: Unique watch identifier.
        """
        watch_id = hashlib.md5(f"{name}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        watch = RegWatch(
            watch_id=watch_id,
            name=name,
            keywords=keywords or [],
            agencies=agencies or [],
            action_types=action_types or ["Proposed Rule", "Final Rule"],
            cfr_titles=cfr_titles or [],
            date_added=datetime.utcnow().isoformat(),
            webhook_url=webhook_url,
        )
        self._watches[watch_id] = watch
        logger.info("Added regulatory watch: %s", name)
        return watch_id

    def remove_watch(self, watch_id: str) -> None:
        """Remove a watch."""
        self._watches.pop(watch_id, None)

    async def check_all_watches(self) -> Dict[str, List[RegulatoryAction]]:
        """
        Check all active regulatory watches for new actions.

        Returns:
            Dict mapping watch_id → list of new RegulatoryAction objects.
        """
        results: Dict[str, List[RegulatoryAction]] = {}
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for watch_id, watch in self._watches.items():
            if not watch.is_active:
                continue
            try:
                since = watch.last_checked[:10] if watch.last_checked else (
                    (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
                )
                actions = await self.search_federal_register(
                    keywords=watch.keywords or None,
                    agencies=watch.agencies or None,
                    action_types=watch.action_types or None,
                    cfr_titles=watch.cfr_titles or None,
                    publication_date_gte=since,
                    per_page=25,
                )
                results[watch_id] = actions
                watch.last_checked = datetime.utcnow().isoformat()

                if actions and watch.webhook_url:
                    await self._send_webhook(watch, actions)

                logger.info(
                    "Regulatory watch '%s': %d new actions", watch.name, len(actions)
                )
            except Exception as exc:
                logger.error("Error checking watch %s: %s", watch_id, exc)
                results[watch_id] = []

        return results

    async def _send_webhook(self, watch: RegWatch, actions: List[RegulatoryAction]) -> None:
        """Send webhook notification."""
        payload = {
            "watch_id": watch.watch_id,
            "watch_name": watch.name,
            "new_action_count": len(actions),
            "actions": [
                {
                    "title": a.title,
                    "agency": a.agency,
                    "type": a.action_type,
                    "published": a.publication_date,
                    "url": a.url,
                }
                for a in actions[:5]
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
        session = self._ensure_session()
        try:
            await session.post(watch.webhook_url, json=payload)
        except Exception as exc:
            logger.error("Webhook failed for watch %s: %s", watch.watch_id, exc)

    def get_agency_list(self) -> Dict[str, str]:
        """Get the full list of tracked federal agencies."""
        return dict(FEDERAL_AGENCIES)

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
