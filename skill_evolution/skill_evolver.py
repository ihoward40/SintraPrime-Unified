"""
SkillEvolver – The self-learning heart of the SintraPrime-Unified system.

Inspired by Hermes Agent's procedural memory and autonomous skill evolution.

Capabilities:
- Analyzes execution failures to identify patterns
- Generates improvement suggestions based on error analysis
- Auto-improves skill code by applying patches
- Creates new skills from successful task outcomes
- Merges related skills into composite super-skills
- Generates weekly evolution reports
- Runs a continuous background improvement loop
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .skill_library import SkillLibrary
from .skill_types import (
    FailureAnalysis,
    ImprovementSuggestion,
    Skill,
    SkillCategory,
    SkillImprovement,
    SkillStatus,
)


# ---------------------------------------------------------------------------
# Error pattern registry
# ---------------------------------------------------------------------------

ERROR_PATTERNS: Dict[str, Dict[str, Any]] = {
    "KeyError": {
        "pattern": r"KeyError: '(.+?)'",
        "suggestion": "Add a .get() check or validate the key exists before accessing it.",
        "patch_template": "# TODO: Add key validation for missing key: {match}",
    },
    "AttributeError": {
        "pattern": r"AttributeError: '(.+?)' object has no attribute '(.+?)'",
        "suggestion": "Check if the object is None or the attribute name is correct.",
        "patch_template": "# TODO: Add hasattr() check before accessing attribute",
    },
    "TypeError": {
        "pattern": r"TypeError: (.+)",
        "suggestion": "Ensure correct types are passed; add isinstance() guards.",
        "patch_template": "# TODO: Add type checking/conversion",
    },
    "ValueError": {
        "pattern": r"ValueError: (.+)",
        "suggestion": "Validate input values before processing.",
        "patch_template": "# TODO: Add input validation",
    },
    "IndexError": {
        "pattern": r"IndexError: (.+)",
        "suggestion": "Check list/sequence length before indexing.",
        "patch_template": "# TODO: Guard against empty sequences",
    },
    "TimeoutError": {
        "pattern": r"timed out after (\d+)s",
        "suggestion": "Optimize the skill code or reduce scope of operations.",
        "patch_template": "# TODO: Add caching or reduce computation",
    },
    "ImportError": {
        "pattern": r"(ImportError|ModuleNotFoundError): (.+)",
        "suggestion": "Ensure the required module is importable in the sandbox.",
        "patch_template": "# TODO: Remove or replace unavailable import",
    },
}


# ---------------------------------------------------------------------------
# SkillEvolver
# ---------------------------------------------------------------------------

class SkillEvolver:
    """
    Continuously monitors skill performance and evolves the skill library.

    Acts as the procedural memory and self-improvement engine.
    """

    def __init__(self, library: SkillLibrary, db_path: Optional[Path] = None):
        self.library = library
        db = db_path or library.db_path
        self._db_path = Path(db)
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Failure Analysis
    # ------------------------------------------------------------------

    def analyze_failures(self, skill_id: str, lookback_days: int = 7) -> FailureAnalysis:
        """
        Analyze execution failures for a skill over the past N days.

        Returns structured failure analysis with common error patterns.
        """
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT success, error FROM skill_executions
                   WHERE skill_id = ? AND timestamp >= ?""",
                (skill_id, cutoff),
            ).fetchall()

        total = len(rows)
        failures = [r for r in rows if not r["success"]]
        failed_count = len(failures)
        failure_rate = failed_count / total if total > 0 else 0.0

        # Extract error messages
        errors = [r["error"] or "" for r in failures if r["error"]]
        error_counter: Counter = Counter()
        pattern_counter: Counter = Counter()

        for err in errors:
            # Get first line (exception type)
            first_line = err.strip().splitlines()[-1] if err.strip() else "Unknown"
            error_counter[first_line[:120]] += 1

            # Pattern matching
            for pname, pdata in ERROR_PATTERNS.items():
                if re.search(pdata["pattern"], err):
                    pattern_counter[pname] += 1

        common_errors = [e for e, _ in error_counter.most_common(5)]
        failure_patterns = [p for p, _ in pattern_counter.most_common(5)]

        return FailureAnalysis(
            skill_id=skill_id,
            total_executions=total,
            failed_executions=failed_count,
            failure_rate=failure_rate,
            common_errors=common_errors,
            failure_patterns=failure_patterns,
            lookback_days=lookback_days,
        )

    # ------------------------------------------------------------------
    # Improvement Suggestions
    # ------------------------------------------------------------------

    def suggest_improvements(self, skill_id: str) -> List[ImprovementSuggestion]:
        """
        Generate improvement suggestions for a skill based on failure analysis.

        Uses pattern matching (no LLM required).
        """
        analysis = self.analyze_failures(skill_id)
        suggestions: List[ImprovementSuggestion] = []

        if analysis.failure_rate < 0.05:
            return []   # Skill is performing well

        skill = self.library.get(skill_id)
        if not skill:
            return []

        for pattern_name in analysis.failure_patterns:
            pdata = ERROR_PATTERNS.get(pattern_name, {})
            if not pdata:
                continue

            # Confidence is proportional to how often this pattern appears
            confidence = min(0.9, 0.3 + analysis.failure_rate)
            patch = pdata.get("patch_template", "").format(match=pattern_name)

            suggestions.append(ImprovementSuggestion(
                skill_id=skill_id,
                suggestion=pdata.get("suggestion", "Review code logic."),
                confidence=confidence,
                failure_pattern=pattern_name,
                proposed_code_patch=patch,
            ))

        # Generic suggestion if failure rate is high
        if analysis.failure_rate > 0.5 and not suggestions:
            suggestions.append(ImprovementSuggestion(
                skill_id=skill_id,
                suggestion="High failure rate detected. Consider adding try/except and input validation.",
                confidence=0.6,
                failure_pattern="generic_high_failure",
                proposed_code_patch="# TODO: Wrap core logic in try/except",
            ))

        return suggestions

    # ------------------------------------------------------------------
    # Auto-Improve
    # ------------------------------------------------------------------

    def auto_improve(self, skill_id: str) -> Optional[SkillImprovement]:
        """
        Automatically rewrite skill code to address detected failures.

        Applies the highest-confidence improvement suggestion.
        Returns a SkillImprovement record, or None if no improvement needed.
        """
        suggestions = self.suggest_improvements(skill_id)
        if not suggestions:
            return None

        skill = self.library.get(skill_id)
        if not skill:
            return None

        # Pick highest confidence suggestion
        best = max(suggestions, key=lambda s: s.confidence)

        # Apply defensive coding patterns
        improved_code = self._apply_improvement(skill.code, best)

        old_version = skill.version
        updated = self.library.update(
            skill_id,
            improved_code,
            f"Auto-improved: {best.suggestion} (pattern: {best.failure_pattern})",
            performance_delta=best.confidence * 0.2,  # Estimated improvement
        )

        if not updated:
            return None

        return SkillImprovement(
            skill_id=skill_id,
            old_version=old_version,
            new_version=updated.version,
            change_description=f"Auto-improved: {best.suggestion}",
            performance_delta=best.confidence * 0.2,
        )

    def _apply_improvement(self, code: str, suggestion: ImprovementSuggestion) -> str:
        """Apply improvement patch to code."""
        header = f"""# Auto-improved by SkillEvolver (pattern: {suggestion.failure_pattern})
# Improvement: {suggestion.suggestion}

"""
        # For common error patterns, add try/except wrapper if not present
        if suggestion.failure_pattern in ("KeyError", "AttributeError", "TypeError", "ValueError", "IndexError"):
            if "try:" not in code and "except" not in code:
                # Wrap the core logic
                indented = "\n".join("    " + line for line in code.splitlines())
                code = f"try:\n{indented}\nexcept ({suggestion.failure_pattern}) as _e:\n    result = None\n    print(f'Skill error: {{_e}}')"

        return header + code

    # ------------------------------------------------------------------
    # Create Skill from Task
    # ------------------------------------------------------------------

    def create_from_task(
        self,
        task_description: str,
        task_outcome: str,
        code_used: str,
        category: SkillCategory = SkillCategory.AUTOMATION,
        author: str = "auto",
    ) -> Skill:
        """
        Auto-create a new skill from a successful task execution.

        Hermes-inspired procedural memory: when a task succeeds, the approach
        is captured as a reusable skill.
        """
        # Derive a name from the task description
        name_words = re.sub(r"[^a-zA-Z0-9 ]", "", task_description.lower()).split()[:4]
        skill_name = "_".join(name_words) or f"auto_skill_{uuid.uuid4().hex[:6]}"

        # Extract tags from description
        tags = list(set(name_words[:5]))

        skill = Skill(
            name=skill_name,
            description=f"Auto-created from task: {task_description[:200]}. Outcome: {task_outcome[:200]}",
            category=category,
            code=code_used,
            parameters={},
            author=author,
            tags=tags,
            status=SkillStatus.EXPERIMENTAL,
        )

        return self.library.register(skill)

    # ------------------------------------------------------------------
    # Merge Skills
    # ------------------------------------------------------------------

    def merge_skills(self, skill_ids: List[str], merged_name: str = None) -> Optional[Skill]:
        """
        Combine related skills into a composite skill.

        The merged skill runs each sub-skill in sequence.
        """
        skills = [self.library.get(sid) for sid in skill_ids]
        skills = [s for s in skills if s is not None]

        if len(skills) < 2:
            return None

        name = merged_name or "merged_" + "_".join(s.name[:10] for s in skills[:3])

        # Build merged code: run each skill's code with output passing
        code_parts = []
        for i, skill in enumerate(skills):
            code_parts.append(f"# === Sub-skill: {skill.name} (v{skill.version}) ===")
            code_parts.append(f"_skill_{i}_result = None")
            code_parts.append(f"try:")
            for line in skill.code.splitlines():
                code_parts.append(f"    {line}")
            code_parts.append(f"    _skill_{i}_result = result")
            code_parts.append(f"except Exception as _e:")
            code_parts.append(f"    print(f'Sub-skill {skill.name} failed: {{_e}}')")
            code_parts.append("")

        # Collect results
        collect = "result = {" + ", ".join(f'"{s.name}": _skill_{i}_result' for i, s in enumerate(skills)) + "}"
        code_parts.append(collect)

        merged_code = "\n".join(code_parts)

        # Combine tags and categories
        all_tags = list(set(tag for s in skills for tag in s.tags))
        # Use category of first skill
        category = skills[0].category

        merged_skill = Skill(
            name=name,
            description=f"Merged composite of: {', '.join(s.name for s in skills)}",
            category=category,
            code=merged_code,
            tags=all_tags,
            author="merger",
        )

        return self.library.register(merged_skill)

    # ------------------------------------------------------------------
    # Evolution Report
    # ------------------------------------------------------------------

    def evolution_report(self) -> Dict[str, Any]:
        """
        Generate a weekly skill evolution summary.

        Reports new skills, improved skills, top performers, and struggling skills.
        """
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()

        with self._get_conn() as conn:
            # New skills this week
            try:
                new_skills_count = conn.execute(
                    "SELECT COUNT(*) as c FROM skills WHERE created_at >= ?", (cutoff,)
                ).fetchone()["c"]
            except Exception:
                new_skills_count = 0

            # Improvements this week
            try:
                improvements_count = conn.execute(
                    "SELECT COUNT(*) as c FROM skill_history WHERE created_at >= ?", (cutoff,)
                ).fetchone()["c"]
            except Exception:
                improvements_count = 0

            # Execution stats
            try:
                exec_stats = conn.execute(
                    """SELECT COUNT(*) as total,
                              SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes
                       FROM skill_executions WHERE timestamp >= ?""",
                    (cutoff,),
                ).fetchone()
                total_execs = exec_stats["total"] or 0
                success_execs = exec_stats["successes"] or 0
            except Exception:
                total_execs = success_execs = 0

        top_skills = self.library.get_top_skills(5)
        all_skills = self.library.list_all()

        struggling = [s for s in all_skills if s.usage_count >= 3 and s.success_rate < 0.7]

        return {
            "report_period": "last_7_days",
            "generated_at": datetime.utcnow().isoformat(),
            "new_skills": new_skills_count,
            "improvements_applied": improvements_count,
            "total_executions": total_execs,
            "successful_executions": success_execs,
            "overall_success_rate": (success_execs / total_execs) if total_execs > 0 else 1.0,
            "total_skills": len(all_skills),
            "top_performers": [{"name": s.name, "success_rate": s.success_rate, "uses": s.usage_count} for s in top_skills],
            "struggling_skills": [{"name": s.name, "success_rate": s.success_rate, "uses": s.usage_count} for s in struggling[:5]],
        }

    # ------------------------------------------------------------------
    # Watch and Evolve
    # ------------------------------------------------------------------

    def watch_and_evolve(self, interval_hours: float = 24) -> None:
        """
        Start a background thread that continuously monitors and improves skills.

        Runs every `interval_hours` hours. Stops when stop_watch() is called.
        """
        if self._watcher_thread and self._watcher_thread.is_alive():
            return  # Already running

        self._stop_event.clear()

        def _loop():
            while not self._stop_event.wait(interval_hours * 3600):
                self._evolve_all()

        self._watcher_thread = threading.Thread(target=_loop, daemon=True, name="SkillEvolverWatcher")
        self._watcher_thread.start()

    def stop_watch(self) -> None:
        """Stop the background evolution watcher."""
        self._stop_event.set()

    def _evolve_all(self) -> None:
        """Run auto-improvement on all skills that need it."""
        skills = self.library.list_all()
        for skill in skills:
            if skill.is_builtin:
                continue
            analysis = self.analyze_failures(skill.id)
            if analysis.failure_rate > 0.2 and analysis.total_executions >= 5:
                self.auto_improve(skill.id)
