"""P0-003: Tests verifying exec() is gated behind NOVA_ALLOW_DYNAMIC_EXEC.

These tests confirm that:
1. NovaAgent.execute_action() raises PermissionError for unknown actions when
   NOVA_ALLOW_DYNAMIC_EXEC is not 'true', even when an LLM key is present.
2. TaskExecutor.execute_python() raises PermissionError when
   NOVA_ALLOW_DYNAMIC_EXEC is not set or is not 'true'.
3. TaskExecutor.execute_python() succeeds when NOVA_ALLOW_DYNAMIC_EXEC='true'.
4. TaskExecutor.execute_shell() uses shell=False (list args, no injection).
5. Gate is case-insensitive ('TRUE', 'True', 'true' all work).
6. Known registered actions are never affected by the exec gate.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.nova.nova_agent import NovaAgent
from scheduler.task_executor import TaskExecutor


def _make_mock_openai_response(code: str) -> MagicMock:
    """Build a mock openai response object returning the given code string."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = code
    return mock_response


HANDLER_CODE = "def dynamic_handler(params):\n    return {'status': 'ok'}\n"


class TestNovaExecGate(unittest.TestCase):
    """Tests for the NOVA_ALLOW_DYNAMIC_EXEC gate in nova_agent.py.

    Strategy: openai is imported inline inside execute_action(), so we patch
    sys.modules['openai'] to intercept the import and return a mock client
    that provides a valid LLM response — allowing us to reach the exec() gate.
    """

    def setUp(self):
        os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)
        os.environ.pop("OPENAI_API_KEY", None)
        self.agent = NovaAgent(user_id="test-user")

    def tearDown(self):
        os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)
        os.environ.pop("OPENAI_API_KEY", None)

    def _patched_openai(self):
        """Return a mock openai module whose OpenAI() client returns HANDLER_CODE."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_openai_response(
            HANDLER_CODE
        )
        mock_openai.OpenAI.return_value = mock_client
        return mock_openai

    def _run_with_mocked_llm(self, allow_exec_value: str):
        """Run execute_action for an unknown action with a mocked LLM and given env value."""
        os.environ["OPENAI_API_KEY"] = "fake-key"
        if allow_exec_value is None:
            os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)
        else:
            os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = allow_exec_value
        with patch.dict("sys.modules", {"openai": self._patched_openai()}):
            return self.agent.execute_action("UNKNOWN_ACTION_XYZ", {"param": "value"})

    def test_dynamic_exec_blocked_by_default(self):
        """exec() must be blocked when NOVA_ALLOW_DYNAMIC_EXEC is not set."""
        with self.assertRaises(PermissionError) as ctx:
            self._run_with_mocked_llm(None)
        self.assertIn("NOVA_ALLOW_DYNAMIC_EXEC", str(ctx.exception))

    def test_dynamic_exec_blocked_when_false(self):
        """exec() must be blocked when NOVA_ALLOW_DYNAMIC_EXEC=false."""
        with self.assertRaises(PermissionError):
            self._run_with_mocked_llm("false")

    def test_dynamic_exec_blocked_when_zero(self):
        """exec() must be blocked when NOVA_ALLOW_DYNAMIC_EXEC=0."""
        with self.assertRaises(PermissionError):
            self._run_with_mocked_llm("0")

    def test_dynamic_exec_blocked_when_empty(self):
        """exec() must be blocked when NOVA_ALLOW_DYNAMIC_EXEC is empty string."""
        with self.assertRaises(PermissionError):
            self._run_with_mocked_llm("")

    def test_dynamic_exec_permitted_when_true(self):
        """exec() must be permitted when NOVA_ALLOW_DYNAMIC_EXEC=true."""
        try:
            self._run_with_mocked_llm("true")
        except PermissionError:
            self.fail("PermissionError raised even though NOVA_ALLOW_DYNAMIC_EXEC=true")

    def test_dynamic_exec_gate_case_insensitive_TRUE(self):
        """Gate must accept uppercase TRUE."""
        try:
            self._run_with_mocked_llm("TRUE")
        except PermissionError:
            self.fail("PermissionError raised for NOVA_ALLOW_DYNAMIC_EXEC=TRUE")

    def test_dynamic_exec_gate_case_insensitive_Title(self):
        """Gate must accept mixed-case True."""
        try:
            self._run_with_mocked_llm("True")
        except PermissionError:
            self.fail("PermissionError raised for NOVA_ALLOW_DYNAMIC_EXEC=True")

    def test_known_actions_never_hit_exec_gate(self):
        """Registered actions (SEND_DISPUTE_LETTER etc.) must never raise PermissionError."""
        # No NOVA_ALLOW_DYNAMIC_EXEC set — known actions must work fine
        try:
            self.agent.execute_action(
                "SEND_DISPUTE_LETTER",
                {
                    "recipient_name": "Test",
                    "recipient_address": "123 Main St",
                    "dispute_reason": "Test",
                    "account_number": "ACC-001",
                },
            )
        except PermissionError:
            self.fail("PermissionError raised for a known registered action")

    def test_gate_re_evaluated_per_call(self):
        """Gate must re-evaluate on each call (not cached)."""
        # First call: blocked
        with self.assertRaises(PermissionError):
            self._run_with_mocked_llm("false")
        # Second call: permitted
        try:
            self._run_with_mocked_llm("true")
        except PermissionError:
            self.fail("Gate appears to be cached — second call still blocked")


class TestTaskExecutorExecGate(unittest.TestCase):
    """Tests for the NOVA_ALLOW_DYNAMIC_EXEC gate in task_executor.py."""

    def setUp(self):
        os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)
        self.executor = TaskExecutor()

    def tearDown(self):
        os.environ.pop("NOVA_ALLOW_DYNAMIC_EXEC", None)

    def test_execute_python_blocked_by_default(self):
        """execute_python() must raise PermissionError when flag is not set."""
        with self.assertRaises(PermissionError) as ctx:
            self.executor.execute_python("x = 1 + 1")
        self.assertIn("NOVA_ALLOW_DYNAMIC_EXEC", str(ctx.exception))

    def test_execute_python_blocked_when_false(self):
        """execute_python() must raise PermissionError when flag is 'false'."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "false"
        with self.assertRaises(PermissionError):
            self.executor.execute_python("x = 1 + 1")

    def test_execute_python_blocked_when_zero(self):
        """execute_python() must raise PermissionError when flag is '0'."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "0"
        with self.assertRaises(PermissionError):
            self.executor.execute_python("x = 1 + 1")

    def test_execute_python_blocked_when_empty(self):
        """execute_python() must raise PermissionError when flag is empty string."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = ""
        with self.assertRaises(PermissionError):
            self.executor.execute_python("x = 1 + 1")

    def test_execute_python_permitted_when_true(self):
        """execute_python() must succeed when NOVA_ALLOW_DYNAMIC_EXEC=true."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        result = self.executor.execute_python("result = 2 + 2")
        self.assertEqual(result, 4)

    def test_execute_python_permitted_case_insensitive_TRUE(self):
        """execute_python() must accept 'TRUE'."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "TRUE"
        result = self.executor.execute_python("result = 10")
        self.assertEqual(result, 10)

    def test_execute_python_permitted_case_insensitive_Title(self):
        """execute_python() must accept 'True'."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "True"
        result = self.executor.execute_python("result = 7")
        self.assertEqual(result, 7)

    def test_execute_python_blocked_then_permitted(self):
        """Gate must re-evaluate on each call (not cached)."""
        with self.assertRaises(PermissionError):
            self.executor.execute_python("result = 1")
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        result = self.executor.execute_python("result = 99")
        self.assertEqual(result, 99)

    def test_execute_python_safe_builtins_still_enforced(self):
        """Even with flag enabled, dangerous imports must still be blocked."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        with self.assertRaises(RuntimeError):
            self.executor.execute_python("import os; result = os.getcwd()")

    def test_execute_python_output_capture(self):
        """execute_python() must capture stdout when flag is enabled."""
        os.environ["NOVA_ALLOW_DYNAMIC_EXEC"] = "true"
        result = self.executor.execute_python("print('hello world')")
        self.assertIn("hello world", result)

    def test_execute_python_error_message_mentions_flag(self):
        """PermissionError message must mention NOVA_ALLOW_DYNAMIC_EXEC."""
        with self.assertRaises(PermissionError) as ctx:
            self.executor.execute_python("result = 1")
        self.assertIn("NOVA_ALLOW_DYNAMIC_EXEC", str(ctx.exception))


