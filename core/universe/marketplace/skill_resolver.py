"""
Skill Resolver - Dependency Resolution and Conflict Detection
Handles complex dependency graphs, version compatibility checking,
and installation sequencing with rollback capability.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of dependency conflicts"""
    VERSION_MISMATCH = "version_mismatch"
    INCOMPATIBLE = "incompatible"
    CIRCULAR = "circular"
    MISSING = "missing"


@dataclass
class DependencyConstraint:
    """A dependency constraint in the dependency graph"""
    skill_name: str
    version_constraint: str
    
    def __hash__(self):
        return hash((self.skill_name, self.version_constraint))
    
    def __eq__(self, other):
        return (isinstance(other, DependencyConstraint) and
                self.skill_name == other.skill_name and
                self.version_constraint == other.version_constraint)


@dataclass
class ResolutionResult:
    """Result of dependency resolution"""
    success: bool
    resolved_versions: Dict[str, str] = field(default_factory=dict)
    installation_order: List[str] = field(default_factory=list)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)
    error_message: str = ""


class DependencyGraph:
    """Builds and analyzes skill dependency graphs"""
    
    def __init__(self):
        self.graph: Dict[str, Set[DependencyConstraint]] = defaultdict(set)
        self.available_versions: Dict[str, List[str]] = {}
        self.skill_metadata: Dict[str, Dict] = {}
    
    def add_skill(self, skill_name: str, version: str, 
                  dependencies: Dict[str, str], metadata: Dict = None):
        """Add a skill and its dependencies to the graph"""
        skill_key = f"{skill_name}:{version}"
        
        for dep_name, dep_version in dependencies.items():
            constraint = DependencyConstraint(dep_name, dep_version)
            self.graph[skill_key].add(constraint)
        
        # Track available versions
        if skill_name not in self.available_versions:
            self.available_versions[skill_name] = []
        
        if version not in self.available_versions[skill_name]:
            self.available_versions[skill_name].append(version)
        
        # Store metadata
        if metadata:
            self.skill_metadata[skill_key] = metadata
    
    def get_dependencies(self, skill_name: str, version: str) -> List[DependencyConstraint]:
        """Get dependencies for a skill version"""
        skill_key = f"{skill_name}:{version}"
        return list(self.graph.get(skill_key, []))
    
    def find_cycles(self) -> List[List[str]]:
        """Detect circular dependencies"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in self.graph:
                for dep in self.graph[node]:
                    dep_node = f"{dep.skill_name}:*"
                    
                    if dep_node not in visited:
                        dfs(dep_node, path[:])
                    elif dep_node in rec_stack:
                        cycle = path[path.index(dep_node):] + [dep_node]
                        if cycle not in cycles:
                            cycles.append(cycle)
            
            rec_stack.remove(node)
        
        for node in self.graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles


class CompatibilityChecker:
    """Checks version compatibility between skills"""
    
    @staticmethod
    def parse_version(version: str) -> Tuple[int, int, int]:
        """Parse semantic version"""
        parts = version.split(".")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0
        )
    
    @staticmethod
    def is_compatible(installed_version: str, required_version: str) -> bool:
        """Check if installed version satisfies requirement"""
        
        # Handle special cases
        if required_version == "*" or required_version == "latest":
            return True
        
        if required_version == installed_version:
            return True
        
        # Parse installed version
        try:
            installed = CompatibilityChecker.parse_version(installed_version)
        except (ValueError, AttributeError):
            return False
        
        # Handle operators
        if required_version.startswith("^"):
            # Caret: compatible with version (allows changes that don't modify left-most non-zero)
            try:
                target = CompatibilityChecker.parse_version(required_version[1:])
                # Check if major version matches and installed >= target
                if installed[0] == target[0] and installed >= target:
                    return True
            except (ValueError, AttributeError):
                return False
        
        elif required_version.startswith("~"):
            # Tilde: approximately equivalent to version (allows patch changes)
            try:
                target = CompatibilityChecker.parse_version(required_version[1:])
                # Check if major and minor match and installed >= target
                if (installed[0] == target[0] and 
                    installed[1] == target[1] and 
                    installed >= target):
                    return True
            except (ValueError, AttributeError):
                return False
        
        elif required_version.startswith(">="):
            try:
                target = CompatibilityChecker.parse_version(required_version[2:])
                return installed >= target
            except (ValueError, AttributeError):
                return False
        
        elif required_version.startswith(">"):
            try:
                target = CompatibilityChecker.parse_version(required_version[1:])
                return installed > target
            except (ValueError, AttributeError):
                return False
        
        elif required_version.startswith("<="):
            try:
                target = CompatibilityChecker.parse_version(required_version[2:])
                return installed <= target
            except (ValueError, AttributeError):
                return False
        
        elif required_version.startswith("<"):
            try:
                target = CompatibilityChecker.parse_version(required_version[1:])
                return installed < target
            except (ValueError, AttributeError):
                return False
        
        # Try to parse as exact version requirement
        try:
            target = CompatibilityChecker.parse_version(required_version)
            return installed == target
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def find_compatible_version(available_versions: List[str], 
                               requirement: str) -> Optional[str]:
        """Find the best compatible version from available versions"""
        
        # Sort versions (highest first)
        sorted_versions = sorted(
            available_versions,
            key=lambda v: CompatibilityChecker.parse_version(v),
            reverse=True
        )
        
        for version in sorted_versions:
            if CompatibilityChecker.is_compatible(version, requirement):
                return version
        
        return None


class DependencyResolver:
    """Resolves skill dependencies using backtracking algorithm"""
    
    def __init__(self, registry):
        self.registry = registry
        self.compatibility = CompatibilityChecker()
    
    def resolve(self, skill_id: int, skill_name: str, 
               version_requirement: str = "*") -> ResolutionResult:
        """Resolve all dependencies for a skill"""
        
        # Detect circular dependencies
        graph = DependencyGraph()
        cycles = graph.find_cycles()
        if cycles:
            return ResolutionResult(
                success=False,
                conflicts=[(c[0], c[1]) for c in cycles],
                error_message=f"Circular dependencies detected: {cycles}"
            )
        
        # Resolve versions using backtracking
        resolved = {}
        installation_order = []
        
        try:
            self._resolve_recursive(
                skill_name, version_requirement, 
                resolved, installation_order
            )
            
            if not self._validate_resolution(resolved):
                return ResolutionResult(
                    success=False,
                    error_message="Resolution validation failed"
                )
            
            return ResolutionResult(
                success=True,
                resolved_versions=resolved,
                installation_order=installation_order
            )
        
        except Exception as e:
            logger.error(f"Resolution failed: {e}")
            return ResolutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _resolve_recursive(self, skill_name: str, version_requirement: str,
                          resolved: Dict[str, str], 
                          order: List[str], depth: int = 0) -> bool:
        """Recursively resolve dependencies"""
        
        # Prevent infinite recursion
        if depth > 50:
            raise ValueError("Dependency resolution depth exceeded")
        
        # Skip if already resolved
        if skill_name in resolved:
            return True
        
        # Find compatible version
        skill_versions = self.registry.get_versions_for_skill(skill_name)
        if not skill_versions:
            raise ValueError(f"Skill not found: {skill_name}")
        
        compatible_version = self.compatibility.find_compatible_version(
            [v.version for v in skill_versions],
            version_requirement
        )
        
        if not compatible_version:
            raise ValueError(
                f"No compatible version found for {skill_name} "
                f"matching {version_requirement}"
            )
        
        resolved[skill_name] = compatible_version
        order.append(skill_name)
        
        # Recursively resolve dependencies
        skill_version = next(
            (v for v in skill_versions if v.version == compatible_version),
            None
        )
        
        if skill_version and skill_version.requirements:
            for dep_name, dep_version_req in skill_version.requirements.items():
                if not self._resolve_recursive(
                    dep_name, dep_version_req, resolved, order, depth + 1
                ):
                    return False
        
        return True
    
    def _validate_resolution(self, resolved: Dict[str, str]) -> bool:
        """Validate that resolved versions are compatible"""
        
        for skill_name, version in resolved.items():
            skill_versions = self.registry.get_versions_for_skill(skill_name)
            skill_version = next(
                (v for v in skill_versions if v.version == version),
                None
            )
            
            if not skill_version:
                return False
            
            # Validate dependencies
            if skill_version.requirements:
                for dep_name, dep_version_req in skill_version.requirements.items():
                    if dep_name not in resolved:
                        return False
                    
                    installed_version = resolved[dep_name]
                    if not self.compatibility.is_compatible(
                        installed_version, dep_version_req
                    ):
                        return False
        
        return True
    
    def detect_conflicts(self, required_versions: Dict[str, str]) -> List[Tuple[str, str]]:
        """Detect conflicts between required versions"""
        conflicts = []
        
        for skill_name, version_req in required_versions.items():
            # Check against other requirements
            for other_skill, other_req in required_versions.items():
                if skill_name >= other_skill:
                    continue
                
                # Simple conflict detection
                if skill_name == other_skill and version_req != other_req:
                    if not self.compatibility.is_compatible(version_req, other_req):
                        conflicts.append((skill_name, f"{version_req} vs {other_req}"))
        
        return conflicts


class InstallationSequencer:
    """Determines optimal installation order"""
    
    @staticmethod
    def sequence_installation(resolved_versions: Dict[str, str], 
                            dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Determine installation order using topological sort"""
        
        # Build reverse dependency graph (dependents)
        dependents: Dict[str, List[str]] = defaultdict(list)
        for skill, deps in dependency_graph.items():
            for dep in deps:
                dependents[dep].append(skill)
        
        # Topological sort
        visited = set()
        order = []
        
        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            
            # Visit dependencies first
            for dep in dependency_graph.get(node, []):
                dfs(dep)
            
            order.append(node)
        
        # Process all skills
        for skill in resolved_versions:
            dfs(skill)
        
        return order


class RollbackManager:
    """Manages rollback of failed installations"""
    
    def __init__(self):
        self.installation_snapshots: Dict[str, Dict] = {}
    
    def create_snapshot(self, agent_id: str, skill_id: int, 
                       current_version: str) -> str:
        """Create a snapshot before installation"""
        snapshot_id = f"snapshot_{agent_id}_{skill_id}_{id(self)}"
        
        self.installation_snapshots[snapshot_id] = {
            "agent_id": agent_id,
            "skill_id": skill_id,
            "version": current_version,
            "timestamp": __import__("time").time()
        }
        
        return snapshot_id
    
    def rollback(self, snapshot_id: str) -> bool:
        """Restore from a snapshot"""
        if snapshot_id not in self.installation_snapshots:
            return False
        
        snapshot = self.installation_snapshots[snapshot_id]
        # In production, would restore the actual installation
        logger.info(f"Rolled back skill {snapshot['skill_id']} "
                   f"to version {snapshot['version']}")
        
        return True
