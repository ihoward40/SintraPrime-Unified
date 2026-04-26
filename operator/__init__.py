"""
SintraPrime Autonomous Operator Mode
=====================================
Inspired by:
  - OpenAI Operator (browser control agent)
  - Manus AI (autonomous web task execution)
  - Claude Computer Use (desktop/browser automation)
  - GPT-5.5 Spud (plan → execute → verify → iterate loop)

Quick Start:
    from operator import OperatorAgent
    agent = OperatorAgent()
    result = agent.execute("Research the top 10 trust attorneys in California")
    print(result.summary)
"""

from .operator_agent import OperatorAgent
from .browser_controller import BrowserController
from .task_planner import TaskPlanner
from .web_researcher import WebResearcher
from .operator_agent import HumanInLoopCheckpoint

__all__ = [
    "OperatorAgent",
    "BrowserController",
    "TaskPlanner",
    "WebResearcher",
    "HumanInLoopCheckpoint",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Team"
