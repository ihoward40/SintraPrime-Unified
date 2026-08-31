"""
CI-visible regression tests for SigmaAgent's governed inference routing path.

The concrete test cases live in agents/sigma/tests/test_sigma_agent_governed.py;
this wrapper re-exports them so the default pytest testpaths pick them up.
"""

from agents.sigma.tests.test_sigma_agent_governed import (
    TestSigmaAgentGovernedRouting,
)

__all__ = ["TestSigmaAgentGovernedRouting"]
