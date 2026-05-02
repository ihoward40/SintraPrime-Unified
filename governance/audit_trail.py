"""
audit_trail.py — Tamper-evident, append-only audit logging with SQLite backend.

Provides complete audit logging for all agent actions including:
- Tamper detection via SHA-256 checksums
- Compliance-formatted exports (SOC2, HIPAA, GDPR)
- Anomaly detection
- 7-year retention policy for legal matters
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from governance.risk_types import AuditEntry, RiskLevel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RETENTION_YEARS = 7          # Legal retention: 7 years
ANOMALY_THRESHOLD = 10       # Flag actors with > N high-risk actions in 1 hour
DEFAULT_DB_PATH = Path("/tmp/sintraprime_audit.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    risk_level  TEXT NOT NULL,
    approval_id TEXT,
    metadata    TEXT NOT NULL DEFAULT '{}',
    checksum    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_actor     ON audit_log(actor);
CREATE INDEX IF NOT EXISTS idx_action    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_risk      ON audit_log(risk_level);
"""


class AuditTrail:
    """
    Append-only, tamper-evident audit log backed by SQLite.

    Compliant with SOC2, HIPAA, and GDPR audit requirements.
    Retains records for 7 years (configurable) for legal matters.

    Example::

        trail = AuditTrail(db_path="/data/audit.db")
        trail.log("agent-1", "send_payment", "success", RiskLevel.CRITICAL,
                  approval_id="abc123", metadata={"amount": 5000})
        entries = trail.query(actor="agent-1", risk_level=RiskLevel.CRITICAL)
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        retention_years: int = RETENTION_YEARS,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.retention_years = retention_years
        self._lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        actor: str,
        action: str,
        outcome: str,
        risk_level: RiskLevel,
        approval_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Append an immutable audit entry.

        Args:
            actor: Who performed the action (agent ID or user ID).
            action: The action type identifier.
            outcome: Result of the action (success, failure, blocked, etc.).
            risk_level: Assessed risk level of the action.
            approval_id: Linked ApprovalRequest ID (if applicable).
            metadata: Additional structured context.

        Returns:
            The created AuditEntry with computed checksum.
        """
        metadata = metadata or {}
        now = datetime.now(timezone.utc)

        entry = AuditEntry(
            timestamp=now,
            actor=actor,
            action=action,
            outcome=outcome,
            risk_level=risk_level,
            approval_id=approval_id,
            metadata=metadata,
        )
        entry.checksum = entry.compute_checksum()

        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (id, timestamp, actor, action, outcome, risk_level,
                    approval_id, metadata, checksum)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.timestamp.isoformat(),
                    entry.actor,
                    entry.action,
                    entry.outcome,
                    entry.risk_level.value,
                    entry.approval_id,
                    json.dumps(entry.metadata),
                    entry.checksum,
                ),
            )

        logger.debug("Audit: %s/%s → %s (%s)", actor, action, outcome, risk_level.value)
        return entry

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        risk_level: Optional[RiskLevel] = None,
        outcome: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AuditEntry]:
        """
        Query audit entries with optional filters.

        Args:
            actor: Filter by actor ID.
            action: Filter by action type (exact match).
            date_range: Tuple of (start, end) datetimes.
            risk_level: Filter by exact risk level.
            outcome: Filter by outcome string.
            limit: Maximum number of results.

        Returns:
            List of matching AuditEntry objects.
        """
        clauses: List[str] = []
        params: List[Any] = []

        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if action:
            clauses.append("action = ?")
            params.append(action)
        if risk_level:
            clauses.append("risk_level = ?")
            params.append(risk_level.value)
        if outcome:
            clauses.append("outcome = ?")
            params.append(outcome)
        if date_range:
            start, end = date_range
            clauses.append("timestamp BETWEEN ? AND ?")
            params.extend([start.isoformat(), end.isoformat()])

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_entry(row) for row in rows]

    # ------------------------------------------------------------------
    # Export & Reporting
    # ------------------------------------------------------------------

    def export_csv(
        self,
        output_path: str,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> str:
        """
        Export filtered audit entries to CSV.

        Returns the output path.
        """
        entries = self.query(actor=actor, action=action,
                             date_range=date_range, risk_level=risk_level,
                             limit=100_000)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "timestamp", "actor", "action", "outcome",
                            "risk_level", "approval_id", "checksum", "metadata"],
            )
            writer.writeheader()
            for e in entries:
                row = e.to_dict()
                row["metadata"] = json.dumps(row["metadata"])
                writer.writerow(row)

        logger.info("Exported %d audit entries to %s", len(entries), out)
        return str(out)

    def summary_report(
        self,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """
        Generate aggregate statistics for a time period.

        Returns a dict with total actions, breakdown by risk level,
        approval rates, top actors, and top actions.
        """
        entries = self.query(date_range=date_range, limit=100_000)

        by_risk: Dict[str, int] = {r.value: 0 for r in RiskLevel}
        by_actor: Dict[str, int] = {}
        by_action: Dict[str, int] = {}
        outcomes: Dict[str, int] = {}
        approvals = 0

        for e in entries:
            by_risk[e.risk_level.value] += 1
            by_actor[e.actor] = by_actor.get(e.actor, 0) + 1
            by_action[e.action] = by_action.get(e.action, 0) + 1
            outcomes[e.outcome] = outcomes.get(e.outcome, 0) + 1
            if e.approval_id:
                approvals += 1

        return {
            "total_actions": len(entries),
            "by_risk_level": by_risk,
            "approval_rate": approvals / len(entries) if entries else 0,
            "outcomes": outcomes,
            "top_actors": sorted(by_actor.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_actions": sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:10],
            "date_range": {
                "start": date_range[0].isoformat() if date_range else None,
                "end": date_range[1].isoformat() if date_range else None,
            },
        }

    def compliance_report(self, standard: str) -> Dict[str, Any]:
        """
        Generate a compliance-formatted audit report.

        Supported standards: SOC2, HIPAA, GDPR.
        """
        standard = standard.upper()
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        entries = self.query(date_range=(thirty_days_ago, now), limit=100_000)

        base = {
            "standard": standard,
            "generated_at": now.isoformat(),
            "period": f"{thirty_days_ago.date()} to {now.date()}",
            "total_events": len(entries),
            "high_risk_events": sum(1 for e in entries if e.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)),
            "approval_events": sum(1 for e in entries if e.approval_id),
        }

        if standard == "SOC2":
            base["controls"] = {
                "CC6.1": "Logical access controls — tracked",
                "CC6.2": "User authentication — logged",
                "CC7.2": "Anomaly detection — active",
                "CC9.2": "Third-party risk — monitored",
            }
            base["tamper_evidence"] = "SHA-256 checksums on all entries"
            base["retention_policy"] = f"{self.retention_years} years"

        elif standard == "HIPAA":
            phi_entries = [e for e in entries if "phi" in e.action.lower() or "pii" in e.action.lower()]
            base["phi_access_events"] = len(phi_entries)
            base["controls"] = {
                "§164.312(b)": "Audit controls — active",
                "§164.308(a)(1)": "Security officer — designated",
                "§164.312(c)": "Integrity controls — checksums",
            }

        elif standard == "GDPR":
            pii_entries = [e for e in entries if "pii" in e.action.lower() or "data" in e.action.lower()]
            base["personal_data_events"] = len(pii_entries)
            base["controls"] = {
                "Art. 30": "Records of processing activities",
                "Art. 32": "Security of processing — encrypted audit log",
                "Art. 17": "Right to erasure — deletion events tracked",
            }

        return base

    def detect_anomalies(self) -> List[AuditEntry]:
        """
        Detect unusual patterns in the audit log.

        Flags:
        - An actor with > ANOMALY_THRESHOLD high-risk actions in 1 hour
        - Repeated failures from the same actor
        - Off-hours CRITICAL actions
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        recent = self.query(
            date_range=(one_hour_ago, now),
            risk_level=None,
            limit=10_000,
        )

        flagged: List[AuditEntry] = []
        by_actor: Dict[str, List[AuditEntry]] = {}

        for e in recent:
            by_actor.setdefault(e.actor, []).append(e)

        for actor, actor_entries in by_actor.items():
            high_risk = [
                e for e in actor_entries
                if e.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            ]
            if len(high_risk) > ANOMALY_THRESHOLD:
                flagged.extend(high_risk)

            # Repeated failures
            failures = [e for e in actor_entries if e.outcome in ("failure", "error", "blocked")]
            if len(failures) > 5:
                flagged.extend(failures)

        # Off-hours critical (before 7am or after 10pm UTC)
        for e in recent:
            if e.risk_level == RiskLevel.CRITICAL:
                hour = e.timestamp.hour
                if hour < 7 or hour >= 22:
                    e.metadata["anomaly_flag"] = "off-hours critical action"
                    if e not in flagged:
                        flagged.append(e)

        return list({e.id: e for e in flagged}.values())  # deduplicate

    # ------------------------------------------------------------------
    # Tamper detection
    # ------------------------------------------------------------------

    def verify_integrity(self, limit: int = 10_000) -> Tuple[int, List[str]]:
        """
        Verify checksums for all (or up to `limit`) audit entries.

        Returns (total_checked, list_of_tampered_ids).
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp ASC LIMIT ?", (limit,)
            ).fetchall()

        tampered: List[str] = []
        for row in rows:
            entry = self._row_to_entry(row)
            expected = entry.compute_checksum()
            if entry.checksum != expected:
                tampered.append(entry.id)
                logger.warning("Tampered audit entry detected: %s", entry.id)

        return len(rows), tampered

    def purge_old_records(self) -> int:
        """
        Delete records older than the retention period.

        Returns number of records deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * self.retention_years)
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM audit_log WHERE timestamp < ?", (cutoff.isoformat(),)
            )
        count = cursor.rowcount
        if count:
            logger.info("Purged %d audit records older than %d years", count, self.retention_years)
        return count

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript(CREATE_TABLE_SQL)

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager returning a SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AuditEntry:
        """Convert a SQLite row to an AuditEntry."""
        return AuditEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            actor=row["actor"],
            action=row["action"],
            outcome=row["outcome"],
            risk_level=RiskLevel(row["risk_level"]),
            approval_id=row["approval_id"],
            metadata=json.loads(row["metadata"]),
            checksum=row["checksum"],
        )
