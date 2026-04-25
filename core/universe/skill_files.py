"""
SKILL.md System - Real-time skill compilation, hot-reload, and versioning
Inspired by space-agent architecture for dynamic skill loading
"""

import os
import json
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3


class SkillStatus(Enum):
    """Skill compilation status"""
    PENDING = "pending"
    COMPILING = "compiling"
    COMPILED = "compiled"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class SkillDependency:
    """Represents a skill dependency"""
    name: str
    version: str
    required: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass
class SkillMetadata:
    """Metadata extracted from SKILL.md"""
    name: str
    version: str
    description: str
    category: str
    dependencies: List[SkillDependency]
    author: str = "Unknown"
    tags: List[str] = None
    compatibility: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.compatibility is None:
            self.compatibility = {}

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "author": self.author,
            "tags": self.tags,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "compatibility": self.compatibility
        }


class SkillParser:
    """Parses SKILL.md markdown files"""

    SKILL_HEADER_PATTERN = re.compile(r"^#\s+(\w+)\s*\n", re.MULTILINE)
    METADATA_SECTION_PATTERN = re.compile(r"##\s+Metadata\s*\n(.*?)(?=\n##|\Z)", re.DOTALL)
    INSTRUCTIONS_SECTION_PATTERN = re.compile(r"##\s+Instructions\s*\n(.*?)(?=\n##|\Z)", re.DOTALL)
    YAML_PATTERN = re.compile(r"(\w+):\s*(.+)")

    @staticmethod
    def parse_skill_file(file_path: str) -> Tuple[SkillMetadata, str, Optional[str]]:
        """
        Parse a SKILL.md file and extract metadata and content
        
        Returns:
            Tuple of (metadata, instructions, error_message)
        """
        if not os.path.exists(file_path):
            return None, None, f"File not found: {file_path}"

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Extract title
            title_match = SkillParser.SKILL_HEADER_PATTERN.search(content)
            if not title_match:
                return None, None, "Missing main header (# Title)"

            title = title_match.group(1)

            # Extract metadata section
            metadata_match = SkillParser.METADATA_SECTION_PATTERN.search(content)
            if not metadata_match:
                return None, None, "Missing ## Metadata section"

            metadata_text = metadata_match.group(1)
            metadata = SkillParser._parse_metadata(title, metadata_text)

            # Extract instructions
            instructions_match = SkillParser.INSTRUCTIONS_SECTION_PATTERN.search(content)
            instructions = instructions_match.group(1).strip() if instructions_match else ""

            if not instructions:
                return None, None, "Missing ## Instructions section"

            return metadata, instructions, None

        except Exception as e:
            return None, None, f"Parse error: {str(e)}"

    @staticmethod
    def _parse_metadata(title: str, metadata_text: str) -> SkillMetadata:
        """Parse YAML-like metadata section"""
        lines = metadata_text.strip().split('\n')
        metadata_dict = {}

        for line in lines:
            match = SkillParser.YAML_PATTERN.match(line.strip())
            if match:
                key, value = match.groups()
                value = value.strip()
                # Parse JSON for complex types
                if value.startswith('[') or value.startswith('{'):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                metadata_dict[key] = value

        # Build SkillMetadata
        dependencies = []
        if "dependencies" in metadata_dict:
            deps = metadata_dict.get("dependencies", [])
            if isinstance(deps, str):
                deps = json.loads(deps)
            for dep in (deps or []):
                if isinstance(dep, dict):
                    dependencies.append(SkillDependency(
                        name=dep.get("name", ""),
                        version=dep.get("version", "*"),
                        required=dep.get("required", True)
                    ))
                elif isinstance(dep, str):
                    # Simple format: "name@version"
                    parts = dep.split("@")
                    dependencies.append(SkillDependency(
                        name=parts[0],
                        version=parts[1] if len(parts) > 1 else "*"
                    ))

        return SkillMetadata(
            name=metadata_dict.get("name", title),
            version=metadata_dict.get("version", "1.0.0"),
            description=metadata_dict.get("description", ""),
            category=metadata_dict.get("category", "general"),
            author=metadata_dict.get("author", "Unknown"),
            tags=metadata_dict.get("tags", []),
            dependencies=dependencies,
            compatibility=metadata_dict.get("compatibility", {})
        )


