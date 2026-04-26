"""
Root conftest.py for SintraPrime-Unified test suite.

Ensures correct import resolution when running pytest from the repo root.
The repo has two 'integrations' directories:
  - integrations/          (top-level: banking, case_law, airtable_crm)
  - core/universe/integrations/  (Discord/Slack bridges)

Both are registered as paths in the 'integrations' namespace package so that
both "from integrations.banking" and "from integrations.discord_handlers"
resolve correctly regardless of test collection order.
"""
import sys
import os
import sysconfig
import types

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

# Both integrations directories that need to be in the namespace package
_TOP_INTEGRATIONS = os.path.join(ROOT, "integrations")
_UNIVERSE_INTEGRATIONS = os.path.join(ROOT, "core", "universe", "integrations")
_BOTH_PATHS = [_TOP_INTEGRATIONS, _UNIVERSE_INTEGRATIONS]


def _register_integrations():
    """
    Register 'integrations' as a namespace package covering both:
      - ROOT/integrations/          (banking, case_law, airtable_crm)
      - ROOT/core/universe/integrations/  (discord_handlers, discord_embeds, etc.)

    This is called at conftest load time AND before each file is collected,
    to prevent pytest's import machinery from replacing our registration
    with a single-path namespace package.
    """
    current = sys.modules.get("integrations")
    current_paths = list(getattr(current, "__path__", []))

    # Check if both paths are already registered
    if current is not None and all(p in current_paths for p in _BOTH_PATHS):
        return  # Already correctly registered

    # Create or update the namespace package with both paths
    if current is None:
        pkg = types.ModuleType("integrations")
    else:
        pkg = current

    pkg.__path__ = _BOTH_PATHS[:]
    pkg.__package__ = "integrations"
    pkg.__file__ = os.path.join(_TOP_INTEGRATIONS, "__init__.py")
    pkg.__spec__ = None
    sys.modules["integrations"] = pkg


# Register immediately at conftest load time
_register_integrations()


def pytest_configure(config):
    """Re-register integrations namespace package when pytest is configured."""
    _register_integrations()


def pytest_collectstart(collector):
    """Re-register integrations namespace package before each file is collected."""
    _register_integrations()
