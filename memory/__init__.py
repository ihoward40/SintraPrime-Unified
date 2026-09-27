"""
SintraPrime-Unified Memory Engine
Multi-layer persistent memory plus governed OmniBrain context services.
"""

from .memory_engine import MemoryEngine
from .semantic_memory import SemanticMemory
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .user_profile import UserProfileManager
from .memory_types import MemoryEntry, MemoryType, UserProfile, MemorySearchResult, SkillRecord
from .context_packages import ContextItem, ContextPackage, ContextPackageBuilder, ContextScope
from .knowledge_graph import GraphEdge, KnowledgeGraphStore
from .obsidian_projection import ObsidianProjector

__all__ = [
    "MemoryEngine",
    "SemanticMemory",
    "WorkingMemory",
    "EpisodicMemory",
    "UserProfileManager",
    "UserProfile",
    "MemoryEntry",
    "MemoryType",
    "MemorySearchResult",
    "SkillRecord",
    "ContextScope",
    "ContextItem",
    "ContextPackage",
    "ContextPackageBuilder",
    "GraphEdge",
    "KnowledgeGraphStore",
    "ObsidianProjector",
]

__version__ = "1.1.0"
__author__ = "SintraPrime-Unified"
