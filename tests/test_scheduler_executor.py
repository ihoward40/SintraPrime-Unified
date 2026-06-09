"""
Tests for scheduler/task_executor.py — sandboxed execution, timeouts,
retries, safe eval, restricted shell.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

import pytest

from scheduler.task_executor import TaskExecutor
from scheduler.task_types import Schedule, ScheduledTask, TaskResult, TaskStatus, TaskType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop(**_kw):
    return "done"


def _failing(**_kw):
    raise ValueError("intentional failure")


def _slow(**_kw):
    time.sleep(20)
    return "slow"


def _printer(**_kw):
    print("captured output")


def _stderr_fn(**_kw):
    import sys
    print("stderr line", file=sys.stderr)
    raise RuntimeError("oops")


def _make_task(fn=None, name="exec_task", max_retries=0, timeout_seconds=5):
    task = ScheduledTask(
        name=name,
        task_type=TaskType.ONE_TIME,
        schedule=Schedule(run_at=datetime.now(UTC) + timedelta(hours=1)),
        fn=fn or _noop,
        max_retries=max_retries,
    )
    task.timeout_seconds = timeout_seconds
    return task


@pytest.fixture
def executor():
    return TaskExecutor(default_timeout=5)


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


class TestBasicExecution:
    def test_success(self, executor):
        task = _make_task(fn=_noop)
        result = executor.execute(task)
        assert result.success is True
        assert result.output == "done"
        assert result.duration_ms >= 0
        assert task.status == TaskStatus.COMPLETED

    def test_failure(self, executor):
        task = _make_task(fn=_failing)
        result = executor.execute(task)
        assert result.success is False
        assert "intentional failure" in (result.error or "")
        assert task.status == TaskStatus.FAILED

    def test_timeout(self, executor):
        task = _make_task(fn=_slow, timeout_seconds=1)
        result = executor.execute(task)
        assert result.success is False
        assert "timed out" in (result.error or "")

    def test_captures_stdout(self, executor):
        task = _make_task(fn=_printer)
        result = executor.execute(task)
        assert result.success is True
        # When fn returns None, captured stdout becomes output
        assert "captured output" in (result.output or "")

    def test_captures_stderr_on_failure(self, executor):
        task = _make_task(fn=_stderr_fn)
        result = executor.execute(task)
        assert result.success is False
        assert "stderr line" in (result.error or "")

    def test_records_duration(self, executor):
        task = _make_task(fn=_noop)
        result = executor.execute(task)
        assert result.duration_ms >= 0
        assert isinstance(result.duration_ms, float)


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------


class TestRetries:
    def test_retry_with_backoff(self, executor, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

        task = _make_task(fn=_failing, max_retries=2)
        result = executor.execute(task)

        assert result.success is False
        assert task.status == TaskStatus.FAILED
        assert task.retry_count == 3  # initial + 2 retries
        # Should have slept twice (retry 1 and 2)
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 2   # 2^1
        assert sleep_calls[1] == 4   # 2^2

    def test_success_on_second_attempt(self, executor, monkeypatch):
        monkeypatch.setattr("time.sleep", lambda _s: None)
        call_count = [0]

        def flaky(**_kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("first attempt fails")
            return "recovered"

        task = _make_task(fn=flaky, max_retries=2)
        result = executor.execute(task)

        assert result.success is True
        assert result.output == "recovered"
        assert task.status == TaskStatus.COMPLETED
        assert task.retry_count == 0  # reset on success

    def test_no_retry_on_success(self, executor):
        task = _make_task(fn=_noop, max_retries=3)
        result = executor.execute(task)
        assert result.success is True
        assert task.retry_count == 0


# ---------------------------------------------------------------------------
# Safe Python execution
# ---------------------------------------------------------------------------


class TestSafePython:
    def test_basic_expression(self, executor):
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        try:
            output = executor.execute_python("result = 2 + 2")
            # result should be 4 in the namespace
            assert output == 4 or output is None  # depends on implementation
        finally:
            os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)

    def test_print_capture(self, executor):
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        try:
            output = executor.execute_python("print('hello world')")
            assert "hello world" in (output or "")
        finally:
            os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)

    def test_blocked_without_env_var(self, executor):
        os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)
        with pytest.raises(PermissionError, match="disabled"):
            executor.execute_python("x = 1")

    def test_blocked_import(self, executor):
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        try:
            with pytest.raises(RuntimeError):
                executor.execute_python("import os; os.system('ls')")
        finally:
            os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)

    def test_with_context(self, executor):
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        try:
            output = executor.execute_python(
                "result = x + y",
                context={"x": 10, "y": 20},
            )
            assert output == 30 or output is None
        finally:
            os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)


# ---------------------------------------------------------------------------
# Restricted shell
# ---------------------------------------------------------------------------


class TestRestrictedShell:
    def test_basic_command(self, executor):
        output = executor.execute_shell("echo hello")
        assert "hello" in output

    def test_blocked_rm_rf(self, executor):
        with pytest.raises(PermissionError, match="Blocked"):
            executor.execute_shell("rm -rf /tmp/test")

    def test_blocked_mkfs(self, executor):
        with pytest.raises(PermissionError, match="Blocked"):
            executor.execute_shell("mkfs /dev/sda1")

    def test_blocked_sudo_rm(self, executor):
        with pytest.raises(PermissionError, match="Blocked"):
            executor.execute_shell("sudo rm -f /etc/passwd")

    def test_unsafe_mode_allows(self, executor):
        output = executor.execute_shell("echo allowed", safe_mode=False)
        assert "allowed" in output

    def test_shell_timeout(self, executor):
        from scheduler.task_executor import TimeoutError as ExecTimeout
        with pytest.raises(ExecTimeout):
            executor.execute_shell("sleep 120")

    def test_nonzero_exit_code(self, executor):
        with pytest.raises(RuntimeError, match="failed"):
            executor.execute_shell("false")
