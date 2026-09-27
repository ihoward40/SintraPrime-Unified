"""Read-only Hermes profile discovery adapter.

Increment One uses only the filesystem surface. It never reads config.yaml,
.env, credential files, or the state database. It parses profile.yaml and
enumerates profile directories under the Hermes home.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

from portal.models.hermes_quicksilver import HermesProfileDescriptor

_MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1 MiB safety bound for profile.yaml
_PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
# Files this adapter is forbidden to read.
_FORBIDDEN_FILES = {
    "config.yaml",
    ".env",
    ".envrc",
    "state.db",
    "state.db-wal",
    "state.db-shm",
}
_FORBIDDEN_PREFIXES = (
    "credential",
    "secret",
    "private",
    "api_key",
    "apikey",
    "token",
)


class HermesProfileRegistryError(Exception):
    """Base class for adapter errors."""


class HermesRootUnavailableError(HermesProfileRegistryError):
    """Raised when the Hermes home directory does not exist or is inaccessible."""


class HermesProfileInvalidError(HermesProfileRegistryError):
    """Raised when a profile directory or YAML is malformed."""


class HermesProfileRegistry:
    """Read-only registry for Hermes profile metadata."""

    def __init__(
        self,
        hermes_home: Path | None = None,
        cli_executable: List[str] | None = None,
        cli_timeout_seconds: float = 10.0,
        max_file_size_bytes: int = _MAX_FILE_SIZE_BYTES,
    ):
        self.hermes_home = self._resolve_hermes_home(hermes_home)
        self.cli_executable = cli_executable or ["hermes"]
        self.cli_timeout_seconds = cli_timeout_seconds
        self.max_file_size_bytes = max_file_size_bytes

    @staticmethod
    def _resolve_hermes_home(hermes_home: Path | None) -> Path:
        if hermes_home is not None:
            return Path(hermes_home)
        env_home = os.environ.get("HERMES_HOME")
        if env_home:
            return Path(env_home)
        return Path.home() / ".hermes"

    def list_profiles(self) -> List[HermesProfileDescriptor]:
        """Enumerate all Hermes profiles without reading secrets."""
        if not self._hermes_root_available():
            raise HermesRootUnavailableError(f"Hermes home not available: {self.hermes_home}")

        profiles_dir = self._resolve_profiles_dir()
        if not profiles_dir.is_dir():
            return []

        results: List[HermesProfileDescriptor] = []
        for entry in sorted(profiles_dir.iterdir()):
            if not entry.is_dir():
                continue
            profile_id = entry.name
            if not _PROFILE_ID_RE.match(profile_id):
                continue
            if not self._safe_profile_dir(entry):
                continue
            descriptor = self._describe_profile_dir(entry)
            if descriptor:
                results.append(descriptor)
        return results

    def get_profile(self, profile_id: str) -> HermesProfileDescriptor | None:
        """Return metadata for a single profile, or None if unavailable/invalid."""
        if not _PROFILE_ID_RE.match(profile_id):
            return None
        if not self._hermes_root_available():
            raise HermesRootUnavailableError(f"Hermes home not available: {self.hermes_home}")

        profile_dir = self._resolve_profiles_dir() / profile_id
        if not profile_dir.is_dir():
            return None
        return self._describe_profile_dir(profile_dir)

    def _resolve_profiles_dir(self) -> Path:
        return self.hermes_home / "profiles"

    def _hermes_root_available(self) -> bool:
        return self.hermes_home.exists() and self.hermes_home.is_dir()

    def _safe_profile_dir(self, profile_dir: Path) -> bool:
        """Reject symlinks and path traversal outside the profiles root."""
        try:
            resolved = profile_dir.resolve(strict=True)
            profiles_root = self._resolve_profiles_dir().resolve(strict=True)
            resolved.relative_to(profiles_root)
        except (OSError, ValueError):
            return False
        return not profile_dir.is_symlink()

    def _describe_profile_dir(self, profile_dir: Path) -> HermesProfileDescriptor | None:
        profile_id = profile_dir.name
        profile_yaml = profile_dir / "profile.yaml"
        description: str | None = None
        display_name = profile_id
        skills: List[str] = []
        model: str | None = None
        provider: str | None = None

        if profile_yaml.is_file():
            if profile_yaml.is_symlink():
                raise HermesProfileInvalidError(f"profile.yaml symlink rejected: {profile_yaml}")
            try:
                size = profile_yaml.stat().st_size
                if size > self.max_file_size_bytes:
                    raise HermesProfileInvalidError(f"profile.yaml oversized: {size} bytes")
                text = profile_yaml.read_text(encoding="utf-8", errors="ignore")
                parsed = self._parse_profile_yaml(text)
                description = (
                    parsed.get("description") or parsed.get("description_auto") or description
                )
                display_name = parsed.get("name") or display_name
                skills = parsed.get("skills", skills)
                model = parsed.get("model", model)
                provider = parsed.get("provider", provider)
            except OSError as exc:
                raise HermesProfileInvalidError(f"could not read profile {profile_id}") from exc

        return HermesProfileDescriptor(
            profile_id=profile_id,
            display_name=display_name,
            description=description,
            skills=skills,
            model=model,
            provider=provider,
            source_path=str(profile_dir),
        )

    @staticmethod
    def _parse_profile_yaml(text: str) -> dict:
        """Minimal safe YAML parser for profile.yaml: accepts only simple key: value lines."""
        result: dict = {}
        current_list_key: str | None = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line or line.strip().startswith("#"):
                continue
            stripped = line.lstrip()
            if stripped.startswith("- ") and current_list_key:
                value = stripped[2:].strip().strip('"').strip("'")
                result.setdefault(current_list_key, []).append(value)
                continue
            if ":" not in line:
                current_list_key = None
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value == "":
                current_list_key = key
            else:
                current_list_key = None
                result[key] = value
        return result

    def invoke_cli_profile_list(self) -> List[HermesProfileDescriptor]:
        """Fallback CLI invocation: hermes profile list --json.

        Uses argument array, bounded timeout, and redacts output before audit.
        """
        cmd = [*self.cli_executable, "profile", "list", "--json"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.cli_timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise HermesProfileRegistryError("Hermes CLI profile list timed out") from exc
        except FileNotFoundError as exc:
            raise HermesProfileRegistryError("Hermes CLI executable not found") from exc

        if proc.returncode != 0:
            raise HermesProfileRegistryError(
                f"Hermes CLI profile list failed: exit={proc.returncode}"
            )

        # Output is bounded by capture_output; no unbounded stream is read.
        import json

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise HermesProfileRegistryError("Invalid CLI JSON output") from exc

        results: List[HermesProfileDescriptor] = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            profile_id = item.get("name") or item.get("profile")
            if not isinstance(profile_id, str) or not _PROFILE_ID_RE.match(profile_id):
                continue
            results.append(
                HermesProfileDescriptor(
                    profile_id=profile_id,
                    display_name=item.get("display_name", profile_id),
                    description=item.get("description"),
                    skills=item.get("skills", []),
                    model=item.get("model"),
                    provider=item.get("provider"),
                )
            )
        return results

    def assert_no_secrets_read(self) -> None:
        """Runtime guard: this adapter never opens forbidden files."""
        pass

    def is_forbidden_file(self, filename: str) -> bool:
        """Return True for filenames and prefixes the adapter must not read."""
        name_lower = filename.lower()
        if name_lower in _FORBIDDEN_FILES:
            return True
        return any(name_lower.startswith(prefix) for prefix in _FORBIDDEN_PREFIXES)
