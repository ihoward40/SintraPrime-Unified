"""Evidence chain and sealing for offline integration."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable evidence record with SHA-256 hash."""
    mission_id: str
    record_type: str
    content: Dict[str, Any]
    previous_hash: str
    record_hash: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, 'timestamp', time.time())
        if not self.record_hash:
            content_str = json.dumps({
                "mission_id": self.mission_id,
                "record_type": self.record_type,
                "content": self.content,
                "previous_hash": self.previous_hash,
                "timestamp": self.timestamp
            }, sort_keys=True, separators=(",", ":"))
            object.__setattr__(self, 'record_hash', hashlib.sha256(content_str.encode()).hexdigest())


class EvidenceChain:
    """Append-only hash-chained evidence store."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.records: List[EvidenceRecord] = []
        self.genesis_hash = hashlib.sha256(f"SP-LIVE-001|{mission_id}|genesis".encode()).hexdigest()

    def append(self, record_type: str, content: Dict[str, Any]) -> EvidenceRecord:
        """Append a new evidence record."""
        previous_hash = self.records[-1].record_hash if self.records else self.genesis_hash
        record = EvidenceRecord(
            mission_id=self.mission_id,
            record_type=record_type,
            content=content,
            previous_hash=previous_hash
        )
        self.records.append(record)
        return record

    def verify_chain(self) -> bool:
        """Verify the entire hash chain."""
        if not self.records:
            return True
        
        # Check genesis
        if self.records[0].previous_hash != self.genesis_hash:
            return False
        
        # Check each link
        for i, record in enumerate(self.records):
            expected_hash = record.record_hash
            content_str = json.dumps({
                "mission_id": record.mission_id,
                "record_type": record.record_type,
                "content": record.content,
                "previous_hash": record.previous_hash,
                "timestamp": record.timestamp
            }, sort_keys=True, separators=(",", ":"))
            actual_hash = hashlib.sha256(content_str.encode()).hexdigest()
            if expected_hash != actual_hash:
                return False
            
            # Check link to previous
            if i > 0 and record.previous_hash != self.records[i-1].record_hash:
                return False
        
        return True

    def get_chain_root(self) -> str:
        """Get the root hash of the evidence chain."""
        return self.records[-1].record_hash if self.records else self.genesis_hash

    def get_all_records(self) -> List[Dict[str, Any]]:
        return [{"type": r.record_type, "content": r.content, "hash": r.record_hash, "previous": r.previous_hash, "timestamp": r.timestamp} for r in self.records]