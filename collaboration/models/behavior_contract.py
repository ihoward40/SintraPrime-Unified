"""AgentBehaviorContract — hard-scoped, hashed, versioned (§XIV)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class AgentBehaviorContract:
    agent_id: str
    mission: str = ""
    allowed_capabilities: list[str] = field(default_factory=list)
    forbidden_capabilities: list[str] = field(default_factory=list)
    accepted_event_types: list[str] = field(default_factory=list)
    output_schema: str = ""
    max_response_tokens: int = 12000
    max_execution_time: float = 300.0
    max_parallelism: int = 3
    authority_class: str = "A0"
    behavior_contract_version: str = "1"
    behavior_contract_hash: str = ""

    def compute_hash(self) -> str:
        canonical = json.dumps(
            {
                "agent_id": self.agent_id,
                "mission": self.mission,
                "allowed": sorted(self.allowed_capabilities),
                "forbidden": sorted(self.forbidden_capabilities),
                "events": sorted(self.accepted_event_types),
                "authority_class": self.authority_class,
                "version": self.behavior_contract_version,
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __post_init__(self):
        if not self.behavior_contract_hash:
            self.behavior_contract_hash = self.compute_hash()
