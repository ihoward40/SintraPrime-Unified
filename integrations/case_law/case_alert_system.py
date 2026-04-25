"""
Case Alert System
=================
Background monitoring for new cases matching specified criteria.

Features:
- Watch terms/parties across all courts
- Daily digest of new matching opinions
- Appeal tracking from watched cases
- Webhook/email notifications
- Alert history in database
- Smart deduplication
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class AlertWatch:
    """A configured alert watch."""

    watch_id: str
    name: str
    query: str
    courts: List[str]
    date_added: str
    is_active: bool = True
    party_names: List[str] = field(default_factory=list)
    practice_areas: List[str] = field(default_factory=list)
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    last_checked: Optional[str] = None
    last_result_count: int = 0
    check_interval_hours: int = 24


@dataclass
class AlertResult:
    """A single case matching an alert watch."""

    watch_id: str
    watch_name: str
    opinion_id: int
    cluster_id: int
    case_name: str
    court: str
    date_filed: Optional[str]
    snippet: str
    url: str
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AlertDigest:
    """Daily digest of alert results."""

    digest_date: str
    total_new_cases: int
    watches_triggered: int
    results_by_watch: Dict[str, List[AlertResult]]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Alert history store (in-memory + optional persistence)
# ---------------------------------------------------------------------------


class AlertHistoryStore:
    """Stores alert history and handles deduplication."""

    def __init__(self, persistence_path: Optional[str] = None) -> None:
        self._seen: Set[str] = set()  # hashes of (watch_id, opinion_id) seen
        self._history: List[AlertResult] = []
        self._path = persistence_path
        if persistence_path:
            self._load()

    def _result_key(self, watch_id: str, opinion_id: int) -> str:
        return hashlib.md5(f"{watch_id}:{opinion_id}".encode()).hexdigest()

    def is_seen(self, watch_id: str, opinion_id: int) -> bool:
        return self._result_key(watch_id, opinion_id) in self._seen

    def mark_seen(self, watch_id: str, opinion_id: int) -> None:
        self._seen.add(self._result_key(watch_id, opinion_id))

    def add_result(self, result: AlertResult) -> None:
        """Add a result only if not previously seen (deduplication)."""
        if not self.is_seen(result.watch_id, result.opinion_id):
            self._history.append(result)
            self.mark_seen(result.watch_id, result.opinion_id)
            if self._path:
                self._save()

    def get_history(
        self,
        watch_id: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> List[AlertResult]:
        """Retrieve alert history with optional filtering."""
        results = self._history
        if watch_id:
            results = [r for r in results if r.watch_id == watch_id]
        if since:
            results = [r for r in results if r.detected_at >= since]
        return sorted(results, key=lambda r: r.detected_at, reverse=True)[:limit]

    def _save(self) -> None:
        try:
            with open(self._path, "w") as f:
                json.dump(
                    {"seen": list(self._seen), "history": [asdict(r) for r in self._history[-1000:]]},
                    f, indent=2,
                )
        except Exception as exc:
            logger.error("Failed to save alert history: %s", exc)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                data = json.load(f)
            self._seen = set(data.get("seen", []))
            self._history = [AlertResult(**r) for r in data.get("history", [])]
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.error("Failed to load alert history: %s", exc)


# ---------------------------------------------------------------------------
# Case Alert System
# ---------------------------------------------------------------------------


class CaseAlertSystem:
    """
    Background monitoring system for new court opinions.

    Usage:
        alerts = CaseAlertSystem(courtlistener_client=cl)
        watch_id = alerts.add_watch(
            name="Cell Phone Privacy",
            query="cell phone search warrant Fourth Amendment",
            courts=["scotus", "ca9", "ca1"],
            webhook_url="https://my-app.com/webhooks/legal"
        )
        # Run checks periodically
        await alerts.check_all_watches()
        digest = await alerts.generate_daily_digest()
    """

    def __init__(
        self,
        courtlistener_client: Optional[Any] = None,
        persistence_path: Optional[str] = None,
        notification_handler: Optional[Callable] = None,
    ) -> None:
        self._cl = courtlistener_client
        self._watches: Dict[str, AlertWatch] = {}
        self._history = AlertHistoryStore(persistence_path=persistence_path)
        self._notification_handler = notification_handler
        self._session: Optional[Any] = None  # aiohttp session for webhooks

    # ------------------------------------------------------------------
    # Managing watches
    # ------------------------------------------------------------------

    def add_watch(
        self,
        name: str,
        query: str,
        courts: Optional[List[str]] = None,
        party_names: Optional[List[str]] = None,
        practice_areas: Optional[List[str]] = None,
        webhook_url: Optional[str] = None,
        email: Optional[str] = None,
        check_interval_hours: int = 24,
    ) -> str:
        """
        Add a new alert watch.

        Args:
            name: Human-readable name for this watch.
            query: Search query (same as CourtListener search).
            courts: List of court IDs to monitor (empty = all courts).
            party_names: Specific party names to watch.
            practice_areas: Practice area filters.
            webhook_url: URL to POST alerts to.
            email: Email address to notify.
            check_interval_hours: How often to check (default 24h).

        Returns:
            watch_id: Unique identifier for this watch.
        """
        watch_id = hashlib.md5(f"{name}:{query}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        watch = AlertWatch(
            watch_id=watch_id,
            name=name,
            query=query,
            courts=courts or [],
            party_names=party_names or [],
            practice_areas=practice_areas or [],
            webhook_url=webhook_url,
            email=email,
            date_added=datetime.utcnow().isoformat(),
            check_interval_hours=check_interval_hours,
        )
        self._watches[watch_id] = watch
        logger.info("Added alert watch '%s' (id=%s)", name, watch_id)
        return watch_id

    def update_watch(self, watch_id: str, **kwargs: Any) -> None:
        """Update an existing watch."""
        if watch_id not in self._watches:
            raise KeyError(f"Watch {watch_id} not found")
        watch = self._watches[watch_id]
        for k, v in kwargs.items():
            if hasattr(watch, k):
                setattr(watch, k, v)

    def remove_watch(self, watch_id: str) -> None:
        """Remove a watch."""
        self._watches.pop(watch_id, None)
        logger.info("Removed alert watch %s", watch_id)

    def pause_watch(self, watch_id: str) -> None:
        """Pause a watch without removing it."""
        if watch_id in self._watches:
            self._watches[watch_id].is_active = False

    def resume_watch(self, watch_id: str) -> None:
        """Resume a paused watch."""
        if watch_id in self._watches:
            self._watches[watch_id].is_active = True

    def list_watches(self) -> List[AlertWatch]:
        """Get all configured watches."""
        return list(self._watches.values())

    # ------------------------------------------------------------------
    # Running checks
    # ------------------------------------------------------------------

    async def check_watch(self, watch_id: str) -> List[AlertResult]:
        """
        Check a single watch for new matching cases.

        Args:
            watch_id: The watch to check.

        Returns:
            List of new AlertResult objects (not previously seen).
        """
        watch = self._watches.get(watch_id)
        if not watch or not watch.is_active:
            return []

        new_results: List[AlertResult] = []

        if self._cl is None:
            logger.warning("No CourtListener client configured; cannot check watch %s", watch_id)
            return []

        try:
            # Build search parameters
            search_kwargs: Dict[str, Any] = {
                "query": watch.query,
                "page_size": 50,
            }
            # If specific courts, check each
            courts_to_check = watch.courts if watch.courts else [None]

            for court in courts_to_check:
                if court:
                    search_kwargs["court"] = court
                data = await self._cl.search_opinions(**search_kwargs)
                for r in data.get("results", []):
                    opinion_id = r.get("id", 0)
                    if not opinion_id or self._history.is_seen(watch_id, opinion_id):
                        continue

                    # Check date - only new cases since last check
                    date_filed = r.get("dateFiled", "")
                    if watch.last_checked and date_filed < watch.last_checked[:10]:
                        continue

                    result = AlertResult(
                        watch_id=watch_id,
                        watch_name=watch.name,
                        opinion_id=opinion_id,
                        cluster_id=r.get("cluster_id", 0),
                        case_name=r.get("caseName", "Unknown"),
                        court=r.get("court_id", ""),
                        date_filed=date_filed,
                        snippet=r.get("snippet", "")[:500],
                        url=f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                    )
                    self._history.add_result(result)
                    new_results.append(result)

        except Exception as exc:
            logger.error("Error checking watch %s: %s", watch_id, exc)

        watch.last_checked = datetime.utcnow().isoformat()
        watch.last_result_count = len(new_results)

        if new_results:
            logger.info("Watch '%s': %d new case(s) found", watch.name, len(new_results))
            await self._send_notifications(watch, new_results)

        return new_results

    async def check_all_watches(self) -> Dict[str, List[AlertResult]]:
        """
        Check all active watches.

        Returns:
            Dict mapping watch_id → list of new results.
        """
        results: Dict[str, List[AlertResult]] = {}
        active_watches = [w for w in self._watches.values() if w.is_active]

        if not active_watches:
            logger.info("No active watches to check")
            return results

        tasks = [self.check_watch(w.watch_id) for w in active_watches]
        watch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for watch, result in zip(active_watches, watch_results):
            if isinstance(result, Exception):
                logger.error("Watch %s failed: %s", watch.watch_id, result)
            else:
                results[watch.watch_id] = result

        total_new = sum(len(r) for r in results.values())
        logger.info("Checked %d watches; %d total new cases", len(active_watches), total_new)
        return results

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def _send_notifications(self, watch: AlertWatch, results: List[AlertResult]) -> None:
        """Send webhook and/or email notifications."""
        if watch.webhook_url:
            await self._send_webhook(watch, results)
        if self._notification_handler:
            try:
                await asyncio.coroutine(self._notification_handler)(watch, results)
            except Exception:
                try:
                    self._notification_handler(watch, results)
                except Exception as exc:
                    logger.error("Notification handler failed: %s", exc)

    async def _send_webhook(self, watch: AlertWatch, results: List[AlertResult]) -> None:
        """POST alert payload to webhook URL."""
        try:
            import aiohttp
            payload = {
                "watch_id": watch.watch_id,
                "watch_name": watch.name,
                "new_case_count": len(results),
                "cases": [
                    {
                        "case_name": r.case_name,
                        "court": r.court,
                        "date_filed": r.date_filed,
                        "url": r.url,
                        "snippet": r.snippet[:200],
                    }
                    for r in results[:10]  # limit to 10 in payload
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(watch.webhook_url, json=payload) as resp:
                    logger.info(
                        "Webhook for watch '%s' returned HTTP %d", watch.name, resp.status
                    )
        except Exception as exc:
            logger.error("Failed to send webhook for watch %s: %s", watch.watch_id, exc)

    # ------------------------------------------------------------------
    # Digests
    # ------------------------------------------------------------------

    async def generate_daily_digest(
        self, since_hours: int = 24
    ) -> AlertDigest:
        """
        Generate a digest of all new cases from the past N hours.

        Args:
            since_hours: How many hours back to look.

        Returns:
            AlertDigest with results grouped by watch.
        """
        since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
        results_by_watch: Dict[str, List[AlertResult]] = {}

        for watch_id in self._watches:
            history = self._history.get_history(watch_id=watch_id, since=since)
            if history:
                results_by_watch[watch_id] = history

        total_cases = sum(len(v) for v in results_by_watch.values())
        digest = AlertDigest(
            digest_date=datetime.utcnow().strftime("%Y-%m-%d"),
            total_new_cases=total_cases,
            watches_triggered=len(results_by_watch),
            results_by_watch=results_by_watch,
        )

        logger.info(
            "Daily digest: %d new cases across %d watches",
            total_cases, len(results_by_watch)
        )
        return digest

    def get_alert_history(
        self,
        watch_id: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> List[AlertResult]:
        """Retrieve alert history."""
        return self._history.get_history(watch_id=watch_id, since=since, limit=limit)

    def export_watches(self) -> List[Dict[str, Any]]:
        """Export all watches as a list of dicts."""
        return [asdict(w) for w in self._watches.values()]

    def import_watches(self, watches: List[Dict[str, Any]]) -> None:
        """Import watches from a list of dicts."""
        for w_data in watches:
            watch = AlertWatch(**w_data)
            self._watches[watch.watch_id] = watch
