"""
SkillMarketplace – Community-driven skill sharing.

OpenClaw-inspired marketplace for publishing, discovering, and installing
community skills. Uses local JSON file storage with optional GitHub Gists sync.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .skill_library import SkillLibrary
from .skill_types import MarketplaceSkill, Skill, SkillCategory


# ---------------------------------------------------------------------------
# Default marketplace path
# ---------------------------------------------------------------------------
DEFAULT_MARKETPLACE_FILE = Path(__file__).parent / "data" / "marketplace.json"


class SkillMarketplace:
    """
    Community marketplace for publishing and discovering skills.

    Local JSON-backed storage. Skills are shared as serializable dicts.
    Ratings, download counts, and trending calculation are maintained locally.
    """

    def __init__(
        self,
        library: SkillLibrary,
        marketplace_file: Optional[Path] = None,
        gist_sync: bool = False,
    ):
        self.library = library
        self.marketplace_file = Path(marketplace_file) if marketplace_file else DEFAULT_MARKETPLACE_FILE
        self.marketplace_file.parent.mkdir(parents=True, exist_ok=True)
        self.gist_sync = gist_sync
        self._data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        if self.marketplace_file.exists():
            try:
                return json.loads(self.marketplace_file.read_text())
            except Exception:
                pass
        return {"skills": {}, "ratings": {}}

    def _save(self) -> None:
        self.marketplace_file.write_text(json.dumps(self._data, indent=2, default=str))

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(
        self,
        skill_id: str,
        author_info: Optional[Dict[str, str]] = None,
        overwrite: bool = False,
    ) -> Optional[MarketplaceSkill]:
        """
        Publish a skill from the local library to the marketplace.

        Returns the MarketplaceSkill record, or None if skill not found.
        """
        skill = self.library.get(skill_id)
        if not skill:
            return None

        # Check if already published
        existing_id = self._find_marketplace_id_by_skill(skill_id)
        if existing_id and not overwrite:
            raise ValueError(f"Skill '{skill_id}' is already published. Use overwrite=True to update.")

        marketplace_id = existing_id or str(uuid.uuid4())

        ms = MarketplaceSkill(
            skill=skill,
            marketplace_id=marketplace_id,
            author_info=author_info or {"name": skill.author},
            rating=0.0,
            rating_count=0,
            download_count=0,
            published_at=datetime.utcnow(),
        )

        self._data["skills"][marketplace_id] = ms.to_dict()
        self._save()
        return ms

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------

    def browse(
        self,
        category: Optional[SkillCategory] = None,
        min_rating: float = 0.0,
        limit: int = 50,
    ) -> List[MarketplaceSkill]:
        """
        Browse marketplace skills, optionally filtered by category and rating.

        Returns skills sorted by download count (most popular first).
        """
        results = []
        for mid, data in self._data["skills"].items():
            ms = MarketplaceSkill.from_dict(data)
            if category and ms.skill.category != category:
                continue
            if ms.rating < min_rating and ms.rating_count > 0:
                continue
            results.append(ms)

        results.sort(key=lambda x: x.download_count, reverse=True)
        return results[:limit]

    def search(self, query: str, category: Optional[SkillCategory] = None) -> List[MarketplaceSkill]:
        """Search marketplace skills by name/description keyword."""
        query_lower = query.lower()
        results = []
        for data in self._data["skills"].values():
            ms = MarketplaceSkill.from_dict(data)
            text = f"{ms.skill.name} {ms.skill.description} {' '.join(ms.skill.tags)}".lower()
            if query_lower in text:
                if category and ms.skill.category != category:
                    continue
                results.append(ms)
        results.sort(key=lambda x: x.download_count, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------

    def install(self, marketplace_skill_id: str) -> Optional[Skill]:
        """
        Install a marketplace skill into the local library.

        Increments download count.
        """
        data = self._data["skills"].get(marketplace_skill_id)
        if not data:
            return None

        ms = MarketplaceSkill.from_dict(data)
        skill = ms.skill

        # Update download count
        self._data["skills"][marketplace_skill_id]["download_count"] += 1
        self._save()

        # Register in local library (generate new ID to avoid conflicts)
        if self.library.get(skill.id):
            # Already installed – just return existing
            return self.library.get(skill.id)

        return self.library.register(skill)

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def rate(self, marketplace_skill_id: str, score: float, feedback: str = "") -> bool:
        """
        Rate a marketplace skill 1–5 stars with optional text feedback.

        Updates the rolling average rating.
        """
        if not (1.0 <= score <= 5.0):
            return False

        data = self._data["skills"].get(marketplace_skill_id)
        if not data:
            return False

        old_rating = data.get("rating", 0.0)
        old_count = data.get("rating_count", 0)
        new_count = old_count + 1
        new_rating = ((old_rating * old_count) + score) / new_count

        self._data["skills"][marketplace_skill_id]["rating"] = round(new_rating, 2)
        self._data["skills"][marketplace_skill_id]["rating_count"] = new_count

        # Store feedback
        if feedback:
            ratings_list = self._data["ratings"].setdefault(marketplace_skill_id, [])
            ratings_list.append({
                "score": score,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            })

        self._save()
        return True

    def get_ratings(self, marketplace_skill_id: str) -> List[Dict[str, Any]]:
        """Return all ratings/feedback for a marketplace skill."""
        return self._data["ratings"].get(marketplace_skill_id, [])

    # ------------------------------------------------------------------
    # Trending
    # ------------------------------------------------------------------

    def get_trending(self, limit: int = 10) -> List[MarketplaceSkill]:
        """
        Return trending skills based on recent downloads and rating momentum.

        Skills with high download counts and ratings are ranked highest.
        """
        all_skills = list(self._data["skills"].values())

        def trending_score(data: Dict) -> float:
            downloads = data.get("download_count", 0)
            rating = data.get("rating", 0.0)
            rating_count = data.get("rating_count", 0)
            return downloads * 0.6 + rating * rating_count * 0.4

        all_skills.sort(key=trending_score, reverse=True)
        results = []
        for data in all_skills[:limit]:
            ms = MarketplaceSkill.from_dict(data)
            ms.is_trending = True
            results.append(ms)
        return results

    def community_top_10(self) -> List[MarketplaceSkill]:
        """
        Return the community's top 10 skills by weighted score (rating + usage).

        Like OpenClaw's 'hottest skills' leaderboard.
        """
        all_skills = list(self._data["skills"].values())

        def community_score(data: Dict) -> float:
            rating = data.get("rating", 0.0)
            rating_count = data.get("rating_count", 0)
            downloads = data.get("download_count", 0)
            # Bayesian-style weighted rating (min 3 ratings to count fully)
            confidence = min(rating_count / 3.0, 1.0)
            return (rating * confidence + 3.0 * (1.0 - confidence)) + downloads * 0.01

        all_skills.sort(key=community_score, reverse=True)
        results = []
        for data in all_skills[:10]:
            results.append(MarketplaceSkill.from_dict(data))
        return results

    # ------------------------------------------------------------------
    # GitHub Gists sync (optional)
    # ------------------------------------------------------------------

    def sync_to_gist(self, gist_token: str, gist_id: Optional[str] = None) -> str:
        """
        Sync the local marketplace to a GitHub Gist.

        Returns the Gist ID (create new if gist_id is None).
        Note: Requires httpx or requests in environment.
        """
        content = json.dumps(self._data, indent=2, default=str)
        # Stub: real implementation would call GitHub Gists API
        # POST /gists (create) or PATCH /gists/{gist_id} (update)
        return gist_id or "gist_sync_not_implemented"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_marketplace_id_by_skill(self, skill_id: str) -> Optional[str]:
        for mid, data in self._data["skills"].items():
            if data.get("skill", {}).get("id") == skill_id:
                return mid
        return None

    def __len__(self) -> int:
        return len(self._data["skills"])

    def stats(self) -> Dict[str, Any]:
        """Return marketplace statistics."""
        skills = list(self._data["skills"].values())
        total_downloads = sum(d.get("download_count", 0) for d in skills)
        avg_rating = (
            sum(d.get("rating", 0) for d in skills if d.get("rating_count", 0) > 0)
            / max(1, sum(1 for d in skills if d.get("rating_count", 0) > 0))
        )
        return {
            "total_skills": len(skills),
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
        }
