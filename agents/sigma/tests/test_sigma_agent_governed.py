"""
Regression tests for SigmaAgent's governed inference routing path.

These tests verify that the AI Code Review section of Sigma's gate report
delegates to GovernedInferenceRouter while preserving the report shape. They
use the deterministic MockProvider so no OpenAI API key or network access is
needed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from agents.sigma.sigma_agent import SigmaAgent
from governed_inference import GovernedInferenceRouter, InferencePolicy
from governed_inference.contracts import InferenceError, PerRequestPolicy, ProviderErrorKind
from governed_inference.providers import MockProvider


class TestSigmaAgentGovernedRouting(unittest.TestCase):
    """Verify generate_gate_report AI review routes through GovernedInferenceRouter."""

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

    def _base_results(self, pr_diff: str | None = None) -> dict:
        return {
            "overall_passed": True,
            "total": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "coverage_pct": 85.0,
            "coverage_passed": True,
            "security_findings": 0,
            "critical_findings": 0,
            "security_passed": True,
            "type_errors": 0,
            "type_check_passed": True,
            "blocking_reasons": [],
            "pr_diff": pr_diff,
        }

    def test_governed_router_generates_ai_review(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = SigmaAgent()
        agent._governed_router = self._build_router(provider)

        results = self._base_results(pr_diff="diff content")
        report = agent.generate_gate_report(results)

        self.assertIn("## AI Code Review", report)
        self.assertIn("mock-local", report)
        self.assertEqual(provider.invoke_count, 1)

    def test_no_pr_diff_skips_ai_review(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = SigmaAgent()
        agent._governed_router = self._build_router(provider)

        results = self._base_results(pr_diff=None)
        report = agent.generate_gate_report(results)

        self.assertNotIn("## AI Code Review", report)
        self.assertEqual(provider.invoke_count, 0)

    def test_governed_router_error_omits_ai_review_section(self):
        provider = MockProvider(
            name="mock-local",
            model="mock-model",
            fail_times=5,
            error_kind=ProviderErrorKind.TRANSIENT,
        )
        agent = SigmaAgent()
        agent._governed_router = self._build_router(provider)

        results = self._base_results(pr_diff="diff content")
        report = agent.generate_gate_report(results)

        self.assertNotIn("## AI Code Review", report)

    def test_lazy_router_build(self):
        agent = SigmaAgent()
        self.assertIsNone(agent._governed_router)
        provider = MockProvider(name="mock-local", model="mock-model")
        agent._governed_router = self._build_router(provider)

        results = self._base_results(pr_diff="diff content")
        agent.generate_gate_report(results)

        self.assertEqual(provider.invoke_count, 1)

    def test_report_shape_preserved(self):
        provider = MockProvider(name="mock-local", model="mock-model")
        agent = SigmaAgent()
        agent._governed_router = self._build_router(provider)

        results = self._base_results(pr_diff="diff content")
        report = agent.generate_gate_report(results)

        self.assertIn("# Sigma Gate Report", report)
        self.assertIn("## Test Results", report)
        self.assertIn("## Coverage", report)
        self.assertIn("## Security", report)
        self.assertIn("## Type Checking", report)


if __name__ == "__main__":
    unittest.main()
