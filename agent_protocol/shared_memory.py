"""Shared memory that syncs across all agent instances."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

_PERSIST_PATH = Path(
    "/agent/home/SintraPrime-Unified/agent_protocol/shared_memory.json"
)

_CATEGORIES = {
    "general",
    "legal_knowledge",
    "case_outcomes",
    "trust_templates",
    "precedents",
    "banking",
    "federal",
}


class SharedMemory:
    """
    Key-value store that syncs across all connected SintraPrime agents.

    Architecture
    ------------
    - Each entry is stored as ``(value, vector_clock, category, author, ts)``.
    - **Conflict resolution**: last-write-wins, broken by higher timestamp.
    - **Gossip sync**: when a peer connects, agents exchange their full stores
      (or just the deltas since a given lamport clock value).
    - **Persistence**: data is saved to ``shared_memory.json`` on every write
      so it survives restarts.

    Categories
    ----------
    ``general``, ``legal_knowledge``, ``case_outcomes``, ``trust_templates``,
    ``precedents``, ``banking``, ``federal``
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(f"SharedMemory:{node_id}")
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def set(
        self, key: str, value: Any, category: str = "general"
    ) -> None:
        """Set a value and persist it locally.

        The caller (AgentNode) is responsible for propagating the change to
        peers via SHARE_KNOWLEDGE messages.
        """
        if category not in _CATEGORIES:
            category = "general"

        async with self._lock:
            existing = self._store.get(key, {})
            existing_ts = existing.get("ts", 0)
            new_ts = time.time()

            if new_ts <= existing_ts:
                new_ts = existing_ts + 0.000001  # ensure monotonic

            entry = {
                "value": value,
                "category": category,
                "author": self.node_id,
                "ts": new_ts,
                "version": existing.get("version", 0) + 1,
            }
            self._store[key] = entry
            self.logger.debug("SET %s = %r (cat=%s)", key, value, category)
            self._save_to_disk()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from local store (returns None if not found)."""
        entry = self._store.get(key)
        return entry["value"] if entry else None

    async def get_with_meta(self, key: str) -> Optional[dict]:
        """Get a value along with its metadata dict."""
        return self._store.get(key)

    async def get_category(self, category: str) -> dict[str, Any]:
        """Get all ``{key: value}`` pairs in a given category."""
        return {
            k: v["value"]
            for k, v in self._store.items()
            if v.get("category") == category
        }

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        async with self._lock:
            existed = key in self._store
            if existed:
                del self._store[key]
                self._save_to_disk()
            return existed

    async def keys(self) -> list[str]:
        """Return all stored keys."""
        return list(self._store.keys())

    async def sync_with_peer(self, peer_id: str, peer_store: dict) -> int:
        """
        Merge a peer's store into local store using last-write-wins.

        Parameters
        ----------
        peer_id:
            ID of the peer (for logging).
        peer_store:
            The raw ``_store`` dict from the peer's snapshot.

        Returns
        -------
        int
            Number of items that were updated locally.
        """
        updated = 0
        async with self._lock:
            for key, remote_entry in peer_store.items():
                local_entry = self._store.get(key)
                if local_entry is None or remote_entry.get("ts", 0) > local_entry.get("ts", 0):
                    self._store[key] = remote_entry
                    updated += 1

            if updated:
                self._save_to_disk()
                self.logger.info(
                    "Synced %d item(s) from peer %s", updated, peer_id
                )
        return updated

    def snapshot(self) -> dict:
        """Return a complete copy of the in-memory store (for gossip sync)."""
        return dict(self._store)

    async def merge_entry(self, key: str, remote_entry: dict) -> bool:
        """
        Merge a single remote entry.

        Returns True if the local copy was updated.
        """
        async with self._lock:
            local = self._store.get(key)
            if local is None or remote_entry.get("ts", 0) > local.get("ts", 0):
                self._store[key] = remote_entry
                self._save_to_disk()
                return True
        return False

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_to_disk(self) -> None:
        """Write the store to JSON (called inside lock)."""
        try:
            _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = _PERSIST_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._store, indent=2))
            tmp.replace(_PERSIST_PATH)
        except Exception as exc:
            self.logger.warning("Could not persist shared memory: %s", exc)

    def _load_from_disk(self) -> None:
        """Load store from JSON on startup."""
        if _PERSIST_PATH.exists():
            try:
                data = json.loads(_PERSIST_PATH.read_text())
                if isinstance(data, dict):
                    self._store = data
                    self.logger.info(
                        "Loaded %d item(s) from %s", len(self._store), _PERSIST_PATH
                    )
            except Exception as exc:
                self.logger.warning("Could not load shared memory: %s", exc)
