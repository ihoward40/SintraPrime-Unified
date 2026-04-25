"""
Legal News Aggregator
=====================
Aggregates legal news from multiple sources into a unified feed.

Sources:
- SCOTUSblog (RSS)
- Law360 RSS feeds
- Above the Law RSS
- Law.com
- National Law Review
- ABA Journal
- Jurist Legal News
- Reuters Legal
- CourtListener opinion announcements
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A single legal news item."""

    title: str
    source: str
    url: str
    published: Optional[str]
    summary: str
    categories: List[str] = field(default_factory=list)
    author: Optional[str] = None
    item_id: str = ""

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = hashlib.md5(self.url.encode()).hexdigest()[:12]


@dataclass
class NewsFeed:
    """Configuration for a legal news RSS/Atom feed."""

    name: str
    url: str
    categories: List[str] = field(default_factory=list)
    is_active: bool = True


# ---------------------------------------------------------------------------
# Configured feeds
# ---------------------------------------------------------------------------

DEFAULT_FEEDS: List[NewsFeed] = [
    NewsFeed(
        name="SCOTUSblog",
        url="https://www.scotusblog.com/feed/",
        categories=["supreme court", "federal", "constitutional law"],
    ),
    NewsFeed(
        name="Above the Law",
        url="https://abovethelaw.com/feed/",
        categories=["legal industry", "law firms", "lawyers"],
    ),
    NewsFeed(
        name="ABA Journal",
        url="https://www.abajournal.com/news/rss",
        categories=["bar association", "legal profession", "ethics"],
    ),
    NewsFeed(
        name="Jurist Legal News",
        url="https://jurist.org/feed",
        categories=["international law", "human rights", "legal news"],
    ),
    NewsFeed(
        name="National Law Review",
        url="https://www.natlawreview.com/rss.xml",
        categories=["business law", "employment", "IP", "regulatory"],
    ),
    NewsFeed(
        name="Law360 Top News",
        url="https://www.law360.com/rss/articles",
        categories=["litigation", "corporate", "regulatory"],
    ),
    NewsFeed(
        name="The Volokh Conspiracy",
        url="https://reason.com/volokh/feed/",
        categories=["constitutional law", "first amendment", "second amendment"],
    ),
    NewsFeed(
        name="PACER/CourtListener Announcements",
        url="https://free.law/rss.xml",
        categories=["court data", "PACER", "legal technology"],
    ),
]


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


