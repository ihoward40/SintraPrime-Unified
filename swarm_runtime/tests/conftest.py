"""Conftest for swarm_runtime acceptance tests.

Ensures repository root is on sys.path so that `swarm_runtime` is importable
regardless of invocation method (pytest, python -m, or direct script execution).
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
