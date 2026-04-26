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

# The root conftest.py now registers 'integrations' as a namespace package
# covering BOTH ROOT/integrations/ and ROOT/core/universe/integrations/.
# No need to delete sys.modules["integrations"] here — the namespace package
# already includes the universe integrations path.
