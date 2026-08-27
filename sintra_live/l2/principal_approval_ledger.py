"""L2-I7B disposable local file-backed single-use approval ledger.

Append-only, CAS-protected, crash-safe, restart-durable.
Uses test-controlled temporary directories only.
No database, no network, no provider, no credential access.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sintra_live.l2.principal_approval_contract import (
    ApprovalState,
    PrincipalApprovalRecord,
    TERMINAL_STATES,
    validate_transition,
)


class LedgerError(Exception):
    """Base ledger error."""


class CASConflict(LedgerError):
    """Prior-hash mismatch on append."""


class DuplicateApprovalId(LedgerError):
    """Approval ID already exists."""


class DuplicateNonce(LedgerError):
    """Nonce already used."""


class ReplayDenied(LedgerError):
    """Replay attempt on consumed/terminal approval."""


class ReuseDenied(LedgerError):
    """Reuse of consumed/terminal approval."""


class BackwardTransition(LedgerError):
    """Attempted backward or invalid state transition."""


class TerminalStateReopening(LedgerError):
    """Attempted transition from a terminal state."""


class HashChainBreak(LedgerError):
    """Ledger entry hash-chain verification failed."""


class MultipleHeads(LedgerError):
    """Multiple competing head entries for one approval ID."""


class MalformedLedgerEntry(LedgerError):
    """Ledger entry is structurally invalid."""


class AmbiguousConsumptionReuse(LedgerError):
    """Attempted reuse of an approval in CONSUMPTION_AMBIGUOUS state."""


class ApprovalLedger:
    """Disposable local file-backed append-only approval ledger.

    Stores one JSON file per approval_id, with an append-only list of
    ledger entries. Each entry binds the prior entry's hash for CAS.
    """

    def __init__(self, store_root: Path | str):
        self.root = Path(store_root)
        self.ledger_dir = self.root / "approvals"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self._nonce_index: Dict[str, str] = {}
        self._approval_index: Dict[str, str] = {}
        self._rebuild_indexes()

    def _path_for(self, approval_id: str) -> Path:
        return self.ledger_dir / f"{approval_id}.json"

    def _rebuild_indexes(self) -> None:
        """Rebuild in-memory indexes from persisted files on restart."""
        self._nonce_index.clear()
        self._approval_index.clear()
        for f in sorted(self.ledger_dir.glob("*.json")):
            entries = self._read_file(f)
            if not entries:
                continue
            head = entries[-1]
            aid = head["approval_id"]
            nonce = head["approval_nonce"]
            if aid in self._approval_index:
                raise MultipleHeads(f"duplicate approval file for {aid}")
            if nonce in self._nonce_index:
                raise DuplicateNonce(f"nonce collision on restart: {nonce}")
            self._approval_index[aid] = head["approval_record_sha256"]
            self._nonce_index[nonce] = aid

    def _read_file(self, path: Path) -> List[dict]:
        try:
            raw = path.read_bytes()
            data = json.loads(raw)
            if not isinstance(data, list):
                raise MalformedLedgerEntry("not a list")
            return data
        except (json.JSONDecodeError, OSError) as exc:
            raise MalformedLedgerEntry(str(exc)) from exc

    def _write_file(self, path: Path, entries: List[dict]) -> None:
        """Atomic write: temp → fsync → replace → fsync → readback."""
        raw = json.dumps(entries, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
        tmp = path.parent / f".{path.stem}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, "xb") as fh:
                fh.write(raw)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            with open(path, "r+b") as fh:
                os.fsync(fh.fileno())
            readback = path.read_bytes()
            if readback != raw:
                raise LedgerError("readback mismatch")
        except Exception as exc:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if isinstance(exc, LedgerError):
                raise
            raise LedgerError(f"write failed: {exc}") from exc

    def _verify_chain(self, entries: List[dict]) -> None:
        """Verify hash-chain integrity: each entry's prior must match previous entry's hash."""
        if not entries:
            return
        if entries[0]["prior_ledger_entry_sha256"] != "0" * 64:
            raise HashChainBreak("first entry prior must be zero hash")
        for i in range(1, len(entries)):
            prev_hash = entries[i - 1]["approval_record_sha256"]
            if entries[i]["prior_ledger_entry_sha256"] != prev_hash:
                raise HashChainBreak(f"chain break at entry {i}")

    def append(self, record: PrincipalApprovalRecord, from_state: ApprovalState,
               to_state: ApprovalState) -> dict:
        """Append a new ledger entry with CAS and transition validation."""
        aid = record.approval_id
        nonce = record.approval_nonce

        # Check nonce uniqueness
        if nonce in self._nonce_index and self._nonce_index[nonce] != aid:
            raise DuplicateNonce(f"nonce already used by {self._nonce_index[nonce]}")

        # Check approval ID uniqueness (first entry only)
        if aid in self._approval_index and not self._path_for(aid).exists():
            raise DuplicateApprovalId(f"approval ID {aid} already exists")

        path = self._path_for(aid)
        entries: List[dict] = []
        if path.exists():
            entries = self._read_file(path)
            self._verify_chain(entries)
            head = entries[-1]
            head_state = ApprovalState(head["state"])
            # Check transition validity
            if head_state in TERMINAL_STATES:
                if to_state != head_state:
                    raise TerminalStateReopening(
                        f"cannot transition from terminal {head_state.value}")
                if to_state in (ApprovalState.CONSUMED, ApprovalState.CONSUMPTION_AMBIGUOUS):
                    raise ReuseDenied(f"cannot reuse terminal {head_state.value}")
                raise ReuseDenied(f"terminal state {head_state.value}")
            if not validate_transition(head_state, to_state):
                raise BackwardTransition(
                    f"invalid transition {head_state.value} -> {to_state.value}")
            # CAS check
            if record.prior_ledger_entry_sha256 != head["approval_record_sha256"]:
                raise CASConflict("prior hash mismatch")
        else:
            if record.prior_ledger_entry_sha256 != "0" * 64:
                raise CASConflict("first entry prior must be zero hash")
            if from_state != ApprovalState.PROPOSED:
                raise BackwardTransition(
                    f"first entry must start from PROPOSED, got {from_state.value}")

        entry = {
            "approval_id": aid,
            "approval_nonce": nonce,
            "state": to_state.value,
            "from_state": from_state.value,
            "approval_record_sha256": record.approval_record_sha256,
            "prior_ledger_entry_sha256": record.prior_ledger_entry_sha256,
            "action_envelope_sha256": record.action_envelope_sha256,
            "timestamp": record.issued_at,
        }
        entries.append(entry)
        self._write_file(path, entries)

        # Update indexes
        self._approval_index[aid] = record.approval_record_sha256
        if nonce not in self._nonce_index:
            self._nonce_index[nonce] = aid

        return entry

    def load_head(self, approval_id: str) -> Optional[dict]:
        """Load the current head entry for an approval ID."""
        path = self._path_for(approval_id)
        if not path.exists():
            return None
        entries = self._read_file(path)
        self._verify_chain(entries)
        return entries[-1] if entries else None

    def load_all(self, approval_id: str) -> List[dict]:
        """Load all entries for an approval ID."""
        path = self._path_for(approval_id)
        if not path.exists():
            return []
        entries = self._read_file(path)
        self._verify_chain(entries)
        return entries

    def verify_integrity(self, approval_id: str) -> bool:
        """Verify the hash-chain integrity of an approval's ledger."""
        path = self._path_for(approval_id)
        if not path.exists():
            return True
        entries = self._read_file(path)
        self._verify_chain(entries)
        return True

    @property
    def approval_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._approval_index.keys()))


__all__ = [
    "ApprovalLedger",
    "LedgerError",
    "CASConflict",
    "DuplicateApprovalId",
    "DuplicateNonce",
    "ReplayDenied",
    "ReuseDenied",
    "BackwardTransition",
    "TerminalStateReopening",
    "HashChainBreak",
    "MultipleHeads",
    "MalformedLedgerEntry",
    "AmbiguousConsumptionReuse",
]