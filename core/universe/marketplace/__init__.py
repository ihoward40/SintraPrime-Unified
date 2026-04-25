"""
SintraPrime UniVerse Skill Marketplace
A production-grade marketplace for agent skills with versioning, 
dependency resolution, ratings, and one-click installation.
"""

from .marketplace import (
    SkillRegistry,
    SkillInstaller,
    SkillMetadata,
    SkillVersion,
    VersionParser,
    SkillStatus,
    InstallationStatus,
    create_marketplace
)

from .skill_publish import (
    SkillPublisher,
    SkillValidator,
    SkillManifest,
    SkillPackager,
    VersionManager,
    ReleaseNotes,
    LicenseType,
    ValidationError
)

from .skill_resolver import (
    DependencyResolver,
    DependencyGraph,
    CompatibilityChecker,
    InstallationSequencer,
    RollbackManager,
    DependencyConstraint,
    ResolutionResult,
    ConflictType
)

from .skill_reviews import (
    ReviewModeration,
    RatingAggregator,
    SpamDetector,
    SkillReview,
    ReviewStatus,
    RatingScore
)

from .marketplace_ui import (
    MarketplaceUI,
    APIEndpoint,
    create_marketplace_ui
)

__version__ = "1.0.0"
__author__ = "SintraPrime Development Team"
__all__ = [
    # Marketplace core
    "SkillRegistry",
    "SkillInstaller",
    "SkillMetadata",
    "SkillVersion",
    "VersionParser",
    "SkillStatus",
    "InstallationStatus",
    "create_marketplace",
    
    # Publishing
    "SkillPublisher",
    "SkillValidator",
    "SkillManifest",
    "SkillPackager",
    "VersionManager",
    "ReleaseNotes",
    "LicenseType",
    "ValidationError",
    
    # Resolver
    "DependencyResolver",
    "DependencyGraph",
    "CompatibilityChecker",
    "InstallationSequencer",
    "RollbackManager",
    "DependencyConstraint",
    "ResolutionResult",
    "ConflictType",
    
    # Reviews
    "ReviewModeration",
    "RatingAggregator",
    "SpamDetector",
    "SkillReview",
    "ReviewStatus",
    "RatingScore",
    
    # UI
    "MarketplaceUI",
    "APIEndpoint",
    "create_marketplace_ui"
]
