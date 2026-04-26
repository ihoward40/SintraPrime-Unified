"""
User Profile Manager — Persistent, growing personal AI profile.
Inspired by Pi AI's personal context that deepens with each interaction.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory_types import UserProfile


class UserProfileManager:
    """
    Manages persistent user profiles stored as JSON files.
    Learns communication style, expertise, and preferences from conversations.
    """

    def __init__(self, profiles_dir: Optional[str] = None):
        if profiles_dir is None:
            profiles_dir = str(Path.home() / ".sintra" / "profiles")
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, UserProfile] = {}

    def _profile_path(self, user_id: str) -> Path:
        # Sanitize user_id to safe filename
        safe_id = re.sub(r"[^\w\-]", "_", user_id)
        return self.profiles_dir / f"{safe_id}.json"

    def _load(self, user_id: str) -> Optional[UserProfile]:
        """Load profile from disk, updating cache."""
        path = self._profile_path(user_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = UserProfile.from_dict(data)
        self._cache[user_id] = profile
        return profile

    def _save(self, profile: UserProfile) -> None:
        """Persist profile to disk."""
        path = self._profile_path(profile.user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        self._cache[profile.user_id] = profile

    # ------------------------------------------------------------------ #
    #  CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def create_profile(self, user_id: str, name: str, **kwargs) -> UserProfile:
        """Create a new user profile."""
        existing = self.get_profile(user_id)
        if existing:
            return existing
        profile = UserProfile(
            user_id=user_id,
            name=name,
            **{k: v for k, v in kwargs.items() if hasattr(UserProfile, k)},
        )
        self._save(profile)
        return profile

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get a profile by user_id, checking cache first."""
        if user_id in self._cache:
            return self._cache[user_id]
        return self._load(user_id)

    def get_or_create(self, user_id: str, name: str = "User") -> UserProfile:
        """Get existing profile or create a new one."""
        profile = self.get_profile(user_id)
        if profile:
            return profile
        return self.create_profile(user_id, name)

    def update_preference(self, user_id: str, key: str, value: Any) -> UserProfile:
        """Update a single preference key."""
        profile = self.get_or_create(user_id)
        profile.preferences[key] = value
        profile.updated_at = datetime.utcnow()
        self._save(profile)
        return profile

    def delete_profile(self, user_id: str) -> bool:
        """Delete a user profile (GDPR)."""
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            self._cache.pop(user_id, None)
            return True
        return False

    def list_profiles(self) -> List[str]:
        """Return all user IDs with existing profiles."""
        return [p.stem for p in self.profiles_dir.glob("*.json")]

    # ------------------------------------------------------------------ #
    #  Learning from conversations                                          #
    # ------------------------------------------------------------------ #

    def learn_from_conversation(
        self, user_id: str, messages: List[Dict[str, str]]
    ) -> UserProfile:
        """Auto-extract preferences and style from a conversation."""
        profile = self.get_or_create(user_id)

        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
        all_user_text = " ".join(user_messages)

        # Detect communication style
        new_style = self._infer_communication_style(all_user_text)
        if new_style != "neutral":
            profile.communication_style = new_style

        # Extract topics of interest
        topics = self._extract_topics(all_user_text)
        for t in topics:
            if t not in profile.topics_of_interest:
                profile.topics_of_interest.append(t)
        profile.topics_of_interest = profile.topics_of_interest[:50]  # cap

        # Detect expertise signals
        domains = self._infer_expertise(all_user_text)
        profile.expertise_level.update(domains)

        # Increment interaction count
        profile.interaction_count += 1
        profile.updated_at = datetime.utcnow()

        self._save(profile)
        return profile

    def _infer_communication_style(self, text: str) -> str:
        """Classify communication style from user message patterns."""
        lower = text.lower()
        formal_signals = ["therefore", "moreover", "pursuant", "accordingly", "herein", "shall"]
        casual_signals = ["hey", "yeah", "nah", "lol", "gonna", "wanna", "kinda", "btw"]
        technical_signals = ["function", "api", "algorithm", "database", "latency", "stack", "deploy"]

        formal_count = sum(1 for s in formal_signals if s in lower)
        casual_count = sum(1 for s in casual_signals if s in lower)
        tech_count = sum(1 for s in technical_signals if s in lower)

        scores = {"formal": formal_count, "casual": casual_count, "technical": tech_count}
        max_style = max(scores, key=lambda k: scores[k])
        if scores[max_style] == 0:
            return "neutral"
        return max_style

    def _extract_topics(self, text: str) -> List[str]:
        """Extract high-frequency meaningful words as topics."""
        words = re.findall(r"[a-zA-Z]{5,}", text.lower())
        stopwords = {
            "their", "there", "these", "those", "about", "which", "where",
            "would", "could", "should", "might", "really", "going", "think",
            "being", "having", "after", "before", "under", "again", "against",
        }
        filtered = [w for w in words if w not in stopwords]
        freq: Dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:15]
        return [w for w, _ in top]

    def _infer_expertise(self, text: str) -> Dict[str, str]:
        """Estimate domain expertise from vocabulary usage."""
        lower = text.lower()
        domains: Dict[str, str] = {}

        legal_advanced = ["mens rea", "habeas corpus", "amicus curiae", "certiorari", "subpoena duces tecum"]
        legal_intermediate = ["plaintiff", "defendant", "deposition", "discovery", "injunction"]
        if any(t in lower for t in legal_advanced):
            domains["legal"] = "expert"
        elif any(t in lower for t in legal_intermediate):
            domains["legal"] = "intermediate"

        tech_advanced = ["kubernetes", "microservices", "concurrency", "recursion", "polynomial", "neural"]
        tech_intermediate = ["api", "database", "function", "server", "deploy", "debug"]
        if any(t in lower for t in tech_advanced):
            domains["technical"] = "expert"
        elif any(t in lower for t in tech_intermediate):
            domains["technical"] = "intermediate"

        return domains

    # ------------------------------------------------------------------ #
    #  Accessors                                                            #
    # ------------------------------------------------------------------ #

    def get_communication_style(self, user_id: str) -> str:
        """Return the user's communication style."""
        profile = self.get_profile(user_id)
        return profile.communication_style if profile else "neutral"

    def get_expertise_level(self, user_id: str, domain: str) -> str:
        """Return expertise level for a given domain."""
        profile = self.get_profile(user_id)
        if not profile:
            return "unknown"
        return profile.expertise_level.get(domain, "novice")

    def summarize_profile(self, user_id: str) -> str:
        """Generate a human-readable profile summary."""
        profile = self.get_profile(user_id)
        if not profile:
            return f"No profile found for user '{user_id}'."

        lines = [
            f"👤 {profile.name} (ID: {profile.user_id})",
            f"💬 Communication style: {profile.communication_style}",
            f"🌐 Language: {profile.language} | Timezone: {profile.timezone}",
            f"🔄 Interactions: {profile.interaction_count}",
        ]
        if profile.expertise_level:
            exp_str = ", ".join(f"{d}: {l}" for d, l in profile.expertise_level.items())
            lines.append(f"🎓 Expertise: {exp_str}")
        if profile.topics_of_interest:
            lines.append(f"📚 Topics of interest: {', '.join(profile.topics_of_interest[:5])}")
        if profile.goals:
            lines.append(f"🎯 Goals: {', '.join(profile.goals[:3])}")
        if profile.legal_matters:
            lines.append(f"⚖️  Legal matters: {len(profile.legal_matters)} tracked")
        if profile.preferences:
            lines.append(f"⚙️  Preferences: {len(profile.preferences)} stored")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Legal matter tracking                                                #
    # ------------------------------------------------------------------ #

    def track_legal_matter(
        self, user_id: str, matter_id: str, details: Dict[str, Any]
    ) -> UserProfile:
        """Record or update a legal matter for a user."""
        profile = self.get_or_create(user_id)
        details["updated_at"] = datetime.utcnow().isoformat()
        profile.legal_matters[matter_id] = details
        profile.updated_at = datetime.utcnow()
        self._save(profile)
        return profile

    def get_legal_matter(self, user_id: str, matter_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific legal matter."""
        profile = self.get_profile(user_id)
        if not profile:
            return None
        return profile.legal_matters.get(matter_id)

    def add_goal(self, user_id: str, goal: str) -> UserProfile:
        """Add a goal to the user profile."""
        profile = self.get_or_create(user_id)
        if goal not in profile.goals:
            profile.goals.append(goal)
        profile.updated_at = datetime.utcnow()
        self._save(profile)
        return profile

    def add_trusted_contact(
        self, user_id: str, contact: Dict[str, str]
    ) -> UserProfile:
        """Add a trusted contact entry."""
        profile = self.get_or_create(user_id)
        # Avoid exact duplicates
        if contact not in profile.trusted_contacts:
            profile.trusted_contacts.append(contact)
        profile.updated_at = datetime.utcnow()
        self._save(profile)
        return profile

    def export_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Export profile data as a dict."""
        profile = self.get_profile(user_id)
        return profile.to_dict() if profile else None
