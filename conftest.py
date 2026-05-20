"""
Root conftest.py for SintraPrime-Unified test suite.

Ensures correct import resolution when running pytest from the repo root.
The repo has two 'integrations' directories:
  - integrations/          (top-level: banking, case_law, airtable_crm)
  - core/universe/integrations/  (Discord/Slack bridges)

Both are registered as paths in the 'integrations' namespace package so that
both "from integrations.banking" and "from integrations.discord_handlers"
resolve correctly regardless of test collection order.

Default CI collects Tier 1 lanes only (tests/, backend/, core/tests/).
See docs/ci/dependency-matrix.md for the full lane classification.
"""
import sys
import os
import sysconfig
import types
import glob

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

# ---------------------------------------------------------------------------
# Directories to skip during collection
# ---------------------------------------------------------------------------
# PR #94 baseline exclusions (namespace collisions / non-test dirs):
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
    # -------------------------------------------------------------------
    # Tier 2-5: deferred from default CI (PR #98 / Issue #97)
    # These lanes require optional extras or have unverified transitive
    # imports. Install .[portal], .[predictive], .[integrations], or
    # .[all] and override testpaths to run them.
    # See docs/ci/dependency-matrix.md for details.
    # -------------------------------------------------------------------
    # Tier 2 — Portal (needs .[portal])
    "portal/*",
    # Tier 3 — Predictive (needs .[predictive])
    "predictive/*",
    # Tier 4 — Integrations (needs .[integrations])
    "integrations/*",
    # Tier 5 — Deferred (transitive imports unverified)
    "backend/*",
    "core/*",
    "agents/*",
    "agent_protocol/*",
    "ai_compliance/*",
    "app_builder/*",
    "artifacts/*",
    "channels/*",
    "claude_code/*",
    "cross_platform/*",
    "developer_experience/*",
    "docket/*",
    "emotional_intelligence/*",
    "esignature/*",
    "federal_agencies/*",
    "financial_mastery/*",
    "governance/*",
    "legal_integrations/*",
    "legal_intelligence/*",
    "life_governance/*",
    "local_llm/*",
    "local_models/*",
    "mcp_server/*",
    "memory/*",
    "multimodal/*",
    "observability/*",
    "orchestration/*",
    "packages/*",
    "parl/*",
    "performance/*",
    "phase15/*",
    "phase16/*",
    "phase17/*",
    "phase18/*",
    "phase19/*",
    "rag/*",
    "saas/*",
    "scheduler/*",
    "secure_execution/*",
    "security/*",
    "skill_evolution/*",
    "superintelligence/*",
    "trust_law/*",
    "twin_layer/*",
    "voice/*",
    "workflow_builder/*",
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
    """Re-register integrations namespace package when pytest is configured.
    
    Also cleans stale .coverage* files to prevent DataError when
    branch-mode and statement-mode data coexist from prior runs.
    See docs/ci/sigma-gate-coverage.md.
    """
    # Clean stale coverage data to prevent combine() DataError
    for f in glob.glob(os.path.join(ROOT, ".coverage*")):
        try:
            os.remove(f)
        except OSError:
            pass
    _register_integrations()


def pytest_collectstart(collector):
    """Re-register integrations namespace package before each file is collected."""
    _register_integrations()