class LegalNewsAggregator:
    """
    Aggregates legal news from multiple RSS/Atom sources.

    Usage:
        aggregator = LegalNewsAggregator()
        await aggregator.fetch_all()
        items = aggregator.get_items(categories=["supreme court"], limit=20)
    """

    def __init__(
        self,
        feeds: Optional[List[NewsFeed]] = None,
        timeout: int = 15,
        max_items_per_feed: int = 50,
    ) -> None:
        self._feeds = feeds if feeds is not None else list(DEFAULT_FEEDS)
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_items = max_items_per_feed
        self._items: List[NewsItem] = []
        self._seen_ids: set = set()
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "LegalNewsAggregator":
        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            headers={"User-Agent": "SintraPrime Legal News Aggregator/1.0"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    async def fetch_feed(self, feed: NewsFeed) -> List[NewsItem]:
        """
        Fetch and parse a single RSS/Atom feed.

        Args:
            feed: The NewsFeed configuration.

        Returns:
            List of NewsItem parsed from the feed.
        """
        session = self._ensure_session()
        try:
            async with session.get(feed.url) as resp:
                if resp.status != 200:
                    logger.warning("Feed %s returned HTTP %d", feed.name, resp.status)
                    return []
                text = await resp.text()
        except asyncio.TimeoutError:
            logger.warning("Timeout fetching feed: %s", feed.name)
            return []
        except Exception as exc:
            logger.error("Error fetching feed %s: %s", feed.name, exc)
            return []

        try:
            return self._parse_rss(text, feed)
        except Exception as exc:
            logger.error("Error parsing feed %s: %s", feed.name, exc)
            return []

    def _parse_rss(self, xml_text: str, feed: NewsFeed) -> List[NewsItem]:
        """Parse RSS 2.0 or Atom XML."""
        items: List[NewsItem] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            # Try stripping BOM / bad chars
            xml_text = xml_text.lstrip("\ufeff").strip()
            root = ET.fromstring(xml_text)

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "")
            author = item.findtext("author", item.findtext("dc:creator", "", {"dc": "http://purl.org/dc/elements/1.1/"}))

            # Parse categories
            cats = [c.text for c in item.findall("category") if c.text]

            published = None
            if pub_date:
                try:
                    published = parsedate_to_datetime(pub_date).isoformat()
                except Exception:
                    published = pub_date

            desc_clean = re.sub(r"<[^>]+>", " ", desc).strip()[:500]

            items.append(
                NewsItem(
                    title=title,
                    source=feed.name,
                    url=link,
                    published=published,
                    summary=desc_clean,
                    categories=feed.categories + cats,
                    author=author or None,
                )
            )
            if len(items) >= self._max_items:
                break

        # Atom feed fallback
        if not items:
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", entry.findtext("atom:content", "", ns), ns)
                summary_clean = re.sub(r"<[^>]+>", " ", summary or "").strip()[:500]
                published = entry.findtext("atom:published", entry.findtext("atom:updated", "", ns), ns)

                items.append(
                    NewsItem(
                        title=title,
                        source=feed.name,
                        url=link,
                        published=published,
                        summary=summary_clean,
                        categories=feed.categories,
                    )
                )
                if len(items) >= self._max_items:
                    break

        return items

    async def fetch_all(
        self, active_only: bool = True
    ) -> Dict[str, List[NewsItem]]:
        """
        Fetch all configured feeds concurrently.

        Args:
            active_only: Only fetch active feeds.

        Returns:
            Dict mapping feed name → list of new NewsItem objects.
        """
        feeds = [f for f in self._feeds if f.is_active] if active_only else self._feeds

        tasks = [self.fetch_feed(f) for f in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        feed_results: Dict[str, List[NewsItem]] = {}
        new_total = 0

        for feed, result in zip(feeds, results):
            if isinstance(result, Exception):
                logger.error("Feed %s failed: %s", feed.name, result)
                feed_results[feed.name] = []
                continue

            new_items = []
            for item in result:
                if item.item_id not in self._seen_ids:
                    self._seen_ids.add(item.item_id)
                    self._items.append(item)
                    new_items.append(item)

            feed_results[feed.name] = new_items
            new_total += len(new_items)

        logger.info("Fetched %d new items from %d feeds", new_total, len(feeds))
        return feed_results

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_items(
        self,
        query: Optional[str] = None,
        categories: Optional[List[str]] = None,
        source: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> List[NewsItem]:
        """
        Query aggregated news items with filters.

        Args:
            query: Full-text search in title and summary.
            categories: Filter by category tags.
            source: Filter by source name.
            since: ISO datetime; only return items after this.
            limit: Max items to return.

        Returns:
            List of matching NewsItem sorted by published date (newest first).
        """
        items = list(self._items)

        if source:
            items = [i for i in items if i.source.lower() == source.lower()]

        if since:
            items = [i for i in items if (i.published or "0") >= since]

        if categories:
            cats_lower = [c.lower() for c in categories]
            items = [
                i for i in items
                if any(cat in [c.lower() for c in i.categories] for cat in cats_lower)
            ]

        if query:
            q_lower = query.lower()
            items = [
                i for i in items
                if q_lower in i.title.lower() or q_lower in i.summary.lower()
            ]

        # Sort by published date, newest first
        items.sort(key=lambda i: i.published or "0", reverse=True)
        return items[:limit]

    def get_trending_topics(self, top_n: int = 10) -> List[str]:
        """Identify trending legal topics from recent news."""
        from collections import Counter
        words: List[str] = []
        for item in self._items[-200:]:  # last 200 items
            text = (item.title + " " + item.summary).lower()
            # Extract meaningful multi-word phrases
            tokens = re.findall(r'\b[a-z]{4,}\b', text)
            words.extend(tokens)

        # Filter stop words
        stop_words = {
            "that", "this", "with", "from", "have", "been", "will", "more",
            "also", "about", "they", "their", "which", "court", "case", "legal",
            "says", "said", "year", "first", "after", "into", "over",
        }
        words = [w for w in words if w not in stop_words]
        counter = Counter(words)
        return [word for word, _ in counter.most_common(top_n)]

    def add_feed(self, feed: NewsFeed) -> None:
        """Add a custom news feed."""
        self._feeds.append(feed)

    def remove_feed(self, name: str) -> None:
        """Remove a feed by name."""
        self._feeds = [f for f in self._feeds if f.name != name]

    def clear_cache(self) -> None:
        """Clear all cached news items."""
        self._items.clear()
        self._seen_ids.clear()

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
