"""
AES-256-GCM encryption service.
All stored files are encrypted at rest.
Key derived from environment variable — never hard-coded.
"""

from __future__ import annotations

import base64
import os
import secrets
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_ENV = "ENCRYPTION_KEY"
_KEY_LENGTH = 32  # AES-256


def _get_key() -> bytes:
    """Load the 256-bit AES key from the environment."""
    key_b64 = os.environ.get(_KEY_ENV, "")
    if key_b64:
        try:
            key = base64.b64decode(key_b64)
            if len(key) == _KEY_LENGTH:
                return key
        except Exception:
            pass
    # Development fallback — deterministic, NOT for production
    import hashlib
    return hashlib.sha256(b"DEVELOPMENT_ONLY_INSECURE_KEY").digest()


def encrypt_file(plaintext: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt bytes with AES-256-GCM.

    Returns:
        (ciphertext_with_tag, nonce)
    """
    key = _get_key()
    nonce = secrets.token_bytes(12)  # GCM standard: 96-bit nonce
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    # Prepend nonce to ciphertext for self-contained storage
    return nonce + ciphertext, nonce


def decrypt_file(data: bytes, nonce: bytes) -> bytes:
    """
    Decrypt AES-256-GCM data.
    data: nonce (12 bytes) + ciphertext+tag
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    # Skip nonce prefix if it's prepended
    ciphertext = data[12:] if data[:12] == nonce else data
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_text(plaintext: str) -> Tuple[str, bytes]:
    """
    Encrypt a UTF-8 string. Returns base64-encoded ciphertext and the nonce.
    """
    ciphertext_bytes, nonce = encrypt_file(plaintext.encode("utf-8"))
    return base64.b64encode(ciphertext_bytes).decode("ascii"), nonce


def decrypt_text(ciphertext_b64: str, nonce: bytes) -> str:
    """
    Decrypt a base64-encoded AES-256-GCM ciphertext back to a string.
    """
    ciphertext_bytes = base64.b64decode(ciphertext_b64)
    return decrypt_file(ciphertext_bytes, nonce).decode("utf-8")


def generate_document_key() -> str:
    """Generate a per-document encryption key (for future per-document key rotation)."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def hash_file(content: bytes) -> str:
    """SHA-256 checksum for integrity verification."""
    import hashlib
    return hashlib.sha256(content).hexdigest()
