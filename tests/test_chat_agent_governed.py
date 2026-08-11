"""
CI-visible regression tests for ChatAgent's governed inference routing path.

The concrete test cases live in agents/chat/tests/test_chat_agent_governed.py;
this wrapper re-exports them so the default pytest testpaths pick them up.
"""

from agents.chat.tests.test_chat_agent_governed import (
    TestChatAgentGovernedRouting,
    TestChatAgentStreamingGovernedRouting,
)

__all__ = ["TestChatAgentGovernedRouting", "TestChatAgentStreamingGovernedRouting"]
