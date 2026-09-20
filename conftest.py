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

import contextlib
import glob
import os
import sys
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
    if p.startswith(stdlib_path) or p.startswith(stdlib_platstdlib) or p == "":
        insert_pos = i + 1

sys.path.insert(insert_pos, ROOT)

# ---------------------------------------------------------------------------
# Directories to skip during collection
# ---------------------------------------------------------------------------
# Tier-2/3/4 lanes (portal, backend, core, agents, ...) are EXCLUDED from the
# default lane by design (PR #98 / Issue #97). Wave 2B (SP-CONVERGE-001) makes
# the exclusion intentional and visible: setting
#   SINTRAPRIME_TEST_LANES="default,portal"     (comma-separated)
# re-enables the listed lane directories at collection time. scripts/certify.py
# sets this per target; CI sets it for the dedicated portal lane. Nothing is
# silently ignored anymore — either a lane is explicitly included, or its
# exclusion is documented right here.
import os as _os  # noqa: E402  (conftest: env gate must follow sys.path setup)

_ACTIVE_LANES = {lane.strip().lower() for lane in _os.environ.get("SINTRAPRIME_TEST_LANES", "default").split(",") if lane.strip()}

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
    # Tier 2 — Portal (needs .[portal]) — included only via SINTRAPRIME_TEST_LANES
    *(set() if "portal" in _ACTIVE_LANES else ["portal/*"]),
    # Tier 3 — Predictive (needs .[predictive])
    *(set() if ("predictive" in _ACTIVE_LANES or "release" in _ACTIVE_LANES) else ["predictive/*"]),
    # Tier 4 — Integrations (needs .[integrations])
    *(set() if ("integrations" in _ACTIVE_LANES or "release" in _ACTIVE_LANES) else ["integrations/*"]),
    # Tier 5 — Deferred (transitive imports unverified). SUPPRESSED when the
    # 'release' lane is active so the RC release-test universe (G0-R3,
    # SP-RC-RUNTIME-COLLECTION-VERIFY-001) can collect these modules.
    *(set() if "release" in _ACTIVE_LANES else [
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
        "integrations/*",
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
        "voice/__init__.py",
        "voice/legal_nlp.py",
        "voice/persona.py",
        "voice/response_formatter.py",
        "voice/speech_processor.py",
        "voice/voice_api.py",
        "voice/voice_engine.py",
        "voice/wake_word.py",
        "voice/tests/*",
        "workflow_builder/*",
    ]),

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
        with contextlib.suppress(OSError):
            os.remove(f)
    _register_integrations()


def pytest_collectstart(collector):
    """Re-register integrations namespace package before each file is collected."""
    _register_integrations()


# ---------------------------------------------------------------------------
# G0-R4.1 (SP-RC-EXECUTION-SAFETY-UNBLOCK-001): certification network guard.
# Default-deny outbound network for certification execution. Activated ONLY when
# SINTRAPRIME_CERT_NET_GUARD=1 (set by scripts/certify.py). Loopback traffic is
# allowed; every other outbound connect/sendto raises a clear, loud error so a
# forgotten mock becomes a visible certification failure, never a live call.
# This is test-infrastructure only; no application behavior is modified.
# ---------------------------------------------------------------------------
import os as _os
import socket as _socket

if _os.environ.get("SINTRAPRIME_CERT_NET_GUARD") == "1":
    _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "0.0.0.0", "localhost"}
    _GUARD_NOTICE = ("[SINTRAPRIME-CERT-NET-GUARD] outbound network denied "
                     "certification policy (default-deny; loopback only). "
                     "Destination: {dest!r}. If this test legitimately needs an "
                     "external service it must be classified and sandboxed.")

    def _is_loopback(dest):
        host = dest[0] if isinstance(dest, tuple) else dest
        if not isinstance(host, str):
            return True  # AF_UNIX / non-INET targets: allow
        return host in _LOOPBACK_HOSTS or host.startswith("127.") or host.endswith(".localhost")

    class _GuardedSocket(_socket.socket):
        def connect(self, address):
            if not _is_loopback(address):
                raise ConnectionAbortedError(_GUARD_NOTICE.format(dest=address))
            return super().connect(address)

        def connect_ex(self, address):
            if not _is_loopback(address):
                raise ConnectionAbortedError(_GUARD_NOTICE.format(dest=address))
            return super().connect_ex(address)

        def sendto(self, data, address=None):
            if address is not None and not _is_loopback(address):
                raise ConnectionAbortedError(_GUARD_NOTICE.format(dest=address))
            return super().sendto(data, address) if address is not None else super().sendto(data)

    _REAL_CREATE_CONNECTION = _socket.create_connection

    def _guarded_create_connection(address, *a, **kw):
        if not _is_loopback(address):
            raise ConnectionAbortedError(_GUARD_NOTICE.format(dest=address))
        return _REAL_CREATE_CONNECTION(address, *a, **kw)

    _socket.socket = _GuardedSocket
    _socket.create_connection = _guarded_create_connection
