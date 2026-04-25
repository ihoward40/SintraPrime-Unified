"""
SintraPrime UniVerse v2.0
Revolutionary multi-agent ecosystem

One for all, and all for one.
"""

__version__ = "2.0.0-alpha"
__author__ = "Isiah Howard"
__license__ = "MIT"

# Core imports with graceful fallback
try:
    from .core_engine import UniVerseOrchestrator
except (ImportError, AttributeError):
    UniVerseOrchestrator = None

try:
    from .agent_types import (
        AnalystAgent,
        ExecutorAgent,
        LearnerAgent,
        CoordinatorAgent,
        VisionAgent,
        GuardAgent,
    )
except (ImportError, AttributeError):
    AnalystAgent = ExecutorAgent = LearnerAgent = CoordinatorAgent = VisionAgent = GuardAgent = None

try:
    from .memory_system import HiveMindMemory
except (ImportError, AttributeError):
    HiveMindMemory = None

try:
    from .skill_system import SkillGenerator, SkillLibrary
except (ImportError, AttributeError):
    SkillGenerator = SkillLibrary = None

try:
    from .swarm_patterns import (
        ResearchSwarm,
        DevelopmentSwarm,
        OperationsSwarm,
        ContentSwarm,
        SalesSwarm,
    )
except (ImportError, AttributeError):
    ResearchSwarm = DevelopmentSwarm = OperationsSwarm = ContentSwarm = SalesSwarm = None

__all__ = [
    "UniVerseOrchestrator",
    "AnalystAgent",
    "ExecutorAgent",
    "LearnerAgent",
    "CoordinatorAgent",
    "VisionAgent",
    "GuardAgent",
    "HiveMindMemory",
    "SkillGenerator",
    "SkillLibrary",
    "ResearchSwarm",
    "DevelopmentSwarm",
    "OperationsSwarm",
    "ContentSwarm",
    "SalesSwarm",
]
