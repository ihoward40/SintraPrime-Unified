"""
conftest.py for core/universe/tests.

Adds core/universe to sys.path so that 'from integrations.discord_handlers import ...'
resolves to core/universe/integrations/discord_handlers.py rather than the top-level
integrations/ package.
"""
import sys
import os

# Insert core/universe at the FRONT of sys.path so local 'integrations' package
# (core/universe/integrations/) takes precedence for tests in this directory.
UNIVERSE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if UNIVERSE_ROOT not in sys.path:
    sys.path.insert(0, UNIVERSE_ROOT)

# Also ensure that any previously cached 'integrations' module pointing to the
# top-level integrations/ is removed so the local one is picked up.
if "integrations" in sys.modules:
    existing_path = getattr(sys.modules["integrations"], "__path__", [])
    if existing_path and not any(UNIVERSE_ROOT in str(p) for p in existing_path):
        del sys.modules["integrations"]
