"""
Regression tests for ZeroAgent's governed inference routing path.

These tests verify that the Zero Agent's LLM-based patch generation path
delegates to GovernedInferenceRouter while preserving the rule-based fallback
and patch lifecycle. They use the deterministic MockProvider so no OpenAI API
key or network access is needed.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from agents.zero.zero_agent import (
    ZeroAgent,
    TestFailure,
    Patch,
)
from governed_inference import GovernedInferenceRouter, InferencePolicy
from governed_inference.contracts import InferenceError, PerRequestPolicy, ProviderErrorKind
from governed_inference.providers import MockProvider


class TestZeroAgentGovernedRouting(unittest.TestCase):
    """Verify generate_fix_patch routes through GovernedInferenceRouter."""

    def _build_router(self, provider: MockProvider) -> GovernedInferenceRouter:
        per_request = PerRequestPolicy(
            max_input_tokens=12000,
            max_output_tokens=4096,
            timeout_seconds=60,
            max_attempts=3,
        )
        policy = InferencePolicy(
            per_request=per_request,
            paid_models_allowed=True,
            paid_escalation_requires_explicit_approval=False,
        )
        return GovernedInferenceRouter([provider], policy=policy)

    def _write_file(self, tmp_path: Path, content: str) -> str:
        fpath = tmp_path / "broken.py"
        fpath.write_text(content, encoding="utf-8")
        return str(fpath)

    def test_governed_router_generates_patch(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = ZeroAgent()
        agent._governed_router = self._build_router(provider)

        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fpath = self._write_file(Path(td), "x = 1\n")
            failure = TestFailure(
                test_id="test_broken.py::test_x",
                file_path=fpath,
                error_type="AssertionError",
                error_message="assert 1 == 2",
                traceback="",
            )
            patch = agent.generate_fix_patch(failure)

        self.assertIsNotNone(patch)
        self.assertEqual(provider.invoke_count, 1)
        self.assertIn("LLM-generated fix", patch.description)

    def test_governed_router_error_falls_back_to_rule_based(self):
        provider = MockProvider(
            name="mock-local",
            model="mock-model",
            fail_times=5,
            error_kind=ProviderErrorKind.TRANSIENT,
        )
        agent = ZeroAgent()
        agent._governed_router = self._build_router(provider)

        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fpath = self._write_file(Path(td), "x = 1\n")
            failure = TestFailure(
                test_id="test_broken.py::test_x",
                file_path=fpath,
                error_type="AssertionError",
                error_message="fixture 'missing' not found",
                traceback="",
            )
            patch = agent.generate_fix_patch(failure)

        self.assertIsNotNone(patch)
        self.assertIn("fixture", patch.patched_content)

    def test_no_key_returns_none_for_clean_file(self):
        agent = ZeroAgent()
        # Ensure no governed router is injected and no API key is present
        self.assertIsNone(agent._governed_router)

        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fpath = self._write_file(Path(td), "x = 1\n")
            failure = TestFailure(
                test_id="test_broken.py::test_x",
                file_path=fpath,
                error_type="AssertionError",
                error_message="assert 1 == 2",
                traceback="",
            )
            patch = agent.generate_fix_patch(failure)

        self.assertIsNone(patch)

    def test_missing_file_returns_none(self):
        agent = ZeroAgent()
        failure = TestFailure(
            test_id="test_broken.py::test_x",
            file_path="/nonexistent/file.py",
            error_type="FileNotFoundError",
            error_message="not found",
            traceback="",
        )
        self.assertIsNone(agent.generate_fix_patch(failure))

    def test_lazy_router_build(self):
        agent = ZeroAgent()
        self.assertIsNone(agent._governed_router)
        provider = MockProvider(name="mock-local", model="mock-model")
        agent._governed_router = self._build_router(provider)

        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fpath = self._write_file(Path(td), "x = 1\n")
            failure = TestFailure(
                test_id="test_broken.py::test_x",
                file_path=fpath,
                error_type="AssertionError",
                error_message="assert 1 == 2",
                traceback="",
            )
            agent.generate_fix_patch(failure)

        self.assertEqual(provider.invoke_count, 1)


if __name__ == "__main__":
    unittest.main()
