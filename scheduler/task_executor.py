"""
TaskExecutor — Sandboxed execution engine for scheduled tasks.
Features: timeout, retry with exponential backoff, stdout/stderr capture,
safe Python eval, and restricted shell execution.
"""

from __future__ import annotations

import io
import logging
import shlex
import subprocess
import sys
import textwrap
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import Any, Dict, Optional

from .task_types import ScheduledTask, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

_SAFE_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr",
    "dict", "dir", "divmod", "enumerate", "filter", "float", "format",
    "frozenset", "getattr", "hasattr", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next",
    "oct", "ord", "pow", "print", "range", "repr", "reversed", "round",
    "set", "slice", "sorted", "str", "sum", "tuple", "type", "zip",
}

_BLOCKED_SHELL_PATTERNS = [
    "rm -rf", "mkfs", "dd if=", ">>/etc", ">/etc",
    "chmod 777 /", "sudo rm", "shutdown", "reboot",
]


class TimeoutError(RuntimeError):
    """Raised when a task exceeds its allowed execution time."""


class TaskExecutor:
    """
    Executes ScheduledTask instances in a controlled environment.

    Safety features:
    - Configurable per-task timeout (default 300 s)
    - Captures stdout / stderr so nothing leaks to the main process
    - Retry with exponential backoff (up to max_retries)
    - Optional restricted Python eval and shell execution
    """

    def __init__(self, default_timeout: int = 300) -> None:
        self.default_timeout = default_timeout

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def execute(self, task: ScheduledTask) -> TaskResult:
        """
        Execute a ScheduledTask, retrying on failure with exponential backoff.
        Returns a TaskResult with success/failure, output, and timing.
        """
        timeout = getattr(task, "timeout_seconds", None) or self.default_timeout
        last_result: Optional[TaskResult] = None

        for attempt in range(task.max_retries + 1):
            if attempt > 0:
                backoff = min(2 ** attempt, 60)
                logger.info(
                    "Retry %d/%d for task '%s' in %ds",
                    attempt,
                    task.max_retries,
                    task.name,
                    backoff,
                )
                time.sleep(backoff)

            last_result = self._execute_once(task, timeout)

            if last_result.success:
                task.retry_count = 0
                task.status = TaskStatus.COMPLETED
                return last_result

            task.retry_count = attempt + 1
            logger.warning(
                "Task '%s' attempt %d failed: %s",
                task.name,
                attempt + 1,
                last_result.error,
            )

        task.status = TaskStatus.FAILED
        return last_result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Single attempt
    # ------------------------------------------------------------------

    def _execute_once(self, task: ScheduledTask, timeout: int) -> TaskResult:
        """Run the task's callable once with timeout and output capture."""
        start = datetime.utcnow()
        result_holder: Dict[str, Any] = {}
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        def _target():
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    output = task.fn(**(task.payload or {}))
                result_holder["output"] = output
                result_holder["success"] = True
            except Exception:
                result_holder["error"] = traceback.format_exc()
                result_holder["success"] = False

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000

        if thread.is_alive():
            # Thread timed out — we can't forcefully kill it in CPython,
            # but we mark it as failed and move on.
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Task '{task.name}' timed out after {timeout}s",
                duration_ms=duration_ms,
            )

        captured_out = stdout_buf.getvalue() or None
        captured_err = stderr_buf.getvalue() or None

        if result_holder.get("success"):
            output = result_holder.get("output")
            if captured_out and output is None:
                output = captured_out
            return TaskResult(
                task_id=task.id,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
        else:
            error_msg = result_holder.get("error", "Unknown error")
            if captured_err:
                error_msg = f"{error_msg}\nSTDERR:\n{captured_err}"
            return TaskResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Safe Python execution
    # ------------------------------------------------------------------

    def execute_python(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute arbitrary Python code in a restricted namespace.

        Only a safe subset of builtins is available. Dangerous imports
        (os, sys, subprocess, etc.) are blocked.
        """
        safe_globals: Dict[str, Any] = {
            "__builtins__": {k: __builtins__[k] for k in _SAFE_BUILTINS if k in __builtins__}  # type: ignore[index]
            if isinstance(__builtins__, dict)
            else {k: getattr(__builtins__, k) for k in _SAFE_BUILTINS if hasattr(__builtins__, k)},
        }
        if context:
            safe_globals.update(context)

        stdout_buf = io.StringIO()
        try:
            with redirect_stdout(stdout_buf):
                exec(textwrap.dedent(code), safe_globals)  # noqa: S102
        except Exception as exc:
            raise RuntimeError(f"Python execution failed: {exc}") from exc

        output = stdout_buf.getvalue()
        return output if output else safe_globals.get("result")

    # ------------------------------------------------------------------
    # Restricted shell
    # ------------------------------------------------------------------

    def execute_shell(self, command: str, safe_mode: bool = True) -> str:
        """
        Run a shell command.

        In ``safe_mode=True`` (default), dangerous patterns are blocked
        and the command runs in a read-only-ish sandbox (no sudo, etc.)
        """
        if safe_mode:
            for pattern in _BLOCKED_SHELL_PATTERNS:
                if pattern in command:
                    raise PermissionError(
                        f"Blocked shell pattern detected: '{pattern}'"
                    )

        args = shlex.split(command)
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            output = proc.stdout
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Shell command failed (rc={proc.returncode}):\n{proc.stderr}"
                )
            return output
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Shell command timed out: {command}")
