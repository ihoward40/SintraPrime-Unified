"""
Congress.gov API Client
========================
Integrates with https://api.congress.gov/v3/ for legislative intelligence.

Set CONGRESS_API_KEY in environment variables (free key at api.congress.gov).

Features:
- Search bills by keyword, status, sponsor
- Track bill progress through committees
- Get bill full text and summaries
- Amendment tracking
- Presidential action tracking
- Committee hearings
- Member voting records
- Legislative history for any statute
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CongressAPIError(Exception):
    """Base exception for Congress API errors."""


class CongressRateLimitError(CongressAPIError):
    """Rate limit exceeded."""


class CongressNotFoundError(CongressAPIError):
    """Resource not found."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Bill:
    """Represents a congressional bill."""

    congress: int
    bill_type: str  # hr, s, hjres, sjres, hconres, sconres, hres, sres
    bill_number: str
    title: str
    introduced_date: Optional[str]
    sponsor_name: Optional[str]
    sponsor_party: Optional[str]
    sponsor_state: Optional[str]
    latest_action: Optional[str]
    latest_action_date: Optional[str]
    status: str
    policy_area: Optional[str]
    subjects: List[str] = field(default_factory=list)
    cosponsors_count: int = 0
    committees: List[str] = field(default_factory=list)
    url: Optional[str] = None

    @property
    def identifier(self) -> str:
        return f"{self.bill_type.upper()} {self.bill_number} ({self.congress}th)"


@dataclass
class BillAction:
    """A single action in a bill's legislative history."""

    action_date: str
    action_code: Optional[str]
    text: str
    action_type: str
    committee: Optional[str] = None
    recorded_votes: List[str] = field(default_factory=list)


@dataclass
class Amendment:
    """A bill amendment."""

    congress: int
    amendment_type: str
    amendment_number: str
    sponsor_name: Optional[str]
    description: str
    purpose: Optional[str]
    proposed_date: Optional[str]
    latest_action: Optional[str]
    chamber: str


@dataclass
class CommitteeHearing:
    """Congressional committee hearing."""

    committee_code: str
    committee_name: str
    hearing_date: str
    title: str
    location: str
    url: Optional[str]
    witnesses: List[str] = field(default_factory=list)


@dataclass
class Member:
    """Congressional member."""

    bioguide_id: str
    name: str
    party: str
    state: str
    chamber: str
    district: Optional[str]
    is_current: bool
    terms: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class VoteRecord:
    """A congressional vote record."""

    roll_number: int
    chamber: str
    congress: int
    session: str
    vote_date: str
    question: str
    result: str
    description: str
    yeas: int
    nays: int
    abstain: int
    member_vote: Optional[str] = None  # "Yea", "Nay", "Not Voting"


# ---------------------------------------------------------------------------
# Congress API Client
# ---------------------------------------------------------------------------


