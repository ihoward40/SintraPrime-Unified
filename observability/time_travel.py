"""
Time-Travel Debugger for SintraPrime-Unified
Snapshot agent state at decision points; rewind, diff, and branch.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Snapshot model
# ---------------------------------------------------------------------------

@dataclass
class Snapshot:
    """Immutable snapshot of agent state at a decision point."""
    snapshot_id: str
    session_id: str
    agent_name: str
    label: str
    state: Dict[str, Any]
    timestamp: float
    parent_snapshot_id: Optional[str] = None
    branch_name: str = "main"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        agent_name: str,
        state: Dict[str, Any],
        label: str = "",
        parent_snapshot_id: Optional[str] = None,
        branch_name: str = "main",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Snapshot":
        return cls(
            snapshot_id=str(uuid.uuid4()),
            session_id=session_id,
            agent_name=agent_name,
            label=label or f"snap-{int(time.time())}",
            state=copy.deepcopy(state),
            timestamp=time.time(),
            parent_snapshot_id=parent_snapshot_id,
            branch_name=branch_name,
            tags=tags or [],
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp_iso"] = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc
        ).isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Snapshot":
        d = dict(d)
        d.pop("timestamp_iso", None)
        return cls(**d)


# ---------------------------------------------------------------------------
# Diff utilities
# ---------------------------------------------------------------------------

def _diff_values(a: Any, b: Any, path: str, diffs: List[Dict[str, Any]]) -> None:
    """Recursively compute differences between two values."""
    if type(a) != type(b):
        diffs.append({"path": path, "old": a, "new": b, "kind": "type_change"})
        return
    if isinstance(a, dict):
        all_keys = set(a) | set(b)
        for k in sorted(all_keys):
            child_path = f"{path}.{k}" if path else k
            if k not in a:
                diffs.append({"path": child_path, "old": None, "new": b[k], "kind": "added"})
            elif k not in b:
                diffs.append({"path": child_path, "old": a[k], "new": None, "kind": "removed"})
            else:
                _diff_values(a[k], b[k], child_path, diffs)
    elif isinstance(a, list):
        max_len = max(len(a), len(b))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(a):
                diffs.append({"path": child_path, "old": None, "new": b[i], "kind": "added"})
            elif i >= len(b):
                diffs.append({"path": child_path, "old": a[i], "new": None, "kind": "removed"})
            else:
                _diff_values(a[i], b[i], child_path, diffs)
    else:
        if a != b:
            diffs.append({"path": path, "old": a, "new": b, "kind": "changed"})


def diff_snapshots(snap_a: Snapshot, snap_b: Snapshot) -> Dict[str, Any]:
    """
    Compute a structured diff between two snapshots.
    Returns a dict with summary and list of field-level changes.
    """
    diffs: List[Dict[str, Any]] = []
    _diff_values(snap_a.state, snap_b.state, "", diffs)

    return {
        "from_snapshot": snap_a.snapshot_id,
        "to_snapshot": snap_b.snapshot_id,
        "from_label": snap_a.label,
        "to_label": snap_b.label,
        "from_agent": snap_a.agent_name,
        "to_agent": snap_b.agent_name,
        "time_delta_s": snap_b.timestamp - snap_a.timestamp,
        "changes_count": len(diffs),
        "changes": diffs,
        "summary": {
            "added": sum(1 for d in diffs if d["kind"] == "added"),
            "removed": sum(1 for d in diffs if d["kind"] == "removed"),
            "changed": sum(1 for d in diffs if d["kind"] == "changed"),
            "type_change": sum(1 for d in diffs if d["kind"] == "type_change"),
        },
    }


# ---------------------------------------------------------------------------
# SQLite snapshot store
# ---------------------------------------------------------------------------

class SnapshotStore:
    """Persistent SQLite-backed store for snapshots."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_id       TEXT PRIMARY KEY,
        session_id        TEXT NOT NULL,
        agent_name        TEXT NOT NULL,
        label             TEXT,
        state_json        TEXT NOT NULL,
        timestamp         REAL NOT NULL,
        parent_snapshot_id TEXT,
        branch_name       TEXT DEFAULT 'main',
        tags_json         TEXT DEFAULT '[]',
        metadata_json     TEXT DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_snap_session ON snapshots(session_id);
    CREATE INDEX IF NOT EXISTS idx_snap_branch  ON snapshots(branch_name);
    CREATE INDEX IF NOT EXISTS idx_snap_ts      ON snapshots(timestamp);
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(self.SCHEMA)
        conn.commit()

    def save(self, snap: Snapshot) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO snapshots
            (snapshot_id, session_id, agent_name, label, state_json, timestamp,
             parent_snapshot_id, branch_name, tags_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snap.snapshot_id,
                snap.session_id,
                snap.agent_name,
                snap.label,
                json.dumps(snap.state),
                snap.timestamp,
                snap.parent_snapshot_id,
                snap.branch_name,
                json.dumps(snap.tags),
                json.dumps(snap.metadata),
            ),
        )
        conn.commit()

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()
        return self._row_to_snapshot(row) if row else None

    def list_for_session(self, session_id: str) -> List[Snapshot]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def list_for_branch(self, branch_name: str) -> List[Snapshot]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE branch_name = ? ORDER BY timestamp ASC",
            (branch_name,),
        ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def list_all(self, limit: int = 200) -> List[Snapshot]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def delete(self, snapshot_id: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
        conn.commit()

    def count(self) -> int:
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
        return Snapshot(
            snapshot_id=row["snapshot_id"],
            session_id=row["session_id"],
            agent_name=row["agent_name"],
            label=row["label"] or "",
            state=json.loads(row["state_json"]),
            timestamp=row["timestamp"],
            parent_snapshot_id=row["parent_snapshot_id"],
            branch_name=row["branch_name"] or "main",
            tags=json.loads(row["tags_json"] or "[]"),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ---------------------------------------------------------------------------
# TimeTravelDebugger
# ---------------------------------------------------------------------------

class TimeTravelDebugger:
    """
    Main time-travel debugging interface.

    Workflow:
        ttd = TimeTravelDebugger(db_path="snapshots.db")
        session_id = ttd.start_session("legal-workflow-42")
        snap1 = ttd.checkpoint(session_id, "LegalAgent", {"contract": "v1"}, "before-review")
        snap2 = ttd.checkpoint(session_id, "LegalAgent", {"contract": "v2"}, "after-review")

        # Rewind to snap1 and re-execute
        state = ttd.rewind(snap1.snapshot_id)
        # ... agent re-executes with state ...

        # Diff
        diff = ttd.diff(snap1.snapshot_id, snap2.snapshot_id)

        # Branch from snap1 to try alternative
        branch_snap = ttd.branch(snap1.snapshot_id, new_state, "alternative-branch")
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.store = SnapshotStore(db_path)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._rewind_callbacks: List[Callable[[Snapshot], None]] = []

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self, name: str = "") -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "name": name,
            "started_at": time.time(),
            "active_branch": "main",
        }
        return session_id

    def session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Checkpoint / snapshot
    # ------------------------------------------------------------------

    def checkpoint(
        self,
        session_id: str,
        agent_name: str,
        state: Dict[str, Any],
        label: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """Create a snapshot of the current agent state."""
        session = self._sessions.get(session_id, {})
        branch = session.get("active_branch", "main")

        # find latest snap in this session as parent
        existing = self.store.list_for_session(session_id)
        parent_id = existing[-1].snapshot_id if existing else None

        snap = Snapshot.create(
            session_id=session_id,
            agent_name=agent_name,
            state=state,
            label=label,
            parent_snapshot_id=parent_id,
            branch_name=branch,
            tags=tags,
            metadata=metadata,
        )
        self.store.save(snap)
        return snap

    # ------------------------------------------------------------------
    # Rewind
    # ------------------------------------------------------------------

    def rewind(self, snapshot_id: str) -> Dict[str, Any]:
        """Return the state at a given snapshot for re-execution."""
        snap = self.store.get(snapshot_id)
        if snap is None:
            raise KeyError(f"Snapshot not found: {snapshot_id}")
        for cb in self._rewind_callbacks:
            try:
                cb(snap)
            except Exception:
                pass
        return copy.deepcopy(snap.state)

    def register_rewind_callback(self, cb: Callable[[Snapshot], None]) -> None:
        self._rewind_callbacks.append(cb)

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def diff(self, snapshot_id_a: str, snapshot_id_b: str) -> Dict[str, Any]:
        snap_a = self.store.get(snapshot_id_a)
        snap_b = self.store.get(snapshot_id_b)
        if snap_a is None:
            raise KeyError(f"Snapshot not found: {snapshot_id_a}")
        if snap_b is None:
            raise KeyError(f"Snapshot not found: {snapshot_id_b}")
        return diff_snapshots(snap_a, snap_b)

    # ------------------------------------------------------------------
    # Branch
    # ------------------------------------------------------------------

    def branch(
        self,
        from_snapshot_id: str,
        new_state: Dict[str, Any],
        branch_name: str,
        label: str = "",
    ) -> Snapshot:
        """Create a new snapshot on an alternative branch."""
        origin = self.store.get(from_snapshot_id)
        if origin is None:
            raise KeyError(f"Snapshot not found: {from_snapshot_id}")
        snap = Snapshot.create(
            session_id=origin.session_id,
            agent_name=origin.agent_name,
            state=new_state,
            label=label or f"branch:{branch_name}",
            parent_snapshot_id=from_snapshot_id,
            branch_name=branch_name,
        )
        self.store.save(snap)
        return snap

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    def history(self, session_id: str) -> List[Snapshot]:
        return self.store.list_for_session(session_id)

    def list_all_snapshots(self, limit: int = 200) -> List[Snapshot]:
        return self.store.list_all(limit=limit)

    def list_branches(self, session_id: str) -> List[str]:
        snaps = self.store.list_for_session(session_id)
        return sorted({s.branch_name for s in snaps})

    # ------------------------------------------------------------------
    # Context manager checkpoint
    # ------------------------------------------------------------------

    @contextmanager
    def auto_checkpoint(
        self,
        session_id: str,
        agent_name: str,
        state_ref: Dict[str, Any],
        label: str = "",
    ) -> Generator[None, None, None]:
        """Checkpoint before and after a block of code."""
        self.checkpoint(session_id, agent_name, state_ref, label=f"{label}:before")
        yield
        self.checkpoint(session_id, agent_name, state_ref, label=f"{label}:after")

    def close(self) -> None:
        self.store.close()
