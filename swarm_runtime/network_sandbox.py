"""OS / runtime network containment for the governed swarm execution backend.

SP-GOD1X-OS-NETWORK-SANDBOX-001.

GOD-1X already denies the NETWORKED / EXTERNAL_EFFECT execution classes at the
admission gate (policy layer). This module adds a *second*, independent layer of
network containment so that even a non-network-class worker (e.g. a BUILD step
that runs ``pip install``) cannot reach the network, and so the system can never
mislabel "policy-only" as "OS-enforced".

Design invariants (fail-closed):

  * POLICY_ONLY is always available. It strips proxy/escape environment variables
    and relies on the admission gate to deny network execution classes. It does
    NOT claim OS enforcement.
  * OS_ENFORCED attempts real OS-level isolation (Linux network namespace). If the
    capability is absent it FAILS CLOSED — it never silently downgrades to policy
    and never claims "os_enforced".
  * CONTAINER_NETWORK_NONE is asserted by configuration (the orchestrator launched
    the worker in a ``--network=none`` container). Without the declaration it is
    treated as unavailable and fails closed.
  * UNAVAILABLE_FAIL_CLOSED denies all executions because the requested
    containment could not be established.

This module performs NO external network calls and never mutates the controller's
own process network state (OS probes run in throwaway child processes only).
"""

from __future__ import annotations

import ctypes
import enum
import os
import platform
import subprocess
import sys
from dataclasses import dataclass

__all__ = [
    "PROXY_ENV_VARS",
    "NetworkSandbox",
    "NetworkSandboxMode",
]


class NetworkSandboxMode(enum.StrEnum):
    POLICY_ONLY = "policy_only"
    OS_ENFORCED = "os_enforced"
    CONTAINER_NETWORK_NONE = "container_network_none"
    UNAVAILABLE_FAIL_CLOSED = "unavailable_fail_closed"


# Variables that can redirect a subprocess's traffic through a proxy or otherwise
# escape the network-deny policy via environment configuration.
PROXY_ENV_VARS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "ftp_proxy",
    "NO_PROXY", "no_proxy",
    "GIT_PROXY_COMMAND", "GIT_SSH_COMMAND", "RSYNC_PROXY",
    "npm_config_proxy", "npm_config_https_proxy", "PIP_INDEX_URL",
    "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE",
)


_CLONE_NEWNET = 0x40000000


def _unshare_newnet() -> None:
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    rc = libc.unshare(_CLONE_NEWNET)
    if rc != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


def _probe_os_netns() -> bool:
    """Best-effort detection of an OS network-isolation capability.

    Runs in a throwaway child process so the controller's own networking is never
    touched. Returns True only when a child can unshare a fresh network namespace
    (Linux CLONE_NEWNET, 0x40000000).
    """
    if platform.system() != "Linux":
        return False
    probe = (
        "import ctypes,os;"
        "libc=ctypes.CDLL('libc.so.6', use_errno=True);"
        "raise SystemExit(0 if libc.unshare(0x40000000)==0 else 1)"
    )
    try:
        rc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, timeout=20,
        )
        return rc.returncode == 0
    except Exception:
        return False


def _container_network_none_verified() -> bool:
    """Verify the current runtime appears network-disabled (fail-closed)."""
    if platform.system() != "Linux":
        return False
    try:
        # A `--network=none` runtime should not be in the initial host netns.
        if os.readlink("/proc/self/ns/net") == "net:[4026531993]":
            return False
        # A `--network=none` runtime should expose only loopback.
        interfaces = [name for name in os.listdir("/sys/class/net") if name != "lo"]
        if interfaces:
            return False
        # And it should not have a default route.
        with open("/proc/net/route", encoding="utf-8") as route_file:
            for line in route_file.readlines()[1:]:
                fields = line.split()
                if len(fields) > 1 and fields[1] == "00000000":
                    return False
        return True
    except OSError:
        return False


