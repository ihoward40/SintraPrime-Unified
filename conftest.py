"""Root conftest.py — pytest collection configuration.

Default CI collects only Tier 1 lanes (tests/, backend/, core/tests/).
See docs/ci/dependency-matrix.md for the full lane classification.
"""
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# stdlib path ordering — ensure stdlib modules resolve before local shadows
# ---------------------------------------------------------------------------
stdlib_path = str(Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}")
if stdlib_path in sys.path:
    sys.path.remove(stdlib_path)
    sys.path.insert(0, stdlib_path)

# ---------------------------------------------------------------------------
# namespace package registration — allow pytest to collect from sub-packages
# ---------------------------------------------------------------------------
for pkg in ("core", "portal", "backend"):
    pkg_dir = Path(__file__).parent / pkg
    if pkg_dir.is_dir() and str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir.parent))

# ---------------------------------------------------------------------------
# Collection scope — only Tier 1 lanes in default CI
# All other lanes are excluded to prevent collection errors from
# missing optional dependencies. Install extras to run them:
#   pip install .[portal]      → portal tests
#   pip install .[predictive]  → predictive tests
#   pip install .[integrations] → integration tests
#   pip install .[all]         → everything
# ---------------------------------------------------------------------------
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
    # Tier 2-5: deferred lanes (require optional extras)
    "portal/*",
    "packages/*",
    "agents/*",
    "integrations/*",
    "docket/*",
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
    "parl/*",
    "performance/*",
    "predictive/*",
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
    "phase15/*",
    "phase16/*",
    "phase17/*",
    "phase18/*",
    "phase19/*",
    "agent_protocol/*",
    "ai_compliance/*",
    "app_builder/*",
    "artifacts/*",
    "channels/*",
    "claude_code/*",
    "cross_platform/*",
    "developer_experience/*",
    "emotional_intelligence/*",
]


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "integration: marks integration tests requiring external services")
