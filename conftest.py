"""
Root conftest.py — SintraPrime-Unified
Collection exclusions live here (pytest.ini uses norecursedirs for directory-level).
"""
import sys
import os

# Prevent operator/ from shadowing the Python stdlib operator module
collect_ignore_glob = [
    "apps/*",
    "deployment/*",
    "web/*",
    "mobile/*",
    "models/*",
    "shared/*",
    "docs/*",
    ".github/*",
    "node_modules/*",
    "operator/*",
    "phase19/revenue_smoke_test/run_smoke_test.py",
]

# Ensure repo root is on sys.path for relative imports in tests
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
