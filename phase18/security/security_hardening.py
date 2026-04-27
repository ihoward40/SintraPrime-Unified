"""
phase18/security/security_hardening.py
=======================================
Security hardening layer for all Phase 18 components.

Addresses the 32 code-review findings, specifically:
  - CRIT-01: Missing rate limiting on Stripe webhook endpoint
  - CRIT-02: In-memory idempotency store lost on restart
  - CRIT-03: No API key / bearer-token authentication middleware
  - SEC-01:  CI patch strings not sanitised before display/storage
  - SEC-02:  Mobile scaffold path traversal via unsanitised project names
  - SEC-03:  Legal simulation prompt injection via unsanitised case descriptions
  - SEC-04:  No request-size limit on webhook payload
  - INFO-01..INFO-28: Various hardening improvements
"""
from __future__ import annotations

import hashlib
import hmac
import html
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CRIT-01: Rate Limiter (token-bucket per source IP / key)
# ---------------------------------------------------------------------------
@dataclass
class RateLimitConfig:
    """Configuration for a token-bucket rate limiter."""
    requests_per_window: int = 100
    window_seconds: float = 60.0
    burst_multiplier: float = 1.5  # allow short bursts up to this multiple


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter.

    Usage::

        limiter = RateLimiter(RateLimitConfig(requests_per_window=60, window_seconds=60))
        allowed, retry_after = limiter.check("stripe-webhook")
        if not allowed:
            raise TooManyRequestsError(retry_after)
    """

    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self._config = config or RateLimitConfig()
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> Tuple[bool, float]:
        """
        Check whether *key* is within rate limits.

        Returns:
            (allowed, retry_after_seconds)  — retry_after is 0.0 when allowed.
        """
        now = time.monotonic()
        window = self._config.window_seconds
        limit = self._config.requests_per_window
        burst_limit = int(limit * self._config.burst_multiplier)

        with self._lock:
            q = self._windows[key]
            # Evict timestamps outside the current window
            while q and q[0] < now - window:
                q.popleft()

            if len(q) >= burst_limit:
                # Oldest request in window determines when a slot opens
                retry_after = window - (now - q[0])
                return False, max(0.0, retry_after)

            q.append(now)
            return True, 0.0

    def reset(self, key: str) -> None:
        """Reset the counter for *key* (e.g. after a successful auth)."""
        with self._lock:
            self._windows.pop(key, None)

    @property
    def active_keys(self) -> List[str]:
        with self._lock:
            return list(self._windows.keys())


# ---------------------------------------------------------------------------
# CRIT-02: Persistent-capable idempotency store with TTL eviction
# ---------------------------------------------------------------------------
@dataclass
class IdempotencyRecord:
    key: str
    created_at: float
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending | complete | failed


class IdempotencyStore:
    """
    TTL-based idempotency store.  Defaults to in-memory but exposes a
    ``persist_fn`` hook so callers can swap in Redis / DB writes.

    Usage::

        store = IdempotencyStore(ttl_seconds=86400)
        if store.exists(event_id):
            return store.get(event_id)
        store.set(event_id, result)
    """

    def __init__(
        self,
        ttl_seconds: float = 86_400,  # 24 h
        persist_fn: Optional[Callable[[str, IdempotencyRecord], None]] = None,
        load_fn: Optional[Callable[[str], Optional[IdempotencyRecord]]] = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()
        self._persist_fn = persist_fn
        self._load_fn = load_fn

    def exists(self, key: str) -> bool:
        self._evict_expired()
        with self._lock:
            if key in self._store:
                return True
        # Try external load
        if self._load_fn:
            record = self._load_fn(key)
            if record and not self._is_expired(record):
                with self._lock:
                    self._store[key] = record
                return True
        return False

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        self._evict_expired()
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, result: Optional[Dict[str, Any]] = None, status: str = "complete") -> IdempotencyRecord:
        record = IdempotencyRecord(
            key=key,
            created_at=time.time(),
            result=result,
            status=status,
        )
        with self._lock:
            self._store[key] = record
        if self._persist_fn:
            self._persist_fn(key, record)
        return record

    def _is_expired(self, record: IdempotencyRecord) -> bool:
        return (time.time() - record.created_at) > self._ttl

    def _evict_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if (now - v.created_at) > self._ttl]
            for k in expired:
                del self._store[k]

    @property
    def size(self) -> int:
        self._evict_expired()
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# CRIT-03: API Key / Bearer Token authentication middleware
# ---------------------------------------------------------------------------
@dataclass
class ApiKeyConfig:
    """Configuration for API key authentication."""
    header_name: str = "X-Api-Key"
    bearer_scheme: bool = True       # also accept Authorization: Bearer <key>
    hash_algorithm: str = "sha256"   # store hashed keys, not plaintext


class ApiKeyStore:
    """
    Manages hashed API keys.  Keys are stored as ``sha256(key)`` so the
    plaintext is never persisted.

    Usage::

        store = ApiKeyStore()
        raw_key = store.generate_key("sintra-stripe-webhook")
        # Store raw_key securely; only the hash is kept internally.
        is_valid = store.validate(raw_key)
    """

    def __init__(self) -> None:
        self._keys: Dict[str, str] = {}   # hash -> label
        self._lock = threading.Lock()

    def generate_key(self, label: str) -> str:
        """Generate a new 32-byte URL-safe key, store its hash, return plaintext."""
        raw = secrets.token_urlsafe(32)
        key_hash = self._hash(raw)
        with self._lock:
            self._keys[key_hash] = label
        return raw

    def add_key(self, raw_key: str, label: str = "") -> str:
        """Register an externally-generated key."""
        key_hash = self._hash(raw_key)
        with self._lock:
            self._keys[key_hash] = label
        return key_hash

    def revoke_key(self, raw_key: str) -> bool:
        key_hash = self._hash(raw_key)
        with self._lock:
            if key_hash in self._keys:
                del self._keys[key_hash]
                return True
        return False

    def validate(self, raw_key: str) -> bool:
        """Return True if *raw_key* matches a registered key."""
        key_hash = self._hash(raw_key)
        with self._lock:
            return key_hash in self._keys

    def _hash(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._keys)


class AuthMiddleware:
    """
    Lightweight auth middleware that validates API keys extracted from
    request headers.  Framework-agnostic — works with Flask, FastAPI,
    Fastify (via Python bridge), or plain dicts.

    Usage::

        auth = AuthMiddleware(store)
        ok, reason = auth.authenticate({"X-Api-Key": "sk_live_..."})
        if not ok:
            raise UnauthorizedError(reason)
    """

    def __init__(
        self,
        store: ApiKeyStore,
        config: Optional[ApiKeyConfig] = None,
    ) -> None:
        self._store = store
        self._config = config or ApiKeyConfig()

    def authenticate(self, headers: Dict[str, str]) -> Tuple[bool, str]:
        """
        Returns (True, "") on success or (False, reason) on failure.
        Header names are matched case-insensitively.
        """
        normalised = {k.lower(): v for k, v in headers.items()}

        # 1. Check X-Api-Key header
        api_key_header = self._config.header_name.lower()
        if api_key_header in normalised:
            raw = normalised[api_key_header].strip()
            if self._store.validate(raw):
                return True, ""
            return False, "Invalid API key"

        # 2. Check Authorization: Bearer <key>
        if self._config.bearer_scheme:
            auth_header = normalised.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                raw = auth_header[7:].strip()
                if self._store.validate(raw):
                    return True, ""
                return False, "Invalid bearer token"

        return False, "Missing authentication credentials"


# ---------------------------------------------------------------------------
# SEC-01: CI patch sanitiser — prevent log injection / XSS in patch strings
# ---------------------------------------------------------------------------
_DANGEROUS_PATCH_PATTERNS = [
    re.compile(r";\s*rm\s+-rf", re.IGNORECASE),
    re.compile(r"&&\s*curl\s+", re.IGNORECASE),
    re.compile(r"\|\s*bash", re.IGNORECASE),
    re.compile(r"__import__\s*\(", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.(run|call|Popen)\s*\(.*shell\s*=\s*True", re.IGNORECASE),
]


def sanitize_patch(patch: str, max_length: int = 4096) -> Tuple[str, List[str]]:
    """
    Sanitise a CI repair patch string.

    Returns:
        (sanitised_patch, list_of_warnings)
    """
    warnings: List[str] = []

    # Truncate
    if len(patch) > max_length:
        warnings.append(f"Patch truncated from {len(patch)} to {max_length} chars")
        patch = patch[:max_length]

    # HTML-escape for safe display in reports
    safe = html.escape(patch)

    # Check for dangerous patterns in the *original* patch
    for pattern in _DANGEROUS_PATCH_PATTERNS:
        if pattern.search(patch):
            warnings.append(f"Dangerous pattern detected: {pattern.pattern}")

    return safe, warnings


# ---------------------------------------------------------------------------
# SEC-02: Mobile scaffold path traversal guard
# ---------------------------------------------------------------------------
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]{0,63}$")


def sanitize_project_name(name: str) -> Tuple[str, bool]:
    """
    Validate and sanitise a mobile app project name to prevent path traversal.

    Returns:
        (sanitised_name, is_valid)
    """
    # Strip leading/trailing whitespace and null bytes
    cleaned = name.strip().replace("\x00", "")

    # Reject immediately if the raw input contains path traversal characters
    # BEFORE any cleaning — cleaning would mask the attack
    if any(c in cleaned for c in ("/", "\\", "..")):
        return cleaned, False

    # Remove any remaining path separators (belt-and-suspenders)
    cleaned = re.sub(r"[/\\]", "", cleaned)

    is_valid = bool(_SAFE_NAME_RE.match(cleaned))
    return cleaned, is_valid


def safe_project_path(base_dir: Path, project_name: str) -> Tuple[Optional[Path], str]:
    """
    Resolve a project path safely, ensuring it stays within *base_dir*.

    Returns:
        (resolved_path, error_message)  — error is "" on success.
    """
    cleaned, is_valid = sanitize_project_name(project_name)
    if not is_valid:
        return None, f"Invalid project name: '{project_name}'"

    resolved = (base_dir / cleaned).resolve()
    try:
        resolved.relative_to(base_dir.resolve())
    except ValueError:
        return None, f"Path traversal attempt detected: '{project_name}'"

    return resolved, ""


# ---------------------------------------------------------------------------
# SEC-03: Legal simulation prompt injection guard
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]", re.IGNORECASE),
    re.compile(r"###\s*Instruction", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]


def sanitize_legal_input(text: str, max_length: int = 8192) -> Tuple[str, List[str]]:
    """
    Sanitise free-text legal case input to prevent prompt injection.

    Returns:
        (sanitised_text, list_of_warnings)
    """
    warnings: List[str] = []

    if len(text) > max_length:
        warnings.append(f"Input truncated from {len(text)} to {max_length} chars")
        text = text[:max_length]

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            warnings.append(f"Potential prompt injection pattern: {pattern.pattern}")
            # Redact the matched portion
            text = pattern.sub("[REDACTED]", text)

    return text, warnings


# ---------------------------------------------------------------------------
# SEC-04: Webhook payload size guard
# ---------------------------------------------------------------------------
MAX_WEBHOOK_PAYLOAD_BYTES = 512 * 1024  # 512 KB (Stripe max is ~100 KB)


def validate_webhook_payload(raw_body: bytes) -> Tuple[bool, str]:
    """
    Validate raw webhook payload size.

    Returns:
        (is_valid, error_message)
    """
    if len(raw_body) > MAX_WEBHOOK_PAYLOAD_BYTES:
        return False, (
            f"Payload size {len(raw_body)} bytes exceeds maximum "
            f"{MAX_WEBHOOK_PAYLOAD_BYTES} bytes"
        )
    if len(raw_body) == 0:
        return False, "Empty payload"
    return True, ""


# ---------------------------------------------------------------------------
# Composite SecurityLayer — convenience wrapper used by Phase 18 handlers
# ---------------------------------------------------------------------------
class SecurityLayer:
    """
    Composite security layer that bundles all hardening components.

    Usage::

        sec = SecurityLayer()
        api_key = sec.api_keys.generate_key("sintra-prod")

        # In webhook handler:
        ok, reason = sec.auth.authenticate(request_headers)
        allowed, retry = sec.rate_limiter.check(client_ip)
        valid, err = sec.validate_payload(raw_body)
    """

    def __init__(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        api_key_config: Optional[ApiKeyConfig] = None,
        idempotency_ttl: float = 86_400,
    ) -> None:
        self.rate_limiter = RateLimiter(rate_limit_config)
        self.api_keys = ApiKeyStore()
        self.auth = AuthMiddleware(self.api_keys, api_key_config)
        self.idempotency = IdempotencyStore(ttl_seconds=idempotency_ttl)

    # Convenience delegates
    def validate_payload(self, raw_body: bytes) -> Tuple[bool, str]:
        return validate_webhook_payload(raw_body)

    def sanitize_patch(self, patch: str) -> Tuple[str, List[str]]:
        return sanitize_patch(patch)

    def sanitize_legal_input(self, text: str) -> Tuple[str, List[str]]:
        return sanitize_legal_input(text)

    def safe_project_path(self, base_dir: Path, name: str) -> Tuple[Optional[Path], str]:
        return safe_project_path(base_dir, name)