class SkillCompiler:
    """Compiles and validates SKILL.md files"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or ":memory:"
        self.compiled_skills = {}
        self.compilation_errors = {}
        self.compilation_cache = {}

    def compile_skill(self, file_path: str, force: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Compile a skill file with validation
        
        Returns:
            Tuple of (success, error_message)
        """
        cache_key = hashlib.md5(file_path.encode()).hexdigest()

        if cache_key in self.compilation_cache and not force:
            return True, None

        # Parse the skill file
        metadata, instructions, parse_error = SkillParser.parse_skill_file(file_path)

        if parse_error:
            self.compilation_errors[file_path] = parse_error
            return False, parse_error

        # Validate metadata
        validation_error = self._validate_metadata(metadata)
        if validation_error:
            self.compilation_errors[file_path] = validation_error
            return False, validation_error

        # Validate dependencies
        dep_error = self._validate_dependencies(metadata.dependencies)
        if dep_error:
            self.compilation_errors[file_path] = dep_error
            return False, dep_error

        # Validate instructions
        if not instructions or len(instructions) < 50:
            error = "Instructions section is too short (minimum 50 characters)"
            self.compilation_errors[file_path] = error
            return False, error

        # Success - cache the compiled skill
        self.compiled_skills[file_path] = {
            "metadata": metadata,
            "instructions": instructions,
            "file_path": file_path,
            "compiled_at": datetime.now().isoformat()
        }

        self.compilation_cache[cache_key] = True

        if file_path in self.compilation_errors:
            del self.compilation_errors[file_path]

        return True, None

    @staticmethod
    def _validate_metadata(metadata: SkillMetadata) -> Optional[str]:
        """Validate skill metadata"""
        if not metadata.name or len(metadata.name) < 1:
            return "Skill name cannot be empty"

        if not SkillCompiler._is_valid_version(metadata.version):
            return f"Invalid version format: {metadata.version}"

        if not metadata.description or len(metadata.description) < 10:
            return "Description must be at least 10 characters"

        if not metadata.category:
            return "Category must be specified"

        return None

    @staticmethod
    def _validate_dependencies(dependencies: List[SkillDependency]) -> Optional[str]:
        """Validate dependency list"""
        seen = set()
        for dep in dependencies:
            if not dep.name:
                return "Dependency name cannot be empty"
            if dep.name in seen:
                return f"Duplicate dependency: {dep.name}"
            seen.add(dep.name)
        return None

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Check if version follows semver-like format"""
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?(\+[a-zA-Z0-9]+)?$'
        return bool(re.match(pattern, version))

    def get_compiled_skill(self, file_path: str) -> Optional[Dict]:
        """Retrieve compiled skill"""
        return self.compiled_skills.get(file_path)

    def get_compilation_status(self, file_path: str) -> Dict[str, Any]:
        """Get detailed compilation status"""
        if file_path in self.compiled_skills:
            return {"status": "compiled", "error": None}
        elif file_path in self.compilation_errors:
            return {"status": "failed", "error": self.compilation_errors[file_path]}
        else:
            return {"status": "pending", "error": None}


class SkillRegistry:
    """Manages skill registration and hot-reload"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or ":memory:"
        self.compiler = SkillCompiler(db_path)
        self.active_skills = {}
        self.skill_versions = {}  # skill_name -> [versions]
        self._init_db()

    def _init_db(self):
        """Initialize database if using a real DB"""
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def register_skill(self, file_path: str, auto_compile: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Register a skill file for tracking
        
        Returns:
            Tuple of (success, error_message)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        skill_id = hashlib.md5(file_path.encode()).hexdigest()

        if auto_compile:
            success, error = self.compiler.compile_skill(file_path)
            if not success:
                return False, error

        compiled_skill = self.compiler.get_compiled_skill(file_path)
        if compiled_skill:
            metadata = compiled_skill["metadata"]
            skill_key = f"{metadata.name}:{metadata.version}"

            self.active_skills[skill_key] = {
                "skill_id": skill_id,
                "file_path": file_path,
                "metadata": metadata,
                "instructions": compiled_skill["instructions"],
                "registered_at": datetime.now().isoformat(),
                "hot_reload_enabled": True
            }

            if metadata.name not in self.skill_versions:
                self.skill_versions[metadata.name] = []

            if metadata.version not in self.skill_versions[metadata.name]:
                self.skill_versions[metadata.name].append(metadata.version)

            return True, None

        return False, "Failed to compile skill"

    def get_skill(self, name: str, version: str = "latest") -> Optional[Dict]:
        """Retrieve a registered skill"""
        if version == "latest":
            # Get the highest version
            if name in self.skill_versions:
                versions = sorted(self.skill_versions[name])
                if versions:
                    version = versions[-1]
                else:
                    return None
            else:
                return None

        skill_key = f"{name}:{version}"
        return self.active_skills.get(skill_key)

    def hot_reload_skill(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Hot-reload a skill without requiring restart
        
        Returns:
            Tuple of (success, error_message)
        """
        success, error = self.compiler.compile_skill(file_path, force=True)

        if not success:
            return False, error

        # Re-register the skill
        return self.register_skill(file_path, auto_compile=False)

    def list_active_skills(self) -> List[Dict]:
        """List all active skills"""
        return [
            {
                "name": skill["metadata"].name,
                "version": skill["metadata"].version,
                "category": skill["metadata"].category,
                "registered_at": skill["registered_at"]
            }
            for skill in self.active_skills.values()
        ]

    def check_skill_health(self, name: str, version: str = "latest") -> Dict[str, Any]:
        """Check health of a skill"""
        skill = self.get_skill(name, version)

        if not skill:
            return {"status": "not_found", "name": name, "version": version}

        return {
            "status": "healthy",
            "name": skill["metadata"].name,
            "version": skill["metadata"].version,
            "category": skill["metadata"].category,
            "dependencies": [d.to_dict() for d in skill["metadata"].dependencies],
            "registered_at": skill["registered_at"],
            "hot_reload_enabled": skill["hot_reload_enabled"]
        }


class SkillLoader:
    """Loads and executes skills dynamically"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.execution_cache = {}

    def load_skill(self, name: str, version: str = "latest") -> Optional[Dict]:
        """Load a skill into memory"""
        skill = self.registry.get_skill(name, version)
        if not skill:
            return None

        cache_key = f"{name}:{version}"
        self.execution_cache[cache_key] = {
            "skill": skill,
            "loaded_at": datetime.now().isoformat(),
            "execution_count": 0
        }

        return skill

    def execute_skill_instructions(self, name: str, context: Dict = None) -> Dict[str, Any]:
        """Execute skill instructions with context"""
        cache_key = f"{name}:latest"
        skill = self.registry.get_skill(name)

        if not skill:
            return {"success": False, "error": f"Skill not found: {name}"}

        try:
            if cache_key not in self.execution_cache:
                self.load_skill(name)

            self.execution_cache[cache_key]["execution_count"] += 1

            # In a real implementation, this would execute the instructions
            # For now, return metadata
            return {
                "success": True,
                "skill_name": name,
                "version": skill["metadata"].version,
                "category": skill["metadata"].category,
                "instructions": skill["instructions"][:200] + "...",  # First 200 chars
                "context": context
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_execution_stats(self, name: str) -> Dict:
        """Get execution statistics for a skill"""
        cache_key = f"{name}:latest"
        if cache_key in self.execution_cache:
            return {
                "skill": name,
                "execution_count": self.execution_cache[cache_key]["execution_count"],
                "loaded_at": self.execution_cache[cache_key]["loaded_at"]
            }
        return {"skill": name, "execution_count": 0, "loaded_at": None}
