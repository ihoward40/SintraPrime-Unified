"""
document_vault.py — Encrypted Document Vault

Provides AES-256-GCM encryption for legal documents at rest, using
PBKDF2-derived keys from a user master password.  Includes:

  - DocumentVault           : store / retrieve / shred documents
  - VaultKeyManager         : PBKDF2 key derivation + per-document key wrapping
  - DocumentAccessLog       : immutable append-only access audit trail
  - TemporaryAccessToken    : auto-expiring read tokens for sharing
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class VaultOperation(Enum):
    STORE = "store"
    RETRIEVE = "retrieve"
    SHRED = "shred"
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    LIST = "list"


class DocumentStatus(Enum):
    ACTIVE = "active"
    SHREDDED = "shredded"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DocumentMetadata:
    doc_id: str
    name: str
    owner: str
    created_at: float
    modified_at: float
    size_bytes: int
    content_type: str = "application/octet-stream"
    tags: List[str] = field(default_factory=list)
    status: str = DocumentStatus.ACTIVE.value
    expires_at: Optional[float] = None


@dataclass
class EncryptedDocument:
    doc_id: str
    ciphertext: bytes
    nonce: bytes
    wrapped_key: bytes          # per-document key encrypted with master key
    wrapped_key_nonce: bytes
    key_salt: bytes             # PBKDF2 salt for master key derivation
    metadata: DocumentMetadata


@dataclass
class AccessLogEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    subject: str = ""
    operation: str = ""
    timestamp: float = field(default_factory=time.time)
    ip_address: Optional[str] = None
    success: bool = True
    details: str = ""


@dataclass
class TemporaryAccessToken:
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    granted_to: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    used: bool = False
    max_uses: int = 1
    use_count: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_exhausted(self) -> bool:
        return self.use_count >= self.max_uses

    def is_valid(self) -> bool:
        return not self.is_expired() and not self.is_exhausted()


# ---------------------------------------------------------------------------
# Key Manager
# ---------------------------------------------------------------------------

class VaultKeyManager:
    """
    Derives an AES-256 master key from the user's password via PBKDF2.
    Each document gets its own random DEK (Data Encryption Key) which is
    wrapped (encrypted) by the master key.
    """

    PBKDF2_ITERATIONS = 260_000  # OWASP 2023 recommendation for SHA-256
    KEY_LENGTH = 32              # 256 bits

    def __init__(self) -> None:
        self._master_cache: Dict[str, bytes] = {}   # password_hash -> master_key

    # ------------------------------------------------------------------
    def derive_master_key(self, password: str, salt: bytes) -> bytes:
        """Derive the master key from a user password and a stored salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    def new_salt(self) -> bytes:
        return os.urandom(32)

    # ------------------------------------------------------------------
    def generate_dek(self) -> bytes:
        """Generate a fresh random Data Encryption Key."""
        return os.urandom(self.KEY_LENGTH)

    # ------------------------------------------------------------------
    def wrap_dek(self, dek: bytes, master_key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt the DEK with the master key. Returns (wrapped_key, nonce)."""
        nonce = os.urandom(12)
        wrapped = AESGCM(master_key).encrypt(nonce, dek, None)
        return wrapped, nonce

    def unwrap_dek(self, wrapped_key: bytes, nonce: bytes, master_key: bytes) -> bytes:
        """Decrypt and recover the DEK."""
        try:
            return AESGCM(master_key).decrypt(nonce, wrapped_key, None)
        except Exception as exc:
            raise ValueError(f"DEK unwrap failed — wrong password or corrupted key: {exc}") from exc

    # ------------------------------------------------------------------
    def encrypt_document(
        self, plaintext: bytes, dek: bytes, aad: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """Encrypt document content with its DEK. Returns (ciphertext, nonce)."""
        nonce = os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext, aad)
        return ciphertext, nonce

    def decrypt_document(
        self, ciphertext: bytes, nonce: bytes, dek: bytes, aad: Optional[bytes] = None
    ) -> bytes:
        """Decrypt document content."""
        try:
            return AESGCM(dek).decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise ValueError(f"Document decryption failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Document Access Log
# ---------------------------------------------------------------------------

class DocumentAccessLog:
    """Append-only, in-memory access audit trail with optional file persistence."""

    def __init__(self, log_path: Optional[str] = None) -> None:
        self._entries: List[AccessLogEntry] = []
        self._lock = threading.RLock()  # reentrant — shred() calls retrieve() internally
        self._log_path = log_path

    def record(
        self,
        doc_id: str,
        subject: str,
        operation: VaultOperation,
        success: bool = True,
        details: str = "",
        ip_address: Optional[str] = None,
    ) -> AccessLogEntry:
        entry = AccessLogEntry(
            doc_id=doc_id,
            subject=subject,
            operation=operation.value,
            success=success,
            details=details,
            ip_address=ip_address,
        )
        with self._lock:
            self._entries.append(entry)
        if self._log_path:
            self._persist(entry)
        return entry

    def _persist(self, entry: AccessLogEntry) -> None:
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist access log entry: %s", exc)

    def query(
        self,
        doc_id: Optional[str] = None,
        subject: Optional[str] = None,
        operation: Optional[VaultOperation] = None,
        since: Optional[float] = None,
        limit: int = 500,
    ) -> List[AccessLogEntry]:
        with self._lock:
            results = list(self._entries)

        if doc_id:
            results = [e for e in results if e.doc_id == doc_id]
        if subject:
            results = [e for e in results if e.subject == subject]
        if operation:
            results = [e for e in results if e.operation == operation.value]
        if since:
            results = [e for e in results if e.timestamp >= since]

        return results[-limit:]

    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)


# ---------------------------------------------------------------------------
# Secure Shredder
# ---------------------------------------------------------------------------

class SecureShredder:
    """
    Overwrites data multiple times before deletion to prevent recovery.
    (Effective for HDDs; SSDs/NVMe may require full-disk encryption instead.)
    """

    PASSES = 3

    @staticmethod
    def shred_bytes(data: bytearray) -> None:
        """Overwrite a bytearray in-place with random data, then zeros."""
        for _ in range(SecureShredder.PASSES):
            for i in range(len(data)):
                data[i] = secrets.randbits(8)
        for i in range(len(data)):
            data[i] = 0

    @staticmethod
    def shred_file(path: str) -> None:
        """Overwrite a file with random data then delete it."""
        if not os.path.exists(path):
            return
        size = os.path.getsize(path)
        for _ in range(SecureShredder.PASSES):
            with open(path, "r+b") as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
        os.remove(path)
        logger.info("Securely shredded file: %s", path)


# ---------------------------------------------------------------------------
# Token Store
# ---------------------------------------------------------------------------

class TemporaryTokenStore:
    """In-memory store for temporary access tokens with automatic expiry."""

    def __init__(self) -> None:
        self._tokens: Dict[str, TemporaryAccessToken] = {}
        self._lock = threading.RLock()  # reentrant — shred() calls retrieve() internally

    def issue(
        self,
        doc_id: str,
        granted_to: str,
        ttl_seconds: float = 3600,
        max_uses: int = 1,
    ) -> TemporaryAccessToken:
        token = TemporaryAccessToken(
            doc_id=doc_id,
            granted_to=granted_to,
            expires_at=time.time() + ttl_seconds,
            max_uses=max_uses,
        )
        with self._lock:
            self._tokens[token.token_id] = token
        return token

    def consume(self, token_id: str, subject: str) -> Optional[TemporaryAccessToken]:
        """Validate and consume one use of the token; returns None if invalid."""
        with self._lock:
            token = self._tokens.get(token_id)
            if token is None:
                return None
            if not token.is_valid():
                return None
            if token.granted_to != subject:
                return None
            token.use_count += 1
            if token.is_exhausted():
                del self._tokens[token_id]
            return token

    def revoke(self, token_id: str) -> bool:
        with self._lock:
            return self._tokens.pop(token_id, None) is not None

    def purge_expired(self) -> int:
        with self._lock:
            expired = [tid for tid, t in self._tokens.items() if t.is_expired()]
            for tid in expired:
                del self._tokens[tid]
        return len(expired)

    def active_count(self) -> int:
        return sum(1 for t in self._tokens.values() if t.is_valid())


# ---------------------------------------------------------------------------
# Document Vault
# ---------------------------------------------------------------------------

class DocumentVault:
    """
    High-level vault that stores, retrieves, and shreds encrypted documents.

    All documents are encrypted at rest using AES-256-GCM.
    The key hierarchy is:
        master_key = PBKDF2(password, salt)
        dek        = random 256-bit key per document
        ciphertext = AES-256-GCM(dek, plaintext)
        wrapped_dek= AES-256-GCM(master_key, dek)

    Only the wrapped_dek, ciphertext, nonces, and salt are stored.
    The master key is never persisted.
    """

    def __init__(
        self,
        access_log: Optional[DocumentAccessLog] = None,
        token_store: Optional[TemporaryTokenStore] = None,
    ) -> None:
        self._key_mgr = VaultKeyManager()
        self._docs: Dict[str, EncryptedDocument] = {}
        self._access_log = access_log or DocumentAccessLog()
        self._token_store = token_store or TemporaryTokenStore()
        self._lock = threading.RLock()  # reentrant — shred() calls retrieve() internally

    # ------------------------------------------------------------------
    def store(
        self,
        plaintext: bytes,
        name: str,
        owner: str,
        password: str,
        content_type: str = "application/octet-stream",
        tags: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
    ) -> str:
        """Encrypt and store a document. Returns the doc_id."""
        doc_id = str(uuid.uuid4())
        salt = self._key_mgr.new_salt()
        master_key = self._key_mgr.derive_master_key(password, salt)
        dek = self._key_mgr.generate_dek()

        # Encrypt document content
        aad = doc_id.encode()   # bind ciphertext to doc_id
        ciphertext, nonce = self._key_mgr.encrypt_document(plaintext, dek, aad)

        # Wrap DEK
        wrapped_key, wk_nonce = self._key_mgr.wrap_dek(dek, master_key)

        metadata = DocumentMetadata(
            doc_id=doc_id,
            name=name,
            owner=owner,
            created_at=time.time(),
            modified_at=time.time(),
            size_bytes=len(plaintext),
            content_type=content_type,
            tags=tags or [],
            expires_at=expires_at,
        )

        enc_doc = EncryptedDocument(
            doc_id=doc_id,
            ciphertext=ciphertext,
            nonce=nonce,
            wrapped_key=wrapped_key,
            wrapped_key_nonce=wk_nonce,
            key_salt=salt,
            metadata=metadata,
        )

        with self._lock:
            self._docs[doc_id] = enc_doc

        # Securely wipe the DEK from memory
        dek_arr = bytearray(dek)
        SecureShredder.shred_bytes(dek_arr)
        del dek_arr

        self._access_log.record(doc_id, owner, VaultOperation.STORE,
                                success=True, details=f"name={name}")
        logger.info("Document stored: %s (%s)", doc_id, name)
        return doc_id

    # ------------------------------------------------------------------
    def retrieve(
        self,
        doc_id: str,
        password: str,
        subject: str,
        temp_token_id: Optional[str] = None,
    ) -> bytes:
        """Decrypt and return a document's plaintext."""
        with self._lock:
            enc_doc = self._docs.get(doc_id)

        if enc_doc is None:
            self._access_log.record(doc_id, subject, VaultOperation.RETRIEVE,
                                    success=False, details="Document not found")
            raise FileNotFoundError(f"Document {doc_id} not found")

        # Expiry check
        meta = enc_doc.metadata
        if meta.expires_at and time.time() > meta.expires_at:
            self._access_log.record(doc_id, subject, VaultOperation.RETRIEVE,
                                    success=False, details="Document expired")
            raise PermissionError(f"Document {doc_id} has expired")

        # Temp token check (if not owner)
        if subject != meta.owner:
            if temp_token_id is None:
                self._access_log.record(doc_id, subject, VaultOperation.RETRIEVE,
                                        success=False, details="No access token provided")
                raise PermissionError("Access denied — no valid token")

            token = self._token_store.consume(temp_token_id, subject)
            if token is None or token.doc_id != doc_id:
                self._access_log.record(doc_id, subject, VaultOperation.RETRIEVE,
                                        success=False, details="Invalid or expired token")
                raise PermissionError("Access denied — invalid or expired token")

        master_key = self._key_mgr.derive_master_key(password, enc_doc.key_salt)
        dek = self._key_mgr.unwrap_dek(
            enc_doc.wrapped_key, enc_doc.wrapped_key_nonce, master_key
        )
        aad = doc_id.encode()
        plaintext = self._key_mgr.decrypt_document(
            enc_doc.ciphertext, enc_doc.nonce, dek, aad
        )

        # Wipe DEK from memory
        dek_arr = bytearray(dek)
        SecureShredder.shred_bytes(dek_arr)
        del dek_arr

        self._access_log.record(doc_id, subject, VaultOperation.RETRIEVE,
                                success=True, details=f"size={len(plaintext)}")
        return plaintext

    # ------------------------------------------------------------------
    def shred(self, doc_id: str, password: str, owner: str) -> None:
        """Securely delete a document — overwrites in-memory ciphertext."""
        with self._lock:
            enc_doc = self._docs.get(doc_id)
            if enc_doc is None:
                raise FileNotFoundError(f"Document {doc_id} not found")
            if enc_doc.metadata.owner != owner:
                self._access_log.record(doc_id, owner, VaultOperation.SHRED,
                                        success=False, details="Not owner")
                raise PermissionError("Only the document owner can shred it")

            # Verify password before shredding
            try:
                self.retrieve(doc_id, password, owner)
            except (ValueError, PermissionError, FileNotFoundError):
                raise PermissionError("Incorrect password — shred aborted")

            # Overwrite ciphertext in memory
            ct_arr = bytearray(enc_doc.ciphertext)
            SecureShredder.shred_bytes(ct_arr)
            del self._docs[doc_id]

        self._access_log.record(doc_id, owner, VaultOperation.SHRED,
                                success=True, details="Document securely shredded")
        logger.info("Document %s shredded by %s", doc_id, owner)

    # ------------------------------------------------------------------
    def grant_temp_access(
        self,
        doc_id: str,
        owner: str,
        granted_to: str,
        ttl_seconds: float = 3600,
        max_uses: int = 1,
    ) -> TemporaryAccessToken:
        with self._lock:
            enc_doc = self._docs.get(doc_id)
        if enc_doc is None:
            raise FileNotFoundError(f"Document {doc_id} not found")
        if enc_doc.metadata.owner != owner:
            raise PermissionError("Only the owner can grant access")
        token = self._token_store.issue(doc_id, granted_to, ttl_seconds, max_uses)
        self._access_log.record(doc_id, owner, VaultOperation.GRANT_ACCESS,
                                success=True, details=f"granted_to={granted_to}")
        return token

    # ------------------------------------------------------------------
    def list_documents(self, owner: str) -> List[DocumentMetadata]:
        """Return metadata for all documents owned by *owner*."""
        with self._lock:
            return [
                d.metadata for d in self._docs.values()
                if d.metadata.owner == owner
            ]

    def get_metadata(self, doc_id: str) -> Optional[DocumentMetadata]:
        with self._lock:
            enc = self._docs.get(doc_id)
        return enc.metadata if enc else None

    def document_count(self) -> int:
        return len(self._docs)

    @property
    def access_log(self) -> DocumentAccessLog:
        return self._access_log

    @property
    def token_store(self) -> TemporaryTokenStore:
        return self._token_store
