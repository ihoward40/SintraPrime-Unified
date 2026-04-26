"""
SkillRunner – Safe, sandboxed skill execution engine.

Provides:
- Restricted exec() sandbox (no filesystem/network/os access by default)
- Configurable timeout enforcement via threading
- Input/output validation
- Execution chaining (pipeline)
- Dry-run mode
- Full execution logging

Inspired by Hermes Agent's safe tool execution and CrewAI's role isolation.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from .skill_library import SkillLibrary
from .skill_types import Skill, SkillExecution


# ---------------------------------------------------------------------------
# Sandbox configuration
# ---------------------------------------------------------------------------

# Builtins allowed inside the sandbox
_ALLOWED_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr",
    "dict", "dir", "divmod", "enumerate", "filter", "float", "format",
    "frozenset", "getattr", "hasattr", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next",
    "oct", "ord", "pow", "print", "range", "repr", "reversed", "round",
    "set", "setattr", "slice", "sorted", "str", "sum", "super", "tuple",
    "type", "vars", "zip",
}

_FORBIDDEN_PATTERNS = [
    "__import__", "eval(", "compile(", "exec(",
    "open(", "os.system", "subprocess", "socket",
    "shutil", "sys.exit",
]


def _build_sandbox_globals(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a restricted globals dict for sandboxed execution."""
    import builtins
    safe_builtins = {k: getattr(builtins, k) for k in _ALLOWED_BUILTINS if hasattr(builtins, k)}
    return {
        "__builtins__": safe_builtins,
        "params": params,
        "result": None,
        "json": json,
        "datetime": datetime,
    }


def _check_code_safety(code: str) -> List[str]:
    """Static safety scan of skill code. Returns list of violation messages."""
    violations = []
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in code:
            violations.append(f"Forbidden pattern detected: '{pattern}'")
    return violations


# ---------------------------------------------------------------------------
# Execution timeout helper
# ---------------------------------------------------------------------------

