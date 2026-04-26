"""
SkillLibrary – Core skill storage, retrieval, and versioning.

Uses SQLite as the backend for persistence. Supports fuzzy search,
category filtering, versioned updates, soft deletion, and import/export.

Inspired by Hermes Agent's procedural memory and OpenClaw's skills registry.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

from .skill_types import Skill, SkillCategory, SkillStatus


# ---------------------------------------------------------------------------
# Default DB path
# ---------------------------------------------------------------------------
DEFAULT_DB_PATH = Path(__file__).parent / "data" / "skills.db"


# ---------------------------------------------------------------------------
# Built-in skill stubs (loaded at library initialisation)
# ---------------------------------------------------------------------------

_BUILTIN_SKILLS: List[Dict[str, Any]] = [
    {
        "id": "builtin_legal_research",
        "name": "legal_research",
        "description": "Searches case law, statutes, and regulations by keyword and jurisdiction.",
        "category": "legal",
        "code": "from skill_evolution.builtin_skills.legal_research import LegalResearchSkill\nskill = LegalResearchSkill()\nresult = skill.execute(**params)",
        "parameters": json.dumps({"query": {"type": "str", "required": True}, "jurisdiction": {"type": "str", "required": False, "default": "federal"}}),
        "tags": json.dumps(["legal", "research", "case-law"]),
        "is_builtin": 1,
        "author": "system",
    },
    {
        "id": "builtin_doc_draft",
        "name": "doc_draft",
        "description": "Generates legal documents from templates given a context dictionary.",
        "category": "legal",
        "code": "from skill_evolution.builtin_skills.document_drafter import DocumentDrafterSkill\nskill = DocumentDrafterSkill()\nresult = skill.execute(**params)",
        "parameters": json.dumps({"template_name": {"type": "str", "required": True}, "context": {"type": "dict", "required": True}}),
        "tags": json.dumps(["legal", "document", "drafting"]),
        "is_builtin": 1,
        "author": "system",
    },
    {
        "id": "builtin_case_summary",
        "name": "case_summary",
        "description": "Produces a structured summary of a legal case given its text.",
        "category": "legal",
        "code": "from skill_evolution.builtin_skills.legal_research import LegalResearchSkill\nskill = LegalResearchSkill()\nresult = skill.summarize(**params)",
        "parameters": json.dumps({"case_text": {"type": "str", "required": True}}),
        "tags": json.dumps(["legal", "summary", "nlp"]),
        "is_builtin": 1,
        "author": "system",
    },
    {
        "id": "builtin_financial_calc",
        "name": "financial_calc",
        "description": "Performs budget analysis, credit scoring, and financial ratio calculations.",
        "category": "financial",
        "code": "from skill_evolution.builtin_skills.financial_analyzer import FinancialAnalyzerSkill\nskill = FinancialAnalyzerSkill()\nresult = skill.execute(**params)",
        "parameters": json.dumps({"data": {"type": "dict", "required": True}, "analysis_type": {"type": "str", "required": True}}),
        "tags": json.dumps(["financial", "analysis", "budget"]),
        "is_builtin": 1,
        "author": "system",
    },
    {
        "id": "builtin_court_search",
        "name": "court_search",
        "description": "Monitors court docket entries for specified case numbers or parties.",
        "category": "legal",
        "code": "from skill_evolution.builtin_skills.court_monitor import CourtMonitorSkill\nskill = CourtMonitorSkill()\nresult = skill.execute(**params)",
        "parameters": json.dumps({"case_number": {"type": "str", "required": False}, "party_name": {"type": "str", "required": False}, "court": {"type": "str", "required": True}}),
        "tags": json.dumps(["legal", "court", "docket"]),
        "is_builtin": 1,
        "author": "system",
    },
]


# ---------------------------------------------------------------------------
# SkillLibrary
# ---------------------------------------------------------------------------

class SkillLibrary:
    """
    Central registry for all skills in the SintraPrime-Unified ecosystem.

    Thread-safe SQLite-backed storage with fuzzy search, versioning,
    and import/export capabilities.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        self._load_builtins()

    # ------------------------------------------------------------------
    # DB setup
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    code TEXT NOT NULL,
                    parameters TEXT DEFAULT '{}',
                    success_rate REAL DEFAULT 1.0,
                    usage_count INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    created_at TEXT,
                    last_updated TEXT,
                    author TEXT DEFAULT 'system',
                    tags TEXT DEFAULT '[]',
                    is_builtin INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS skill_history (
                    id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    old_version INTEGER,
                    new_version INTEGER,
                    old_code TEXT,
                    new_code TEXT,
                    change_description TEXT,
                    performance_delta REAL DEFAULT 0.0,
                    created_at TEXT,
                    FOREIGN KEY (skill_id) REFERENCES skills(id)
                );
            """)

    def _load_builtins(self) -> None:
        """Pre-load built-in skills if they don't exist yet."""
        now = datetime.utcnow().isoformat()
        with self._lock, self._get_conn() as conn:
            for stub in _BUILTIN_SKILLS:
                existing = conn.execute("SELECT id FROM skills WHERE id = ?", (stub["id"],)).fetchone()
                if not existing:
                    conn.execute(
                        """INSERT INTO skills
                           (id, name, description, category, code, parameters,
                            success_rate, usage_count, version, created_at,
                            last_updated, author, tags, is_builtin, status)
                           VALUES (?,?,?,?,?,?,1.0,0,1,?,?,?,?,?,?)""",
                        (
                            stub["id"], stub["name"], stub["description"],
                            stub["category"], stub["code"], stub["parameters"],
                            now, now, stub["author"], stub["tags"],
                            stub["is_builtin"], "active",
                        ),
                    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(self, skill: Skill) -> Skill:
        """Add a new skill to the library. Raises ValueError if ID already exists."""
        now = datetime.utcnow().isoformat()
        with self._lock, self._get_conn() as conn:
            existing = conn.execute("SELECT id FROM skills WHERE id = ?", (skill.id,)).fetchone()
            if existing:
                raise ValueError(f"Skill with ID '{skill.id}' already exists. Use update() to modify.")
            conn.execute(
                """INSERT INTO skills
                   (id, name, description, category, code, parameters,
                    success_rate, usage_count, version, created_at,
                    last_updated, author, tags, is_builtin, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    skill.id, skill.name, skill.description,
                    skill.category.value if isinstance(skill.category, SkillCategory) else skill.category,
                    skill.code, json.dumps(skill.parameters),
                    skill.success_rate, skill.usage_count, skill.version,
                    now, now, skill.author, json.dumps(skill.tags),
                    1 if skill.is_builtin else 0,
                    skill.status.value if isinstance(skill.status, SkillStatus) else skill.status,
                ),
            )
        skill.created_at = datetime.fromisoformat(now)
        skill.last_updated = datetime.fromisoformat(now)
        return skill

    def get(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID. Returns None if not found."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not row:
                return None
            return self._row_to_skill(row)

    def get_by_name(self, name: str) -> Optional[Skill]:
        """Retrieve first skill matching the given name."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT * FROM skills WHERE name = ? AND status != 'deprecated'", (name,)).fetchone()
            if not row:
                return None
            return self._row_to_skill(row)

    def search(self, query: str, category: Optional[SkillCategory] = None) -> List[Skill]:
        """
        Fuzzy search across name, description, and tags.

        Returns ranked list of active skills matching the query.
        """
        query_lower = query.lower()
        with self._lock, self._get_conn() as conn:
            if category:
                cat_val = category.value if isinstance(category, SkillCategory) else category
                rows = conn.execute(
                    "SELECT * FROM skills WHERE status != 'deprecated' AND category = ?", (cat_val,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM skills WHERE status != 'deprecated'").fetchall()

        skills = [self._row_to_skill(r) for r in rows]

        def score(skill: Skill) -> float:
            text = f"{skill.name} {skill.description} {' '.join(skill.tags)}".lower()
            # exact substring
            if query_lower in text:
                return 2.0
            # fuzzy ratio
            return SequenceMatcher(None, query_lower, text[:200]).ratio()

        scored = sorted(skills, key=score, reverse=True)
        return [s for s in scored if score(s) > 0.3]

    def list_all(self, include_deprecated: bool = False) -> List[Skill]:
        """List all skills, optionally including deprecated ones."""
        with self._lock, self._get_conn() as conn:
            if include_deprecated:
                rows = conn.execute("SELECT * FROM skills ORDER BY usage_count DESC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM skills WHERE status != 'deprecated' ORDER BY usage_count DESC").fetchall()
        return [self._row_to_skill(r) for r in rows]

    def list_by_category(self, category: SkillCategory) -> List[Skill]:
        """List all active skills in a given category."""
        cat_val = category.value if isinstance(category, SkillCategory) else category
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM skills WHERE category = ? AND status != 'deprecated' ORDER BY success_rate DESC",
                (cat_val,),
            ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Return top skills by success rate (min 5 uses to qualify)."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM skills
                   WHERE status != 'deprecated'
                   ORDER BY success_rate DESC, usage_count DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def update(
        self,
        skill_id: str,
        new_code: str,
        change_description: str,
        performance_delta: float = 0.0,
    ) -> Optional[Skill]:
        """
        Versioned update of a skill's code.

        Saves the old version to history before applying the new code.
        """
        import uuid as _uuid
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not row:
                return None
            old_version = row["version"]
            new_version = old_version + 1
            now = datetime.utcnow().isoformat()
            # Archive old version
            conn.execute(
                """INSERT INTO skill_history
                   (id, skill_id, old_version, new_version, old_code, new_code,
                    change_description, performance_delta, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    str(_uuid.uuid4()), skill_id, old_version, new_version,
                    row["code"], new_code, change_description, performance_delta, now,
                ),
            )
            conn.execute(
                "UPDATE skills SET code = ?, version = ?, last_updated = ? WHERE id = ?",
                (new_code, new_version, now, skill_id),
            )
        return self.get(skill_id)

    def update_stats(self, skill_id: str, success: bool) -> None:
        """Update usage count and success rate after execution."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT usage_count, success_rate FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if not row:
                return
            n = row["usage_count"]
            old_rate = row["success_rate"]
            new_count = n + 1
            # Rolling average
            new_rate = ((old_rate * n) + (1.0 if success else 0.0)) / new_count
            conn.execute(
                "UPDATE skills SET usage_count = ?, success_rate = ? WHERE id = ?",
                (new_count, new_rate, skill_id),
            )

    def deprecate(self, skill_id: str) -> bool:
        """Soft-delete a skill (marks as deprecated, not removed)."""
        with self._lock, self._get_conn() as conn:
            result = conn.execute(
                "UPDATE skills SET status = 'deprecated' WHERE id = ?", (skill_id,)
            )
        return result.rowcount > 0

    def delete(self, skill_id: str) -> bool:
        """Hard-delete a skill. Use deprecate() to preserve history."""
        with self._lock, self._get_conn() as conn:
            result = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Export a skill as a portable JSON-serializable dictionary."""
        skill = self.get(skill_id)
        if not skill:
            return None
        return skill.to_dict()

    def import_skill(self, skill_dict: Dict[str, Any], overwrite: bool = False) -> Skill:
        """Import a skill from a dictionary. Optionally overwrite existing."""
        skill = Skill.from_dict(skill_dict)
        existing = self.get(skill.id)
        if existing:
            if overwrite:
                self.delete(skill.id)
            else:
                raise ValueError(f"Skill '{skill.id}' already exists. Use overwrite=True to replace.")
        return self.register(skill)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, skill_id: str) -> List[Dict[str, Any]]:
        """Return version history for a skill."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM skill_history WHERE skill_id = ? ORDER BY new_version DESC",
                (skill_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        d = dict(row)
        d["tags"] = json.loads(d["tags"]) if isinstance(d["tags"], str) else d["tags"]
        d["parameters"] = json.loads(d["parameters"]) if isinstance(d["parameters"], str) else d["parameters"]
        d["is_builtin"] = bool(d["is_builtin"])
        d["category"] = SkillCategory(d["category"])
        d["status"] = SkillStatus(d.get("status", "active"))
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        d["last_updated"] = datetime.fromisoformat(d["last_updated"])
        return Skill(**d)

    def __len__(self) -> int:
        with self._lock, self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM skills WHERE status != 'deprecated'").fetchone()[0]
