"""
Skill Marketplace - Core Registry and Discovery Engine
A production-grade marketplace for agent skills with versioning, 
dependency resolution, and installation orchestration.
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """Skill publication status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class InstallationStatus(Enum):
    """Installation status tracking"""
    PENDING = "pending"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class SkillMetadata:
    """Skill metadata structure"""
    name: str
    version: str
    author: str
    description: str
    license: str
    repo_url: str
    requirements: Dict[str, str]
    tags: List[str]
    min_version: str = "1.0.0"
    max_version: Optional[str] = None
    

@dataclass
class SkillVersion:
    """Skill version record"""
    skill_id: int
    version: str
    checksum: str
    published_at: datetime
    requirements: Dict[str, str]
    downloads: int = 0
    rating: float = 0.0


class VersionParser:
    """Semantic versioning parser and comparator"""
    
    VERSION_PATTERN = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?(?:\+(.+))?$'
    
    @staticmethod
    def parse(version: str) -> Tuple[int, int, int, str, str]:
        """Parse semantic version string"""
        match = re.match(VersionParser.VERSION_PATTERN, version)
        if not match:
            raise ValueError(f"Invalid version format: {version}")
        
        major, minor, patch, prerelease, build = match.groups()
        return int(major), int(minor), int(patch), prerelease or "", build or ""
    
    @staticmethod
    def compare(v1: str, v2: str) -> int:
        """Compare two versions: -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        try:
            p1 = VersionParser.parse(v1)
            p2 = VersionParser.parse(v2)
            
            # Compare major, minor, patch
            if p1[:3] < p2[:3]:
                return -1
            elif p1[:3] > p2[:3]:
                return 1
            
            # Handle prerelease versions
            if p1[3] and not p2[3]:
                return -1
            elif not p1[3] and p2[3]:
                return 1
            elif p1[3] and p2[3] and p1[3] != p2[3]:
                return -1 if p1[3] < p2[3] else 1
            
            return 0
        except ValueError:
            return 0
    
    @staticmethod
    def satisfies(version: str, requirement: str) -> bool:
        """Check if version satisfies requirement (e.g., >=1.0.0, ~1.2.3, ^1.0.0)"""
        if requirement == "*" or requirement == "latest":
            return True
        
        # Exact version
        if not any(c in requirement for c in "~^><=!"):
            return VersionParser.compare(version, requirement) == 0
        
        # Range operators
        if requirement.startswith(">="):
            target = requirement[2:]
            return VersionParser.compare(version, target) >= 0
        elif requirement.startswith(">"):
            target = requirement[1:]
            return VersionParser.compare(version, target) > 0
        elif requirement.startswith("<="):
            target = requirement[2:]
            return VersionParser.compare(version, target) <= 0
        elif requirement.startswith("<"):
            target = requirement[1:]
            return VersionParser.compare(version, target) < 0
        elif requirement.startswith("~"):
            # ~1.2.3 := >=1.2.3 <1.3.0
            target = requirement[1:]
            v_parts = VersionParser.parse(version)
            t_parts = VersionParser.parse(target)
            if VersionParser.compare(version, target) < 0:
                return False
            return v_parts[0] == t_parts[0] and v_parts[1] == t_parts[1]
        elif requirement.startswith("^"):
            # ^1.2.3 := >=1.2.3 <2.0.0
            target = requirement[1:]
            v_parts = VersionParser.parse(version)
            t_parts = VersionParser.parse(target)
            if VersionParser.compare(version, target) < 0:
                return False
            return v_parts[0] == t_parts[0]
        
        return False


class SkillRegistry:
    """Central registry for all published skills"""
    
    def __init__(self, db_path: str = "marketplace.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize marketplace database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Skills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                repo_url TEXT,
                license TEXT,
                status TEXT DEFAULT 'published',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Skill versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER NOT NULL,
                version TEXT NOT NULL,
                checksum TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requirements TEXT,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                UNIQUE (skill_id, version)
            )
        """)
        
        # Index for quick lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_versions_id_version 
            ON skill_versions(skill_id, version)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_name 
            ON skills(name)
        """)
        
        conn.commit()
        conn.close()
    
    def register_skill(self, metadata: SkillMetadata) -> int:
        """Register a new skill or return existing skill ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO skills (name, author, description, repo_url, license)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metadata.name,
                metadata.author,
                metadata.description,
                metadata.repo_url,
                metadata.license
            ))
            skill_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Registered skill: {metadata.name}")
            return skill_id
        except sqlite3.IntegrityError:
            # Skill already exists
            cursor.execute("SELECT id FROM skills WHERE name = ?", (metadata.name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def publish_version(self, skill_id: int, metadata: SkillMetadata, 
                       content: bytes) -> str:
        """Publish a new skill version"""
        checksum = hashlib.sha256(content).hexdigest()
        requirements_json = json.dumps(metadata.requirements)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO skill_versions 
            (skill_id, version, checksum, requirements)
            VALUES (?, ?, ?, ?)
        """, (skill_id, metadata.version, checksum, requirements_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Published {metadata.name} v{metadata.version}")
        return checksum
    
    def search_skills(self, query: str = "", tags: List[str] = None, 
                     limit: int = 50) -> List[Dict[str, Any]]:
        """Search skills by name, description, or tags"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build search query
        sql = "SELECT id, name, author, description, license, created_at FROM skills WHERE status = 'published'"
        params = []
        
        if query:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "name": r[1],
                "author": r[2],
                "description": r[3],
                "license": r[4],
                "created_at": r[5]
            }
            for r in results
        ]
    
    def get_skill(self, skill_id: int) -> Optional[Dict[str, Any]]:
        """Get skill details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, author, description, repo_url, license, created_at
            FROM skills WHERE id = ?
        """, (skill_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "name": result[1],
                "author": result[2],
                "description": result[3],
                "repo_url": result[4],
                "license": result[5],
                "created_at": result[6]
            }
        return None
    
    def get_versions(self, skill_id: int) -> List[SkillVersion]:
        """Get all versions of a skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, version, checksum, published_at, requirements, downloads, rating
            FROM skill_versions WHERE skill_id = ?
            ORDER BY published_at DESC
        """, (skill_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        versions = []
        for r in results:
            req = json.loads(r[4]) if r[4] else {}
            versions.append(SkillVersion(
                skill_id=skill_id,
                version=r[1],
                checksum=r[2],
                published_at=datetime.fromisoformat(r[3]),
                requirements=req,
                downloads=r[5],
                rating=r[6]
            ))
        
        return versions
    
    def resolve_version(self, skill_id: int, version_requirement: str) -> Optional[str]:
        """Resolve a version requirement to actual version"""
        versions = self.get_versions(skill_id)
        
        for v in versions:
            if VersionParser.satisfies(v.version, version_requirement):
                return v.version
        
        return None
    
    def increment_downloads(self, skill_id: int, version: str):
        """Increment download counter for version tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skill_versions 
            SET downloads = downloads + 1
            WHERE skill_id = ? AND version = ?
        """, (skill_id, version))
        
        conn.commit()
        conn.close()
    
    def mark_deprecated(self, skill_id: int):
        """Mark a skill as deprecated"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skills 
            SET status = 'deprecated'
            WHERE id = ?
        """, (skill_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"Marked skill {skill_id} as deprecated")


