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
    capability or hardening sequence is absent it FAILS CLOSED — it never silently
    downgrades to policy and never claims "os_enforced".
  * CONTAINER_NETWORK_NONE is only treated as verified when a trusted orchestration
    component both declares ``--network=none`` and identifies itself as the
    verification component. Mere env declaration is not enough to claim the
    boundary.
  * UNAVAILABLE_FAIL_CLOSED denies all executions because the requested
    containment could not be established.

This module performs NO external network calls and never mutates the controller's
own process network state (OS probes run in throwaway child processes only).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import enum
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "PROXY_ENV_VARS",
    "NetworkSandbox",
    "NetworkSandboxMode",
]

CLONE_NEWNET = 0x40000000
PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECUREBITS = 28
PR_CAPBSET_DROP = 24
PR_CAP_AMBIENT = 47
PR_CAP_AMBIENT_CLEAR_ALL = 4
LINUX_CAPABILITY_VERSION_3 = 0x20080522
SECBIT_NOROOT = 1 << 0
SECBIT_NOROOT_LOCKED = 1 << 1
SECBIT_NO_SETUID_FIXUP = 1 << 2
SECBIT_NO_SETUID_FIXUP_LOCKED = 1 << 3
SECBIT_NO_CAP_AMBIENT_RAISE = 1 << 6
SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED = 1 << 7

_MODE_ALIASES = {
    "policy": "policy_only",
    "policy_only": "policy_only",
    "os": "os_enforced",
    "os_enforced": "os_enforced",
    "container": "container_network_none",
    "container_network_none": "container_network_none",
    "unavailable_fail_closed": "unavailable_fail_closed",
}

_PROBE_ALLOW_ENV_VARS = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "WINDIR",
)

_PROBE_DENY_ENV_VARS = (
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "LD_AUDIT",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
)


class _CapHeader(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("pid", ctypes.c_int),
    ]


class _CapData(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32),
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
TRUSTED_CONTAINER_VERIFIERS = frozenset({
    "docker",
    "kubernetes",
    "orchestrator",
    "podman",
})


def _raise_oserror(name: str) -> None:
    err = ctypes.get_errno() or 1
    raise OSError(err, f"{name} failed: {os.strerror(err)}")


def _load_libc() -> ctypes.CDLL:
    libc_name = ctypes.util.find_library("c")
    if not libc_name:
        raise OSError("libc_not_found")
    return ctypes.CDLL(libc_name, use_errno=True)


def _cap_last_cap() -> int:
    try:
        return int(Path("/proc/sys/kernel/cap_last_cap").read_text(encoding="utf-8").strip())
    except Exception:
        return 40


def _linux_prctl(libc: ctypes.CDLL, option: int, arg2: int = 0, arg3: int = 0, arg4: int = 0, arg5: int = 0) -> None:
    libc.prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(option, arg2, arg3, arg4, arg5) != 0:
        _raise_oserror(f"prctl({option})")


def _linux_unshare_netns(libc: ctypes.CDLL) -> None:
    libc.unshare.argtypes = [ctypes.c_int]
    libc.unshare.restype = ctypes.c_int
    if libc.unshare(CLONE_NEWNET) != 0:
        _raise_oserror("unshare(CLONE_NEWNET)")


def _linux_drop_namespace_escape_capabilities(libc: ctypes.CDLL) -> None:
    _linux_prctl(libc, PR_SET_NO_NEW_PRIVS, 1)
    _linux_prctl(
        libc,
        PR_SET_SECUREBITS,
        SECBIT_NOROOT
        | SECBIT_NOROOT_LOCKED
        | SECBIT_NO_SETUID_FIXUP
        | SECBIT_NO_SETUID_FIXUP_LOCKED
        | SECBIT_NO_CAP_AMBIENT_RAISE
        | SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED,
    )
    _linux_prctl(libc, PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL)

    libc.capset.argtypes = [ctypes.POINTER(_CapHeader), ctypes.POINTER(_CapData)]
    libc.capset.restype = ctypes.c_int
    header = _CapHeader(version=LINUX_CAPABILITY_VERSION_3, pid=0)
    data = (_CapData * 2)()
    if libc.capset(ctypes.byref(header), data) != 0:
        _raise_oserror("capset")

    for cap in range(_cap_last_cap() + 1):
        _linux_prctl(libc, PR_CAPBSET_DROP, cap)


def _apply_linux_os_sandbox() -> None:
    """Apply the real Linux netns boundary in the child before Python worker code."""
    if platform.system() != "Linux":
        raise OSError("linux_netns_unavailable")
    libc = _load_libc()
    _linux_unshare_netns(libc)
    _linux_drop_namespace_escape_capabilities(libc)


