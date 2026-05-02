"""
JWT-based authentication guard for SintraPrime.
Lightweight implementation — no external dependencies.
Sierra-4 Security Module
"""

import hashlib
import hmac
import time
import json
import base64
import os
import re
from typing import Optional, Dict, Any


# Default secret — MUST be overridden via environment variable in production
_DEFAULT_SECRET = os.environ.get("SINTRAPRIME_JWT_SECRET", "change-me-in-production-use-env-var")

VALID_ROLES = {"admin", "attorney", "client", "viewer", "auditor", "system"}

# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY = {
    "viewer": 0,
    "client": 1,
    "auditor": 2,
    "attorney": 3,
    "admin": 4,
    "system": 5,
}


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""
    pass


class TokenInvalidError(Exception):
    """Raised when a JWT token is invalid or tampered."""
    pass


class AuthGuard:
    """
    Lightweight JWT implementation for SintraPrime authentication.
    
    Uses HMAC-SHA256 signing — compatible with standard JWT format.
    No external dependencies required.
    
    Roles: admin > attorney > auditor > client > viewer
    """

    def __init__(self, secret: Optional[str] = None):
        self.secret = (secret or _DEFAULT_SECRET).encode('utf-8')
        if self.secret == b"change-me-in-production-use-env-var":
            import warnings
            warnings.warn(
                "AuthGuard is using the default JWT secret. "
                "Set SINTRAPRIME_JWT_SECRET environment variable in production!",
                UserWarning,
                stacklevel=2,
            )

    # ─── JWT Utilities ─────────────────────────────────────────────────────────

    def _b64_encode(self, data: bytes) -> str:
        """URL-safe base64 encode without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    def _b64_decode(self, data: str) -> bytes:
        """URL-safe base64 decode with padding restoration."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, message: str) -> str:
        """Create HMAC-SHA256 signature."""
        sig = hmac.new(self.secret, message.encode('utf-8'), hashlib.sha256).digest()
        return self._b64_encode(sig)

    # ─── Token Creation ────────────────────────────────────────────────────────

    def create_token(self, user_id: str, role: str, expires_in: int = 3600,
                     extra_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a signed JWT token.
        
        Args:
            user_id: Unique user identifier
            role: User role (admin, attorney, client, viewer, auditor, system)
            expires_in: Token lifetime in seconds (default: 3600 = 1 hour)
            extra_claims: Additional JWT claims to include
            
        Returns:
            Signed JWT token string
            
        Raises:
            ValueError: If role is invalid
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}")

        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        now = int(time.time())

        # Header
        header = {"alg": "HS256", "typ": "JWT"}

        # Payload
        payload = {
            "sub": user_id,
            "role": role,
            "iat": now,
            "exp": now + expires_in,
            "iss": "sintraprime",
            "jti": self._generate_jti(),
        }
        if extra_claims:
            payload.update(extra_claims)

        header_b64 = self._b64_encode(json.dumps(header, separators=(',', ':')).encode())
        payload_b64 = self._b64_encode(json.dumps(payload, separators=(',', ':')).encode())

        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message)

        return f"{message}.{signature}"

    def _generate_jti(self) -> str:
        """Generate a unique JWT ID."""
        random_bytes = os.urandom(16)
        return hashlib.sha256(random_bytes + str(time.time()).encode()).hexdigest()[:16]

    # ─── Token Verification ───────────────────────────────────────────────────

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Decoded payload dict if valid, None if invalid
            
        Raises:
            TokenExpiredError: If token has expired
            TokenInvalidError: If token is malformed or tampered
        """
        if not token or not isinstance(token, str):
            return None

        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise TokenInvalidError("Malformed token: expected 3 parts")

            header_b64, payload_b64, provided_sig = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_sig = self._sign(message)

            if not hmac.compare_digest(expected_sig, provided_sig):
                raise TokenInvalidError("Token signature verification failed")

            # Decode payload
            payload_bytes = self._b64_decode(payload_b64)
            payload = json.loads(payload_bytes)

            # Verify expiration
            now = int(time.time())
            if payload.get("exp", 0) < now:
                raise TokenExpiredError(f"Token expired at {payload.get('exp')}")

            # Verify issuer
            if payload.get("iss") != "sintraprime":
                raise TokenInvalidError("Invalid token issuer")

            return payload

        except (TokenExpiredError, TokenInvalidError):
            raise
        except Exception as e:
            raise TokenInvalidError(f"Token verification failed: {e}")

    def decode_unverified(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token payload WITHOUT verifying signature.
        Only use for debugging/inspection — never for auth decisions.
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload_bytes = self._b64_decode(parts[1])
            return json.loads(payload_bytes)
        except Exception:
            return None

    # ─── Role Checks ──────────────────────────────────────────────────────────

    def require_role(self, token: str, required_role: str) -> bool:
        """
        Check if token has required role or higher in hierarchy.
        
        Role hierarchy (ascending): viewer → client → auditor → attorney → admin → system
        
        Args:
            token: JWT token string
            required_role: Minimum required role
            
        Returns:
            True if user has required role or higher
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return False

            user_role = payload.get("role", "viewer")
            user_level = ROLE_HIERARCHY.get(user_role, -1)
            required_level = ROLE_HIERARCHY.get(required_role, 999)

            return user_level >= required_level

        except (TokenExpiredError, TokenInvalidError):
            return False

    def get_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from a verified token."""
        try:
            payload = self.verify_token(token)
            return payload.get("sub") if payload else None
        except (TokenExpiredError, TokenInvalidError):
            return None

    def get_role(self, token: str) -> Optional[str]:
        """Extract user role from a verified token."""
        try:
            payload = self.verify_token(token)
            return payload.get("role") if payload else None
        except (TokenExpiredError, TokenInvalidError):
            return None

    def is_expired(self, token: str) -> bool:
        """Check if a token is expired (without raising exceptions)."""
        try:
            self.verify_token(token)
            return False
        except TokenExpiredError:
            return True
        except Exception:
            return True

    # ─── Password Hashing ─────────────────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        """
        Hash a password using PBKDF2-HMAC-SHA256 with random salt.
        bcrypt-compatible security level.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Formatted hash string: "pbkdf2:sha256:{iterations}${salt}${hash}"
            
        Raises:
            ValueError: If password is empty or too short
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(password) > 1024:
            raise ValueError("Password must be under 1024 characters")

        salt = os.urandom(32)
        iterations = 600_000  # NIST recommended minimum for PBKDF2-SHA256

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations,
            dklen=32
        )

        salt_b64 = base64.b64encode(salt).decode('utf-8')
        key_b64 = base64.b64encode(key).decode('utf-8')

        return f"pbkdf2:sha256:{iterations}${salt_b64}${key_b64}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a stored hash.
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            password: Plain text password to verify
            hashed: Stored hash string from hash_password()
            
        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed:
            return False

        try:
            # Parse stored hash
            parts = hashed.split('$')
            if len(parts) != 3:
                return False

            algo_part, salt_b64, stored_key_b64 = parts
            algo_parts = algo_part.split(':')
            if len(algo_parts) != 3 or algo_parts[0] != 'pbkdf2' or algo_parts[1] != 'sha256':
                return False

            iterations = int(algo_parts[2])
            salt = base64.b64decode(salt_b64)
            stored_key = base64.b64decode(stored_key_b64)

            # Re-derive key with same parameters
            derived_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations,
                dklen=32
            )

            # Constant-time comparison
            return hmac.compare_digest(derived_key, stored_key)

        except Exception:
            return False

    # ─── Token Refresh ────────────────────────────────────────────────────────

    def refresh_token(self, token: str, expires_in: int = 3600) -> Optional[str]:
        """
        Refresh a valid (non-expired) token with a new expiration.
        
        Args:
            token: Existing valid JWT token
            expires_in: New lifetime in seconds
            
        Returns:
            New token string, or None if original was invalid
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return None

            return self.create_token(
                user_id=payload["sub"],
                role=payload["role"],
                expires_in=expires_in,
            )
        except (TokenExpiredError, TokenInvalidError):
            return None

    # ─── API Key Management ───────────────────────────────────────────────────

    def generate_api_key(self, user_id: str, prefix: str = "sp") -> str:
        """
        Generate a deterministic API key for a user.
        
        Args:
            user_id: User identifier
            prefix: Key prefix (default: 'sp' for SintraPrime)
            
        Returns:
            API key string like 'sp_abc123...'
        """
        random_part = os.urandom(24)
        key_hash = hashlib.sha256(
            random_part + user_id.encode() + self.secret
        ).hexdigest()
        return f"{prefix}_{key_hash[:48]}"

    def validate_api_key_format(self, key: str) -> bool:
        """Check if an API key has valid format."""
        pattern = re.compile(r'^[a-z]{2,8}_[a-zA-Z0-9]{32,64}$')
        return bool(pattern.match(key))
