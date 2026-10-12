"""Durable, append-only SQLite approval ledger for AuthorityApprovalService.

Enforces cross-process atomic issuance, validation, and single-use consumption.
All mutations and status transitions are guarded by SQLite BEGIN IMMEDIATE
write-lock transactions.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ApprovalLedger",
    "LedgerError",
    "LedgerUnavailableError",
    "LedgerRecord",
    "SCHEMA_VERSION",
]

SCHEMA_VERSION = 2

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS approvals (
    approval_id       TEXT PRIMARY KEY,
    mission_id        TEXT NOT NULL,
    actor_id          TEXT NOT NULL,
    tenant_id         TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    resource_json     TEXT NOT NULL,
    issued_by         TEXT NOT NULL,
    issued_at         TEXT NOT NULL,
    expires_at        TEXT NOT NULL,
    permitted_roles   TEXT NOT NULL,
    permitted_workers TEXT NOT NULL,
    permitted_classes TEXT NOT NULL,
    context_hash      TEXT NOT NULL,
    status            TEXT NOT NULL,
    consumed_at       TEXT,
    consumed_by       TEXT,
    revoked_at        TEXT,
    revoked_by        TEXT,
    revocation_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant ON approvals(tenant_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS ledger_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class LedgerError(Exception):
    """Base for ledger failures with machine-readable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class LedgerUnavailableError(LedgerError):
    """Database outage or file access error."""


@dataclass(frozen=True)
class LedgerRecord:
    """Immutable projection of an approval binding from the ledger."""

    approval_id: str
    mission_id: str
    actor_id: str
    tenant_id: str
    capabilities: frozenset[str]
    resource_urls: frozenset[str]
    issued_by: str
    issued_at: datetime
    expires_at: datetime
    permitted_roles: frozenset[str]
    permitted_workers: frozenset[str]
    permitted_execution_classes: frozenset[str]
    context_hash: str
    status: str
    consumed_at: datetime | None = None
    consumed_by: str | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None


