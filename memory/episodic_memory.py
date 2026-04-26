"""
Episodic Memory — Conversation and event history store.
Records sessions, extracts learnings, and summarizes interactions.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .memory_types import Episode, Learning, Session

MAX_SESSIONS = 1000  # Rolling window size


class EpisodicMemory:
    """
    Stores and retrieves conversation sessions and events.
    Maintains a rolling window of recent sessions, summarizing older ones.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = Path.home() / ".sintra" / "memory"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "episodic.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    outcomes TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    summary TEXT,
                    learnings TEXT DEFAULT '[]',
                    is_summarized INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_topics TEXT DEFAULT '[]',
                    outcomes TEXT DEFAULT '[]',
                    date TEXT NOT NULL,
                    importance REAL DEFAULT 0.5
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id)
            """)
            conn.commit()

    # ------------------------------------------------------------------ #
    #  Session logging                                                      #
    # ------------------------------------------------------------------ #

    def log_session(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        outcomes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous",
    ) -> Session:
        """Record a conversation session."""
        if outcomes is None:
            outcomes = []
        if metadata is None:
            metadata = {}
        now = datetime.utcnow().isoformat()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            messages=messages,
            outcomes=outcomes,
            metadata=metadata,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
        )
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                    (session_id, user_id, messages, outcomes, metadata,
                     started_at, ended_at, summary, learnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    json.dumps(messages),
                    json.dumps(outcomes),
                    json.dumps(metadata),
                    now,
                    now,
                    None,
                    json.dumps([]),
                ),
            )
            conn.commit()

        # Enforce rolling window
        self._enforce_rolling_window()
        return session

    def _enforce_rolling_window(self) -> None:
        """Keep only the last MAX_SESSIONS sessions, summarizing older ones."""
        with self._get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE is_summarized=0"
            ).fetchone()[0]

            if count <= MAX_SESSIONS:
                return

            # Get oldest sessions beyond the window
            excess = count - MAX_SESSIONS
            old_rows = conn.execute(
                """
                SELECT session_id FROM sessions
                WHERE is_summarized=0
                ORDER BY started_at ASC LIMIT ?
                """,
                (excess,),
            ).fetchall()

            for row in old_rows:
                sid = row["session_id"]
                # Summarize and move to episodes table
                self._archive_session(conn, sid)

            conn.commit()

    def _archive_session(self, conn: sqlite3.Connection, session_id: str) -> None:
        """Summarize a session and archive it to episodes table."""
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not row:
            return

        messages = json.loads(row["messages"])
        summary = self._generate_summary(messages)
        topics = self._extract_topics(messages)
        outcomes = json.loads(row["outcomes"])

        conn.execute(
            """
            INSERT OR REPLACE INTO episodes
                (session_id, user_id, summary, key_topics, outcomes, date, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                row["user_id"],
                summary,
                json.dumps(topics),
                json.dumps(outcomes),
                row["started_at"],
                0.5,
            ),
        )
        conn.execute(
            "UPDATE sessions SET is_summarized=1 WHERE session_id=?",
            (session_id,),
        )

    # ------------------------------------------------------------------ #
    #  Recall & search                                                      #
    # ------------------------------------------------------------------ #

    def recall_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a full session by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id=?", (session_id,)
            ).fetchone()
        if not row:
            return None
        return Session(
            session_id=row["session_id"],
            user_id=row["user_id"],
            messages=json.loads(row["messages"]),
            outcomes=json.loads(row["outcomes"]),
            metadata=json.loads(row["metadata"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            summary=row["summary"],
            learnings=json.loads(row["learnings"]),
        )

    def search_episodes(
        self,
        query: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Episode]:
        """Search episodic memory for relevant sessions."""
        query_lower = query.lower()
        with self._get_conn() as conn:
            # Search in live sessions
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC",
                    (user_id,),
                ).fetchall()
                ep_rows = conn.execute(
                    "SELECT * FROM episodes WHERE user_id=? ORDER BY date DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC"
                ).fetchall()
                ep_rows = conn.execute(
                    "SELECT * FROM episodes ORDER BY date DESC"
                ).fetchall()

        results: List[Episode] = []

        # Search session messages
        for row in rows:
            messages = json.loads(row["messages"])
            full_text = " ".join(m.get("content", "") for m in messages).lower()
            if query_lower in full_text or any(
                word in full_text for word in query_lower.split()
            ):
                # Apply date filter
                started = datetime.fromisoformat(row["started_at"])
                if date_range:
                    if not (date_range[0] <= started <= date_range[1]):
                        continue
                topics = self._extract_topics(messages)
                ep = Episode(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    summary=row["summary"] or self._generate_summary(messages),
                    key_topics=topics,
                    outcomes=json.loads(row["outcomes"]),
                    date=started,
                )
                results.append(ep)

        # Also search archived episodes
        for row in ep_rows:
            if query_lower in row["summary"].lower():
                ep_date = datetime.fromisoformat(row["date"])
                if date_range and not (date_range[0] <= ep_date <= date_range[1]):
                    continue
                ep = Episode(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    summary=row["summary"],
                    key_topics=json.loads(row["key_topics"]),
                    outcomes=json.loads(row["outcomes"]),
                    date=ep_date,
                    importance=row["importance"],
                )
                results.append(ep)

        return results[:limit]

    def get_user_history(self, user_id: str, limit: int = 50) -> List[Episode]:
        """Get recent episode history for a user."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT session_id, user_id, started_at, summary, outcomes, messages
                FROM sessions WHERE user_id=?
                ORDER BY started_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            ep_rows = conn.execute(
                """
                SELECT * FROM episodes WHERE user_id=?
                ORDER BY date DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        episodes = []
        for row in rows:
            messages = json.loads(row["messages"])
            episodes.append(Episode(
                session_id=row["session_id"],
                user_id=row["user_id"],
                summary=row["summary"] or self._generate_summary(messages),
                key_topics=self._extract_topics(messages),
                outcomes=json.loads(row["outcomes"]),
                date=datetime.fromisoformat(row["started_at"]),
            ))

        for row in ep_rows:
            episodes.append(Episode(
                session_id=row["session_id"],
                user_id=row["user_id"],
                summary=row["summary"],
                key_topics=json.loads(row["key_topics"]),
                outcomes=json.loads(row["outcomes"]),
                date=datetime.fromisoformat(row["date"]),
                importance=row["importance"],
            ))

        episodes.sort(key=lambda e: e.date, reverse=True)
        return episodes[:limit]

    # ------------------------------------------------------------------ #
    #  Summarization & learning extraction                                  #
    # ------------------------------------------------------------------ #

    def _generate_summary(self, messages: List[Dict[str, str]]) -> str:
        """Distill a session to key points (heuristic)."""
        if not messages:
            return "Empty session."
        user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
        assistant_msgs = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
        summary_parts = []
        if user_msgs:
            first_user = user_msgs[0][:200]
            summary_parts.append(f"User asked: {first_user}")
        if assistant_msgs:
            last_assist = assistant_msgs[-1][:200]
            summary_parts.append(f"Assistant concluded: {last_assist}")
        summary_parts.append(f"Session had {len(messages)} messages.")
        return " | ".join(summary_parts)

    def _extract_topics(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extract key topics from messages using keyword frequency."""
        all_text = " ".join(m.get("content", "") for m in messages).lower()
        words = re.findall(r"[a-z]{4,}", all_text)
        stopwords = {
            "that", "this", "with", "from", "have", "will", "your",
            "they", "them", "what", "when", "where", "which", "been",
            "were", "then", "than", "just", "also", "some", "about",
        }
        filtered = [w for w in words if w not in stopwords]
        freq = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
        return [w for w, _ in top]

    def summarize_episode(self, session_id: str) -> str:
        """Summarize a specific session by ID."""
        session = self.recall_session(session_id)
        if not session:
            return "Session not found."
        summary = self._generate_summary(session.messages)
        # Update stored summary
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET summary=? WHERE session_id=?",
                (summary, session_id),
            )
            conn.commit()
        return summary

    def extract_learnings(self, session_id: str) -> List[Learning]:
        """Extract what was learned from a session."""
        session = self.recall_session(session_id)
        if not session:
            return []

        learnings: List[Learning] = []
        for msg in session.messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            if role == "assistant" and len(content) > 50:
                # Heuristic: declarative sentences as learnings
                sentences = re.split(r"[.!?]", content)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 30 and any(
                        kw in sent.lower()
                        for kw in ["therefore", "thus", "because", "means", "should", "important", "key"]
                    ):
                        learnings.append(Learning(
                            content=sent[:300],
                            source_session=session_id,
                            confidence=0.75,
                            domain=self._detect_domain(sent),
                        ))

        # Update stored learnings
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET learnings=? WHERE session_id=?",
                (json.dumps([l.to_dict() for l in learnings]), session_id),
            )
            conn.commit()
        return learnings[:10]

    def _detect_domain(self, text: str) -> str:
        """Heuristically detect the knowledge domain of a text."""
        lower = text.lower()
        if any(w in lower for w in ["law", "legal", "court", "case", "statute", "judge"]):
            return "legal"
        if any(w in lower for w in ["code", "function", "api", "software", "python", "data"]):
            return "technical"
        if any(w in lower for w in ["client", "customer", "meeting", "project", "deadline"]):
            return "business"
        return "general"

    def count_sessions(self, user_id: Optional[str] = None) -> int:
        """Return total session count."""
        with self._get_conn() as conn:
            if user_id:
                return conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,)
                ).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    def forget_user(self, user_id: str) -> int:
        """Delete all sessions for a user (GDPR)."""
        with self._get_conn() as conn:
            c1 = conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,)).rowcount
            c2 = conn.execute("DELETE FROM episodes WHERE user_id=?", (user_id,)).rowcount
            conn.commit()
            return c1 + c2

    def export_user_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Export all session data for a user."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE user_id=?", (user_id,)
            ).fetchall()
        return [
            {
                "session_id": r["session_id"],
                "user_id": r["user_id"],
                "messages": json.loads(r["messages"]),
                "outcomes": json.loads(r["outcomes"]),
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
                "summary": r["summary"],
            }
            for r in rows
        ]