class TestTaskExecutorShellSafety(unittest.TestCase):
    """Tests verifying execute_shell() uses shell=False (no injection)."""

    def setUp(self):
        self.executor = TaskExecutor()

    def test_execute_shell_uses_list_args(self):
        """subprocess.run must be called with a list, not a string (shell=False)."""
        with patch("scheduler.task_executor.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "ok\n"
            mock_run.return_value = mock_proc
            self.executor.execute_shell("echo hello")
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            self.assertIsInstance(cmd, list)
            self.assertEqual(cmd, ["echo", "hello"])

    def test_execute_shell_blocks_rm_rf(self):
        """execute_shell() must block rm -rf."""
        with self.assertRaises(PermissionError):
            self.executor.execute_shell("rm -rf /tmp/test")

    def test_execute_shell_blocks_sudo_rm(self):
        """execute_shell() must block sudo rm."""
        with self.assertRaises(PermissionError):
            self.executor.execute_shell("sudo rm /etc/passwd")

    def test_execute_shell_blocks_mkfs(self):
        """execute_shell() must block mkfs."""
        with self.assertRaises(PermissionError):
            self.executor.execute_shell("mkfs.ext4 /dev/sda1")

    def test_execute_shell_blocks_shutdown(self):
        """execute_shell() must block shutdown."""
        with self.assertRaises(PermissionError):
            self.executor.execute_shell("shutdown -h now")

    def test_execute_shell_safe_mode_false_bypasses_pattern_check(self):
        """safe_mode=False must skip pattern check (for trusted internal use)."""
        with patch("scheduler.task_executor.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "ok\n"
            mock_run.return_value = mock_proc
            result = self.executor.execute_shell("rm -rf /tmp/safe_test", safe_mode=False)
            self.assertEqual(result, "ok\n")

    def test_execute_shell_no_shell_true_kwarg(self):
        """subprocess.run must NOT be called with shell=True."""
        with patch("scheduler.task_executor.subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "ok\n"
            mock_run.return_value = mock_proc
            self.executor.execute_shell("echo test")
            call_kwargs = mock_run.call_args[1]
            if "shell" in call_kwargs:
                self.assertFalse(call_kwargs["shell"])

    def test_execute_shell_timeout_raises(self):
        """execute_shell() must raise TimeoutError on subprocess timeout."""
        import subprocess as sp
        from scheduler.task_executor import TimeoutError as ExecTimeout
        with patch("scheduler.task_executor.subprocess.run") as mock_run:
            mock_run.side_effect = sp.TimeoutExpired(cmd="echo", timeout=60)
            with self.assertRaises(ExecTimeout):
                self.executor.execute_shell("echo slow")


if __name__ == "__main__":
    unittest.main()
