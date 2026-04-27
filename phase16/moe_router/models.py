"""Phase 16A — MoE Legal Specialist Router: data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExpertType(str, Enum):
    TRUST_LAW = "trust_law"
    CORPORATE = "corporate"
    IP = "intellectual_property"
    TAX = "tax"
    FAMILY_LAW = "family_law"
    CRIMINAL = "criminal"
    REAL_ESTATE = "real_estate"
    IMMIGRATION = "immigration"
    EMPLOYMENT = "employment"
    BANKRUPTCY = "bankruptcy"


@dataclass
class RoutingRequest:
    """Input request to route to one or more legal experts."""
    request_id: str
    text: str
    practice_area_hint: Optional[str] = None
    urgency: str = "normal"  # low, normal, high, critical
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfidenceScore:
    """Confidence score for a specific expert on a request."""
    expert_type: ExpertType
    score: float  # 0.0 – 1.0
    reasoning: str = ""
    calibrated: bool = False


@dataclass
class RoutingResult:
    """Result of routing a request through the MoE router."""
    request_id: str
    primary_expert: ExpertType
    secondary_experts: List[ExpertType] = field(default_factory=list)
    confidence_scores: List[ConfidenceScore] = field(default_factory=list)
    analysis: Dict[str, Any] = field(default_factory=dict)
    routing_weights: Dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class ExpertCapacity:
    """Current load and capacity for an expert."""
    expert_type: ExpertType
    current_load: int = 0
    max_capacity: int = 10
    queue_depth: int = 0

    @property
    def utilization(self) -> float:
        return self.current_load / self.max_capacity if self.max_capacity > 0 else 1.0

    @property
    def available(self) -> bool:
        return self.current_load < self.max_capacity