class CongressAPIClient:
    """
    Async client for the Congress.gov API v3.

    Args:
        api_key: Congress.gov API key (or set CONGRESS_API_KEY env var).
        base_url: Override the base API URL.
        max_retries: Number of retries on transient errors.
    """

    BASE_URL = "https://api.congress.gov/v3/"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key or os.getenv("CONGRESS_API_KEY", "")
        self._base_url = base_url
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "CongressAPIClient":
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "SintraPrime/1.0"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self._session

    def _build_params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"api_key": self._api_key, "format": "json"}
        if extra:
            params.update(extra)
        return params

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a GET request with retries."""
        url = self._base_url + endpoint.lstrip("/")
        all_params = self._build_params(params)

        for attempt in range(self._max_retries + 1):
            try:
                session = self._ensure_session()
                async with session.get(url, params=all_params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        raise CongressRateLimitError("Congress.gov rate limit exceeded")
                    elif resp.status == 404:
                        raise CongressNotFoundError(f"Not found: {url}")
                    else:
                        text = await resp.text()
                        raise CongressAPIError(f"HTTP {resp.status}: {text[:200]}")
            except (CongressRateLimitError, aiohttp.ClientError) as exc:
                if attempt >= self._max_retries:
                    raise
                wait = 2 ** attempt
                logger.warning("Retry %d after error: %s (waiting %ds)", attempt + 1, exc, wait)
                await asyncio.sleep(wait)

        raise CongressAPIError("Max retries exceeded")

    # ------------------------------------------------------------------
    # Bills
    # ------------------------------------------------------------------

    async def search_bills(
        self,
        query: str,
        congress: Optional[int] = None,
        bill_type: Optional[str] = None,
        status: Optional[str] = None,
        subject: Optional[str] = None,
        sponsor: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search bills by keyword and filters.

        Args:
            query: Full-text search term.
            congress: Congress number (e.g., 118 for 118th Congress).
            bill_type: hr, s, hjres, sjres, etc.
            status: Filter by status.
            subject: Policy subject area.
            sponsor: Sponsor name or bioguide ID.
            limit: Results per page (max 250).
            offset: Pagination offset.

        Returns:
            Raw API response dict with 'bills' list.
        """
        params: Dict[str, Any] = {"q": query, "limit": limit, "offset": offset}
        if congress:
            params["congress"] = congress
        if bill_type:
            params["billType"] = bill_type
        if subject:
            params["subject"] = subject
        return await self._get("bill", params)

    async def get_bill(self, congress: int, bill_type: str, bill_number: str) -> Dict[str, Any]:
        """
        Get detailed bill information.

        Args:
            congress: Congress number.
            bill_type: Bill type code (hr, s, etc.).
            bill_number: Bill number.
        """
        return await self._get(f"bill/{congress}/{bill_type}/{bill_number}")

    async def get_bill_actions(
        self, congress: int, bill_type: str, bill_number: str
    ) -> List[BillAction]:
        """Get full action history for a bill."""
        data = await self._get(f"bill/{congress}/{bill_type}/{bill_number}/actions")
        actions = []
        for a in data.get("actions", []):
            actions.append(
                BillAction(
                    action_date=a.get("actionDate", ""),
                    action_code=a.get("actionCode"),
                    text=a.get("text", ""),
                    action_type=a.get("type", ""),
                    committee=a.get("committees", [{}])[0].get("name") if a.get("committees") else None,
                )
            )
        return sorted(actions, key=lambda x: x.action_date)

    async def get_bill_text(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Get bill text versions."""
        return await self._get(f"bill/{congress}/{bill_type}/{bill_number}/text")

    async def get_bill_amendments(
        self, congress: int, bill_type: str, bill_number: str
    ) -> List[Amendment]:
        """Get all amendments to a bill."""
        data = await self._get(f"bill/{congress}/{bill_type}/{bill_number}/amendments")
        amendments = []
        for a in data.get("amendments", []):
            amendments.append(
                Amendment(
                    congress=a.get("congress", congress),
                    amendment_type=a.get("type", ""),
                    amendment_number=str(a.get("number", "")),
                    sponsor_name=a.get("sponsor", {}).get("fullName") if a.get("sponsor") else None,
                    description=a.get("description", ""),
                    purpose=a.get("purpose"),
                    proposed_date=a.get("proposedDate"),
                    latest_action=a.get("latestAction", {}).get("text"),
                    chamber=a.get("chamber", ""),
                )
            )
        return amendments

    async def get_bill_cosponsors(
        self, congress: int, bill_type: str, bill_number: str
    ) -> List[Dict[str, Any]]:
        """Get list of bill cosponsors."""
        data = await self._get(f"bill/{congress}/{bill_type}/{bill_number}/cosponsors")
        return data.get("cosponsors", [])

    async def get_bill_committees(
        self, congress: int, bill_type: str, bill_number: str
    ) -> List[Dict[str, Any]]:
        """Get committees that considered this bill."""
        data = await self._get(f"bill/{congress}/{bill_type}/{bill_number}/committees")
        return data.get("committees", [])

    async def get_bill_related(
        self, congress: int, bill_type: str, bill_number: str
    ) -> List[Dict[str, Any]]:
        """Get related bills."""
        data = await self._get(f"bill/{congress}/{bill_type}/{bill_number}/relatedbills")
        return data.get("relatedBills", [])

    async def get_bills_by_subject(
        self, subject: str, congress: Optional[int] = None, limit: int = 20
    ) -> Dict[str, Any]:
        """Get all bills related to a subject/policy area."""
        params: Dict[str, Any] = {"limit": limit}
        if congress:
            params["congress"] = congress
        return await self._get(f"bill", params={"q": subject, "limit": limit})

    # ------------------------------------------------------------------
    # Bill tracking / progress
    # ------------------------------------------------------------------

    async def get_bill_status(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """
        Get current status and progress of a bill.

        Returns a structured status dict with:
        - current_stage: where the bill is in the legislative process
        - actions_summary: key milestones
        - presidential_action: if any
        """
        bill_data = await self.get_bill(congress, bill_type, bill_number)
        actions = await self.get_bill_actions(congress, bill_type, bill_number)
        bill = bill_data.get("bill", {})

        stages = {
            "introduced": False,
            "committee": False,
            "floor_vote": False,
            "passed_chamber": False,
            "passed_both_chambers": False,
            "presidential_action": False,
            "enacted": False,
        }
        presidential_action = None

        for action in actions:
            text_lower = action.text.lower()
            if "introduced" in text_lower:
                stages["introduced"] = True
            if "committee" in text_lower or "referred to" in text_lower:
                stages["committee"] = True
            if "vote" in text_lower:
                stages["floor_vote"] = True
            if "passed" in text_lower:
                stages["passed_chamber"] = True
                if "senate" in text_lower and "house" in text_lower:
                    stages["passed_both_chambers"] = True
            if "president" in text_lower or "signed" in text_lower or "vetoed" in text_lower:
                stages["presidential_action"] = True
                presidential_action = action.text
            if "became law" in text_lower or "public law" in text_lower:
                stages["enacted"] = True

        current_stage = "introduced"
        for stage, reached in stages.items():
            if reached:
                current_stage = stage

        return {
            "identifier": f"{bill_type.upper()} {bill_number} ({congress}th)",
            "title": bill.get("title", ""),
            "current_stage": current_stage,
            "stages_completed": stages,
            "latest_action": bill.get("latestAction", {}).get("text"),
            "latest_action_date": bill.get("latestAction", {}).get("actionDate"),
            "presidential_action": presidential_action,
            "total_actions": len(actions),
        }

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------

    async def get_member(self, bioguide_id: str) -> Dict[str, Any]:
        """Get congressional member information."""
        return await self._get(f"member/{bioguide_id}")

    async def get_member_votes(
        self, bioguide_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get voting record for a member."""
        data = await self._get(f"member/{bioguide_id}/sponsored-legislation", {"limit": limit})
        return data.get("sponsoredLegislation", [])

    async def list_members(
        self,
        congress: Optional[int] = None,
        chamber: Optional[str] = None,
        state: Optional[str] = None,
        party: Optional[str] = None,
        limit: int = 50,
    ) -> List[Member]:
        """List congressional members with optional filtering."""
        params: Dict[str, Any] = {"limit": limit}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        if state:
            params["stateCode"] = state

        data = await self._get("member", params)
        members = []
        for m in data.get("members", []):
            members.append(
                Member(
                    bioguide_id=m.get("bioguideId", ""),
                    name=m.get("name", ""),
                    party=m.get("partyName", ""),
                    state=m.get("state", ""),
                    chamber=m.get("terms", [{}])[-1].get("chamber", "") if m.get("terms") else "",
                    district=m.get("district"),
                    is_current=m.get("currentMember", False),
                    terms=m.get("terms", []),
                )
            )
        return members

    # ------------------------------------------------------------------
    # Committees
    # ------------------------------------------------------------------

    async def list_committees(
        self,
        congress: Optional[int] = None,
        chamber: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List congressional committees."""
        params: Dict[str, Any] = {"limit": limit}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        data = await self._get("committee", params)
        return data.get("committees", [])

    async def get_committee_hearings(
        self,
        committee_code: str,
        congress: Optional[int] = None,
        limit: int = 20,
    ) -> List[CommitteeHearing]:
        """Get hearings for a specific committee."""
        params: Dict[str, Any] = {"limit": limit}
        if congress:
            params["congress"] = congress
        try:
            data = await self._get(f"committee-hearing", params)
        except CongressNotFoundError:
            return []

        hearings = []
        for h in data.get("hearings", []):
            hearings.append(
                CommitteeHearing(
                    committee_code=committee_code,
                    committee_name=h.get("chamber", ""),
                    hearing_date=h.get("date", ""),
                    title=h.get("title", ""),
                    location=h.get("locCode", ""),
                    url=h.get("url"),
                    witnesses=[w.get("name", "") for w in h.get("witnesses", [])],
                )
            )
        return hearings

    # ------------------------------------------------------------------
    # Congressional records and nominations
    # ------------------------------------------------------------------

    async def get_congressional_record(
        self, year: int, month: int, day: int
    ) -> Dict[str, Any]:
        """Get Congressional Record for a specific date."""
        return await self._get(
            f"congressional-record/{year}/{month}/{day}"
        )

    async def search_nominations(
        self, query: str, congress: Optional[int] = None, limit: int = 20
    ) -> Dict[str, Any]:
        """Search presidential nominations."""
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if congress:
            params["congress"] = congress
        return await self._get("nomination", params)

    # ------------------------------------------------------------------
    # Legislative history for statutes
    # ------------------------------------------------------------------

    async def get_legislative_history(
        self,
        statute_citation: str,
        congress: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve legislative history for a US Code citation.

        Args:
            statute_citation: e.g. "42 U.S.C. 1983" or bill-style "HR 1234 118".
            congress: Narrow to a specific Congress.

        Returns:
            Dict with bills, actions, amendments, and related measures.
        """
        # Search for bills matching the citation
        bills_data = await self.search_bills(
            query=statute_citation,
            congress=congress,
            limit=5,
        )
        bills = bills_data.get("bills", [])
        if not bills:
            return {"statute": statute_citation, "history": [], "error": "No bills found"}

        # Get detailed action history for top matching bill
        top_bill = bills[0]
        bc = top_bill.get("congress")
        bt = top_bill.get("type", "").lower()
        bn = str(top_bill.get("number", ""))

        actions = []
        if bc and bt and bn:
            try:
                bill_actions = await self.get_bill_actions(bc, bt, bn)
                actions = [asdict(a) for a in bill_actions]
            except Exception:
                pass

        return {
            "statute": statute_citation,
            "primary_bill": top_bill,
            "related_bills": bills[1:],
            "action_history": actions,
        }

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
