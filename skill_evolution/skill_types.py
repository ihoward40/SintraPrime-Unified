"""
Skill Types and Data Models for SintraPrime-Unified Skill Evolution System

Defines all core data structures used throughout the skill ecosystem.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillCategory(str, Enum):
    """Categorizes skills by domain for organization and discovery."""
    LEGAL = "legal"
    FINANCIAL = "financial"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    DATA = "data"
    AUTOMATION = "automation"
    CODING = "coding"
    ANALYSIS = "analysis"


class SkillStatus(str, Enum):
    """Lifecycle status of a skill."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    PENDING_REVIEW = "pending_review"


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """
    Represents a single executable skill in the library.

    A skill is a named, versioned, categorized piece of executable Python code
    with metadata for discovery, execution, and evolution tracking.
    """
    name: str
    description: str
    category: SkillCategory
    code: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    # Schema format: {"param_name": {"type": "str", "required": True, "default": None}}
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    success_rate: float = 1.0        # 0.0 – 1.0
    usage_count: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    is_builtin: bool = False
    status: SkillStatus = SkillStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, SkillCategory) else self.category,
            "code": self.code,
            "parameters": self.parameters,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "author": self.author,
            "tags": self.tags,
            "is_builtin": self.is_builtin,
            "status": self.status.value if isinstance(self.status, SkillStatus) else self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        data = dict(data)
        data["category"] = SkillCategory(data["category"])
        data["status"] = SkillStatus(data.get("status", "active"))
        data["created_at"] = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        data["last_updated"] = datetime.fromisoformat(data["last_updated"]) if isinstance(data["last_updated"], str) else data["last_updated"]
        if isinstance(data.get("tags"), str):
            import json
            data["tags"] = json.loads(data["tags"])
        if isinstance(data.get("parameters"), str):
            import json
            data["parameters"] = json.loads(data["parameters"])
        return cls(**data)


@dataclass
class SkillExecution:
    """
    Records a single execution of a skill for audit, learning, and improvement.
    """
    skill_id: str
    input_params: Dict[str, Any]
    output: Any
    success: bool
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    feedback_score: Optional[float] = None   # 1.0 – 5.0 user rating
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "input_params": json.dumps(self.input_params),
            "output": json.dumps(self.output) if not isinstance(self.output, str) else self.output,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "feedback_score": self.feedback_score,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SkillImprovement:
    """
    Records an evolutionary improvement made to a skill.
    """
    skill_id: str
    old_version: int
    new_version: int
    change_description: str
    performance_delta: float   # e.g. +0.15 means 15% better success rate
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ImprovementSuggestion:
    """A proposed improvement to a skill, not yet applied."""
    skill_id: str
    suggestion: str
    confidence: float           # 0.0 – 1.0
    failure_pattern: str
    proposed_code_patch: Optional[str] = None


@dataclass
class FailureAnalysis:
    """Analysis of failure patterns for a skill over a time period."""
    skill_id: str
    total_executions: int
    failed_executions: int
    failure_rate: float
    common_errors: List[str]
    failure_patterns: List[str]
    lookback_days: int
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Result of skill safety validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    safety_score: float   # 0.0 – 1.0


@dataclass
class MarketplaceSkill:
    """A skill entry in the community marketplace."""
    skill: Skill
    marketplace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    author_info: Dict[str, str] = field(default_factory=dict)
    rating: float = 0.0
    rating_count: int = 0
    download_count: int = 0
    published_at: datetime = field(default_factory=datetime.utcnow)
    is_trending: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marketplace_id": self.marketplace_id,
            "skill": self.skill.to_dict(),
            "author_info": self.author_info,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "download_count": self.download_count,
            "published_at": self.published_at.isoformat(),
            "is_trending": self.is_trending,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplaceSkill":
        data = dict(data)
        skill_data = data.pop("skill")
        skill = Skill.from_dict(skill_data)
        data["published_at"] = datetime.fromisoformat(data["published_at"]) if isinstance(data["published_at"], str) else data["published_at"]
        return cls(skill=skill, **data)


# ---------------------------------------------------------------------------
# Base class for all skills
# ---------------------------------------------------------------------------

class SkillTemplate(ABC):
    """
    Base class that all built-in skills must inherit.

    Provides a standard interface for skill execution, parameter validation,
    and self-description.
    """

    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Unique identifier for this skill."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """What this skill does."""

    @property
    @abstractmethod
    def category(self) -> SkillCategory:
        """Domain category."""

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        """Override to declare required/optional parameters."""
        return {}

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the skill with the given parameters."""

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against schema. Returns list of errors."""
        errors = []
        schema = self.parameter_schema
        for param_name, meta in schema.items():
            if meta.get("required", False) and param_name not in params:
                errors.append(f"Missing required parameter: {param_name}")
            if param_name in params:
                expected_type = meta.get("type")
                if expected_type and not isinstance(params[param_name], self._resolve_type(expected_type)):
                    errors.append(f"Parameter '{param_name}' expected {expected_type}, got {type(params[param_name]).__name__}")
        return errors

    @staticmethod
    def _resolve_type(type_str: str):
        mapping = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}
        return mapping.get(type_str, object)

    def to_skill(self) -> Skill:
        """Convert this template instance to a Skill record."""
        import inspect
        return Skill(
            id=self.skill_id,
            name=self.name,
            description=self.description,
            category=self.category,
            code=inspect.getsource(self.__class__),
            parameters=self.parameter_schema,
            is_builtin=True,
            author="system",
        )
