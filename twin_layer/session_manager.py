"""
session_manager.py — Twin-inspired Agent Session Manager for SintraPrime

Based on twin's attach/detach display system (server/display.cpp, server/remote.cpp).
Manages agent sessions with multiple display connections, persistence, and state tracking.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SESSIONS_FILE = Path("/agent/home/sessions.json")


# ─── Enums ────────────────────────────────────────────────────────────────────

class SessionState(Enum):
    """Session lifecycle states, mirroring twin's display attach states."""
    ACTIVE = "ACTIVE"
    DETACHED = "DETACHED"
    HIBERNATED = "HIBERNATED"
    TERMINATED = "TERMINATED"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class DisplayConnection:
    """
    Represents one display attached to a session.
    In twin, a single server can drive multiple displays simultaneously.

    Attributes:
        display_id: Unique ID for this display connection.
        display_type: 'terminal', 'websocket', 'vnc', etc.
        endpoint: Connection endpoint (e.g., ':0', 'ws://host:8765').
        connected_at: ISO timestamp when display connected.
        active: Whether the display is currently connected.
        metadata: Extra info (resolution, color depth, etc.).
    """
    display_id: str
    display_type: str
    endpoint: str
    connected_at: str
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DisplayConnection":
        return cls(**d)


@dataclass
class AgentSession:
    """
    An agent work session that persists across display attach/detach cycles.
    Inspired by twin's session model where the server keeps running after
    all displays detach.

    Attributes:
        session_id: Unique session identifier (UUID).
        agent_id: ID of the owning SintraPrime agent.
        created_at: ISO timestamp of creation.
        last_active: ISO timestamp of last activity.
        state: Current SessionState.
        display_connections: List of attached DisplayConnection objects.
        environment: Key-value environment variables for the session.
        tags: Optional labels for filtering.
    """
    session_id: str
    agent_id: str
    created_at: str
    last_active: str
    state: str  # SessionState.value
    display_connections: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    @property
    def session_state(self) -> SessionState:
        return SessionState(self.state)

    @session_state.setter
    def session_state(self, value: SessionState):
        self.state = value.value

    def get_displays(self) -> List[DisplayConnection]:
        """Return DisplayConnection objects."""
        return [DisplayConnection.from_dict(d) for d in self.display_connections]

    def get_active_displays(self) -> List[DisplayConnection]:
        """Return only active (connected) displays."""
        return [d for d in self.get_displays() if d.active]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentSession":
        return cls(**d)

    def touch(self):
        """Update last_active timestamp."""
        self.last_active = _now_iso()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a new UUID."""
    return str(uuid.uuid4())


# ─── SessionManager ───────────────────────────────────────────────────────────

class SessionManager:
    """
    Manages SintraPrime agent sessions with attach/detach display support.

    Inspired by twin's ability to keep server-side state alive while
    displays connect and disconnect dynamically.

    Usage:
        sm = SessionManager()
        session = sm.create_session("agent-001")
        sm.attach_display(session.session_id, {"type": "terminal", "endpoint": ":0"})
        sm.detach_display(session.session_id, display_id)
        sm.resume_session(session.session_id)
    """

    def __init__(self, sessions_file: Optional[Path] = None):
        """
        Initialize SessionManager and load persisted sessions.

        Args:
            sessions_file: Path to JSON persistence file. Defaults to SESSIONS_FILE.
        """
        self._file = sessions_file or SESSIONS_FILE
        self._sessions: Dict[str, AgentSession] = {}
        self._load()
        logger.info("SessionManager loaded %d sessions from %s",
                    len(self._sessions), self._file)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        """Load sessions from JSON file."""
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for item in raw.get("sessions", []):
                    try:
                        s = AgentSession.from_dict(item)
                        self._sessions[s.session_id] = s
                    except Exception as exc:
                        logger.warning("Skipping corrupt session entry: %s", exc)
            except Exception as exc:
                logger.error("Failed to load sessions from %s: %s", self._file, exc)

    def _save(self):
        """Persist all sessions to JSON file."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            data = {"sessions": [s.to_dict() for s in self._sessions.values()]}
            tmp_path = self._file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            tmp_path.replace(self._file)
            logger.debug("Saved %d sessions to %s", len(self._sessions), self._file)
        except Exception as exc:
            logger.error("Failed to save sessions: %s", exc)

    # ── Session CRUD ──────────────────────────────────────────────────────────

    def create_session(self, agent_id: str,
                       environment: Optional[Dict[str, str]] = None,
                       tags: Optional[List[str]] = None) -> AgentSession:
        """
        Create a new session for an agent.

        Args:
            agent_id: SintraPrime agent identifier.
            environment: Optional environment variables.
            tags: Optional labels.

        Returns:
            The newly created AgentSession.
        """
        now = _now_iso()
        session = AgentSession(
            session_id=_new_id(),
            agent_id=agent_id,
            created_at=now,
            last_active=now,
            state=SessionState.ACTIVE.value,
            display_connections=[],
            environment=environment or {},
            tags=tags or [],
        )
        self._sessions[session.session_id] = session
        self._save()
        logger.info("Created session %s for agent %s", session.session_id, agent_id)
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def destroy_session(self, session_id: str) -> bool:
        """
        Permanently destroy a session.

        Args:
            session_id: Session to destroy.

        Returns:
            True if found and destroyed, False otherwise.
        """
        session = self._sessions.pop(session_id, None)
        if session:
            self._save()
            logger.info("Destroyed session %s", session_id)
            return True
        return False

    # ── Display management ────────────────────────────────────────────────────

    def attach_display(self, session_id: str,
                       display_info: Dict[str, Any]) -> Optional[str]:
        """
        Attach a new display to an existing session.
        Mirrors twin's TwinAttach() which adds a display to a running server.

        Args:
            session_id: Target session.
            display_info: Dict with 'type', 'endpoint', and optional 'metadata'.

        Returns:
            The new display_id, or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("attach_display: session %s not found", session_id)
            return None

        display_id = _new_id()
        display = DisplayConnection(
            display_id=display_id,
            display_type=display_info.get("type", "terminal"),
            endpoint=display_info.get("endpoint", ""),
            connected_at=_now_iso(),
            active=True,
            metadata=display_info.get("metadata", {}),
        )
        session.display_connections.append(display.to_dict())
        session.touch()

        # Re-activate if detached (twin behavior: attaching wakes up session)
        if session.session_state == SessionState.DETACHED:
            session.session_state = SessionState.ACTIVE
            logger.info("Session %s re-activated by display attach", session_id)

        self._save()
        logger.info("Attached display %s to session %s", display_id, session_id)
        return display_id

    def detach_display(self, session_id: str, display_id: str) -> bool:
        """
        Detach a display from a session.
        Session continues running without the display (twin's key feature).

        Args:
            session_id: Target session.
            display_id: Display to detach.

        Returns:
            True if found and detached, False otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        found = False
        for i, d in enumerate(session.display_connections):
            if d.get("display_id") == display_id:
                session.display_connections[i]["active"] = False
                found = True
                break

        if not found:
            logger.warning("detach_display: display %s not in session %s",
                           display_id, session_id)
            return False

        session.touch()

        # If no active displays remain, transition to DETACHED (like twin)
        if not session.get_active_displays():
            session.session_state = SessionState.DETACHED
            logger.info("Session %s detached (no active displays)", session_id)

        self._save()
        return True

    def detach_all_displays(self, session_id: str):
        """Detach all displays from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return
        for d in session.display_connections:
            d["active"] = False
        session.session_state = SessionState.DETACHED
        session.touch()
        self._save()

    # ── Session state transitions ─────────────────────────────────────────────

    def resume_session(self, session_id: str) -> bool:
        """
        Resume a detached or hibernated session.

        Args:
            session_id: Session to resume.

        Returns:
            True if resumed, False if not found or not resumable.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        if session.session_state in (SessionState.DETACHED, SessionState.HIBERNATED):
            session.session_state = SessionState.ACTIVE
            session.touch()
            self._save()
            logger.info("Resumed session %s", session_id)
            return True
        return False

    def hibernate_session(self, session_id: str) -> bool:
        """
        Hibernate a session (saves state for long-term storage).

        Args:
            session_id: Session to hibernate.

        Returns:
            True if hibernated successfully.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        self.detach_all_displays(session_id)
        session.session_state = SessionState.HIBERNATED
        session.touch()
        self._save()
        logger.info("Hibernated session %s", session_id)
        return True

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_sessions(self, agent_id: Optional[str] = None,
                      state: Optional[SessionState] = None) -> List[Dict[str, Any]]:
        """
        List all sessions with optional filters.

        Args:
            agent_id: Filter by agent ID.
            state: Filter by SessionState.

        Returns:
            List of session info dicts.
        """
        results = []
        for s in self._sessions.values():
            if agent_id and s.agent_id != agent_id:
                continue
            if state and s.session_state != state:
                continue
            results.append({
                "session_id": s.session_id,
                "agent_id": s.agent_id,
                "state": s.state,
                "created_at": s.created_at,
                "last_active": s.last_active,
                "display_count": len(s.display_connections),
                "active_displays": len(s.get_active_displays()),
                "tags": s.tags,
            })
        return results

    def get_session_by_agent(self, agent_id: str) -> List[AgentSession]:
        """Return all sessions for a given agent."""
        return [s for s in self._sessions.values() if s.agent_id == agent_id]

    def cleanup_terminated(self) -> int:
        """Remove all TERMINATED sessions. Returns count removed."""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.session_state == SessionState.TERMINATED
        ]
        for sid in to_remove:
            del self._sessions[sid]
        if to_remove:
            self._save()
        logger.info("Cleaned up %d terminated sessions", len(to_remove))
        return len(to_remove)

    def __len__(self) -> int:
        return len(self._sessions)

    def __repr__(self) -> str:
        return f"SessionManager(sessions={len(self._sessions)}, file={self._file})"
