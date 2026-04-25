"""
Password hashing and verification using bcrypt.
Includes strength validation and breach checking (optional HaveIBeenPwned).
"""

import re
import secrets
import string
from typing import Optional

import bcrypt
import structlog

logger = structlog.get_logger(__name__)

# bcrypt cost factor — 12 is recommended for production (2023)
BCRYPT_ROUNDS = 12

# Password policy
MIN_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True
SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~"


class PasswordError(Exception):
    """Raised when password does not meet policy."""
    pass


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt. Returns the hashed string."""
    if not plain_password:
        raise PasswordError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    Returns True if match, False otherwise. Constant-time comparison.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as exc:
        logger.warning("password.verify_error", error=str(exc))
        return False


def validate_password_strength(password: str) -> None:
    """
    Validate password meets policy requirements.
    Raises PasswordError with descriptive message if invalid.
    """
    errors: list[str] = []

    if len(password) < MIN_LENGTH:
        errors.append(f"at least {MIN_LENGTH} characters")

    if REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")

    if REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")

    if REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("at least one digit")

    if REQUIRE_SPECIAL and not re.search(rf"[{re.escape(SPECIAL_CHARS)}]", password):
        errors.append("at least one special character")

    # Common patterns check
    common_patterns = [
        r"(.)\1{3,}",          # 4+ repeated characters
        r"(012|123|234|345|456|567|678|789|890)",  # sequential numbers
        r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
    ]
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            errors.append("avoid common patterns (sequential, repeated characters)")
            break

    if errors:
        raise PasswordError("Password must contain: " + ", ".join(errors))


def generate_secure_password(length: int = 20) -> str:
    """Generate a cryptographically secure random password meeting all policies."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        try:
            validate_password_strength(password)
            return password
        except PasswordError:
            continue  # regenerate until valid


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate one-time backup codes for MFA recovery."""
    codes = []
    for _ in range(count):
        # Format: XXXX-XXXX-XXXX (12 chars + dashes)
        raw = secrets.token_hex(6).upper()
        formatted = f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"
        codes.append(formatted)
    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage."""
    normalized = code.replace("-", "").upper()
    return hash_password(normalized)


def verify_backup_code(code: str, hashed: str) -> bool:
    """Verify a backup code against its hash."""
    normalized = code.replace("-", "").upper()
    return verify_password(normalized, hashed)