class SkillInstaller:
    """Orchestrates skill installation and upgrades"""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.installations = {}  # Track active installations
    
    def install_skill(self, agent_id: str, skill_id: int, 
                     version: str) -> Dict[str, Any]:
        """Install a skill for an agent"""
        skill = self.registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        installation_id = f"{agent_id}_{skill_id}_{datetime.now().timestamp()}"
        
        self.installations[installation_id] = {
            "agent_id": agent_id,
            "skill_id": skill_id,
            "version": version,
            "status": InstallationStatus.PENDING.value,
            "started_at": datetime.now(),
            "previous_version": None
        }
        
        try:
            # Update installation status
            self._update_installation_status(installation_id, InstallationStatus.INSTALLING)
            
            # Simulate installation (in production, this would download and install)
            self.registry.increment_downloads(skill_id, version)
            
            self._update_installation_status(installation_id, InstallationStatus.INSTALLED)
            
            return {
                "installation_id": installation_id,
                "status": InstallationStatus.INSTALLED.value,
                "skill": skill["name"],
                "version": version
            }
        except Exception as e:
            self._update_installation_status(installation_id, InstallationStatus.FAILED)
            logger.error(f"Installation failed: {e}")
            raise
    
    def upgrade_skill(self, agent_id: str, skill_id: int, 
                     new_version: str) -> Dict[str, Any]:
        """Upgrade an installed skill to a new version"""
        # Get current installation
        current = self._find_installation(agent_id, skill_id)
        if not current:
            raise ValueError(f"Skill not installed for agent {agent_id}")
        
        old_version = current["version"]
        installation_id = f"{agent_id}_{skill_id}_upgrade_{datetime.now().timestamp()}"
        
        self.installations[installation_id] = {
            "agent_id": agent_id,
            "skill_id": skill_id,
            "version": new_version,
            "status": InstallationStatus.PENDING.value,
            "started_at": datetime.now(),
            "previous_version": old_version,
            "previous_installation_id": current.get("installation_id")
        }
        
        try:
            self._update_installation_status(installation_id, InstallationStatus.INSTALLING)
            self.registry.increment_downloads(skill_id, new_version)
            self._update_installation_status(installation_id, InstallationStatus.INSTALLED)
            
            return {
                "installation_id": installation_id,
                "status": InstallationStatus.INSTALLED.value,
                "old_version": old_version,
                "new_version": new_version
            }
        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            self.rollback_upgrade(installation_id)
            raise
    
    def rollback_upgrade(self, installation_id: str) -> bool:
        """Rollback a failed upgrade to previous version"""
        if installation_id not in self.installations:
            return False
        
        inst = self.installations[installation_id]
        if not inst.get("previous_version"):
            return False
        
        self._update_installation_status(installation_id, InstallationStatus.ROLLING_BACK)
        
        try:
            # Rollback logic here
            self._update_installation_status(installation_id, InstallationStatus.ROLLED_BACK)
            logger.info(f"Rolled back installation {installation_id}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def _find_installation(self, agent_id: str, skill_id: int) -> Optional[Dict]:
        """Find active installation for an agent's skill"""
        for inst in self.installations.values():
            if (inst["agent_id"] == agent_id and 
                inst["skill_id"] == skill_id and
                inst["status"] == InstallationStatus.INSTALLED.value):
                return inst
        return None
    
    def _update_installation_status(self, installation_id: str, 
                                   status: InstallationStatus):
        """Update installation status"""
        if installation_id in self.installations:
            self.installations[installation_id]["status"] = status.value


# Convenience module initialization
def create_marketplace(db_path: str = "marketplace.db") -> Tuple[SkillRegistry, SkillInstaller]:
    """Factory function to create marketplace components"""
    registry = SkillRegistry(db_path)
    installer = SkillInstaller(registry)
    return registry, installer
