"""SintraPrime Superintelligence Package."""

from .memory_system import (
    EpisodicMemory, SemanticMemory, ProceduralMemory,
    MemoryConsolidator, UnifiedMemory, Episode, Fact, Procedure
)
from .distributed_reasoning import (
    ReasoningEngine, ReasoningPath, ReasoningResult,
    DeductiveReasoner, InductiveReasoner, AbductiveReasoner,
    AnalogicalReasoner, ReasoningCache, DebateRound
)
from .self_audit import (
    SelfAuditEngine, AuditRule, AuditResult, AuditIssue,
    AutoFixer, AuditLogger
)
from .learning_engine import (
    LearningEngine, Lesson, PatternRecognizer, Pattern, PerformanceTracker
)
from .agent_parliament import (
    AgentParliament, ParliamentMember, ParliamentaryDecision,
    DebateRound as ParliamentDebateRound
)
from .superintelligence_core import SuperIntelligenceCore, ProcessingResult

__all__ = [
    "EpisodicMemory", "SemanticMemory", "ProceduralMemory",
    "MemoryConsolidator", "UnifiedMemory",
    "ReasoningEngine", "ReasoningPath", "ReasoningResult",
    "DeductiveReasoner", "InductiveReasoner", "AbductiveReasoner",
    "AnalogicalReasoner", "ReasoningCache",
    "SelfAuditEngine", "AuditRule", "AuditResult", "AutoFixer", "AuditLogger",
    "LearningEngine", "Lesson", "PatternRecognizer", "PerformanceTracker",
    "AgentParliament", "ParliamentMember", "ParliamentaryDecision",
    "SuperIntelligenceCore", "ProcessingResult",
]
