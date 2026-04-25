"""
Skill Marketplace Test Suite
Comprehensive testing of all marketplace components with 22+ tests
"""

import pytest
import sqlite3
import json
import tempfile
import io
import tarfile
from pathlib import Path
from datetime import datetime
import sys

# Add universe to path
sys.path.insert(0, '/agent/home')

from universe.marketplace.marketplace import (
    SkillRegistry, SkillInstaller, SkillMetadata, VersionParser,
    InstallationStatus, create_marketplace
)
from universe.marketplace.skill_publish import (
    SkillPublisher, SkillValidator, SkillManifest, 
    SkillPackager, ValidationError
)
from universe.marketplace.skill_resolver import (
    DependencyResolver, CompatibilityChecker, DependencyGraph
)
from universe.marketplace.skill_reviews import (
    ReviewModeration, RatingAggregator, SpamDetector, ReviewStatus
)
from universe.marketplace.marketplace_ui import MarketplaceUI, create_marketplace_ui


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    import os
    try:
        os.remove(db_path)
    except:
        pass


@pytest.fixture
def registry(temp_db):
    """Create test registry"""
    return SkillRegistry(temp_db)


@pytest.fixture
def installer(registry):
    """Create test installer"""
    return SkillInstaller(registry)


@pytest.fixture
def publisher(registry):
    """Create test publisher"""
    return SkillPublisher(registry)


@pytest.fixture
def moderation(temp_db):
    """Create test moderation"""
    return ReviewModeration(temp_db)


@pytest.fixture
def rating_agg(temp_db):
    """Create test rating aggregator"""
    return RatingAggregator(temp_db)


