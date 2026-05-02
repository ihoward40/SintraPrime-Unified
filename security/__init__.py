"""
SintraPrime Security Module
Provides security hardening, input validation, and authentication.
"""

from .security_audit import SecurityAudit
from .secrets_scanner import SecretsScanner
from .input_validator import InputValidator
from .auth_guard import AuthGuard

__all__ = [
    "SecurityAudit",
    "SecretsScanner",
    "InputValidator",
    "AuthGuard",
]

__version__ = "1.0.0"