@dataclass
class NetworkSandbox:
    """Resolved network-containment posture for one execution backend."""

    mode: NetworkSandboxMode
    container_declared: bool = False

    # --- configuration ---------------------------------------------------
    @classmethod
    def from_config(cls, environ: dict[str, str] | None = None) -> NetworkSandbox:
        env = environ if environ is not None else dict(os.environ)
        raw = (env.get("SWARM_NETWORK_ENFORCEMENT") or "policy_only").strip().lower()
        try:
            mode = NetworkSandboxMode(raw)
        except ValueError:
            # Unknown / misconfigured enforcement => fail closed.
            mode = NetworkSandboxMode.UNAVAILABLE_FAIL_CLOSED
        container_declared = env.get("SWARM_NETWORK_CONTAINER") == "none"
        return cls(mode=mode, container_declared=container_declared)

    # --- resolution ------------------------------------------------------
    def resolve(self) -> dict[str, object]:
        """Return the effective posture. Never mislabels policy as OS."""
        if self.mode is NetworkSandboxMode.POLICY_ONLY:
            return {
                "effective_level": "policy",
                "enforcement_level": "policy_enforced",
                "available": True,
                "fail_closed": False,
            }
        if self.mode is NetworkSandboxMode.OS_ENFORCED:
            if _probe_os_netns():
                return {
                    "effective_level": "os",
                    "enforcement_level": "os_enforced",
                    "available": True,
                    "fail_closed": False,
                }
            # Capability absent: FAIL CLOSED, never downgrade to policy.
            return {
                "effective_level": "unavailable",
                "enforcement_level": "unavailable_fail_closed",
                "available": False,
                "fail_closed": True,
            }
        if self.mode is NetworkSandboxMode.CONTAINER_NETWORK_NONE:
            if self.container_declared and _container_network_none_verified():
                return {
                    "effective_level": "os",
                    "enforcement_level": "os_enforced",
                    "available": True,
                    "fail_closed": False,
                }
            return {
                "effective_level": "unavailable",
                "enforcement_level": "unavailable_fail_closed",
                "available": False,
                "fail_closed": True,
            }
        # UNAVAILABLE_FAIL_CLOSED
        return {
            "effective_level": "unavailable",
            "enforcement_level": "unavailable_fail_closed",
            "available": False,
            "fail_closed": True,
        }

    # --- environment hardening ------------------------------------------
    def strip_proxy_env(self, env: dict[str, str]) -> dict[str, str]:
        """Remove proxy / network-escape variables so a child cannot route out.

        Defense-in-depth even in POLICY_ONLY mode: a BUILD step that runs
        ``pip install`` must not inherit a parent HTTP(S)_PROXY that would
        silently reach the network.
        """
        return {k: v for k, v in env.items() if k not in PROXY_ENV_VARS}

    # --- OS-level launch hooks ------------------------------------------
    def popen_kwargs(self, resolved: dict[str, object]) -> dict[str, object]:
        """Subprocess kwargs that apply OS containment to the *child* only.

        On Linux with OS enforcement, unshare a fresh network namespace in the
        child via preexec_fn. On every other posture this is empty (policy and
        unavailable modes do not claim OS enforcement).
        """
        if (
            self.mode is NetworkSandboxMode.OS_ENFORCED
            and resolved.get("effective_level") == "os"
            and platform.system() == "Linux"
        ):
            return {"preexec_fn": _unshare_newnet}
        return {}

    # --- reporting ------------------------------------------------------
    def certification_status(self, resolved: dict[str, object]) -> str:
        level = resolved.get("effective_level")
        if level == "os":
            return "certified"
        if level == "policy":
            return "policy_only"
        return "unavailable"

    def brief_fields(self, resolved: dict[str, object]) -> dict[str, object]:
        return {
            "network_policy_status": "deny",
            "network_enforcement_level": resolved.get("enforcement_level"),
            "network_sandbox_available": bool(resolved.get("available")),
            "network_certification": self.certification_status(resolved),
        }
