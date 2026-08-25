"""SuperCoder context capsule — compressed durable state for successor workers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json


@dataclass(frozen=True)
class ContextCapsule:
    """Minimum context needed for a new worker to continue without rediscovery.

    This is NOT a full history dump. It is the compressed essential state
    that lets a replacement worker resume in seconds, not minutes.
    """
    mission_id: str
    mission_objective: str
    architecture_rules: Tuple[str, ...]
    current_baseline: str
    owned_paths: Tuple[str, ...]
    current_phase: str
    completed_packets: Tuple[str, ...]
    active_packet: Optional[str]
    last_checkpoint_id: Optional[str]
    relevant_apis: Tuple[str, ...]
    discoveries: Tuple[str, ...]
    failing_tests: Tuple[str, ...]
    next_action: str
    prohibited_actions: Tuple[str, ...]
    authority_delta: int = 0
    side_effects: int = 0

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "mission_id": self.mission_id,
                "mission_objective": self.mission_objective,
                "architecture_rules": list(self.architecture_rules),
                "current_baseline": self.current_baseline,
                "owned_paths": list(self.owned_paths),
                "current_phase": self.current_phase,
                "completed_packets": list(self.completed_packets),
                "active_packet": self.active_packet,
                "last_checkpoint_id": self.last_checkpoint_id,
                "relevant_apis": list(self.relevant_apis),
                "discoveries": list(self.discoveries),
                "failing_tests": list(self.failing_tests),
                "next_action": self.next_action,
                "prohibited_actions": list(self.prohibited_actions),
                "authority_delta": self.authority_delta,
                "side_effects": self.side_effects,
            },
            sort_keys=True,
        ).encode()

    def capsule_hash(self) -> str:
        return hashlib.sha256(self.to_json()).hexdigest()

    def summary(self) -> str:
        """One-line summary for logging."""
        return (
            f"Capsule[{self.mission_id[:16]}] "
            f"phase={self.current_phase} "
            f"completed={len(self.completed_packets)} "
            f"next={self.next_action[:60]}"
        )


def build_capsule(
    mission_id: str,
    mission_objective: str,
    architecture_rules: Tuple[str, ...],
    current_baseline: str,
    owned_paths: Tuple[str, ...],
    current_phase: str,
    completed_packets: Tuple[str, ...],
    active_packet: Optional[str],
    last_checkpoint_id: Optional[str],
    relevant_apis: Tuple[str, ...] = (),
    discoveries: Tuple[str, ...] = (),
    failing_tests: Tuple[str, ...] = (),
    next_action: str = "",
    prohibited_actions: Tuple[str, ...] = (),
    authority_delta: int = 0,
    side_effects: int = 0,
) -> ContextCapsule:
    """Factory for creating a context capsule."""
    return ContextCapsule(
        mission_id=mission_id,
        mission_objective=mission_objective,
        architecture_rules=architecture_rules,
        current_baseline=current_baseline,
        owned_paths=owned_paths,
        current_phase=current_phase,
        completed_packets=completed_packets,
        active_packet=active_packet,
        last_checkpoint_id=last_checkpoint_id,
        relevant_apis=relevant_apis,
        discoveries=discoveries,
        failing_tests=failing_tests,
        next_action=next_action,
        prohibited_actions=prohibited_actions,
        authority_delta=authority_delta,
        side_effects=side_effects,
    )