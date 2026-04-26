"""
SintraPrime-Unified Skill Evolution System

A continuous self-learning and skill evolution framework inspired by:
- Hermes Agent: autonomous skill creation from task outcomes, procedural memory
- OpenClaw: modular skills ecosystem, community skills
- CrewAI: role-based skill specialization
- GPT-5.5 Spud: iterative improvement with each execution

This package provides:
- SkillLibrary: Core storage and retrieval for all skills (SQLite-backed)
- SkillEvolver: Self-learning heart – analyzes failures, auto-improves, creates new skills
- SkillRunner: Safe sandboxed execution with timeout and validation
- SkillMarketplace: Community-driven skill sharing (OpenClaw-inspired)
- AutoSkillCreator: Autonomous skill generation from examples and workflows
"""

from .skill_library import SkillLibrary
from .skill_evolver import SkillEvolver
from .skill_runner import SkillRunner
from .skill_marketplace import SkillMarketplace
from .auto_skill_creator import AutoSkillCreator

__all__ = [
    "SkillLibrary",
    "SkillEvolver",
    "SkillRunner",
    "SkillMarketplace",
    "AutoSkillCreator",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified Team"