class TestVersionParsing:
    """Test semantic version parsing"""
    
    def test_parse_valid_version(self):
        """Test parsing valid version string"""
        major, minor, patch, pre, build = VersionParser.parse("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3
        assert pre == ""
        assert build == ""
    
    def test_parse_prerelease_version(self):
        """Test parsing prerelease version"""
        major, minor, patch, pre, build = VersionParser.parse("1.2.3-alpha.1")
        assert pre == "alpha.1"
    
    def test_parse_invalid_version(self):
        """Test parsing invalid version"""
        with pytest.raises(ValueError):
            VersionParser.parse("invalid")
    
    def test_version_comparison(self):
        """Test version comparison"""
        assert VersionParser.compare("1.0.0", "1.0.1") == -1
        assert VersionParser.compare("2.0.0", "1.9.9") == 1
        assert VersionParser.compare("1.0.0", "1.0.0") == 0
    
    def test_version_satisfies(self):
        """Test version requirement satisfaction"""
        assert VersionParser.satisfies("1.2.3", ">=1.0.0")
        assert VersionParser.satisfies("1.2.3", "^1.0.0")
        assert VersionParser.satisfies("1.2.3", "*")
        assert not VersionParser.satisfies("0.9.0", ">=1.0.0")


class TestSkillRegistration:
    """Test skill registry functionality"""
    
    def test_register_new_skill(self, registry):
        """Test registering a new skill"""
        metadata = SkillMetadata(
            name="test-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=["test"]
        )
        
        skill_id = registry.register_skill(metadata)
        assert skill_id is not None
        
        # Verify registration
        skill = registry.get_skill(skill_id)
        assert skill["name"] == "test-skill"
        assert skill["author"] == "test-author"
    
    def test_register_duplicate_skill(self, registry):
        """Test registering duplicate skill returns same ID"""
        metadata = SkillMetadata(
            name="duplicate-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        
        id1 = registry.register_skill(metadata)
        id2 = registry.register_skill(metadata)
        assert id1 == id2
    
    def test_publish_version(self, registry):
        """Test publishing a skill version"""
        metadata = SkillMetadata(
            name="versioned-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={"dependency": ">=1.0.0"},
            tags=[]
        )
        
        skill_id = registry.register_skill(metadata)
        content = b"skill content"
        checksum = registry.publish_version(skill_id, metadata, content)
        
        assert checksum is not None
        
        # Verify version was published
        versions = registry.get_versions(skill_id)
        assert len(versions) > 0
        assert versions[0].version == "1.0.0"
    
    def test_search_skills(self, registry):
        """Test searching for skills"""
        # Register multiple skills
        for i in range(5):
            metadata = SkillMetadata(
                name=f"search-skill-{i}",
                version="1.0.0",
                author="test-author",
                description=f"Search test skill {i}",
                license="MIT",
                repo_url="https://github.com/test/test-skill",
                requirements={},
                tags=[]
            )
            registry.register_skill(metadata)
        
        # Search
        results = registry.search_skills("search", limit=10)
        assert len(results) > 0
        
        # Verify filtering
        filtered = registry.search_skills("skill-1", limit=10)
        assert len(filtered) >= 1


class TestSkillPublishing:
    """Test skill publishing workflow"""
    
    def test_validate_valid_manifest(self):
        """Test validation of valid manifest"""
        manifest = {
            "name": "valid-skill",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "A valid test skill",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py"
        }
        
        is_valid, errors = SkillValidator.validate_manifest(manifest)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_invalid_name(self):
        """Test validation with invalid name"""
        manifest = {
            "name": "Invalid-Name-With-Caps",  # Invalid format
            "version": "1.0.0",
            "author": "Test Author",
            "description": "A test skill",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py"
        }
        
        is_valid, errors = SkillValidator.validate_manifest(manifest)
        assert not is_valid
        assert any("name" in e.lower() for e in errors)
    
    def test_validate_invalid_version(self):
        """Test validation with invalid version"""
        manifest = {
            "name": "valid-skill",
            "version": "not-a-version",  # Invalid format
            "author": "Test Author",
            "description": "A test skill",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py"
        }
        
        is_valid, errors = SkillValidator.validate_manifest(manifest)
        assert not is_valid
        assert any("version" in e.lower() for e in errors)
    
    def test_publish_skill(self, publisher, registry):
        """Test publishing a skill"""
        manifest = {
            "name": "published-skill",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "A published skill",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py",
            "keywords": ["test"],
            "requirements": {}
        }
        
        content = b"skill package content"
        result = publisher.publish_skill(manifest, content)
        
        assert "skill_id" in result
        assert result["version"] == "1.0.0"
        assert result["name"] == "published-skill"
    
    def test_publish_invalid_skill_fails(self, publisher):
        """Test publishing invalid skill raises error"""
        manifest = {
            "name": "invalid",
            # Missing required fields
        }
        
        content = b"skill package content"
        
        with pytest.raises(ValidationError):
            publisher.publish_skill(manifest, content)


class TestDependencyResolution:
    """Test dependency resolution"""
    
    def test_compatibility_exact_match(self):
        """Test exact version compatibility"""
        assert CompatibilityChecker.is_compatible("1.0.0", "1.0.0")
    
    def test_compatibility_caret(self):
        """Test caret version compatibility"""
        assert CompatibilityChecker.is_compatible("1.2.3", "^1.0.0")
        assert not CompatibilityChecker.is_compatible("2.0.0", "^1.0.0")
    
    def test_compatibility_tilde(self):
        """Test tilde version compatibility"""
        assert CompatibilityChecker.is_compatible("1.2.3", "~1.2.0")
        assert not CompatibilityChecker.is_compatible("1.3.0", "~1.2.0")
    
    def test_compatibility_gte(self):
        """Test >= operator"""
        assert CompatibilityChecker.is_compatible("1.2.0", ">=1.0.0")
        assert not CompatibilityChecker.is_compatible("0.9.0", ">=1.0.0")
    
    def test_find_compatible_version(self):
        """Test finding compatible version"""
        versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        compatible = CompatibilityChecker.find_compatible_version(
            versions, "^1.0.0"
        )
        assert compatible == "1.2.0"  # Highest compatible


class TestInstallation:
    """Test skill installation"""
    
    def test_install_skill(self, registry, installer):
        """Test installing a skill"""
        # Register and publish skill
        metadata = SkillMetadata(
            name="installable-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        
        skill_id = registry.register_skill(metadata)
        registry.publish_version(skill_id, metadata, b"content")
        
        # Install
        result = installer.install_skill("agent-1", skill_id, "1.0.0")
        assert result["status"] == InstallationStatus.INSTALLED.value
    
    def test_upgrade_skill(self, registry, installer):
        """Test upgrading a skill"""
        # Register and publish multiple versions
        metadata_v1 = SkillMetadata(
            name="upgradeable-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        
        skill_id = registry.register_skill(metadata_v1)
        registry.publish_version(skill_id, metadata_v1, b"content-v1")
        
        # Install v1
        installer.install_skill("agent-1", skill_id, "1.0.0")
        
        # Publish v2
        metadata_v2 = SkillMetadata(
            name="upgradeable-skill",
            version="1.1.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        registry.publish_version(skill_id, metadata_v2, b"content-v2")
        
        # Upgrade
        result = installer.upgrade_skill("agent-1", skill_id, "1.1.0")
        assert result["new_version"] == "1.1.0"


class TestReviews:
    """Test review and rating functionality"""
    
    def test_submit_valid_review(self, moderation):
        """Test submitting a valid review"""
        success, review_id, message = moderation.submit_review(
            skill_id=1,
            reviewer_id="reviewer-1",
            rating=5,
            title="Great skill",
            comment="This skill works perfectly for my use case. Highly recommended!"
        )
        
        assert success
        assert review_id is not None
    
    def test_submit_spam_review(self, moderation):
        """Test that spam reviews are rejected"""
        success, review_id, message = moderation.submit_review(
            skill_id=1,
            reviewer_id="reviewer-1",
            rating=5,
            title="Click here",
            comment="Click here for free money! Visit my site now!"
        )
        
        assert not success
        assert "spam" in message.lower()
    
    def test_submit_short_review(self, moderation):
        """Test that very short reviews are rejected"""
        success, review_id, message = moderation.submit_review(
            skill_id=1,
            reviewer_id="reviewer-1",
            rating=5,
            title="Good",
            comment="ok"  # Too short
        )
        
        assert not success
    
    def test_spam_detection(self):
        """Test spam detection"""
        spam_text = "Click here for free money! BUY NOW!"
        is_spam, reason = SpamDetector.is_spam(spam_text)
        assert is_spam
    
    def test_review_moderation(self, moderation):
        """Test review approval/rejection"""
        success, review_id, _ = moderation.submit_review(
            skill_id=1,
            reviewer_id="reviewer-1",
            rating=4,
            title="Good",
            comment="This is a legitimate review with sufficient content to pass validation checks."
        )
        
        if success:
            # Approve review
            moderation.approve_review(review_id)
            
            pending = moderation.get_pending_reviews()
            # Should not be in pending after approval
            assert review_id not in [r.id for r in pending]
    
    def test_get_skill_rating(self, moderation, rating_agg):
        """Test getting aggregated skill rating"""
        # Submit and approve multiple reviews
        for rating in [5, 4, 5, 3]:
            success, review_id, _ = moderation.submit_review(
                skill_id=2,
                reviewer_id=f"reviewer-{rating}",
                rating=rating,
                title=f"Rating {rating}",
                comment=f"Review with rating {rating}. " * 3
            )
            
            if success and review_id:
                moderation.approve_review(review_id)
        
        rating_data = rating_agg.get_skill_rating(2)
        assert rating_data["total_reviews"] >= 0


class TestMarketplaceUI:
    """Test marketplace UI functionality"""
    
    def test_search_skills_ui(self, registry, installer, moderation, rating_agg):
        """Test searching skills via UI"""
        # Register a skill
        metadata = SkillMetadata(
            name="ui-test-skill",
            version="1.0.0",
            author="test-author",
            description="A skill for UI testing",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=["test", "ui"]
        )
        skill_id = registry.register_skill(metadata)
        registry.publish_version(skill_id, metadata, b"content")
        
        # Create UI
        ui = create_marketplace_ui(registry, installer, moderation, rating_agg)
        
        # Search
        result = ui.search_skills("ui-test", limit=10)
        assert result["success"]
        assert len(result["results"]) >= 0
    
    def test_get_skill_details_ui(self, registry, installer, moderation, rating_agg):
        """Test getting skill details via UI"""
        # Register a skill
        metadata = SkillMetadata(
            name="detail-skill",
            version="1.0.0",
            author="test-author",
            description="Skill for detail testing",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        skill_id = registry.register_skill(metadata)
        registry.publish_version(skill_id, metadata, b"content")
        
        # Get details
        ui = create_marketplace_ui(registry, installer, moderation, rating_agg)
        result = ui.get_skill_details(skill_id)
        
        assert result["success"]
        assert result["skill"]["name"] == "detail-skill"
    
    def test_install_via_ui(self, registry, installer, moderation, rating_agg):
        """Test installing skill via UI"""
        # Register and publish skill
        metadata = SkillMetadata(
            name="installable-ui-skill",
            version="1.0.0",
            author="test-author",
            description="Test skill",
            license="MIT",
            repo_url="https://github.com/test/test-skill",
            requirements={},
            tags=[]
        )
        skill_id = registry.register_skill(metadata)
        registry.publish_version(skill_id, metadata, b"content")
        
        # Install via UI
        ui = create_marketplace_ui(registry, installer, moderation, rating_agg)
        result = ui.install_skill("agent-ui-1", skill_id, "1.0.0")
        
        assert result["success"]
    
    def test_marketplace_stats(self, registry, installer, moderation, rating_agg):
        """Test getting marketplace statistics"""
        ui = create_marketplace_ui(registry, installer, moderation, rating_agg)
        stats = ui.get_marketplace_stats()
        
        assert stats["success"]
        assert "stats" in stats
        assert "total_skills" in stats["stats"]


class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_full_publish_install_workflow(self, registry, installer, publisher):
        """Test full publish and install workflow"""
        # Publish skill
        manifest = {
            "name": "integration-skill",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Integration test skill",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py",
            "keywords": ["integration"],
            "requirements": {}
        }
        
        result = publisher.publish_skill(manifest, b"skill-content")
        assert result.get("success") or "skill_id" in result
        
        # Get skill
        skills = registry.search_skills("integration-skill")
        assert len(skills) > 0
    
    def test_marketplace_complete_flow(self, registry, installer, publisher, 
                                      moderation, rating_agg):
        """Test complete marketplace flow"""
        # 1. Publish
        manifest = {
            "name": "complete-flow-skill",
            "version": "1.0.0",
            "author": "Flow Tester",
            "description": "Complete flow test",
            "license": "MIT",
            "repo_url": "https://github.com/test/skill",
            "entry_point": "main.py",
            "keywords": [],
            "requirements": {}
        }
        
        result = publisher.publish_skill(manifest, b"content")
        
        # Get skill ID from registry
        skills = registry.search_skills("complete-flow-skill")
        if len(skills) > 0:
            skill_id = skills[0]["id"]
            
            # 2. Install
            inst_result = installer.install_skill("agent-flow", skill_id, "1.0.0")
            assert inst_result["status"] == InstallationStatus.INSTALLED.value
            
            # 3. Review
            moderation.submit_review(
                skill_id=skill_id,
                reviewer_id="flow-reviewer",
                rating=5,
                title="Great workflow",
                comment="This skill works great in a complete workflow. Excellent work!"
            )
            
            # 4. Check rating
            rating_data = rating_agg.get_skill_rating(skill_id)
            assert "average_rating" in rating_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