class ApprovalLedger:
    """Thread-safe and cross-process SQLite ledger for approval state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10.0,
                isolation_level=None,  # Autocommit mode; transactions managed explicitly
            )
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            raise LedgerUnavailableError("LEDGER_UNAVAILABLE", str(exc)) from exc

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(_TABLE_DDL)
            cur = conn.execute("SELECT value FROM ledger_meta WHERE key = 'schema_version'")
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO ledger_meta (key, value) VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )

    def _row_to_record(self, row: sqlite3.Row) -> LedgerRecord:
        return LedgerRecord(
            approval_id=row["approval_id"],
            mission_id=row["mission_id"],
            actor_id=row["actor_id"],
            tenant_id=row["tenant_id"],
            capabilities=frozenset(json.loads(row["capabilities_json"])),
            resource_urls=frozenset(json.loads(row["resource_json"])),
            issued_by=row["issued_by"],
            issued_at=datetime.fromisoformat(row["issued_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            permitted_roles=frozenset(json.loads(row["permitted_roles"])),
            permitted_workers=frozenset(json.loads(row["permitted_workers"])),
            permitted_execution_classes=frozenset(json.loads(row["permitted_classes"])),
            context_hash=row["context_hash"],
            status=row["status"],
            consumed_at=datetime.fromisoformat(row["consumed_at"]) if row["consumed_at"] else None,
            consumed_by=row["consumed_by"],
            revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
            revoked_by=row["revoked_by"],
            revocation_reason=row["revocation_reason"],
        )

    def issue(
        self,
        *,
        approval_id: str,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        issued_by: str,
        issued_at: datetime,
        expires_at: datetime,
        permitted_roles: frozenset[str],
        permitted_workers: frozenset[str],
        permitted_execution_classes: frozenset[str],
        context_hash: str,
    ) -> LedgerRecord:
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute("SELECT 1 FROM approvals WHERE approval_id = ?", (approval_id,))
                if cur.fetchone():
                    raise LedgerError("DUPLICATE_APPROVAL_ID", f"Approval {approval_id} already exists")

                conn.execute(
                    """
                    INSERT INTO approvals (
                        approval_id, mission_id, actor_id, tenant_id,
                        capabilities_json, resource_json, issued_by,
                        issued_at, expires_at, permitted_roles,
                        permitted_workers, permitted_classes, context_hash,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ISSUED')
                    """,
                    (
                        approval_id,
                        mission_id,
                        actor_id,
                        tenant_id,
                        json.dumps(sorted(capabilities)),
                        json.dumps(sorted(resource_urls)),
                        issued_by,
                        issued_at.isoformat(),
                        expires_at.isoformat(),
                        json.dumps(sorted(permitted_roles)),
                        json.dumps(sorted(permitted_workers)),
                        json.dumps(sorted(permitted_execution_classes)),
                        context_hash,
                    ),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        record = self.load(approval_id)
        if record is None:
            raise LedgerUnavailableError("LEDGER_WRITE_VERIFICATION_FAILED", approval_id)
        return record

    def load(self, approval_id: str) -> LedgerRecord | None:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def status(self, approval_id: str) -> str:
        record = self.load(approval_id)
        return record.status if record else "UNKNOWN"

    def revoke(self, approval_id: str, *, by: str, reason: str, now: datetime | None = None) -> None:
        now_dt = now or datetime.now(UTC)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute("SELECT status FROM approvals WHERE approval_id = ?", (approval_id,))
                row = cur.fetchone()
                if not row:
                    raise LedgerError("UNKNOWN_APPROVAL", f"Approval {approval_id} not found")
                if row["status"] == "CONSUMED":
                    raise LedgerError("APPROVAL_ALREADY_CONSUMED", f"Approval {approval_id} was already consumed")

                conn.execute(
                    """
                    UPDATE approvals
                    SET status = 'REVOKED', revoked_at = ?, revoked_by = ?, revocation_reason = ?
                    WHERE approval_id = ?
                    """,
                    (now_dt.isoformat(), by, reason, approval_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def validate_and_consume(
        self,
        approval_id: str,
        *,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        role: str,
        worker_class: str,
        effect_class: str,
        context_hash: str,
        now: datetime | None = None,
    ) -> LedgerRecord:
        """Atomically validate scope and consume the approval under write lock."""
        now_dt = now or datetime.now(UTC)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cur = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))
                row = cur.fetchone()
                if not row:
                    raise LedgerError("UNKNOWN_APPROVAL", f"Approval {approval_id} never issued")

                rec = self._row_to_record(row)

                if rec.status == "CONSUMED":
                    raise LedgerError("APPROVAL_ALREADY_CONSUMED", f"Approval {approval_id} already consumed")
                if rec.status == "REVOKED":
                    raise LedgerError("APPROVAL_REVOKED", f"Approval {approval_id} was revoked")

                if now_dt >= rec.expires_at:
                    raise LedgerError("APPROVAL_EXPIRED", f"Approval {approval_id} expired at {rec.expires_at}")

                if rec.mission_id != mission_id:
                    raise LedgerError("MISSION_MISMATCH", f"Approval binds {rec.mission_id}, got {mission_id}")
                if rec.tenant_id != tenant_id:
                    raise LedgerError("TENANT_MISMATCH", f"Approval binds {rec.tenant_id}, got {tenant_id}")
                if rec.actor_id != actor_id:
                    raise LedgerError("ACTOR_MISMATCH", f"Approval binds {rec.actor_id}, got {actor_id}")

                if not rec.permitted_workers or worker_class not in rec.permitted_workers:
                    raise LedgerError("WORKER_CLASS_DENIED", f"Worker '{worker_class}' not in permitted_workers {sorted(rec.permitted_workers)}")
                if not rec.permitted_roles or role not in rec.permitted_roles:
                    raise LedgerError("ROLE_NOT_ALLOWED", f"Role '{role}' not in permitted_roles {sorted(rec.permitted_roles)}")
                if not rec.permitted_execution_classes or effect_class not in rec.permitted_execution_classes:
                    raise LedgerError("EXECUTION_CLASS_DENIED", f"Class '{effect_class}' not in permitted_classes {sorted(rec.permitted_execution_classes)}")

                if capabilities - rec.capabilities:
                    raise LedgerError("CAPABILITY_NOT_APPROVED", f"Capabilities {capabilities - rec.capabilities} exceed approval")
                if resource_urls - rec.resource_urls:
                    raise LedgerError("RESOURCE_NOT_APPROVED", f"Resources {resource_urls - rec.resource_urls} exceed approval")

                if not context_hash or rec.context_hash.strip() != context_hash.strip():
                    raise LedgerError("CONTEXT_MISMATCH", f"Context hash '{context_hash}' does not match approved '{rec.context_hash}'")

                conn.execute(
                    """
                    UPDATE approvals
                    SET status = 'CONSUMED', consumed_at = ?, consumed_by = ?
                    WHERE approval_id = ?
                    """,
                    (now_dt.isoformat(), actor_id, approval_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        consumed_rec = self.load(approval_id)
        if consumed_rec is None or consumed_rec.status != "CONSUMED":
            raise LedgerUnavailableError("CONSUMPTION_TRANSITION_FAILED", approval_id)
        return consumed_rec
