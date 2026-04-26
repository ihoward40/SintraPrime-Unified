"""
Offline Mode Manager — SintraPrime-Unified local_models
Detects internet connectivity, manages graceful degradation,
caches common legal templates, and supports full air-gap mode.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CACHE_DIR = Path.home() / ".sintra" / "offline_cache"
CONNECTIVITY_TEST_HOSTS = [
    ("8.8.8.8", 53),
    ("1.1.1.1", 53),
    ("208.67.222.222", 53),
]

OFFLINE_CAPABILITY_MAP: Dict[str, bool] = {
    "Local Ollama models":       True,
    "Document review (local)":   True,
    "Contract analysis (local)": True,
    "Legal templates":           True,
    "Cached completions":        True,
    "DeepSeek API":              False,
    "OpenAI API":                False,
    "Anthropic API":             False,
    "Web legal research":        False,
    "Court filings API":         False,
    "Case law databases":        False,
}

# Legal templates pre-cached for offline use
LEGAL_TEMPLATES: Dict[str, str] = {
    "nda_simple": (
        "NON-DISCLOSURE AGREEMENT\n\n"
        "This Non-Disclosure Agreement ('Agreement') is entered into as of [DATE] "
        "between [PARTY_A] ('Disclosing Party') and [PARTY_B] ('Receiving Party').\n\n"
        "1. CONFIDENTIAL INFORMATION. The Receiving Party agrees to keep confidential "
        "all information disclosed by the Disclosing Party.\n\n"
        "2. OBLIGATIONS. The Receiving Party shall not disclose, copy, or use "
        "Confidential Information without prior written consent.\n\n"
        "3. TERM. This Agreement shall remain in effect for [TERM] years.\n\n"
        "IN WITNESS WHEREOF, the parties have executed this Agreement.\n\n"
        "Disclosing Party: _______________  Date: _______________\n"
        "Receiving Party:  _______________  Date: _______________"
    ),
    "engagement_letter": (
        "ATTORNEY-CLIENT ENGAGEMENT LETTER\n\n"
        "Date: [DATE]\n"
        "Client: [CLIENT_NAME]\n"
        "Matter: [MATTER_DESCRIPTION]\n\n"
        "Dear [CLIENT_NAME],\n\n"
        "This letter confirms the terms of your engagement of [FIRM_NAME] "
        "('the Firm') to represent you in the above matter.\n\n"
        "SCOPE OF SERVICES: [SCOPE]\n"
        "FEE ARRANGEMENT: [FEES]\n"
        "RETAINER: [RETAINER_AMOUNT]\n\n"
        "Please sign and return a copy to confirm your acceptance.\n\n"
        "Sincerely,\n[ATTORNEY_NAME]\n[FIRM_NAME]"
    ),
    "motion_caption": (
        "IN THE [COURT_NAME]\n"
        "[JURISDICTION]\n\n"
        "[PLAINTIFF],\n"
        "    Plaintiff,\n\n"
        "v.                          Case No.: [CASE_NUMBER]\n\n"
        "[DEFENDANT],\n"
        "    Defendant.\n\n"
        "MOTION FOR [RELIEF_SOUGHT]\n"
    ),
    "cease_desist": (
        "CEASE AND DESIST LETTER\n\n"
        "Date: [DATE]\n"
        "Via: [DELIVERY_METHOD]\n\n"
        "To: [RECIPIENT_NAME]\n"
        "    [RECIPIENT_ADDRESS]\n\n"
        "Re: Demand to Cease and Desist [INFRINGING_ACTIVITY]\n\n"
        "Dear [RECIPIENT_NAME],\n\n"
        "This firm represents [CLIENT_NAME] ('Client'). It has come to our "
        "attention that you are engaged in [INFRINGING_ACTIVITY], which "
        "infringes upon our client's rights under [LEGAL_BASIS].\n\n"
        "YOU ARE HEREBY DEMANDED to immediately cease and desist from all "
        "such activity. Failure to comply may result in legal action.\n\n"
        "Sincerely,\n[ATTORNEY_NAME]\n[FIRM_NAME]"
    ),
}


# ---------------------------------------------------------------------------
# OfflineMode
# ---------------------------------------------------------------------------


class OfflineMode:
    """
    Manages offline operation for SintraPrime.

    Capabilities:
    - Detects internet connectivity
    - Air-gap mode: blocks all external API calls
    - Response cache: stores completions for offline reuse
    - Template cache: pre-loads legal templates
    - Capability reporting

    Parameters
    ----------
    cache_dir:
        Directory for offline cache storage.
    air_gap:
        If True, all external calls are disabled immediately.
    check_interval:
        Seconds between connectivity re-checks (default 60).
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        air_gap: bool = False,
        check_interval: int = 60,
    ) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._air_gap = air_gap
        self._check_interval = check_interval
        self._last_check: float = 0.0
        self._online: bool = False
        self._blocked_calls: List[str] = []

        # Init sub-caches
        self._response_cache_path = self.cache_dir / "response_cache.json"
        self._template_cache_path = self.cache_dir / "templates.json"
        self._response_cache: Dict[str, Any] = self._load_json(self._response_cache_path)
        self._template_cache: Dict[str, str] = {}
        self._load_templates()

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    @staticmethod
    def _check_connectivity(timeout: float = 3.0) -> bool:
        """Test internet connectivity by attempting TCP connects."""
        for host, port in CONNECTIVITY_TEST_HOSTS:
            try:
                sock = socket.create_connection((host, port), timeout=timeout)
                sock.close()
                return True
            except (socket.timeout, OSError):
                continue
        return False

    def is_online(self, force: bool = False) -> bool:
        """
        Return True if internet is available.

        Results are cached for ``check_interval`` seconds.
        In air-gap mode, always returns False.
        """
        if self._air_gap:
            return False

        now = time.time()
        if force or now - self._last_check > self._check_interval:
            self._online = self._check_connectivity()
            self._last_check = now
            if not self._online:
                logger.info("No internet connectivity detected — offline mode active")

        return self._online

    def is_offline(self, force: bool = False) -> bool:
        return not self.is_online(force=force)

    # ------------------------------------------------------------------
    # Air-gap mode
    # ------------------------------------------------------------------

    def enable_air_gap(self) -> None:
        """Enable air-gap mode: all external API calls are blocked."""
        self._air_gap = True
        self._online = False
        logger.warning("AIR-GAP MODE ENABLED — all external API calls are blocked")

    def disable_air_gap(self) -> None:
        """Disable air-gap mode."""
        self._air_gap = False
        self._last_check = 0.0   # force re-check on next is_online()
        logger.info("Air-gap mode disabled")

    @property
    def air_gap_enabled(self) -> bool:
        return self._air_gap

    def guard_external_call(self, service_name: str) -> None:
        """
        Call before any external API call.
        Raises RuntimeError if air-gap mode is active or no connectivity.
        """
        if self._air_gap:
            self._blocked_calls.append(service_name)
            raise RuntimeError(
                f"Air-gap mode is enabled. External call to '{service_name}' is blocked."
            )
        if self.is_offline():
            self._blocked_calls.append(service_name)
            raise RuntimeError(
                f"No internet connectivity. External call to '{service_name}' cannot proceed."
            )

    @property
    def blocked_call_log(self) -> List[str]:
        return list(self._blocked_calls)

    # ------------------------------------------------------------------
    # Response cache
    # ------------------------------------------------------------------

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _cache_key(self, prompt: str, model: str) -> str:
        import hashlib
        return hashlib.sha256(f"{model}::{prompt}".encode()).hexdigest()[:16]

    def cache_response(self, prompt: str, model: str, response: str) -> None:
        """Cache a model response for offline reuse."""
        key = self._cache_key(prompt, model)
        self._response_cache[key] = {
            "prompt": prompt[:200],     # store preview only
            "model": model,
            "response": response,
            "cached_at": time.time(),
        }
        self._save_json(self._response_cache_path, self._response_cache)

    def get_cached_response(self, prompt: str, model: str) -> Optional[str]:
        """Look up a cached response. Returns None if not found."""
        key = self._cache_key(prompt, model)
        entry = self._response_cache.get(key)
        if entry:
            return entry["response"]
        return None

    def clear_response_cache(self) -> int:
        """Clear all cached responses. Returns number of entries removed."""
        count = len(self._response_cache)
        self._response_cache = {}
        self._save_json(self._response_cache_path, {})
        return count

    @property
    def response_cache_size(self) -> int:
        return len(self._response_cache)

    # ------------------------------------------------------------------
    # Template cache
    # ------------------------------------------------------------------

    def _load_templates(self) -> None:
        """Load templates from disk, then merge built-in ones."""
        disk = self._load_json(self._template_cache_path)
        self._template_cache = {**LEGAL_TEMPLATES, **disk}  # disk overrides built-ins

    def get_template(self, name: str) -> Optional[str]:
        """Return a legal template by name."""
        return self._template_cache.get(name)

    def list_templates(self) -> List[str]:
        """List available template names."""
        return list(self._template_cache.keys())

    def add_template(self, name: str, content: str) -> None:
        """Add or update a legal template."""
        self._template_cache[name] = content
        # Save only user-added templates (not built-ins) to disk
        user_templates = {k: v for k, v in self._template_cache.items() if k not in LEGAL_TEMPLATES}
        self._save_json(self._template_cache_path, user_templates)

    def fill_template(self, name: str, variables: Dict[str, str]) -> Optional[str]:
        """
        Fill a template with variables.

        Replaces ``[KEY]`` placeholders with corresponding values.
        """
        template = self.get_template(name)
        if template is None:
            return None
        result = template
        for key, value in variables.items():
            placeholder = f"[{key.upper()}]"
            result = result.replace(placeholder, value)
        return result

    def pre_cache_templates(self) -> int:
        """
        Ensure all built-in legal templates are cached to disk.

        Returns count of templates cached.
        """
        for name, content in LEGAL_TEMPLATES.items():
            if name not in self._template_cache:
                self._template_cache[name] = content
        return len(LEGAL_TEMPLATES)

    # ------------------------------------------------------------------
    # Capability report
    # ------------------------------------------------------------------

    def capability_report(self) -> Dict[str, Any]:
        """Return what works in the current connectivity state.

        ``OFFLINE_CAPABILITY_MAP`` values are ``True`` when the feature is
        available without internet access (local-only features) and ``False``
        when the feature requires network connectivity.
        """
        online = self.is_online()
        capabilities = {}
        for feature, available_offline in OFFLINE_CAPABILITY_MAP.items():
            if available_offline:
                # Feature works without internet
                capabilities[feature] = True
            else:
                # Feature requires network; blocked in air-gap mode
                capabilities[feature] = online and not self._air_gap

        return {
            "online": online,
            "air_gap_mode": self._air_gap,
            "capabilities": capabilities,
            "available_offline": [k for k, v in capabilities.items() if OFFLINE_CAPABILITY_MAP[k]],
            "unavailable": [k for k, v in capabilities.items() if not v],
            "cached_responses": self.response_cache_size,
            "cached_templates": len(self._template_cache),
        }

    # ------------------------------------------------------------------
    # Graceful degradation helper
    # ------------------------------------------------------------------

    def with_fallback(
        self,
        online_fn: Callable[[], Any],
        offline_fn: Callable[[], Any],
        service_name: str = "external service",
    ) -> Any:
        """
        Run online_fn if connected, else run offline_fn.

        This is the primary hook for graceful degradation.

        Example
        -------
        result = offline_manager.with_fallback(
            online_fn=lambda: deepseek_client.complete(prompt),
            offline_fn=lambda: ollama_client.generate(prompt),
            service_name="DeepSeek",
        )
        """
        if self.is_online() and not self._air_gap:
            try:
                return online_fn()
            except Exception as exc:
                logger.warning(
                    "Online call to '%s' failed (%s) — falling back to offline",
                    service_name, exc,
                )
        return offline_fn()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "online": self.is_online(),
            "air_gap": self._air_gap,
            "cache_dir": str(self.cache_dir),
            "response_cache_entries": self.response_cache_size,
            "template_count": len(self._template_cache),
            "blocked_calls": len(self._blocked_calls),
        }

    def __repr__(self) -> str:
        return (
            f"OfflineMode(air_gap={self._air_gap}, "
            f"online={self._online}, "
            f"cache_entries={self.response_cache_size})"
        )
