"""
CI-visible regression tests for ZeroAgent's governed inference routing path.

The concrete test cases live in agents/zero/tests/test_zero_agent_governed.py;
this wrapper re-exports them so the default pytest testpaths pick them up.
"""

from agents.zero.tests.test_zero_agent_governed import (
    TestZeroAgentGovernedRouting,
)

__all__ = ["TestZeroAgentGovernedRouting"]
