"""JARVIS-001-B1 credential isolation seam (B1-5).

Reasoning workers must never see mutation credentials. The executor-owned
provider adapter receives the credential at the execution boundary; worker
subprocesses get a filtered environment. This is the minimum B1 seam —
it does not redesign secret management.
"""
from __future__ import annotations

import os

MUTATION_CREDENTIAL_KEYS = frozenset({"GITHUB_TOKEN", "GH_TOKEN"})

_KEEP_EXACT = {
    "PATH", "SYSTEMROOT", "COMSPEC", "SYSTEMDRIVE", "TEMP", "TMP",
    "WINDIR", "PYTHONPATH", "VIRTUAL_ENV", "NUMBER_OF_PROCESSORS",
}


def build_worker_env(overrides: dict | None = None) -> dict:
    """Filtered environment for a spawned reasoning worker subprocess."""
    env = {k: v for k, v in os.environ.items() if k not in MUTATION_CREDENTIAL_KEYS}
    if overrides:
        env.update(overrides)
    return env


def strip_mutation_credentials(env: dict) -> dict:
    """Return a copy of env with mutation credentials removed."""
    return {k: v for k, v in env.items() if k not in MUTATION_CREDENTIAL_KEYS}
