from __future__ import annotations

import json
import os
import sqlite3
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .a2a_protocol import A2AProtocol, Message, MessageType, Priority

LIFECYCLE_STATUSES = {"ASSIGNED", "ACK", "IN_PROGRESS", "RESULT", "BLOCKED", "REJECTED", "CLOSED"}
ROLE_PERMISSIONS = {
    "owner": {"workspace:create", "channel:create", "thread:create", "message:create", "thread:read", "objective:create", "approval:decide", "trace:read", "agent:health"},
    "supervisor": {"workspace:create", "channel:create", "thread:create", "message:create", "thread:read", "objective:create", "trace:read", "agent:health"},
    "worker": {"message:create", "thread:read", "agent:health"},
    "reviewer": {"message:create", "thread:read", "agent:health"},
    "observer": {"thread:read", "trace:read", "agent:health"},
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class CommonsError(ValueError):
    pass


class AuthorizationError(CommonsError):
    pass


class LoopDetectedError(CommonsError):
    pass


class IdempotencyConflictError(CommonsError):
    pass


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    principal_id: str
    role: str

    def ensure(self, permission: str) -> None:
        allowed = ROLE_PERMISSIONS.get(self.role, set())
        if permission not in allowed:
            raise AuthorizationError(f"Role '{self.role}' lacks permission '{permission}'")


@dataclass
class AgentInvocation:
    run_id: str
    status: str
    output: dict[str, Any]
    rationale: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    follow_up_capability: str | None = None


class AgentAdapter(ABC):
    def __init__(self, agent_id: str, display_name: str, role: str, capability_list: Sequence[str]) -> None:
        self.agent_id = agent_id
        self.display_name = display_name
        self.role = role
        self._capability_list = list(capability_list)
        self._run_events: dict[str, list[dict[str, Any]]] = {}
        self._cancelled_runs: set[str] = set()

    def _record_events(self, run_id: str, events: list[dict[str, Any]]) -> None:
        self._run_events[run_id] = events

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    def capabilities(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "role": self.role,
            "capabilities": list(self._capability_list),
        }

    @abstractmethod
    def invoke(self, task: dict[str, Any], context: dict[str, Any]) -> AgentInvocation:
        raise NotImplementedError

    def cancel(self, run_id: str) -> bool:
        self._cancelled_runs.add(run_id)
        self._record_events(run_id, [{"timestamp": utc_now(), "event": "cancelled", "run_id": run_id}])
        return True

    def stream_events(self, run_id: str) -> Iterator[dict[str, Any]]:
        yield from self._run_events.get(run_id, [])


class MockAgentAdapter(AgentAdapter):
    def __init__(
        self,
        agent_id: str,
        display_name: str,
        role: str,
        capability_list: Sequence[str],
        *,
        reviewer_disagrees: bool = False,
        follow_up_capability: str | None = None,
    ) -> None:
        super().__init__(agent_id, display_name, role, capability_list)
        self.reviewer_disagrees = reviewer_disagrees
        self.follow_up_capability = follow_up_capability

    def health(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": "healthy",
            "role": self.role,
            "capabilities": list(self._capability_list),
        }

    def invoke(self, task: dict[str, Any], context: dict[str, Any]) -> AgentInvocation:
        run_id = task["run_id"]
        objective = task.get("objective", "")
        acceptance = task.get("acceptance_criteria", [])
        if self.role == "reviewer":
            verdict = "disputed" if self.reviewer_disagrees else "approved"
            output = {
                "verdict": verdict,
                "summary": f"{self.display_name} reviewed '{objective}'",
                "acceptance_criteria": acceptance,
                "material_disagreement": self.reviewer_disagrees,
                "claims": ["review complete"],
            }
            rationale = "Reviewer found material disagreement." if self.reviewer_disagrees else "Reviewer found no material disagreement."
        else:
            output = {
                "result": f"{self.display_name} completed '{objective}'",
                "acceptance_criteria": acceptance,
                "thread_context_messages": len(context.get("thread_history", [])),
                "claims": ["bounded task completed"],
            }
            rationale = "Worker completed bounded task using governed context."
        evidence = [{
            "kind": "mock",
            "uri": f"mock://{self.agent_id}/{run_id}",
            "title": f"{self.display_name} evidence",
            "verified": True,
        }]
        events = [
            {"timestamp": utc_now(), "event": "invoked", "agent_id": self.agent_id},
            {"timestamp": utc_now(), "event": "completed", "agent_id": self.agent_id},
        ]
        invocation = AgentInvocation(
            run_id=run_id,
            status="completed",
            output=output,
            rationale=rationale,
            evidence=evidence,
            tool_calls=[{"tool": "mock", "summary": "deterministic adapter"}],
            events=events,
            follow_up_capability=self.follow_up_capability,
        )
        self._record_events(run_id, events)
        return invocation


class OpenAIResponsesSupervisorAdapter(AgentAdapter):
    def __init__(self, agent_id: str = "chatgpt-supervisor", model: str = "gpt-5.6-luna") -> None:
        super().__init__(agent_id, "ChatGPT Supervisor", "supervisor", ["objective_decomposition", "reconciliation"])
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

    def health(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": "healthy" if self.api_key else "degraded",
            "provider": "openai-responses",
            "configured": bool(self.api_key),
            "model": self.model,
            "capabilities": list(self._capability_list),
        }

    def invoke(self, task: dict[str, Any], context: dict[str, Any]) -> AgentInvocation:
        run_id = task["run_id"]
        objective = task.get("objective", "")
        plan = {
            "builder_task": {
                "objective": objective,
                "acceptance_criteria": task.get("acceptance_criteria", ["produce a bounded result"]),
                "recommended_capability": task.get("builder_capability", "build"),
            },
            "review_task": {
                "objective": f"Review builder output for: {objective}",
                "acceptance_criteria": ["find material disagreements"],
                "recommended_capability": task.get("reviewer_capability", "review"),
            },
            "provider_mode": "api" if self.api_key else "mock-fallback",
            "history_messages": len(context.get("thread_history", [])),
        }
        events = [{"timestamp": utc_now(), "event": "planned", "provider": "openai-responses"}]
        self._record_events(run_id, events)
        return AgentInvocation(
            run_id=run_id,
            status="completed",
            output=plan,
            rationale="Supervisor decomposed the objective into builder and reviewer tasks.",
            events=events,
        )


class AgentCommonsStore:
    def __init__(self, db_path: str = ":memory:", ledger_dir: str | Path | None = None) -> None:
        self.db_path = str(db_path)
        self._persistent_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        self.ledger_dir = Path(ledger_dir) if ledger_dir else None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_if_needed(self, conn: sqlite3.Connection) -> None:
        if self._persistent_conn is None:
            conn.close()

    def _init_db(self) -> None:
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                workspace_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                community_id TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                title TEXT NOT NULL,
                lifecycle_status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT,
                thread_id TEXT,
                principal_id TEXT NOT NULL,
                principal_type TEXT NOT NULL,
                role TEXT NOT NULL,
                display_name TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipients_json TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                lifecycle_status TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                trace_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                run_id TEXT,
                status TEXT NOT NULL,
                actor TEXT NOT NULL,
                details_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_run_id TEXT,
                correlation_id TEXT NOT NULL,
                idempotency_key TEXT,
                context_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                tool_calls_json TEXT NOT NULL,
                rationale TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_runs_tenant_idempotency
                ON agent_runs(tenant_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL;
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                decision TEXT,
                requested_by TEXT NOT NULL,
                approver TEXT,
                reason TEXT,
                idempotency_key TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ix_approvals_tenant_idempotency
                ON approvals(tenant_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL;
            CREATE TABLE IF NOT EXISTS evidence_references (
                evidence_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                run_id TEXT,
                message_id TEXT,
                kind TEXT NOT NULL,
                uri TEXT NOT NULL,
                title TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                scope TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                key TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(scope, tenant_id, key)
            );
            """
        )
        conn.commit()
        self._close_if_needed(conn)

    @staticmethod
    def _loads(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        return json.loads(value)

    @staticmethod
    def _dumps(value: Any) -> str:
        return json.dumps(value or {}, sort_keys=True)

    def _fetchone(self, conn: sqlite3.Connection, query: str, params: Sequence[Any]) -> dict[str, Any] | None:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

    def remember_idempotency(self, scope: str, tenant_id: str, key: str, resource_id: str) -> str:
        conn = self._connect()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys(scope, tenant_id, key, resource_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (scope, tenant_id, key, resource_id, utc_now()),
        )
        existing = self._fetchone(
            conn,
            "SELECT resource_id FROM idempotency_keys WHERE scope = ? AND tenant_id = ? AND key = ?",
            (scope, tenant_id, key),
        )
        conn.commit()
        self._close_if_needed(conn)
        return str(existing["resource_id"]) if existing else resource_id

    def get_idempotency_resource(self, scope: str, tenant_id: str, key: str) -> str | None:
        conn = self._connect()
        existing = self._fetchone(
            conn,
            "SELECT resource_id FROM idempotency_keys WHERE scope = ? AND tenant_id = ? AND key = ?",
            (scope, tenant_id, key),
        )
        self._close_if_needed(conn)
        return str(existing["resource_id"]) if existing else None

    def create_workspace(self, tenant_id: str, name: str, metadata: dict[str, Any] | None = None, community_id: str | None = None) -> dict[str, Any]:
        workspace_id = uuid.uuid4().hex
        record = {
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "community_id": community_id or f"community-{workspace_id[:8]}",
            "name": name,
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO workspaces(workspace_id, tenant_id, community_id, name, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (record["workspace_id"], tenant_id, record["community_id"], name, self._dumps(record["metadata"]), record["created_at"]),
        )
        conn.commit()
        self._close_if_needed(conn)
        return record

    def _require_workspace(self, tenant_id: str, workspace_id: str) -> dict[str, Any]:
        conn = self._connect()
        row = self._fetchone(
            conn,
            "SELECT * FROM workspaces WHERE workspace_id = ? AND tenant_id = ?",
            (workspace_id, tenant_id),
        )
        self._close_if_needed(conn)
        if not row:
            raise CommonsError("Workspace not found")
        return {
            "workspace_id": row["workspace_id"],
            "tenant_id": row["tenant_id"],
            "community_id": row["community_id"],
            "name": row["name"],
        }

    def _require_channel(self, tenant_id: str, channel_id: str, workspace_id: str | None = None) -> dict[str, Any]:
        conn = self._connect()
        row = self._fetchone(
            conn,
            "SELECT * FROM channels WHERE channel_id = ? AND tenant_id = ?",
            (channel_id, tenant_id),
        )
        self._close_if_needed(conn)
        if not row:
            raise CommonsError("Channel not found")
        if workspace_id and row["workspace_id"] != workspace_id:
            raise CommonsError("Channel does not belong to workspace")
        return {
            "channel_id": row["channel_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "name": row["name"],
        }

    def _require_thread(self, tenant_id: str, thread_id: str) -> dict[str, Any]:
        thread = self.get_thread(thread_id, tenant_id)
        if not thread:
            raise CommonsError("Thread not found")
        return thread

    def create_channel(self, tenant_id: str, workspace_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_workspace(tenant_id, workspace_id)
        channel_id = uuid.uuid4().hex
        record = {
            "channel_id": channel_id,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "name": name,
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO channels(channel_id, tenant_id, workspace_id, name, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (channel_id, tenant_id, workspace_id, name, self._dumps(record["metadata"]), record["created_at"]),
        )
        conn.commit()
        self._close_if_needed(conn)
        return record

    def create_thread(
        self,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        title: str,
        task_id: str | None = None,
        lifecycle_status: str = "ASSIGNED",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_workspace(tenant_id, workspace_id)
        self._require_channel(tenant_id, channel_id, workspace_id=workspace_id)
        thread_id = uuid.uuid4().hex
        now = utc_now()
        record = {
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "task_id": task_id or f"TASK-{thread_id[:8]}",
            "title": title,
            "lifecycle_status": lifecycle_status,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO threads(thread_id, tenant_id, workspace_id, channel_id, task_id, title, lifecycle_status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (thread_id, tenant_id, workspace_id, channel_id, record["task_id"], title, lifecycle_status, self._dumps(record["metadata"]), now, now),
        )
        conn.commit()
        self._close_if_needed(conn)
        return record

    def add_participant(
        self,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        principal_id: str,
        principal_type: str,
        role: str,
        display_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_workspace(tenant_id, workspace_id)
        self._require_channel(tenant_id, channel_id, workspace_id=workspace_id)
        self._require_thread(tenant_id, thread_id)
        participant_id = uuid.uuid4().hex
        record = {
            "participant_id": participant_id,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "principal_id": principal_id,
            "principal_type": principal_type,
            "role": role,
            "display_name": display_name,
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO participants(participant_id, tenant_id, workspace_id, channel_id, thread_id, principal_id, principal_type, role, display_name, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (participant_id, tenant_id, workspace_id, channel_id, thread_id, principal_id, principal_type, role, display_name, self._dumps(record["metadata"]), record["created_at"]),
        )
        conn.commit()
        self._close_if_needed(conn)
        return record

    def add_message(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        sender: str,
        recipients: Sequence[str],
        correlation_id: str,
        lifecycle_status: str,
        payload: dict[str, Any],
        evidence: Sequence[dict[str, Any]] | None = None,
        trace: dict[str, Any] | None = None,
        message_id: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        thread = self._require_thread(tenant_id, thread_id)
        if thread["workspace_id"] != workspace_id or thread["channel_id"] != channel_id or thread["task_id"] != task_id:
            raise CommonsError("Message routing metadata does not match the thread")
        message_id = message_id or uuid.uuid4().hex
        record = {
            "message_id": message_id,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "task_id": task_id,
            "sender": sender,
            "recipients": list(recipients),
            "correlation_id": correlation_id,
            "lifecycle_status": lifecycle_status,
            "payload": payload,
            "evidence": list(evidence or []),
            "trace": trace or {},
            "timestamp": timestamp or utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO messages(message_id, tenant_id, workspace_id, channel_id, thread_id, task_id, sender, recipients_json, correlation_id, lifecycle_status, evidence_json, trace_json, payload_json, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message_id,
                tenant_id,
                workspace_id,
                channel_id,
                thread_id,
                task_id,
                sender,
                self._dumps(record["recipients"]),
                correlation_id,
                lifecycle_status,
                self._dumps(record["evidence"]),
                self._dumps(record["trace"]),
                self._dumps(record["payload"]),
                record["timestamp"],
            ),
        )
        conn.execute("UPDATE threads SET lifecycle_status = ?, updated_at = ? WHERE thread_id = ? AND tenant_id = ?", (lifecycle_status, record["timestamp"], thread_id, tenant_id))
        conn.commit()
        self._close_if_needed(conn)
        for item in record["evidence"]:
            self.add_evidence_reference(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                thread_id=thread_id,
                task_id=task_id,
                run_id=trace.get("run_id") if trace else None,
                message_id=message_id,
                kind=item.get("kind", "reference"),
                uri=item.get("uri", "mock://missing"),
                title=item.get("title"),
                metadata=item,
            )
        return record

    def add_task_event(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        status: str,
        actor: str,
        details: dict[str, Any] | None = None,
        evidence: Sequence[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        thread = self._require_thread(tenant_id, thread_id)
        if thread["workspace_id"] != workspace_id or thread["channel_id"] != channel_id or thread["task_id"] != task_id:
            raise CommonsError("Task event metadata does not match the thread")
        event = {
            "event_id": uuid.uuid4().hex,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "task_id": task_id,
            "run_id": run_id,
            "status": status,
            "actor": actor,
            "details": details or {},
            "evidence": list(evidence or []),
            "timestamp": utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO task_events(event_id, tenant_id, workspace_id, channel_id, thread_id, task_id, run_id, status, actor, details_json, evidence_json, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event["event_id"],
                tenant_id,
                workspace_id,
                channel_id,
                thread_id,
                task_id,
                run_id,
                status,
                actor,
                self._dumps(event["details"]),
                self._dumps(event["evidence"]),
                event["timestamp"],
            ),
        )
        conn.execute("UPDATE threads SET lifecycle_status = ?, updated_at = ? WHERE thread_id = ? AND tenant_id = ?", (status, event["timestamp"], thread_id, tenant_id))
        conn.commit()
        self._close_if_needed(conn)
        self._append_ledger(event)
        return event

    def start_agent_run(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        agent_id: str,
        role: str,
        correlation_id: str,
        context: dict[str, Any],
        parent_run_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        thread = self._require_thread(tenant_id, thread_id)
        if thread["workspace_id"] != workspace_id or thread["channel_id"] != channel_id or thread["task_id"] != task_id:
            raise CommonsError("Run metadata does not match the thread")
        if idempotency_key:
            existing = self.get_agent_run_by_idempotency(tenant_id, idempotency_key)
            if existing:
                return existing
        now = utc_now()
        run = {
            "run_id": uuid.uuid4().hex,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "role": role,
            "status": "running",
            "parent_run_id": parent_run_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "context": context,
            "output": {},
            "tool_calls": [],
            "rationale": None,
            "created_at": now,
            "updated_at": now,
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO agent_runs(run_id, tenant_id, workspace_id, channel_id, thread_id, task_id, agent_id, role, status, parent_run_id, correlation_id, idempotency_key, context_json, output_json, tool_calls_json, rationale, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run["run_id"], tenant_id, workspace_id, channel_id, thread_id, task_id, agent_id, role,
                run["status"], parent_run_id, correlation_id, idempotency_key, self._dumps(context), self._dumps({}), self._dumps([]), None, now, now,
            ),
        )
        conn.commit()
        self._close_if_needed(conn)
        return run

    def complete_agent_run(
        self,
        run_id: str,
        tenant_id: str,
        *,
        status: str,
        output: dict[str, Any],
        rationale: str,
        tool_calls: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        conn = self._connect()
        conn.execute(
            "UPDATE agent_runs SET status = ?, output_json = ?, rationale = ?, tool_calls_json = ?, updated_at = ? WHERE run_id = ? AND tenant_id = ?",
            (status, self._dumps(output), rationale, self._dumps(list(tool_calls or [])), now, run_id, tenant_id),
        )
        conn.commit()
        row = self._fetchone(conn, "SELECT * FROM agent_runs WHERE run_id = ? AND tenant_id = ?", (run_id, tenant_id))
        self._close_if_needed(conn)
        return self._row_to_run(row) if row else {}

    def get_agent_run_by_idempotency(self, tenant_id: str, idempotency_key: str) -> dict[str, Any] | None:
        conn = self._connect()
        row = self._fetchone(conn, "SELECT * FROM agent_runs WHERE tenant_id = ? AND idempotency_key = ?", (tenant_id, idempotency_key))
        self._close_if_needed(conn)
        return self._row_to_run(row) if row else None

    def create_approval(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        run_id: str,
        requested_by: str,
        reason: str,
    ) -> dict[str, Any]:
        thread = self._require_thread(tenant_id, thread_id)
        if thread["workspace_id"] != workspace_id or thread["channel_id"] != channel_id or thread["task_id"] != task_id:
            raise CommonsError("Approval metadata does not match the thread")
        approval = {
            "approval_id": uuid.uuid4().hex,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "task_id": task_id,
            "run_id": run_id,
            "status": "PENDING",
            "decision": None,
            "requested_by": requested_by,
            "approver": None,
            "reason": reason,
            "created_at": utc_now(),
            "decided_at": None,
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO approvals(approval_id, tenant_id, workspace_id, channel_id, thread_id, task_id, run_id, status, decision, requested_by, approver, reason, idempotency_key, created_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (approval["approval_id"], tenant_id, workspace_id, channel_id, thread_id, task_id, run_id, approval["status"], None, requested_by, None, reason, None, approval["created_at"], None),
        )
        conn.commit()
        self._close_if_needed(conn)
        return approval

    def decide_approval(
        self,
        approval_id: str,
        tenant_id: str,
        *,
        approver: str,
        decision: str,
        reason: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        conn = self._connect()
        conn.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            existing = self._fetchone(conn, "SELECT * FROM approvals WHERE tenant_id = ? AND idempotency_key = ?", (tenant_id, idempotency_key))
            if existing:
                conn.commit()
                self._close_if_needed(conn)
                return self._row_to_approval(existing)
        now = utc_now()
        conn.execute(
            "UPDATE approvals SET status = ?, decision = ?, approver = ?, reason = ?, idempotency_key = ?, decided_at = ? WHERE approval_id = ? AND tenant_id = ?",
            ("APPROVED" if decision == "approve" else "REJECTED", decision, approver, reason, idempotency_key, now, approval_id, tenant_id),
        )
        conn.commit()
        row = self._fetchone(conn, "SELECT * FROM approvals WHERE approval_id = ? AND tenant_id = ?", (approval_id, tenant_id))
        self._close_if_needed(conn)
        return self._row_to_approval(row) if row else {}

    def add_evidence_reference(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        run_id: str | None,
        message_id: str | None,
        kind: str,
        uri: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence = {
            "evidence_id": uuid.uuid4().hex,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "task_id": task_id,
            "run_id": run_id,
            "message_id": message_id,
            "kind": kind,
            "uri": uri,
            "title": title,
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        conn = self._connect()
        conn.execute(
            "INSERT INTO evidence_references(evidence_id, tenant_id, workspace_id, channel_id, thread_id, task_id, run_id, message_id, kind, uri, title, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (evidence["evidence_id"], tenant_id, workspace_id, channel_id, thread_id, task_id, run_id, message_id, kind, uri, title, self._dumps(evidence["metadata"]), evidence["created_at"]),
        )
        conn.commit()
        self._close_if_needed(conn)
        return evidence

    def get_thread(self, thread_id: str, tenant_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        row = self._fetchone(conn, "SELECT * FROM threads WHERE thread_id = ? AND tenant_id = ?", (thread_id, tenant_id))
        if not row:
            self._close_if_needed(conn)
            return None
        thread = self._row_to_thread(row)
        participants = [self._row_to_participant(dict(item)) for item in conn.execute("SELECT * FROM participants WHERE thread_id = ? AND tenant_id = ? ORDER BY created_at", (thread_id, tenant_id)).fetchall()]
        messages = [self._row_to_message(dict(item)) for item in conn.execute("SELECT * FROM messages WHERE thread_id = ? AND tenant_id = ? ORDER BY timestamp", (thread_id, tenant_id)).fetchall()]
        events = [self._row_to_task_event(dict(item)) for item in conn.execute("SELECT * FROM task_events WHERE thread_id = ? AND tenant_id = ? ORDER BY timestamp", (thread_id, tenant_id)).fetchall()]
        approvals = [self._row_to_approval(dict(item)) for item in conn.execute("SELECT * FROM approvals WHERE thread_id = ? AND tenant_id = ? ORDER BY created_at", (thread_id, tenant_id)).fetchall()]
        runs = [self._row_to_run(dict(item)) for item in conn.execute("SELECT * FROM agent_runs WHERE thread_id = ? AND tenant_id = ? ORDER BY created_at", (thread_id, tenant_id)).fetchall()]
        evidence = [self._row_to_evidence(dict(item)) for item in conn.execute("SELECT * FROM evidence_references WHERE thread_id = ? AND tenant_id = ? ORDER BY created_at", (thread_id, tenant_id)).fetchall()]
        self._close_if_needed(conn)
        return {
            **thread,
            "participants": participants,
            "messages": messages,
            "task_events": events,
            "approvals": approvals,
            "agent_runs": runs,
            "evidence_references": evidence,
        }

    def get_run_trace(self, run_id: str, tenant_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        row = self._fetchone(conn, "SELECT * FROM agent_runs WHERE run_id = ? AND tenant_id = ?", (run_id, tenant_id))
        if not row:
            self._close_if_needed(conn)
            return None
        run = self._row_to_run(row)
        thread = self.get_thread(run["thread_id"], tenant_id)
        self._close_if_needed(conn)
        return {
            "run": run,
            "thread": thread,
            "trace": [event for event in (thread or {}).get("task_events", []) if event.get("run_id") in {None, run_id}],
            "messages": [message for message in (thread or {}).get("messages", []) if message.get("trace", {}).get("run_id") in {None, run_id}],
        }

    def _append_ledger(self, event: dict[str, Any]) -> None:
        if not self.ledger_dir or event["status"] not in LIFECYCLE_STATUSES:
            return
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        month_path = self.ledger_dir / f"{event['timestamp'][:7]}.jsonl"
        entry = {
            "mesh_id": event["event_id"],
            "thread_id": event["thread_id"],
            "from_agent": event["actor"],
            "to_agent": event["details"].get("to_agent", "thread"),
            "task_id": event["task_id"],
            "status": event["status"],
            "priority": event["details"].get("priority", "P1"),
            "objective": event["details"].get("objective", event["task_id"]),
            "evidence": [item.get("uri", item) for item in event.get("evidence", [])],
            "blocker": event["details"].get("blocker"),
            "owner_decision_required": bool(event["details"].get("owner_decision_required", False)),
            "timestamp": event["timestamp"],
            "notes": event["details"].get("notes", ""),
        }
        with month_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _row_to_thread(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "thread_id": row["thread_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "channel_id": row["channel_id"],
            "task_id": row["task_id"],
            "title": row["title"],
            "lifecycle_status": row["lifecycle_status"],
            "metadata": self._loads(row.get("metadata_json"), {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_participant(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "participant_id": row["participant_id"],
            "principal_id": row["principal_id"],
            "principal_type": row["principal_type"],
            "role": row["role"],
            "display_name": row["display_name"],
            "metadata": self._loads(row.get("metadata_json"), {}),
            "created_at": row["created_at"],
        }

    def _row_to_message(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "message_id": row["message_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "channel_id": row["channel_id"],
            "thread_id": row["thread_id"],
            "task_id": row["task_id"],
            "sender": row["sender"],
            "recipients": self._loads(row.get("recipients_json"), []),
            "correlation_id": row["correlation_id"],
            "lifecycle_status": row["lifecycle_status"],
            "evidence": self._loads(row.get("evidence_json"), []),
            "trace": self._loads(row.get("trace_json"), {}),
            "payload": self._loads(row.get("payload_json"), {}),
            "timestamp": row["timestamp"],
        }

    def _row_to_task_event(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": row["event_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "channel_id": row["channel_id"],
            "thread_id": row["thread_id"],
            "task_id": row["task_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "actor": row["actor"],
            "details": self._loads(row.get("details_json"), {}),
            "evidence": self._loads(row.get("evidence_json"), []),
            "timestamp": row["timestamp"],
        }

    def _row_to_run(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": row["run_id"],
            "tenant_id": row["tenant_id"],
            "workspace_id": row["workspace_id"],
            "channel_id": row["channel_id"],
            "thread_id": row["thread_id"],
            "task_id": row["task_id"],
            "agent_id": row["agent_id"],
            "role": row["role"],
            "status": row["status"],
            "parent_run_id": row["parent_run_id"],
            "correlation_id": row["correlation_id"],
            "idempotency_key": row["idempotency_key"],
            "context": self._loads(row.get("context_json"), {}),
            "output": self._loads(row.get("output_json"), {}),
            "tool_calls": self._loads(row.get("tool_calls_json"), []),
            "rationale": row["rationale"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_approval(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "approval_id": row["approval_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "decision": row["decision"],
            "requested_by": row["requested_by"],
            "approver": row["approver"],
            "reason": row["reason"],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
        }

    def _row_to_evidence(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": row["evidence_id"],
            "run_id": row["run_id"],
            "message_id": row["message_id"],
            "kind": row["kind"],
            "uri": row["uri"],
            "title": row["title"],
            "metadata": self._loads(row.get("metadata_json"), {}),
            "created_at": row["created_at"],
        }


class SharedContextBuilder:
    def __init__(self, store: AgentCommonsStore, history_limit: int = 10, evidence_limit: int = 10) -> None:
        self.store = store
        self.history_limit = history_limit
        self.evidence_limit = evidence_limit

    def build(self, tenant_id: str, thread_id: str, *, requested_budget: int = 10) -> dict[str, Any]:
        thread = self.store.get_thread(thread_id, tenant_id)
        if not thread:
            raise CommonsError("Thread not found")
        approved_decisions = [approval for approval in thread["approvals"] if approval["status"] == "APPROVED"]
        history = thread["messages"][-min(self.history_limit, requested_budget):]
        evidence = thread["evidence_references"][-self.evidence_limit:]
        return {
            "thread_id": thread_id,
            "task_id": thread["task_id"],
            "thread_history": history,
            "participants": thread["participants"],
            "prior_approved_decisions": approved_decisions,
            "evidence_links": evidence,
            "agent_registry_metadata": [item["trace"].get("agent") for item in history if item.get("trace", {}).get("agent")],
            "context_budget": {"history_messages": len(history), "evidence_links": len(evidence), "requested_budget": requested_budget},
            "provenance": ["thread_history", "approved_decisions", "evidence_links", "agent_registry_metadata"],
        }


class SupervisorAgent:
    def __init__(
        self,
        store: AgentCommonsStore,
        *,
        protocol: A2AProtocol | None = None,
        context_builder: SharedContextBuilder | None = None,
        supervisor_adapter: AgentAdapter | None = None,
        max_delegation_depth: int = 3,
    ) -> None:
        self.store = store
        self.protocol = protocol or A2AProtocol()
        self.context_builder = context_builder or SharedContextBuilder(store)
        self.supervisor_adapter = supervisor_adapter or OpenAIResponsesSupervisorAdapter()
        self.max_delegation_depth = max_delegation_depth
        self.adapters: dict[str, AgentAdapter] = {self.supervisor_adapter.agent_id: self.supervisor_adapter}
        self.protocol.create_client(self.supervisor_adapter.agent_id, self.supervisor_adapter.display_name, self.supervisor_adapter.capabilities()["capabilities"])
        self.agent_roles: dict[str, str] = {self.supervisor_adapter.agent_id: self.supervisor_adapter.role}

    def register_adapter(self, adapter: AgentAdapter) -> AgentAdapter:
        self.adapters[adapter.agent_id] = adapter
        self.agent_roles[adapter.agent_id] = adapter.role
        self.protocol.create_client(adapter.agent_id, adapter.display_name, adapter.capabilities()["capabilities"])
        return adapter

    def agent_health(self, agent_id: str) -> dict[str, Any] | None:
        adapter = self.adapters.get(agent_id)
        return adapter.health() if adapter else None

    def _find_agent(self, capability: str, *, role: str | None = None) -> AgentAdapter:
        matches = []
        for adapter in self.adapters.values():
            caps = adapter.capabilities()["capabilities"]
            if capability in caps and (role is None or adapter.role == role):
                matches.append(adapter)
        if not matches:
            raise CommonsError(f"No agent registered for capability '{capability}'")
        return matches[0]

    async def _delegate(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        task_id: str,
        sender: str,
        target: AgentAdapter,
        objective: str,
        acceptance_criteria: list[str],
        correlation_id: str,
        trace: dict[str, Any],
        idempotency_key: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        path = list(trace.get("agent_path", []))
        if target.agent_id in path or len(path) >= self.max_delegation_depth:
            raise LoopDetectedError("Delegation loop detected or maximum delegation depth exceeded")
        run = self.store.start_agent_run(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            task_id=task_id,
            agent_id=target.agent_id,
            role=target.role,
            correlation_id=correlation_id,
            context=context,
            parent_run_id=trace.get("parent_run_id"),
            idempotency_key=idempotency_key,
        )
        delegation_trace = {
            **trace,
            "agent": target.agent_id,
            "agent_role": target.role,
            "run_id": run["run_id"],
            "agent_path": [*path, target.agent_id],
        }
        supervisor_client = self.protocol.create_client(sender, sender, ["orchestrate"])
        worker_client = self.protocol.create_client(target.agent_id, target.display_name, target.capabilities()["capabilities"])
        message = Message(
            from_agent=sender,
            to_agent=target.agent_id,
            message_type=MessageType.DELEGATION,
            payload={"run_id": run["run_id"], "objective": objective, "acceptance_criteria": acceptance_criteria},
            correlation_id=correlation_id,
            priority=Priority.HIGH,
        )
        await supervisor_client._bus.publish(message)
        self.store.add_message(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            task_id=task_id,
            sender=sender,
            recipients=[target.agent_id],
            correlation_id=correlation_id,
            lifecycle_status="ASSIGNED",
            payload=message.payload,
            evidence=[],
            trace=delegation_trace,
            message_id=message.message_id,
        )
        self.store.add_task_event(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            task_id=task_id,
            status="ASSIGNED",
            actor=sender,
            run_id=run["run_id"],
            details={"objective": objective, "to_agent": target.agent_id, "priority": "P1", "notes": "Delegated by supervisor."},
        )
        invocation = target.invoke(
            {"run_id": run["run_id"], "objective": objective, "acceptance_criteria": acceptance_criteria},
            context,
        )
        ack_message = Message(
            from_agent=target.agent_id,
            to_agent=sender,
            message_type=MessageType.RESPONSE,
            payload={"run_id": run["run_id"], "status": invocation.status, "output": invocation.output},
            correlation_id=correlation_id,
            priority=Priority.NORMAL,
        )
        await worker_client._bus.publish(ack_message)
        self.store.add_message(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            task_id=task_id,
            sender=target.agent_id,
            recipients=[sender],
            correlation_id=correlation_id,
            lifecycle_status="RESULT",
            payload=ack_message.payload,
            evidence=invocation.evidence,
            trace=delegation_trace,
            message_id=ack_message.message_id,
        )
        self.store.complete_agent_run(
            run["run_id"],
            tenant_id,
            status=invocation.status,
            output=invocation.output,
            rationale=invocation.rationale,
            tool_calls=invocation.tool_calls,
        )
        self.store.add_task_event(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            task_id=task_id,
            status="RESULT",
            actor=target.agent_id,
            run_id=run["run_id"],
            details={"objective": objective, "to_agent": sender, "notes": invocation.rationale},
            evidence=invocation.evidence,
        )
        return {"run": self.store.get_run_trace(run["run_id"], tenant_id)["run"], "invocation": invocation, "trace": delegation_trace}

    async def submit_objective(
        self,
        *,
        principal: Principal,
        workspace_id: str,
        channel_id: str,
        objective: str,
        acceptance_criteria: list[str] | None = None,
        builder_capability: str = "build",
        reviewer_capability: str = "review",
        idempotency_key: str | None = None,
        thread_title: str | None = None,
    ) -> dict[str, Any]:
        principal.ensure("objective:create")
        if idempotency_key:
            existing_thread_id = self.store.get_idempotency_resource("objective", principal.tenant_id, idempotency_key)
            if existing_thread_id:
                existing = self.store.get_thread(existing_thread_id, principal.tenant_id)
                if existing:
                    return existing
        thread = self.store.create_thread(
            principal.tenant_id,
            workspace_id,
            channel_id,
            thread_title or objective,
            metadata={"objective": objective, "builder_capability": builder_capability, "reviewer_capability": reviewer_capability},
        )
        if idempotency_key:
            self.store.remember_idempotency("objective", principal.tenant_id, idempotency_key, thread["thread_id"])
        self.store.add_participant(principal.tenant_id, workspace_id, channel_id, thread["thread_id"], principal.principal_id, "human", principal.role, principal.principal_id)
        self.store.add_participant(principal.tenant_id, workspace_id, channel_id, thread["thread_id"], self.supervisor_adapter.agent_id, "agent", "supervisor", self.supervisor_adapter.display_name)
        self.store.add_message(
            tenant_id=principal.tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            sender=principal.principal_id,
            recipients=[self.supervisor_adapter.agent_id],
            correlation_id=uuid.uuid4().hex,
            lifecycle_status="ASSIGNED",
            payload={"objective": objective, "acceptance_criteria": acceptance_criteria or []},
            evidence=[],
            trace={"agent": self.supervisor_adapter.agent_id, "agent_role": "supervisor"},
        )
        self.store.add_task_event(
            tenant_id=principal.tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            status="ASSIGNED",
            actor=principal.principal_id,
            details={"objective": objective, "to_agent": self.supervisor_adapter.agent_id, "notes": "Owner objective submitted."},
        )
        context = self.context_builder.build(principal.tenant_id, thread["thread_id"])
        plan = self.supervisor_adapter.invoke(
            {"run_id": thread["task_id"], "objective": objective, "acceptance_criteria": acceptance_criteria or [], "builder_capability": builder_capability, "reviewer_capability": reviewer_capability},
            context,
        )
        builder = self._find_agent(builder_capability)
        reviewer = self._find_agent(reviewer_capability, role="reviewer")
        builder_result = await self._delegate(
            tenant_id=principal.tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            sender=self.supervisor_adapter.agent_id,
            target=builder,
            objective=plan.output["builder_task"]["objective"],
            acceptance_criteria=plan.output["builder_task"]["acceptance_criteria"],
            correlation_id=uuid.uuid4().hex,
            trace={"agent_path": [self.supervisor_adapter.agent_id], "parent_run_id": None},
            idempotency_key=f"{thread['thread_id']}:builder",
            context=context,
        )
        reviewer_context = self.context_builder.build(principal.tenant_id, thread["thread_id"])
        reviewer_result = await self._delegate(
            tenant_id=principal.tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            sender=self.supervisor_adapter.agent_id,
            target=reviewer,
            objective=plan.output["review_task"]["objective"],
            acceptance_criteria=plan.output["review_task"]["acceptance_criteria"],
            correlation_id=builder_result["run"]["correlation_id"],
            trace={"agent_path": [self.supervisor_adapter.agent_id], "parent_run_id": builder_result["run"]["run_id"]},
            idempotency_key=f"{thread['thread_id']}:reviewer",
            context={**reviewer_context, "builder_output": builder_result["invocation"].output},
        )
        disagreement = bool(reviewer_result["invocation"].output.get("material_disagreement"))
        if disagreement:
            approval = self.store.create_approval(
                tenant_id=principal.tenant_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                thread_id=thread["thread_id"],
                task_id=thread["task_id"],
                run_id=builder_result["run"]["run_id"],
                requested_by=self.supervisor_adapter.agent_id,
                reason="Material disagreement escalated to owner.",
            )
            self.store.add_task_event(
                tenant_id=principal.tenant_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                thread_id=thread["thread_id"],
                task_id=thread["task_id"],
                status="BLOCKED",
                actor=self.supervisor_adapter.agent_id,
                run_id=builder_result["run"]["run_id"],
                details={"objective": objective, "owner_decision_required": True, "notes": "Reviewer raised material disagreement.", "approval_id": approval["approval_id"]},
            )
        else:
            self.store.add_task_event(
                tenant_id=principal.tenant_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                thread_id=thread["thread_id"],
                task_id=thread["task_id"],
                status="CLOSED",
                actor=self.supervisor_adapter.agent_id,
                run_id=builder_result["run"]["run_id"],
                details={"objective": objective, "notes": "Builder and reviewer completed without material disagreement."},
            )
        return self.store.get_thread(thread["thread_id"], principal.tenant_id) or thread

    def decide_run(
        self,
        *,
        principal: Principal,
        run_id: str,
        decision: str,
        reason: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        principal.ensure("approval:decide")
        trace = self.store.get_run_trace(run_id, principal.tenant_id)
        if not trace:
            raise CommonsError("Run not found")
        approvals = [item for item in trace["thread"]["approvals"] if item["run_id"] == run_id]
        if not approvals:
            raise CommonsError("Approval not found")
        approval = approvals[0]
        if approval["status"] in {"APPROVED", "REJECTED"} and not idempotency_key:
            raise IdempotencyConflictError("Approval already decided")
        decided = self.store.decide_approval(
            approval["approval_id"],
            principal.tenant_id,
            approver=principal.principal_id,
            decision=decision,
            reason=reason,
            idempotency_key=idempotency_key,
        )
        self.store.add_task_event(
            tenant_id=principal.tenant_id,
            workspace_id=trace["run"]["workspace_id"],
            channel_id=trace["run"]["channel_id"],
            thread_id=trace["run"]["thread_id"],
            task_id=trace["run"]["task_id"],
            status="CLOSED" if decision == "approve" else "REJECTED",
            actor=principal.principal_id,
            run_id=run_id,
            details={"objective": trace["thread"]["title"], "notes": reason or "Owner decision recorded.", "owner_decision_required": False},
        )
        return self.store.get_run_trace(run_id, principal.tenant_id) or {"run": trace["run"], "approval": decided}
