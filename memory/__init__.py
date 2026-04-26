"""
SintraPrime-Unified Memory Engine
Multi-layer persistent memory system inspired by Hermes Agent, Claude Memory, GPT-5.5, and Pi AI.
"""

from .memory_engine import MemoryEngine
from .semantic_memory import SemanticMemory
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .user_profile import UserProfileManager
from .memory_types import (
    MemoryEntry,
    MemoryType,
    UserProfile,
    MemorySearchResult,
    SkillRecord,
)

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
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"