def _build_probe_env(parent_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(parent_env or os.environ)
    sanitized = {key: env[key] for key in _PROBE_ALLOW_ENV_VARS if env.get(key)}
    sanitized["LANG"] = sanitized.get("LANG", "C")
    sanitized["LC_ALL"] = sanitized.get("LC_ALL", "C")
    for key in _PROBE_DENY_ENV_VARS:
        sanitized.pop(key, None)
    return sanitized


def _probe_child_main() -> int:
    try:
        _apply_linux_os_sandbox()
    except Exception:
        return 1
    return 0


def _probe_os_netns() -> bool:
    """Best-effort detection of a hardened OS network-isolation capability.

    Runs in a throwaway child process so the controller's own networking is never
    touched. Returns True only when the same Linux sandbox hook used for the real
    worker launch succeeds in a fresh child.
    """
    if platform.system() != "Linux":
        return False
    cmd = [sys.executable, "-I", "-S", __file__, "--probe-os-netns"]
    try:
        rc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=20,
            env=_build_probe_env(),
            text=True,
        )
        return rc.returncode == 0
    except Exception:
        return False


@dataclass
class NetworkSandbox:
    """Resolved network-containment posture for one execution backend."""

    mode: NetworkSandboxMode
    container_declared: bool = False
    container_verified_by: str = ""

    # --- configuration ---------------------------------------------------
    @classmethod
    def from_config(cls, environ: dict[str, str] | None = None) -> NetworkSandbox:
        env = environ if environ is not None else dict(os.environ)
        raw = (env.get("SWARM_NETWORK_ENFORCEMENT") or "policy_only").strip().lower()
        normalized = _MODE_ALIASES.get(raw)
        try:
            mode = NetworkSandboxMode(normalized or raw)
        except ValueError:
            # Unknown / misconfigured enforcement => fail closed.
            mode = NetworkSandboxMode.UNAVAILABLE_FAIL_CLOSED
        container_declared = env.get("SWARM_NETWORK_CONTAINER") == "none"
        return cls(
            mode=mode,
            container_declared=container_declared,
            container_verified_by=(env.get("SWARM_NETWORK_CONTAINER_VERIFIED_BY") or "").strip(),
        )

    # --- resolution ------------------------------------------------------
    def resolve(self) -> dict[str, object]:
        """Return the effective posture. Never mislabels policy as OS."""
        if self.mode is NetworkSandboxMode.POLICY_ONLY:
            return {
                "effective_level": "policy",
                "enforcement_level": "policy_enforced",
                "available": True,
                "fail_closed": False,
                "launch_mechanism": "policy_only",
                "verification_component": "admission_gate",
            }
        if self.mode is NetworkSandboxMode.OS_ENFORCED:
            if _probe_os_netns():
                return {
                    "effective_level": "os",
                    "enforcement_level": "os_enforced",
                    "available": True,
                    "fail_closed": False,
                    "launch_mechanism": "linux_netns",
                    "verification_component": "sandbox_probe",
                }
            # Capability absent: FAIL CLOSED, never downgrade to policy.
            return {
                "effective_level": "unavailable",
                "enforcement_level": "unavailable_fail_closed",
                "available": False,
                "fail_closed": True,
                "launch_mechanism": "unavailable",
                "verification_component": "sandbox_probe",
            }
        if self.mode is NetworkSandboxMode.CONTAINER_NETWORK_NONE:
            if (
                self.container_declared
                and self.container_verified_by in TRUSTED_CONTAINER_VERIFIERS
            ):
                return {
                    "effective_level": "os",
                    "enforcement_level": "os_enforced",
                    "available": True,
                    "fail_closed": False,
                    "launch_mechanism": "container_network_none",
                    "verification_component": self.container_verified_by,
                }
            return {
                "effective_level": "unavailable",
                "enforcement_level": "unavailable_fail_closed",
                "available": False,
                "fail_closed": True,
                "launch_mechanism": "unavailable",
                "verification_component": self.container_verified_by or "unverified_container_declaration",
            }
        # UNAVAILABLE_FAIL_CLOSED
        return {
            "effective_level": "unavailable",
            "enforcement_level": "unavailable_fail_closed",
            "available": False,
            "fail_closed": True,
            "launch_mechanism": "unavailable",
            "verification_component": "configuration",
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

        On Linux with real netns enforcement, unshare a fresh network namespace in
        the child and drop capabilities before worker-controlled Python executes.
        Container-backed containment does not install a local preexec hook because
        the container runtime is the enforcement boundary.
        """
        if (
            resolved.get("launch_mechanism") == "linux_netns"
            and platform.system() == "Linux"
        ):
            return {"preexec_fn": _apply_linux_os_sandbox}
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


def _main(argv: list[str]) -> int:
    if argv == ["--probe-os-netns"]:
        return _probe_child_main()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