class _TimedExec:
    """Runs callable in a daemon thread with timeout enforcement."""

    def __init__(self, fn, timeout_s: float):
        self._fn = fn
        self._timeout = timeout_s
        self._result = None
        self._error: Optional[Exception] = None
        self._done = threading.Event()

    def _run(self):
        try:
            self._result = self._fn()
        except Exception as exc:
            self._error = exc
        finally:
            self._done.set()

    def execute(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        finished = self._done.wait(self._timeout)
        if not finished:
            raise TimeoutError(f"Skill execution timed out after {self._timeout}s")
        if self._error:
            raise self._error
        return self._result


# ---------------------------------------------------------------------------
# SkillRunner
# ---------------------------------------------------------------------------

class SkillRunner:
    """
    Executes skills safely with sandboxing, timeout, and logging.
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT = 300.0

    def __init__(self, library: SkillLibrary, db_path=None, timeout: float = None):
        self.library = library
        self.timeout = min(timeout or self.DEFAULT_TIMEOUT, self.MAX_TIMEOUT)
        self._exec_log: List[SkillExecution] = []

        # Optionally persist executions to same DB
        import sqlite3
        from pathlib import Path
        db = db_path or library.db_path
        self._db_path = Path(db)
        self._init_exec_db()

    def _init_exec_db(self):
        import sqlite3
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS skill_executions (
                    id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    input_params TEXT,
                    output TEXT,
                    success INTEGER,
                    duration_ms REAL,
                    error TEXT,
                    feedback_score REAL,
                    timestamp TEXT
                );
            """)

    def _log_execution(self, ex: SkillExecution):
        import sqlite3
        d = ex.to_dict()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO skill_executions
                   (id, skill_id, input_params, output, success, duration_ms,
                    error, feedback_score, timestamp)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (d["id"], d["skill_id"], d["input_params"], d["output"],
                 1 if d["success"] else 0, d["duration_ms"],
                 d["error"], d["feedback_score"], d["timestamp"]),
            )
        self._exec_log.append(ex)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        skill_id: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> SkillExecution:
        """
        Execute a skill by ID with the given parameters.

        Runs code inside a restricted sandbox with timeout enforcement.
        Records the execution to the database.
        """
        skill = self.library.get(skill_id)
        if not skill:
            return self._fail_exec(skill_id, params, "Skill not found")

        # Validate params
        param_errors = self._validate_params(skill, params)
        if param_errors:
            return self._fail_exec(skill_id, params, f"Param validation failed: {'; '.join(param_errors)}")

        # Safety check
        violations = _check_code_safety(skill.code)
        if violations:
            return self._fail_exec(skill_id, params, f"Safety check failed: {'; '.join(violations)}")

        effective_timeout = min(timeout or self.timeout, self.MAX_TIMEOUT)
        sandbox = _build_sandbox_globals(params)

        def _do_exec():
            exec(compile(skill.code, f"<skill:{skill.name}>", "exec"), sandbox)
            return sandbox.get("result")

        start = time.perf_counter()
        try:
            timed = _TimedExec(_do_exec, effective_timeout)
            output = timed.execute()
            duration_ms = (time.perf_counter() - start) * 1000
            ex = SkillExecution(
                skill_id=skill_id,
                input_params=params,
                output=output,
                success=True,
                duration_ms=duration_ms,
            )
        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start) * 1000
            ex = SkillExecution(
                skill_id=skill_id,
                input_params=params,
                output=None,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            ex = SkillExecution(
                skill_id=skill_id,
                input_params=params,
                output=None,
                success=False,
                duration_ms=duration_ms,
                error=traceback.format_exc(),
            )

        self._log_execution(ex)
        self.library.update_stats(skill_id, ex.success)
        return ex

    def execute_chain(
        self,
        skill_ids: List[str],
        params: Dict[str, Any],
    ) -> List[SkillExecution]:
        """
        Execute a pipeline of skills sequentially.

        The output of each skill is merged into params for the next step
        under the key 'previous_output'.
        """
        results: List[SkillExecution] = []
        current_params = dict(params)

        for skill_id in skill_ids:
            ex = self.execute(skill_id, current_params)
            results.append(ex)
            if not ex.success:
                # Stop chain on failure
                break
            # Pass output forward
            current_params["previous_output"] = ex.output

        return results

    def dry_run(self, skill_id: str, params: Dict[str, Any]) -> str:
        """
        Explain what the skill would do without executing it.

        Returns a human-readable description.
        """
        skill = self.library.get(skill_id)
        if not skill:
            return f"[DRY RUN] Skill '{skill_id}' not found."

        param_errors = self._validate_params(skill, params)
        violations = _check_code_safety(skill.code)

        lines = [
            f"[DRY RUN] Skill: {skill.name} (v{skill.version})",
            f"  Category : {skill.category.value if hasattr(skill.category, 'value') else skill.category}",
            f"  Author   : {skill.author}",
            f"  Desc     : {skill.description}",
            f"  Params   : {json.dumps(params, default=str)}",
            f"  Timeout  : {self.timeout}s",
        ]

        if param_errors:
            lines.append(f"  ⚠ Param errors: {'; '.join(param_errors)}")
        if violations:
            lines.append(f"  ✗ Safety violations: {'; '.join(violations)}")
        else:
            lines.append("  ✓ Safety check passed")

        lines += [
            "",
            "--- Code preview (first 20 lines) ---",
            *skill.code.splitlines()[:20],
        ]
        return "\n".join(lines)

    def add_feedback(self, execution_id: str, score: float) -> bool:
        """Record user feedback (1-5) on a completed execution."""
        import sqlite3
        if not (1.0 <= score <= 5.0):
            return False
        with sqlite3.connect(str(self._db_path)) as conn:
            result = conn.execute(
                "UPDATE skill_executions SET feedback_score = ? WHERE id = ?",
                (score, execution_id),
            )
        return result.rowcount > 0

    def get_executions(self, skill_id: str, limit: int = 100) -> List[Dict]:
        """Retrieve recent executions for a skill from the DB."""
        import sqlite3
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM skill_executions
                   WHERE skill_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (skill_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_params(self, skill: Skill, params: Dict[str, Any]) -> List[str]:
        errors = []
        for pname, meta in (skill.parameters or {}).items():
            if isinstance(meta, dict):
                if meta.get("required", False) and pname not in params:
                    errors.append(f"Missing required param: {pname}")
        return errors

    def _fail_exec(self, skill_id: str, params: Dict[str, Any], error: str) -> SkillExecution:
        ex = SkillExecution(
            skill_id=skill_id,
            input_params=params,
            output=None,
            success=False,
            duration_ms=0,
            error=error,
        )
        self._log_execution(ex)
        return ex
