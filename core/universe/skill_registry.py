"""
Skill Registry System
Manages versioned skills, dependencies, usage statistics, and validation
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import asyncio
from abc import ABC, abstractmethod


class SkillStatus(Enum):
    """Status of a registered skill"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class SkillVersion:
    """A specific version of a skill"""
    skill_id: str
    version: int
    agent_id: str
    code: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    return_type: str = "any"
    created_at: datetime = field(default_factory=datetime.now)
    status: SkillStatus = SkillStatus.DRAFT
    success_rate: float = 0.0
    usage_count: int = 0
    failure_count: int = 0
    avg_execution_time_ms: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    checksum: str = ""

    def __post_init__(self):
        """Calculate checksum"""
        self.checksum = hashlib.sha256(self.code.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "failure_count": self.failure_count,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "checksum": self.checksum
        }


@dataclass
class SkillMetadata:
    """Metadata about a skill"""
    name: str
    description: str
    author: str
    category: str
    version: int
    dependencies: Dict[str, str] = field(default_factory=dict)  # skill_name: min_version
    documentation: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    performance_profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillDependency:
    """Skill dependency relationship"""
    skill_id: str
    depends_on: str
    min_version: int = 1
    required: bool = True


class SkillValidator(ABC):
    """Abstract validator for skills"""

    @abstractmethod
    async def validate(self, skill: SkillVersion) -> bool:
        """Validate a skill"""
        pass


class PythonSkillValidator(SkillValidator):
    """Validates Python skill code"""

    async def validate(self, skill: SkillVersion) -> bool:
        """Validate Python skill code"""
        try:
            # Check for dangerous imports
            dangerous = ['os.system', 'subprocess', '__import__', 'eval', 'exec']
            for item in dangerous:
                if item in skill.code:
                    return False
            
            # Try to compile the code
            compile(skill.code, '<skill>', 'exec')
            return True
        except SyntaxError:
            return False
        except Exception:
            return False


