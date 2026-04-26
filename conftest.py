"""
Root conftest.py for SintraPrime-Unified test suite.

Ensures correct import resolution when running pytest from the repo root.
The repo has two 'integrations' directories:
  - integrations/          (top-level: banking, case_law)
  - core/universe/integrations/  (Discord/Slack bridges)

This conftest ensures the repo root is on sys.path so that top-level
packages resolve correctly, and configures collection to avoid conflicts.
"""
import sys
import os
import sysconfig

# Ensure the repo root is on sys.path, but AFTER stdlib paths to prevent
# the local 'operator/' directory from shadowing Python's built-in operator module.
ROOT = os.path.dirname(os.path.abspath(__file__))

# Get stdlib paths to ensure they come first
stdlib_path = sysconfig.get_paths()["stdlib"]
stdlib_platstdlib = sysconfig.get_paths()["platstdlib"]

# Remove ROOT from sys.path if already there, then re-insert after stdlib
if ROOT in sys.path:
    sys.path.remove(ROOT)

# Find the best insertion point: after all stdlib paths
insert_pos = 0
for i, p in enumerate(sys.path):
    if p.startswith(stdlib_path) or p.startswith(stdlib_platstdlib) or p == '':
        insert_pos = i + 1

sys.path.insert(insert_pos, ROOT)

# Directories to skip during collection (avoid namespace collisions)
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
]

# Fix: The core/universe/integrations package creates a namespace conflict with
# the top-level integrations/ package when pytest collects from root.
# We ensure the top-level integrations package is importable by explicitly
# registering it before any sub-package with the same name.
import importlib
import types

_integrations_path = os.path.join(ROOT, "integrations")
if _integrations_path not in sys.path:
    # Register the top-level integrations as a proper package
    if "integrations" not in sys.modules:
        _pkg = types.ModuleType("integrations")
        _pkg.__path__ = [_integrations_path]
        _pkg.__package__ = "integrations"
        sys.modules["integrations"] = _pkg
