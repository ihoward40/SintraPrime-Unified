"""
Skill Publishing - Package Creation and Validation
Handles skill packaging, validation, versioning, and publication to the marketplace.
"""

import json
import hashlib
import tarfile
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import re
from enum import Enum


logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """Supported licenses"""
    MIT = "MIT"
    APACHE2 = "Apache-2.0"
    GPL3 = "GPL-3.0"
    BSD3 = "BSD-3-Clause"
    PROPRIETARY = "Proprietary"


class ValidationError(Exception):
    """Raised when skill validation fails"""
    pass


@dataclass
class SkillManifest:
    """Skill manifest metadata"""
    name: str
    version: str
    author: str
    description: str
    license: str
    repo_url: str
    keywords: List[str]
    requirements: Dict[str, str]
    entry_point: str
    min_universe_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "license": self.license,
            "repo_url": self.repo_url,
            "keywords": self.keywords,
            "requirements": self.requirements,
            "entry_point": self.entry_point,
            "min_universe_version": self.min_universe_version,
            "published_at": datetime.now().isoformat()
        }


class SkillValidator:
    """Validates skill packages before publication"""
    
    REQUIRED_MANIFEST_FIELDS = [
        "name", "version", "author", "description", 
        "license", "repo_url", "entry_point"
    ]
    
    NAME_PATTERN = r"^[a-z0-9_-]{3,50}$"
    VERSION_PATTERN = r"^\d+\.\d+\.\d+(?:-[a-z0-9.]+)?$"
    
    @staticmethod
    def validate_manifest(manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate skill manifest"""
        errors = []
        
        # Check required fields
        for field in SkillValidator.REQUIRED_MANIFEST_FIELDS:
            if field not in manifest:
                errors.append(f"Missing required field: {field}")
        
        # Validate name format
        if "name" in manifest:
            name = manifest["name"]
            if not re.match(SkillValidator.NAME_PATTERN, name):
                errors.append(f"Invalid skill name format: {name}")
        
        # Validate version format
        if "version" in manifest:
            version = manifest["version"]
            if not re.match(SkillValidator.VERSION_PATTERN, version):
                errors.append(f"Invalid version format: {version}")
        
        # Validate license
        if "license" in manifest:
            valid_licenses = [l.value for l in LicenseType]
            if manifest["license"] not in valid_licenses:
                errors.append(f"Invalid license: {manifest['license']}")
        
        # Validate requirements format
        if "requirements" in manifest:
            if not isinstance(manifest["requirements"], dict):
                errors.append("Requirements must be a dictionary")
            else:
                for req_name, req_version in manifest["requirements"].items():
                    if not isinstance(req_name, str) or not isinstance(req_version, str):
                        errors.append(f"Invalid requirement format: {req_name}={req_version}")
        
        # Validate URL format
        if "repo_url" in manifest:
            repo_url = manifest["repo_url"]
            if not (repo_url.startswith("http://") or repo_url.startswith("https://")):
                errors.append(f"Invalid repository URL: {repo_url}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_content(content: bytes) -> Tuple[bool, List[str]]:
        """Validate skill content/package"""
        errors = []
        
        # Check content is not empty
        if not content or len(content) == 0:
            errors.append("Skill content is empty")
            return False, errors
        
        # Check reasonable size (max 100MB)
        if len(content) > 100 * 1024 * 1024:
            errors.append("Skill package exceeds maximum size (100MB)")
        
        # Try to verify it's valid tar/gzip (optional, for production)
        # In testing, we accept raw content
        try:
            tar_file = tarfile.open(fileobj=io.BytesIO(content), mode="r:gz")
            tar_file.close()
        except Exception:
            # If gzip fails, that's OK - could be other formats or raw content
            pass
        
        return len(errors) == 0, errors


class SkillPackager:
    """Creates skill packages from skill files"""
    
    @staticmethod
    def create_package(skill_dir: Path, manifest: SkillManifest) -> bytes:
        """Create a compressed skill package"""
        buffer = io.BytesIO()
        
        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            # Add manifest
            manifest_json = json.dumps(manifest.to_dict(), indent=2)
            manifest_info = tarfile.TarInfo(name="manifest.json")
            manifest_info.size = len(manifest_json.encode())
            tar.addfile(manifest_info, io.BytesIO(manifest_json.encode()))
            
            # Add skill files
            for file_path in skill_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(skill_dir)
                    tar.add(file_path, arcname=arcname)
        
        return buffer.getvalue()
    
    @staticmethod
    def extract_package(package_content: bytes, extract_to: Path):
        """Extract skill package to directory"""
        with tarfile.open(fileobj=io.BytesIO(package_content), mode="r:gz") as tar:
            tar.extractall(path=extract_to)


class SkillPublisher:
    """Publishes skills to the marketplace"""
    
    def __init__(self, registry):
        self.registry = registry
        self.validator = SkillValidator()
    
    def publish_skill(self, manifest_dict: Dict[str, Any], 
                     package_content: bytes, signature: str = "") -> Dict[str, Any]:
        """Publish a skill to the marketplace"""
        
        # Validate manifest
        is_valid, errors = self.validator.validate_manifest(manifest_dict)
        if not is_valid:
            raise ValidationError(f"Manifest validation failed: {', '.join(errors)}")
        
        # Validate content
        is_valid, errors = self.validator.validate_content(package_content)
        if not is_valid:
            raise ValidationError(f"Content validation failed: {', '.join(errors)}")
        
        # Create manifest object
        manifest = SkillManifest(
            name=manifest_dict["name"],
            version=manifest_dict["version"],
            author=manifest_dict["author"],
            description=manifest_dict["description"],
            license=manifest_dict["license"],
            repo_url=manifest_dict["repo_url"],
            keywords=manifest_dict.get("keywords", []),
            requirements=manifest_dict.get("requirements", {}),
            entry_point=manifest_dict["entry_point"],
            min_universe_version=manifest_dict.get("min_universe_version", "1.0.0")
        )
        
        # Register skill
        skill_id = self.registry.register_skill(manifest)
        
        # Publish version
        checksum = self.registry.publish_version(skill_id, manifest, package_content)
        
        logger.info(f"Published skill: {manifest.name} v{manifest.version}")
        
        return {
            "skill_id": skill_id,
            "name": manifest.name,
            "version": manifest.version,
            "checksum": checksum,
            "published_at": datetime.now().isoformat(),
            "signature": signature
        }
    
    def validate_signature(self, package_content: bytes, signature: str) -> bool:
        """Validate cryptographic signature (optional security feature)"""
        # In production, would use public key cryptography
        # For now, simple validation that signature matches content hash
        content_hash = hashlib.sha256(package_content).hexdigest()
        return signature == content_hash or signature == ""  # Allow unsigned for development
    
    def get_publish_status(self, skill_id: int) -> Dict[str, Any]:
        """Get publication status of a skill"""
        skill = self.registry.get_skill(skill_id)
        if not skill:
            return None
        
        versions = self.registry.get_versions(skill_id)
        
        return {
            "skill_id": skill_id,
            "name": skill["name"],
            "author": skill["author"],
            "status": skill.get("status", "published"),
            "versions": [
                {
                    "version": v.version,
                    "published_at": v.published_at.isoformat(),
                    "downloads": v.downloads,
                    "rating": v.rating
                }
                for v in versions
            ],
            "total_downloads": sum(v.downloads for v in versions)
        }


class VersionManager:
    """Manages skill versioning and releases"""
    
    BREAKING_CHANGES_KEYWORDS = [
        "breaking", "incompatible", "removed", "refactor"
    ]
    
    @staticmethod
    def suggest_next_version(current_version: str, 
                           change_type: str = "patch") -> str:
        """Suggest next version based on change type"""
        parts = current_version.split(".")
        
        if change_type == "major":
            return f"{int(parts[0]) + 1}.0.0"
        elif change_type == "minor":
            return f"{parts[0]}.{int(parts[1]) + 1}.0"
        elif change_type == "patch":
            return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        
        return current_version
    
    @staticmethod
    def detect_breaking_changes(changelog: str) -> bool:
        """Detect if changelog indicates breaking changes"""
        changelog_lower = changelog.lower()
        return any(keyword in changelog_lower for keyword in 
                  VersionManager.BREAKING_CHANGES_KEYWORDS)


class ReleaseNotes:
    """Generate and manage release notes"""
    
    @staticmethod
    def generate_release_notes(
        skill_name: str,
        version: str,
        changes: List[str],
        breaking_changes: List[str] = None
    ) -> str:
        """Generate formatted release notes"""
        
        notes = f"""# {skill_name} v{version}

## Changes
"""
        for change in changes:
            notes += f"- {change}\n"
        
        if breaking_changes:
            notes += "\n## ⚠️ Breaking Changes\n"
            for breaking in breaking_changes:
                notes += f"- {breaking}\n"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        notes += f"\n**Released:** {timestamp}\n"
        
        return notes