class SkillRegistry:
    """
    Central registry for managing skills
    - Versioned skill storage
    - Dependency tracking
    - Usage statistics
    - Validation
    - Auto-cleanup
    """

    def __init__(self):
        self.skills: Dict[str, Dict[int, SkillVersion]] = {}  # skill_name -> {version: SkillVersion}
        self.metadata: Dict[str, SkillMetadata] = {}
        self.dependencies: Dict[str, List[SkillDependency]] = {}
        self.usage_history: Dict[str, List[Dict[str, Any]]] = {}
        self.validators: Dict[str, SkillValidator] = {
            "python": PythonSkillValidator()
        }
        self.skill_locks: Dict[str, asyncio.Lock] = {}
        self.cleanup_threshold = 30  # days
        self.version_retention = 10  # keep last 10 versions

    def _get_skill_lock(self, skill_id: str) -> asyncio.Lock:
        """Get or create lock for skill"""
        if skill_id not in self.skill_locks:
            self.skill_locks[skill_id] = asyncio.Lock()
        return self.skill_locks[skill_id]

    async def register_skill(
        self,
        name: str,
        code: str,
        agent_id: str,
        description: str = "",
        category: str = "general",
        parameters: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Register a new skill"""
        async with self._get_skill_lock(name):
            # Determine version number
            version = 1
            if name in self.skills:
                version = max(self.skills[name].keys()) + 1
            
            skill_id = f"{name}:v{version}"
            
            # Create skill version
            skill = SkillVersion(
                skill_id=skill_id,
                version=version,
                agent_id=agent_id,
                code=code,
                parameters=parameters or {},
                dependencies=dependencies or [],
                tags=tags or []
            )
            
            # Validate skill
            if not await self.validate_skill(skill, "python"):
                skill.status = SkillStatus.FAILED
                return skill_id
            
            # Store skill
            if name not in self.skills:
                self.skills[name] = {}
            
            self.skills[name][version] = skill
            skill.status = SkillStatus.ACTIVE
            
            # Store metadata
            self.metadata[skill_id] = SkillMetadata(
                name=name,
                description=description,
                author=agent_id,
                category=category,
                version=version,
                dependencies={d: "1" for d in (dependencies or [])}
            )
            
            # Register dependencies
            for dep in (dependencies or []):
                if skill_id not in self.dependencies:
                    self.dependencies[skill_id] = []
                self.dependencies[skill_id].append(
                    SkillDependency(skill_id=skill_id, depends_on=dep)
                )
            
            # Initialize usage history
            self.usage_history[skill_id] = []
            
            return skill_id

    async def validate_skill(
        self,
        skill: SkillVersion,
        validator_type: str = "python"
    ) -> bool:
        """Validate a skill before activation"""
        validator = self.validators.get(validator_type)
        if not validator:
            return False
        
        return await validator.validate(skill)

    async def get_skill(
        self,
        name: str,
        version: Optional[int] = None
    ) -> Optional[SkillVersion]:
        """Get a skill by name and optional version"""
        if name not in self.skills:
            return None
        
        versions = self.skills[name]
        if not versions:
            return None
        
        if version is None:
            # Return latest active version
            for v in sorted(versions.keys(), reverse=True):
                if versions[v].status == SkillStatus.ACTIVE:
                    return versions[v]
            return None
        
        return versions.get(version)

    async def get_all_versions(self, name: str) -> List[SkillVersion]:
        """Get all versions of a skill"""
        if name not in self.skills:
            return []
        
        return list(self.skills[name].values())

    async def deprecate_skill(self, skill_id: str) -> bool:
        """Deprecate a skill"""
        for name, versions in self.skills.items():
            for version, skill in versions.items():
                if skill.skill_id == skill_id:
                    skill.status = SkillStatus.DEPRECATED
                    return True
        return False

    async def record_usage(
        self,
        skill_id: str,
        success: bool,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None
    ) -> bool:
        """Record skill usage"""
        for name, versions in self.skills.items():
            for version, skill in versions.items():
                if skill.skill_id == skill_id:
                    skill.usage_count += 1
                    
                    if success:
                        # Update success rate
                        total = skill.usage_count + skill.failure_count
                        skill.success_rate = skill.usage_count / total if total > 0 else 0
                    else:
                        skill.failure_count += 1
                    
                    # Update average execution time
                    if execution_time_ms > 0:
                        prev_avg = skill.avg_execution_time_ms
                        total_samples = skill.usage_count + skill.failure_count
                        skill.avg_execution_time_ms = (
                            (prev_avg * (total_samples - 1) + execution_time_ms) / total_samples
                        )
                    
                    # Record in history
                    if skill_id not in self.usage_history:
                        self.usage_history[skill_id] = []
                    
                    self.usage_history[skill_id].append({
                        "timestamp": datetime.now(),
                        "success": success,
                        "execution_time_ms": execution_time_ms,
                        "error": error
                    })
                    
                    return True
        
        return False

    async def get_usage_stats(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a skill"""
        for name, versions in self.skills.items():
            for version, skill in versions.items():
                if skill.skill_id == skill_id:
                    return {
                        "skill_id": skill_id,
                        "usage_count": skill.usage_count,
                        "failure_count": skill.failure_count,
                        "success_rate": skill.success_rate,
                        "avg_execution_time_ms": skill.avg_execution_time_ms,
                        "total_runs": skill.usage_count + skill.failure_count
                    }
        return None

    async def get_dependencies(self, skill_id: str) -> List[SkillDependency]:
        """Get dependencies for a skill"""
        return self.dependencies.get(skill_id, [])

    async def check_dependency_chain(self, skill_id: str, visited: Optional[Set[str]] = None) -> bool:
        """Check if dependency chain is valid (no circular dependencies)"""
        if visited is None:
            visited = set()
        
        if skill_id in visited:
            return False  # Circular dependency
        
        visited.add(skill_id)
        
        deps = await self.get_dependencies(skill_id)
        for dep in deps:
            if not await self.check_dependency_chain(dep.depends_on, visited):
                return False
        
        visited.remove(skill_id)
        return True

    async def cleanup_unused_skills(self, days_threshold: int = 30) -> int:
        """Auto-cleanup unused skills"""
        removed = 0
        now = datetime.now()
        
        skills_to_remove = []
        for name, versions in list(self.skills.items()):
            for version, skill in list(versions.items()):
                # Check if skill is old and unused
                age_days = (now - skill.created_at).days
                if age_days > days_threshold and skill.usage_count == 0:
                    skills_to_remove.append((name, version, skill.skill_id))
        
        for name, version, skill_id in skills_to_remove:
            if len(self.skills[name]) > self.version_retention:
                del self.skills[name][version]
                if skill_id in self.usage_history:
                    del self.usage_history[skill_id]
                if skill_id in self.dependencies:
                    del self.dependencies[skill_id]
                removed += 1
        
        return removed

    async def export_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Export a skill as a JSON blob"""
        for name, versions in self.skills.items():
            for version, skill in versions.items():
                if skill.skill_id == skill_id:
                    return {
                        "skill": skill.to_dict(),
                        "metadata": self.metadata.get(skill_id),
                        "code": skill.code,
                        "dependencies": [d.depends_on for d in self.dependencies.get(skill_id, [])]
                    }
        return None

    async def import_skill(self, skill_data: Dict[str, Any], agent_id: str) -> Optional[str]:
        """Import a skill from exported data"""
        try:
            metadata = skill_data.get("metadata", {})
            code = skill_data.get("code", "")
            
            return await self.register_skill(
                name=metadata.get("name"),
                code=code,
                agent_id=agent_id,
                description=metadata.get("description", ""),
                category=metadata.get("category", "general"),
                dependencies=skill_data.get("dependencies", [])
            )
        except Exception as e:
            print(f"Import error: {e}")
            return None

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry"""
        total_skills = 0
        total_versions = 0
        total_usage = 0
        active_skills = 0
        
        for name, versions in self.skills.items():
            total_skills += 1
            total_versions += len(versions)
            
            for version, skill in versions.items():
                total_usage += skill.usage_count
                if skill.status == SkillStatus.ACTIVE:
                    active_skills += 1
        
        return {
            "total_skills": total_skills,
            "total_versions": total_versions,
            "active_skills": active_skills,
            "total_usage_count": total_usage,
            "registered_validators": len(self.validators),
            "registry_timestamp": datetime.now().isoformat()
        }
