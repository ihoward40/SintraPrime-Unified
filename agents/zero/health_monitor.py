"""Health Monitor — Tracks repo health metrics over time.

Stores historical data in a local SQLite database and provides
rich dashboards and alerting when health degrades.
"""

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("health_monitor")
logger.setLevel(logging.INFO)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS health_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_tests INTEGER NOT NULL DEFAULT 0,
    passed_tests INTEGER NOT NULL DEFAULT 0,
    failed_tests INTEGER NOT NULL DEFAULT 0,
    skipped_tests INTEGER NOT NULL DEFAULT 0,
    pass_rate REAL NOT NULL DEFAULT 0.0,
    coverage_pct REAL,
    import_errors INTEGER NOT NULL DEFAULT 0,
    outdated_packages INTEGER NOT NULL DEFAULT 0,
    security_vulns INTEGER NOT NULL DEFAULT 0,
    extra_json TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass
class HealthSnapshot:
    """A point-in-time health measurement."""
    timestamp: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    pass_rate: float = 0.0
    coverage_pct: Optional[float] = None
    import_errors: int = 0
    outdated_packages: int = 0
    security_vulns: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Health alert record."""
    alert_type: str
    severity: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False


class HealthMonitor:
    """Monitors and tracks repository health over time.

    Uses a local SQLite database to persist snapshots and provides
    alerting when health degrades below configured thresholds.
    """

    def __init__(
        self,
        repo_root: Optional[str] = None,
        db_path: Optional[str] = None,
        alert_callback: Optional[Any] = None,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.db_path = db_path or str(self.repo_root / ".zero" / "health.db")
        self.alert_callback = alert_callback
        self._ensure_db()
        logger.info("HealthMonitor initialised — db=%s", self.db_path)

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(_SCHEMA_SQL)
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def capture_snapshot(self) -> HealthSnapshot:
        """Run tests and capture a health snapshot."""
        snap = HealthSnapshot(timestamp=datetime.now(timezone.utc).isoformat())
        test_result = self._run_pytest()
        snap.total_tests = test_result.get("total", 0)
        snap.passed_tests = test_result.get("passed", 0)
        snap.failed_tests = test_result.get("failed", 0)
        snap.skipped_tests = test_result.get("skipped", 0)
        snap.pass_rate = (snap.passed_tests / snap.total_tests) if snap.total_tests > 0 else 1.0
        snap.coverage_pct = test_result.get("coverage")
        snap.outdated_packages = len(self.check_dependency_drift())
        vulns = self.check_security_vulnerabilities()
        snap.security_vulns = len(vulns)
        self._save_snapshot(snap)
        logger.info("Snapshot captured — pass_rate=%.2f, vulns=%d", snap.pass_rate, snap.security_vulns)
        return snap

    def _run_pytest(self) -> Dict[str, Any]:
        """Run pytest and return structured results."""
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "--tb=no", "-q", "--no-header",
                 str(self.repo_root / "tests")],
                capture_output=True, text=True, timeout=300, cwd=str(self.repo_root),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        output = proc.stdout + "\n" + proc.stderr
        return self._parse_summary(output)

    @staticmethod
    def _parse_summary(output: str) -> Dict[str, Any]:
        """Parse the one-line pytest summary."""
        result: Dict[str, Any] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        for line in output.splitlines():
            lower = line.lower()
            if "passed" in lower or "failed" in lower:
                num = 0
                for token in line.replace(",", " ").split():
                    if token.isdigit():
                        num = int(token)
                    elif "passed" in token:
                        result["passed"] = num
                    elif "failed" in token:
                        result["failed"] = num
                    elif "skipped" in token:
                        result["skipped"] = num
                result["total"] = result["passed"] + result["failed"] + result["skipped"]
                break
        return result

    def _save_snapshot(self, snap: HealthSnapshot) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO health_snapshots "
            "(timestamp, total_tests, passed_tests, failed_tests, skipped_tests, "
            "pass_rate, coverage_pct, import_errors, outdated_packages, security_vulns, extra_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (snap.timestamp, snap.total_tests, snap.passed_tests, snap.failed_tests,
             snap.skipped_tests, snap.pass_rate, snap.coverage_pct, snap.import_errors,
             snap.outdated_packages, snap.security_vulns, json.dumps(snap.extra)),
        )
        conn.commit()
        conn.close()

    def check_dependency_drift(self) -> List[Dict[str, str]]:
        """Detect outdated packages."""
        outdated: List[Dict[str, str]] = []
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode == 0:
                outdated = json.loads(proc.stdout)
        except Exception:
            logger.warning("Could not check dependency drift.")
        return outdated

    def check_security_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Run pip-audit or safety to detect known vulnerabilities."""
        vulns: List[Dict[str, Any]] = []
        for tool_cmd in [
            [sys.executable, "-m", "pip_audit", "--format=json"],
            [sys.executable, "-m", "safety", "check", "--json"],
        ]:
            try:
                proc = subprocess.run(
                    tool_cmd, capture_output=True, text=True, timeout=120,
                    cwd=str(self.repo_root),
                )
                data = json.loads(proc.stdout)
                if isinstance(data, list):
                    vulns = data
                elif isinstance(data, dict):
                    vulns = data.get("vulnerabilities", data.get("results", []))
                break
            except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
                continue
        return vulns

    def generate_health_dashboard(self, limit: int = 30) -> Dict[str, Any]:
        """Return rich health metrics with trend data."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM health_snapshots ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        columns = [d[0] for d in conn.execute("SELECT * FROM health_snapshots LIMIT 0").description]
        conn.close()

        snapshots = [dict(zip(columns, r)) for r in rows]
        snapshots.reverse()

        pass_rates = [s["pass_rate"] for s in snapshots]
        vuln_counts = [s["security_vulns"] for s in snapshots]
        avg_pass = sum(pass_rates) / len(pass_rates) if pass_rates else 0.0

        latest = snapshots[-1] if snapshots else {}
        trend = "stable"
        if len(pass_rates) >= 3:
            recent = pass_rates[-3:]
            if recent[-1] < recent[0] - 0.05:
                trend = "declining"
            elif recent[-1] > recent[0] + 0.05:
                trend = "improving"

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "latest_snapshot": latest,
            "trend": trend,
            "average_pass_rate": round(avg_pass, 4),
            "total_snapshots": len(snapshots),
            "pass_rate_history": pass_rates,
            "vuln_count_history": vuln_counts,
            "alerts": self._recent_alerts(),
        }

    def _recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, timestamp, alert_type, severity, message, acknowledged "
            "FROM alerts ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "timestamp": r[1], "alert_type": r[2], "severity": r[3],
             "message": r[4], "acknowledged": bool(r[5])}
            for r in rows
        ]

    def alert_on_degradation(self, threshold: float = 0.95) -> Optional[Alert]:
        """Fire alert if pass rate below threshold."""
        conn = self._connect()
        row = conn.execute(
            "SELECT pass_rate FROM health_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        if row is None:
            return None

        current_rate = row[0]
        if current_rate < threshold:
            alert = Alert(
                alert_type="PASS_RATE_DEGRADATION",
                severity="HIGH" if current_rate < 0.80 else "MEDIUM",
                message=f"Test pass rate {current_rate:.2%} is below threshold {threshold:.2%}.",
            )
            self._save_alert(alert)
            if self.alert_callback:
                try:
                    self.alert_callback(asdict(alert))
                except Exception:
                    logger.exception("Alert callback failed.")
            return alert
        return None

    def _save_alert(self, alert: Alert) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO alerts (timestamp, alert_type, severity, message) VALUES (?,?,?,?)",
            (alert.timestamp, alert.alert_type, alert.severity, alert.message),
        )
        conn.commit()
        conn.close()

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert as acknowledged."""
        conn = self._connect()
        cur = conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return affected > 0
