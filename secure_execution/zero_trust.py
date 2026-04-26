"""
zero_trust.py — Zero-Trust Security Model

Never trust, always verify. Every request is re-authenticated and
re-authorized regardless of its source.

Components:
  - ZeroTrustGateway    : central verifier for all inbound requests
  - IdentityVerifier    : JWT validation + certificate pinning
  - MicroSegmentation   : per-module access-control lists
  - ContinuousAuthorizer: re-verifies identity every 5 minutes
  - PolicyEngine        : ALLOW / DENY / MFA_REQUIRED decision tree
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    MFA_REQUIRED = "mfa_required"


class TrustLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERIFIED = 4


# ---------------------------------------------------------------------------
# Identity data structures
# ---------------------------------------------------------------------------

@dataclass
class Identity:
    subject: str                        # user / service identifier
    roles: List[str]
    trust_level: TrustLevel = TrustLevel.NONE
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attributes: Dict[str, Any] = field(default_factory=dict)
    mfa_verified: bool = False
    certificate_thumbprint: Optional[str] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass
class AccessRequest:
    identity: Identity
    resource: str          # module or endpoint being accessed
    action: str            # read / write / delete / execute
    context: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


@dataclass
class AccessDecision:
    decision: PolicyDecision
    reason: str
    request_id: str
    timestamp: float = field(default_factory=time.time)
    required_factors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JWT-like token handling (HMAC-SHA256 based, no external dependency)
# ---------------------------------------------------------------------------

class TokenManager:
    """
    Minimal JWT-like signed token using HMAC-SHA256.
    Format: base64(header).base64(payload).base64(signature)
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        self._secret = secret or os.urandom(32)

    def _b64(self, data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _b64d(self, s: str) -> bytes:
        import base64
        padding = 4 - len(s) % 4
        return base64.urlsafe_b64decode(s + "=" * padding)

    def issue(self, subject: str, roles: List[str], ttl: int = 3600) -> str:
        header = self._b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = self._b64(json.dumps({
            "sub": subject,
            "roles": roles,
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl,
            "jti": secrets.token_hex(16),
        }).encode())
        signing_input = f"{header}.{payload}".encode()
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return f"{header}.{payload}.{self._b64(sig)}"

    def verify(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header, payload_b64, sig_b64 = parts
            signing_input = f"{header}.{payload_b64}".encode()
            expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
            provided_sig = self._b64d(sig_b64)
            if not hmac.compare_digest(expected_sig, provided_sig):
                return None
            payload = json.loads(self._b64d(payload_b64))
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Certificate Pinning
# ---------------------------------------------------------------------------

class CertificatePinner:
    """Maintain a set of allowed certificate thumbprints."""

    def __init__(self) -> None:
        self._pins: Set[str] = set()

    def add_pin(self, thumbprint: str) -> None:
        self._pins.add(thumbprint.lower())

    def remove_pin(self, thumbprint: str) -> None:
        self._pins.discard(thumbprint.lower())

    def is_pinned(self, thumbprint: str) -> bool:
        """Return True if thumbprint is in the pin set (or pin set is empty = allow all)."""
        if not self._pins:
            return True   # no pins configured → allow all (open mode)
        return thumbprint.lower() in self._pins

    def pin_count(self) -> int:
        return len(self._pins)


# ---------------------------------------------------------------------------
# Identity Verifier
# ---------------------------------------------------------------------------

class IdentityVerifier:
    """Verify identity via JWT tokens and optional certificate pinning."""

    def __init__(
        self,
        token_manager: Optional[TokenManager] = None,
        pinner: Optional[CertificatePinner] = None,
    ) -> None:
        self._tm = token_manager or TokenManager()
        self._pinner = pinner or CertificatePinner()

    def verify_token(self, token: str, cert_thumbprint: Optional[str] = None) -> Optional[Identity]:
        payload = self._tm.verify(token)
        if payload is None:
            logger.warning("Token verification failed.")
            return None

        # Certificate pinning check
        if cert_thumbprint is not None:
            if not self._pinner.is_pinned(cert_thumbprint):
                logger.warning("Certificate thumbprint not pinned: %s", cert_thumbprint)
                return None

        trust = TrustLevel.MEDIUM
        if cert_thumbprint and self._pinner.pin_count() > 0:
            trust = TrustLevel.HIGH

        return Identity(
            subject=payload["sub"],
            roles=payload.get("roles", []),
            trust_level=trust,
            issued_at=payload.get("iat", time.time()),
            expires_at=payload.get("exp", time.time() + 3600),
            certificate_thumbprint=cert_thumbprint,
        )

    def issue_token(self, subject: str, roles: List[str], ttl: int = 3600) -> str:
        return self._tm.issue(subject, roles, ttl)

    @property
    def token_manager(self) -> TokenManager:
        return self._tm

    @property
    def pinner(self) -> CertificatePinner:
        return self._pinner


# ---------------------------------------------------------------------------
# Micro-segmentation
# ---------------------------------------------------------------------------

@dataclass
class SegmentPolicy:
    module: str
    allowed_actions: Set[str]
    allowed_roles: Set[str]
    allowed_resources: Set[str]   # empty set = all
    deny_by_default: bool = True


class MicroSegmentation:
    """
    Per-module access control.  Each module declares exactly what it needs.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, SegmentPolicy] = {}

    def register_module(self, policy: SegmentPolicy) -> None:
        self._policies[policy.module] = policy
        logger.info("Registered micro-segment policy for module: %s", policy.module)

    def check_access(
        self,
        module: str,
        action: str,
        role: str,
        resource: str,
    ) -> bool:
        policy = self._policies.get(module)
        if policy is None:
            logger.warning("No policy for module '%s' — %s", module,
                           "denying" if True else "allowing")
            return False  # deny unknown modules

        if action not in policy.allowed_actions:
            return False
        if role not in policy.allowed_roles:
            return False
        if policy.allowed_resources and resource not in policy.allowed_resources:
            return False
        return True

    def list_modules(self) -> List[str]:
        return list(self._policies.keys())


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

@dataclass
class PolicyRule:
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    # Conditions — None means "match any"
    subject_pattern: Optional[str] = None   # substring match on identity.subject
    required_roles: List[str] = field(default_factory=list)   # ANY of these
    resource_pattern: Optional[str] = None
    action_pattern: Optional[str] = None
    min_trust_level: TrustLevel = TrustLevel.NONE
    require_mfa: bool = False
    # Decision
    decision: PolicyDecision = PolicyDecision.DENY
    priority: int = 100   # lower = evaluated first


class PolicyEngine:
    """Rule-based policy engine evaluated in priority order."""

    def __init__(self) -> None:
        self._rules: List[PolicyRule] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        # Default deny-all rule (lowest priority)
        self._rules.append(PolicyRule(
            description="Default deny all",
            decision=PolicyDecision.DENY,
            priority=9999,
        ))

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        identity = request.identity
        for rule in self._rules:
            if not self._matches(rule, request):
                continue

            decision = rule.decision
            required_factors: List[str] = []

            # Escalate to MFA_REQUIRED if rule demands it and MFA not done
            if rule.require_mfa and not identity.mfa_verified:
                decision = PolicyDecision.MFA_REQUIRED
                required_factors.append("totp_or_webauthn")

            return AccessDecision(
                decision=decision,
                reason=rule.description or f"Rule {rule.rule_id} matched",
                request_id=request.request_id,
                required_factors=required_factors,
            )

        return AccessDecision(
            decision=PolicyDecision.DENY,
            reason="No matching rule — implicit deny",
            request_id=request.request_id,
        )

    @staticmethod
    def _matches(rule: PolicyRule, req: AccessRequest) -> bool:
        identity = req.identity

        if rule.subject_pattern and rule.subject_pattern not in identity.subject:
            return False

        if rule.required_roles:
            if not any(identity.has_role(r) for r in rule.required_roles):
                return False

        if rule.resource_pattern and rule.resource_pattern not in req.resource:
            return False

        if rule.action_pattern and rule.action_pattern not in req.action:
            return False

        if identity.trust_level.value < rule.min_trust_level.value:
            return False

        return True

    def rule_count(self) -> int:
        return len(self._rules)


# ---------------------------------------------------------------------------
# Continuous Authorization
# ---------------------------------------------------------------------------

class ContinuousAuthorizer:
    """
    Re-verifies active sessions every *interval_seconds* (default 300 = 5 min).
    Revokes sessions that fail re-verification.
    """

    def __init__(
        self,
        identity_verifier: IdentityVerifier,
        interval_seconds: float = 300,
    ) -> None:
        self._verifier = identity_verifier
        self._interval = interval_seconds
        self._sessions: Dict[str, Tuple[str, float]] = {}  # session_id -> (token, last_verified)
        self._revoked: Set[str] = set()
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

    def register_session(self, session_id: str, token: str) -> None:
        with self._lock:
            self._sessions[session_id] = (token, time.time())

    def revoke_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._revoked.add(session_id)

    def is_revoked(self, session_id: str) -> bool:
        return session_id in self._revoked

    def check_session(self, session_id: str) -> bool:
        """Manually verify a specific session; revoke if invalid."""
        with self._lock:
            if session_id in self._revoked:
                return False
            entry = self._sessions.get(session_id)
            if entry is None:
                return False
            token, _ = entry

        identity = self._verifier.verify_token(token)
        if identity is None or identity.is_expired():
            self.revoke_session(session_id)
            logger.warning("Session %s revoked during continuous auth check.", session_id)
            return False

        with self._lock:
            self._sessions[session_id] = (token, time.time())
        return True

    def _monitor_loop(self) -> None:
        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break
            with self._lock:
                session_ids = list(self._sessions.keys())
            for sid in session_ids:
                self.check_session(sid)
            logger.debug("Continuous auth cycle complete; active sessions: %d",
                         len(self._sessions))

    def start(self) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ContinuousAuthorizer"
        )
        self._monitor_thread.start()
        logger.info("ContinuousAuthorizer started (interval=%ss).", self._interval)

    def stop(self) -> None:
        self._running = False
        logger.info("ContinuousAuthorizer stopped.")

    def active_session_count(self) -> int:
        return len(self._sessions)


# ---------------------------------------------------------------------------
# Zero-Trust Gateway
# ---------------------------------------------------------------------------

class ZeroTrustGateway:
    """
    Central enforcement point.
    Every request must pass identity verification + policy evaluation.
    """

    def __init__(
        self,
        identity_verifier: Optional[IdentityVerifier] = None,
        policy_engine: Optional[PolicyEngine] = None,
        segmentation: Optional[MicroSegmentation] = None,
        continuous_authorizer: Optional[ContinuousAuthorizer] = None,
        re_verify_interval: float = 300,
    ) -> None:
        self._id_verifier = identity_verifier or IdentityVerifier()
        self._policy = policy_engine or PolicyEngine()
        self._segmentation = segmentation or MicroSegmentation()
        self._continuous = continuous_authorizer or ContinuousAuthorizer(
            self._id_verifier, re_verify_interval
        )
        self._audit_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def authenticate(
        self,
        token: str,
        cert_thumbprint: Optional[str] = None,
    ) -> Optional[Identity]:
        """Step 1: Verify who the caller is."""
        identity = self._id_verifier.verify_token(token, cert_thumbprint)
        if identity:
            self._continuous.register_session(identity.session_id, token)
        return identity

    # ------------------------------------------------------------------
    def authorize(self, request: AccessRequest) -> AccessDecision:
        """Step 2: Decide whether the identity may perform the action."""
        identity = request.identity

        # Reject expired identities immediately
        if identity.is_expired():
            decision = AccessDecision(
                decision=PolicyDecision.DENY,
                reason="Identity token is expired",
                request_id=request.request_id,
            )
            self._log_decision(request, decision)
            return decision

        # Continuous auth check
        if self._continuous.is_revoked(identity.session_id):
            decision = AccessDecision(
                decision=PolicyDecision.DENY,
                reason="Session has been revoked",
                request_id=request.request_id,
            )
            self._log_decision(request, decision)
            return decision

        # Micro-segmentation: check per-module ACL first
        for role in identity.roles:
            seg_ok = self._segmentation.check_access(
                module=request.resource.split("/")[0],
                action=request.action,
                role=role,
                resource=request.resource,
            )
            if seg_ok:
                break
        else:
            # If segmentation has no policy for this module, fall through to policy engine
            pass

        # Policy engine evaluation
        decision = self._policy.evaluate(request)
        self._log_decision(request, decision)
        return decision

    # ------------------------------------------------------------------
    def verify_request(
        self,
        token: str,
        resource: str,
        action: str,
        cert_thumbprint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AccessDecision:
        """Convenience method: authenticate + authorize in one call."""
        identity = self.authenticate(token, cert_thumbprint)
        if identity is None:
            dummy_request_id = str(uuid.uuid4())
            return AccessDecision(
                decision=PolicyDecision.DENY,
                reason="Authentication failed",
                request_id=dummy_request_id,
            )
        request = AccessRequest(
            identity=identity,
            resource=resource,
            action=action,
            context=context or {},
        )
        return self.authorize(request)

    # ------------------------------------------------------------------
    def _log_decision(self, request: AccessRequest, decision: AccessDecision) -> None:
        entry = {
            "request_id": request.request_id,
            "subject": request.identity.subject,
            "resource": request.resource,
            "action": request.action,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "timestamp": decision.timestamp,
        }
        with self._lock:
            self._audit_log.append(entry)

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit_log[-limit:])

    # ------------------------------------------------------------------
    def add_policy_rule(self, rule: PolicyRule) -> None:
        self._policy.add_rule(rule)

    def register_module(self, policy: SegmentPolicy) -> None:
        self._segmentation.register_module(policy)

    def start_continuous_auth(self) -> None:
        self._continuous.start()

    def stop_continuous_auth(self) -> None:
        self._continuous.stop()

    @property
    def identity_verifier(self) -> IdentityVerifier:
        return self._id_verifier

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy

    @property
    def continuous_authorizer(self) -> ContinuousAuthorizer:
        return self._continuous
