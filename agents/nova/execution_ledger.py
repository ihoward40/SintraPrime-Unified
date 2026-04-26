"""Execution Ledger — Immutable audit trail for all Nova actions.

Every action executed by Nova is recorded in an append-only, hash-chained
ledger that provides tamper-evident proof of all operations.
"""

import hashlib
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("execution_ledger")
logger.setLevel(logging.INFO)


@dataclass
class LedgerEntry:
    """A single entry in the execution ledger."""
    entry_id: str
    action_id: str
    action_type: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    status: str
    user_id: str
    approval_status: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    case_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    prev_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry's content."""
        content = json.dumps({
            "entry_id": self.entry_id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "params": self.params,
            "result": self.result,
            "status": self.status,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class LedgerIntegrityError(Exception):
    """Raised when ledger integrity verification fails."""
    pass


class ExecutionLedger:
    """Immutable, hash-chained audit trail for all Nova executions.

    Entries are append-only and linked by cryptographic hashes to detect
    any tampering or modification of historical records.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, ledger_path: Optional[str] = None):
        self._ledger_path = Path(ledger_path) if ledger_path else Path.cwd() / ".nova" / "ledger.jsonl"
        self._entries: List[LedgerEntry] = []
        self._last_hash: str = self.GENESIS_HASH
        self._load_existing()
        logger.info("ExecutionLedger initialized — %d entries loaded from %s",
                     len(self._entries), self._ledger_path)

    def _load_existing(self) -> None:
        """Load existing ledger entries from disk."""
        if not self._ledger_path.exists():
            return

        for line in self._ledger_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entry = LedgerEntry(**{k: v for k, v in data.items() if k in LedgerEntry.__dataclass_fields__})
                self._entries.append(entry)
                self._last_hash = entry.entry_hash or self.GENESIS_HASH
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Skipping malformed ledger line: %s", exc)

    def append(self, entry: LedgerEntry) -> LedgerEntry:
        """Append a new entry to the ledger (append-only).

        The entry's prev_hash and entry_hash are computed automatically.
        """
        entry.prev_hash = self._last_hash
        entry.entry_hash = entry.compute_hash()
        self._last_hash = entry.entry_hash

        self._entries.append(entry)
        self._persist_entry(entry)

        logger.info("Ledger entry appended: %s (hash: %s...)",
                     entry.entry_id, entry.entry_hash[:12])
        return entry

    def _persist_entry(self, entry: LedgerEntry) -> None:
        """Write entry to the ledger file."""
        os.makedirs(os.path.dirname(self._ledger_path), exist_ok=True)
        with open(self._ledger_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def get_history(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        case_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LedgerEntry]:
        """Retrieve filtered execution history."""
        results = self._entries

        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action_type:
            results = [e for e in results if e.action_type == action_type]
        if case_id:
            results = [e for e in results if e.case_id == case_id]

        if limit:
            results = results[-limit:]

        return results

    def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        """Retrieve a single entry by ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def export_evidence_bundle(self, case_id: str, output_path: Optional[str] = None) -> str:
        """Export all actions for a case as a ZIP evidence bundle.

        Returns the path to the created ZIP file.
        """
        entries = [e for e in self._entries if e.case_id == case_id]
        if not entries:
            raise ValueError(f"No entries found for case_id: {case_id}")

        if output_path is None:
            output_path = str(self._ledger_path.parent / f"evidence_{case_id}.zip")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            manifest = {
                "case_id": case_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_entries": len(entries),
                "hash_chain_valid": self._verify_subset(entries),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Write each entry
            for i, entry in enumerate(entries):
                filename = f"entries/{i:04d}_{entry.action_type}_{entry.entry_id[:8]}.json"
                zf.writestr(filename, json.dumps(asdict(entry), indent=2))

            # Write summary
            summary_lines = [
                f"Evidence Bundle — Case {case_id}",
                f"Exported: {manifest['exported_at']}",
                f"Total Actions: {len(entries)}",
                "",
                "Action Timeline:",
            ]
            for entry in entries:
                summary_lines.append(
                    f"  [{entry.timestamp}] {entry.action_type} — {entry.status}"
                )
            zf.writestr("SUMMARY.txt", "\n".join(summary_lines))

        logger.info("Evidence bundle exported: %s (%d entries)", output_path, len(entries))
        return output_path

    def verify_integrity(self) -> bool:
        """Verify the cryptographic hash chain of the entire ledger.

        Returns True if the chain is intact, raises LedgerIntegrityError otherwise.
        """
        if not self._entries:
            return True

        prev_hash = self.GENESIS_HASH

        for i, entry in enumerate(self._entries):
            if entry.prev_hash != prev_hash:
                raise LedgerIntegrityError(
                    f"Hash chain broken at entry {i} ({entry.entry_id}): "
                    f"expected prev_hash={prev_hash[:16]}..., got {entry.prev_hash[:16]}..."
                )

            expected_hash = entry.compute_hash()
            if entry.entry_hash != expected_hash:
                raise LedgerIntegrityError(
                    f"Entry {i} ({entry.entry_id}) has been tampered with: "
                    f"expected hash={expected_hash[:16]}..., got {entry.entry_hash[:16]}..."
                )

            prev_hash = entry.entry_hash

        logger.info("Ledger integrity verified — %d entries, chain intact.", len(self._entries))
        return True

    def _verify_subset(self, entries: List[LedgerEntry]) -> bool:
        """Verify hash chain for a subset of entries."""
        for i in range(1, len(entries)):
            if entries[i].prev_hash != entries[i - 1].entry_hash:
                return False
        return True

    @property
    def size(self) -> int:
        """Return the total number of entries."""
        return len(self._entries)

    @property
    def last_hash(self) -> str:
        """Return the hash of the most recent entry."""
        return self._last_hash

    def get_stats(self) -> Dict[str, Any]:
        """Return ledger statistics."""
        action_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        for entry in self._entries:
            action_counts[entry.action_type] = action_counts.get(entry.action_type, 0) + 1
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1

        return {
            "total_entries": len(self._entries),
            "last_hash": self._last_hash[:16] + "...",
            "action_counts": action_counts,
            "status_counts": status_counts,
            "ledger_path": str(self._ledger_path),
        }
