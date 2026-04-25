"""
Marketplace UI - Web Interface for Skill Discovery and Installation
Provides REST API endpoints for browsing, searching, and managing skills.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


logger = logging.getLogger(__name__)


class APIEndpoint(Enum):
    """API endpoints for marketplace UI"""
    SEARCH_SKILLS = "/api/skills/search"
    GET_SKILL = "/api/skills/{skill_id}"
    GET_SKILL_VERSIONS = "/api/skills/{skill_id}/versions"
    GET_SKILL_REVIEWS = "/api/skills/{skill_id}/reviews"
    INSTALL_SKILL = "/api/installations"
    GET_INSTALLATION = "/api/installations/{installation_id}"
    UPGRADE_SKILL = "/api/installations/{installation_id}/upgrade"
    SUBMIT_REVIEW = "/api/skills/{skill_id}/reviews"
    GET_TRENDING = "/api/trending"
    GET_MARKETPLACE_STATS = "/api/marketplace/stats"


class MarketplaceUI:
    """Web UI controller for marketplace"""
    
    def __init__(self, registry, installer, reviewer, rating_agg):
        self.registry = registry
        self.installer = installer
        self.reviewer = reviewer
        self.rating_agg = rating_agg
        self.user_installations = {}  # Track user installations
    
    # ============== Search & Discovery ==============
    
    def search_skills(self, query: str = "", tags: List[str] = None, 
                     limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Search for skills in marketplace"""
        try:
            results = self.registry.search_skills(query, tags, limit + 1)
            
            # Apply pagination
            has_more = len(results) > limit
            results = results[offset:offset + limit]
            
            # Enrich with ratings
            enriched_results = []
            for skill in results:
                rating_data = self.rating_agg.get_skill_rating(skill["id"])
                enriched_results.append({
                    **skill,
                    "rating": rating_data["average_rating"],
                    "review_count": rating_data["total_reviews"]
                })
            
            return {
                "success": True,
                "results": enriched_results,
                "total": len(results),
                "has_more": has_more,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_skill_details(self, skill_id: int) -> Dict[str, Any]:
        """Get detailed information about a skill"""
        try:
            skill = self.registry.get_skill(skill_id)
            if not skill:
                return {"success": False, "error": "Skill not found"}
            
            versions = self.registry.get_versions(skill_id)
            rating_data = self.rating_agg.get_skill_rating(skill_id)
            recent_reviews = self.rating_agg.get_review_history(skill_id)[:5]
            
            return {
                "success": True,
                "skill": {
                    **skill,
                    "versions": [
                        {
                            "version": v.version,
                            "published_at": v.published_at.isoformat(),
                            "downloads": v.downloads,
                            "rating": v.rating
                        }
                        for v in versions
                    ],
                    "rating": {
                        "average": rating_data["average_rating"],
                        "total_reviews": rating_data["total_reviews"],
                        "distribution": rating_data["rating_distribution"]
                    },
                    "recent_reviews": [
                        {
                            "id": r.id,
                            "reviewer": r.reviewer_id,
                            "rating": r.rating,
                            "title": r.title,
                            "comment": r.comment,
                            "helpful_count": r.helpful_count,
                            "created_at": r.created_at.isoformat() if r.created_at else None
                        }
                        for r in recent_reviews
                    ]
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get skill details: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_trending_skills(self, limit: int = 10) -> Dict[str, Any]:
        """Get trending skills"""
        try:
            trending = self.rating_agg.get_trending_skills(limit)
            
            return {
                "success": True,
                "trending": trending,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get trending: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============== Installation Management ==============
    
    def install_skill(self, agent_id: str, skill_id: int, 
                     version: str = "latest") -> Dict[str, Any]:
        """Install a skill for an agent"""
        try:
            # Resolve version if needed
            if version == "latest" or version == "*":
                versions = self.registry.get_versions(skill_id)
                if not versions:
                    return {
                        "success": False,
                        "error": "No versions available"
                    }
                version = versions[0].version
            
            # Perform installation
            result = self.installer.install_skill(agent_id, skill_id, version)
            
            # Track in user installations
            if agent_id not in self.user_installations:
                self.user_installations[agent_id] = []
            
            self.user_installations[agent_id].append({
                "skill_id": skill_id,
                "version": version,
                "installed_at": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "installation": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_installations(self, agent_id: str) -> Dict[str, Any]:
        """Get all installations for a user"""
        try:
            installations = self.user_installations.get(agent_id, [])
            
            # Enrich with skill details
            enriched = []
            for inst in installations:
                skill = self.registry.get_skill(inst["skill_id"])
                if skill:
                    enriched.append({
                        **inst,
                        "skill_name": skill["name"],
                        "author": skill["author"]
                    })
            
            return {
                "success": True,
                "installations": enriched,
                "count": len(enriched),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get installations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upgrade_skill(self, agent_id: str, skill_id: int, 
                     new_version: str) -> Dict[str, Any]:
        """Upgrade an installed skill"""
        try:
            result = self.installer.upgrade_skill(agent_id, skill_id, new_version)
            
            # Update user installations
            if agent_id in self.user_installations:
                for inst in self.user_installations[agent_id]:
                    if inst["skill_id"] == skill_id:
                        inst["version"] = new_version
                        inst["upgraded_at"] = datetime.now().isoformat()
                        break
            
            return {
                "success": True,
                "upgrade": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============== Reviews & Ratings ==============
    
    def submit_review(self, skill_id: int, reviewer_id: str, rating: int,
                     title: str, comment: str) -> Dict[str, Any]:
        """Submit a review for a skill"""
        try:
            success, review_id, message = self.reviewer.submit_review(
                skill_id, reviewer_id, rating, title, comment
            )
            
            return {
                "success": success,
                "review_id": review_id,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Review submission failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_skill_reviews(self, skill_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get reviews for a skill"""
        try:
            reviews = self.rating_agg.get_review_history(skill_id)[:limit]
            
            return {
                "success": True,
                "reviews": [
                    {
                        "id": r.id,
                        "reviewer": r.reviewer_id,
                        "rating": r.rating,
                        "title": r.title,
                        "comment": r.comment,
                        "helpful_count": r.helpful_count,
                        "unhelpful_count": r.unhelpful_count,
                        "created_at": r.created_at.isoformat() if r.created_at else None
                    }
                    for r in reviews
                ],
                "count": len(reviews),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get reviews: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def mark_review_helpful(self, review_id: int) -> Dict[str, Any]:
        """Mark a review as helpful"""
        try:
            self.rating_agg.mark_helpful(review_id)
            return {
                "success": True,
                "message": "Review marked as helpful"
            }
        except Exception as e:
            logger.error(f"Failed to mark review: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============== Marketplace Statistics ==============
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        try:
            # In a real implementation, these would be gathered from the database
            all_skills = self.registry.search_skills(limit=1000)
            
            total_downloads = 0
            total_reviews = 0
            avg_rating = 0.0
            
            for skill in all_skills:
                versions = self.registry.get_versions(skill["id"])
                for v in versions:
                    total_downloads += v.downloads
                
                rating_data = self.rating_agg.get_skill_rating(skill["id"])
                total_reviews += rating_data["total_reviews"]
                avg_rating += rating_data["average_rating"]
            
            if all_skills:
                avg_rating /= len(all_skills)
            
            return {
                "success": True,
                "stats": {
                    "total_skills": len(all_skills),
                    "total_downloads": total_downloads,
                    "total_reviews": total_reviews,
                    "average_rating": round(avg_rating, 2),
                    "active_installations": sum(
                        len(insts) for insts in self.user_installations.values()
                    )
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ============== User Dashboard ==============
    
    def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get user dashboard with their skills and activity"""
        try:
            # Get user's installed skills
            installations = self.user_installations.get(user_id, [])
            
            enriched_installations = []
            for inst in installations:
                skill = self.registry.get_skill(inst["skill_id"])
                if skill:
                    rating_data = self.rating_agg.get_skill_rating(inst["skill_id"])
                    enriched_installations.append({
                        **inst,
                        "skill_name": skill["name"],
                        "author": skill["author"],
                        "rating": rating_data["average_rating"],
                        "review_count": rating_data["total_reviews"]
                    })
            
            return {
                "success": True,
                "user_id": user_id,
                "dashboard": {
                    "installations": enriched_installations,
                    "total_installed": len(enriched_installations),
                    "update_available": self._check_updates(user_id)
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get user dashboard: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_updates(self, user_id: str) -> List[Dict[str, str]]:
        """Check for available skill updates"""
        updates = []
        
        installations = self.user_installations.get(user_id, [])
        for inst in installations:
            versions = self.registry.get_versions(inst["skill_id"])
            if versions and versions[0].version != inst["version"]:
                skill = self.registry.get_skill(inst["skill_id"])
                updates.append({
                    "skill_id": inst["skill_id"],
                    "skill_name": skill["name"],
                    "current_version": inst["version"],
                    "latest_version": versions[0].version
                })
        
        return updates


def create_marketplace_ui(registry, installer, reviewer, rating_agg) -> MarketplaceUI:
    """Factory function to create marketplace UI"""
    return MarketplaceUI(registry, installer, reviewer, rating_agg)
