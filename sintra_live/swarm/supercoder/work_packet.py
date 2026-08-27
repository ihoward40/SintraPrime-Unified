"""SuperCoder work packets — bounded, resumable units of work for one worker slice."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json


class PacketStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CHECKPOINTED = "CHECKPOINTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class WorkPacket:
    """A bounded work unit that fits within one worker slice (~210s).

    Never dispatch 'fix the whole system' — dispatch a WorkPacket.
    """
    packet_id: str
    mission_id: str
    objective: str
    exact_files: Tuple[str, ...]
    required_reads: Tuple[str, ...] = ()
    starting_checkpoint_id: Optional[str] = None
    expected_delta: str = ""
    tests: Tuple[str, ...] = ()
    prohibited_actions: Tuple[str, ...] = ()
    completion_condition: str = ""
    handoff_condition: str = ""
    worker_id: str = ""
    status: PacketStatus = PacketStatus.PENDING
    created_at: str = ""
    sequence: int = 0

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", _utc_now())
        if not self.packet_id:
            h = hashlib.sha256(
                f"{self.mission_id}:{self.objective}:{self.sequence}".encode()
            ).hexdigest()[:24]
            object.__setattr__(self, "packet_id", f"pkt-{h}")

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "packet_id": self.packet_id,
                "mission_id": self.mission_id,
                "objective": self.objective,
                "exact_files": list(self.exact_files),
                "required_reads": list(self.required_reads),
                "starting_checkpoint_id": self.starting_checkpoint_id,
                "expected_delta": self.expected_delta,
                "tests": list(self.tests),
                "prohibited_actions": list(self.prohibited_actions),
                "completion_condition": self.completion_condition,
                "handoff_condition": self.handoff_condition,
                "worker_id": self.worker_id,
                "status": self.status.value,
                "created_at": self.created_at,
                "sequence": self.sequence,
            },
            sort_keys=True,
        ).encode()

    def packet_hash(self) -> str:
        return hashlib.sha256(self.to_json()).hexdigest()


class PacketScheduler:
    """Manages work packet lifecycle and sequencing for a coding mission."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._packets: List[WorkPacket] = []
        self._seq = 0

    def create_packet(
        self,
        objective: str,
        exact_files: Tuple[str, ...],
        required_reads: Tuple[str, ...] = (),
        expected_delta: str = "",
        tests: Tuple[str, ...] = (),
        prohibited_actions: Tuple[str, ...] = (),
        completion_condition: str = "",
        handoff_condition: str = "",
    ) -> WorkPacket:
        pkt = WorkPacket(
            packet_id="",
            mission_id=self.mission_id,
            objective=objective,
            exact_files=exact_files,
            required_reads=required_reads,
            expected_delta=expected_delta,
            tests=tests,
            prohibited_actions=prohibited_actions,
            completion_condition=completion_condition,
            handoff_condition=handoff_condition,
            sequence=self._seq,
        )
        self._seq += 1
        self._packets.append(pkt)
        return pkt

    def restore_packet(self, packet: WorkPacket) -> None:
        """Restore an integrity-verified packet during process recovery."""
        if packet.mission_id != self.mission_id:
            raise ValueError("Packet mission identity mismatch")
        if any(existing.packet_id == packet.packet_id for existing in self._packets):
            raise ValueError(f"Duplicate restored packet {packet.packet_id}")
        self._packets.append(packet)
        self._seq = max(self._seq, packet.sequence + 1)

    def next_pending(self) -> Optional[WorkPacket]:
        for pkt in self._packets:
            if pkt.status == PacketStatus.PENDING:
                return pkt
        return None

    def get_packet(self, packet_id: str) -> WorkPacket:
        for packet in self._packets:
            if packet.packet_id == packet_id:
                return packet
        raise KeyError(f"Packet {packet_id} not found")

    def mark_active(self, packet_id: str, worker_id: str) -> WorkPacket:
        for i, pkt in enumerate(self._packets):
            if pkt.packet_id == packet_id:
                updated = WorkPacket(
                    packet_id=pkt.packet_id,
                    mission_id=pkt.mission_id,
                    objective=pkt.objective,
                    exact_files=pkt.exact_files,
                    required_reads=pkt.required_reads,
                    starting_checkpoint_id=pkt.starting_checkpoint_id,
                    expected_delta=pkt.expected_delta,
                    tests=pkt.tests,
                    prohibited_actions=pkt.prohibited_actions,
                    completion_condition=pkt.completion_condition,
                    handoff_condition=pkt.handoff_condition,
                    worker_id=worker_id,
                    status=PacketStatus.ACTIVE,
                    created_at=pkt.created_at,
                    sequence=pkt.sequence,
                )
                self._packets[i] = updated
                return updated
        raise KeyError(f"Packet {packet_id} not found")

    def mark_completed(self, packet_id: str) -> WorkPacket:
        for i, pkt in enumerate(self._packets):
            if pkt.packet_id == packet_id:
                updated = WorkPacket(
                    packet_id=pkt.packet_id,
                    mission_id=pkt.mission_id,
                    objective=pkt.objective,
                    exact_files=pkt.exact_files,
                    required_reads=pkt.required_reads,
                    starting_checkpoint_id=pkt.starting_checkpoint_id,
                    expected_delta=pkt.expected_delta,
                    tests=pkt.tests,
                    prohibited_actions=pkt.prohibited_actions,
                    completion_condition=pkt.completion_condition,
                    handoff_condition=pkt.handoff_condition,
                    worker_id=pkt.worker_id,
                    status=PacketStatus.COMPLETED,
                    created_at=pkt.created_at,
                    sequence=pkt.sequence,
                )
                self._packets[i] = updated
                return updated
        raise KeyError(f"Packet {packet_id} not found")

    def all_packets(self) -> List[WorkPacket]:
        return list(self._packets)

    def completed_count(self) -> int:
        return sum(1 for p in self._packets if p.status == PacketStatus.COMPLETED)

    def pending_count(self) -> int:
        return sum(1 for p in self._packets if p.status == PacketStatus.PENDING)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")