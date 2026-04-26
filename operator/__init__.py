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

# Re-export everything from the stdlib operator module to avoid shadowing it.
# This allows 'from operator import or_, add, mul' etc. to work correctly.
import importlib as _importlib
import sys as _sys

# Load the real stdlib operator module
_stdlib_operator = _importlib.import_module("_operator")

# Also get the full stdlib operator via a workaround
# (the stdlib operator wraps _operator)
import _operator as _op_module

# Re-export all stdlib operator functions
from _operator import (
    abs, add, and_, attrgetter, concat, contains, countOf, delitem,
    eq, floordiv, ge, getitem, gt, iadd, iand, iconcat, ifloordiv,
    ilshift, imatmul, imod, imul, index, indexOf, inv, invert, ior,
    ipow, irshift, is_, is_not, isub, itemgetter, itruediv, ixor,
    le, length_hint, lshift, lt, matmul, methodcaller, mod, mul, ne,
    neg, not_, or_, pos, pow, rshift, setitem, sub, truediv, truth,
    xor,
)

__version__ = "1.0.0"
__author__ = "SintraPrime Team"

__all__ = [
    "OperatorAgent",
    "BrowserController",
    "TaskPlanner",
    "WebResearcher",
    "HumanInLoopCheckpoint",
    # stdlib re-exports
    "abs", "add", "and_", "attrgetter", "concat", "contains",
    "countOf", "delitem", "eq", "floordiv", "ge", "getitem", "gt",
    "iadd", "iand", "iconcat", "ifloordiv", "ilshift", "imatmul",
    "imod", "imul", "index", "indexOf", "inv", "invert", "ior",
    "ipow", "irshift", "is_", "is_not", "isub", "itemgetter",
    "itruediv", "ixor", "le", "length_hint", "lshift", "lt",
    "matmul", "methodcaller", "mod", "mul", "ne", "neg", "not_",
    "or_", "pos", "pow", "rshift", "setitem", "sub", "truediv",
    "truth", "xor",
]


def __getattr__(name):
    """Lazy imports for SintraPrime operator classes."""
    if name == "OperatorAgent":
        from .operator_agent import OperatorAgent
        return OperatorAgent
    elif name == "BrowserController":
        from .browser_controller import BrowserController
        return BrowserController
    elif name == "TaskPlanner":
        from .task_planner import TaskPlanner
        return TaskPlanner
    elif name == "WebResearcher":
        from .web_researcher import WebResearcher
        return WebResearcher
    elif name == "HumanInLoopCheckpoint":
        from .operator_agent import HumanInLoopCheckpoint
        return HumanInLoopCheckpoint
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
