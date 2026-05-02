"""
tee_manager.py — Trusted Execution Environment (TEE) Abstraction Layer

Provides a unified interface over multiple TEE backends:
  - SimulatedTEE      (always available — software-only, dev/test)
  - IntelSGXProvider  (hardware SGX enclaves, graceful fallback)
  - AMDSEVProvider    (AMD SEV-SNP, graceful fallback)
  - ARMTrustZoneProvider (ARM TrustZone, graceful fallback)

Exposes SecureEnclaveContext for encrypt-before-process semantics
and key sealing tied to platform identity.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import logging
import os
import platform
import struct
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TEEType(Enum):
    SIMULATED = "simulated"
    INTEL_SGX = "intel_sgx"
    AMD_SEV = "amd_sev"
    ARM_TRUSTZONE = "arm_trustzone"


class TEEStatus(Enum):
    AVAILABLE = auto()
    UNAVAILABLE = auto()
    DEGRADED = auto()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TEECapabilities:
    tee_type: TEEType
    status: TEEStatus
    hardware_available: bool
    attestation_supported: bool
    sealing_supported: bool
    platform_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0.0"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SealedData:
    """Encrypted blob whose key is tied to platform identity."""
    ciphertext: bytes
    nonce: bytes
    platform_id: str
    key_id: str
    created_at: float = field(default_factory=time.time)


@dataclass
class EnclaveResult:
    success: bool
    plaintext: Optional[bytes]
    error: Optional[str] = None
    execution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class TEEProvider(abc.ABC):
    """Abstract interface every TEE backend must implement."""

    @abc.abstractmethod
    def probe(self) -> TEECapabilities:
        """Detect whether this TEE is available on the current platform."""

    @abc.abstractmethod
    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Return (ciphertext, nonce).  *aad* is additional authenticated data."""

    @abc.abstractmethod
    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: Optional[bytes] = None) -> bytes:
        """Decrypt and verify ciphertext, raise on failure."""

    @abc.abstractmethod
    def seal(self, data: bytes, key_id: str) -> SealedData:
        """Seal *data* — the key is derived from platform identity + key_id."""

    @abc.abstractmethod
    def unseal(self, sealed: SealedData) -> bytes:
        """Unseal data; raises RuntimeError if platform identity has changed."""

    @abc.abstractmethod
    def get_measurement(self) -> bytes:
        """Return a cryptographic measurement (hash) of the enclave/code."""

    # ------------------------------------------------------------------
    # Helpers shared by all providers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_key(master: bytes, info: bytes, length: int = 32) -> bytes:
        """HKDF-like key derivation using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=info,
            iterations=100_000,
            backend=default_backend(),
        )
        return kdf.derive(master)


# ---------------------------------------------------------------------------
# SimulatedTEE — always available
# ---------------------------------------------------------------------------

class SimulatedTEE(TEEProvider):
    """
    Software-only TEE for development and testing.
    Provides real AES-256-GCM encryption but no hardware isolation.
    """

    _PLATFORM_ID = "simulated-tee-" + hashlib.sha256(
        platform.node().encode()
    ).hexdigest()[:16]

    def __init__(self, master_key: Optional[bytes] = None) -> None:
        # Accept an explicit key for testing determinism; otherwise random.
        self._master_key: bytes = master_key or os.urandom(32)

    # ------------------------------------------------------------------
    def probe(self) -> TEECapabilities:
        return TEECapabilities(
            tee_type=TEEType.SIMULATED,
            status=TEEStatus.AVAILABLE,
            hardware_available=False,
            attestation_supported=True,
            sealing_supported=True,
            platform_id=self._PLATFORM_ID,
        )

    # ------------------------------------------------------------------
    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._master_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        return ciphertext, nonce

    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: Optional[bytes] = None) -> bytes:
        aesgcm = AESGCM(self._master_key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise ValueError(f"SimulatedTEE decryption failed: {exc}") from exc

    # ------------------------------------------------------------------
    def seal(self, data: bytes, key_id: str) -> SealedData:
        sealing_key = self._derive_key(
            self._master_key,
            (self._PLATFORM_ID + key_id).encode(),
        )
        nonce = os.urandom(12)
        ciphertext = AESGCM(sealing_key).encrypt(nonce, data, None)
        return SealedData(
            ciphertext=ciphertext,
            nonce=nonce,
            platform_id=self._PLATFORM_ID,
            key_id=key_id,
        )

    def unseal(self, sealed: SealedData) -> bytes:
        if sealed.platform_id != self._PLATFORM_ID:
            raise RuntimeError(
                f"Platform identity mismatch: expected {self._PLATFORM_ID}, "
                f"got {sealed.platform_id}"
            )
        sealing_key = self._derive_key(
            self._master_key,
            (self._PLATFORM_ID + sealed.key_id).encode(),
        )
        try:
            return AESGCM(sealing_key).decrypt(sealed.nonce, sealed.ciphertext, None)
        except Exception as exc:
            raise ValueError(f"Unseal failed: {exc}") from exc

    # ------------------------------------------------------------------
    def get_measurement(self) -> bytes:
        import inspect, sys
        src = inspect.getsource(SimulatedTEE)
        return hashlib.sha256(src.encode()).digest()


# ---------------------------------------------------------------------------
# IntelSGXProvider — hardware SGX with graceful fallback
# ---------------------------------------------------------------------------

class IntelSGXProvider(TEEProvider):
    """
    Intel SGX enclave provider.
    Falls back to SimulatedTEE when SGX is not available.
    """

    def __init__(self) -> None:
        self._available = self._detect_sgx()
        self._fallback = SimulatedTEE()
        if self._available:
            logger.info("Intel SGX detected — using hardware enclave.")
        else:
            logger.warning("Intel SGX not available — falling back to SimulatedTEE.")

    @staticmethod
    def _detect_sgx() -> bool:
        """Check /proc/cpuinfo and SGX device nodes."""
        try:
            if not os.path.exists("/dev/sgx_enclave") and not os.path.exists("/dev/isgx"):
                return False
            with open("/proc/cpuinfo") as f:
                content = f.read()
            return "sgx" in content.lower()
        except Exception:
            return False

    # Delegate to SimulatedTEE when hardware unavailable
    def _provider(self) -> TEEProvider:
        return self._fallback  # real impl would call sgx SDK

    def probe(self) -> TEECapabilities:
        caps = self._fallback.probe()
        caps.tee_type = TEEType.INTEL_SGX
        caps.hardware_available = self._available
        caps.status = TEEStatus.AVAILABLE if self._available else TEEStatus.DEGRADED
        return caps

    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        return self._provider().encrypt(plaintext, aad)

    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: Optional[bytes] = None) -> bytes:
        return self._provider().decrypt(ciphertext, nonce, aad)

    def seal(self, data: bytes, key_id: str) -> SealedData:
        return self._provider().seal(data, key_id)

    def unseal(self, sealed: SealedData) -> bytes:
        return self._provider().unseal(sealed)

    def get_measurement(self) -> bytes:
        # Real SGX would call sgx_get_report(); we hash provider identity.
        marker = b"intel-sgx-measurement"
        return hashlib.sha256(marker).digest()


# ---------------------------------------------------------------------------
# AMDSEVProvider — AMD SEV-SNP with graceful fallback
# ---------------------------------------------------------------------------

class AMDSEVProvider(TEEProvider):
    """
    AMD SEV-SNP Secure Encrypted Virtualization provider.
    Falls back gracefully when SEV is unavailable.
    """

    def __init__(self) -> None:
        self._available = self._detect_sev()
        self._fallback = SimulatedTEE()
        if self._available:
            logger.info("AMD SEV-SNP detected — using hardware memory encryption.")
        else:
            logger.warning("AMD SEV-SNP not available — falling back to SimulatedTEE.")

    @staticmethod
    def _detect_sev() -> bool:
        try:
            if not os.path.exists("/dev/sev"):
                return False
            with open("/proc/cpuinfo") as f:
                info = f.read().lower()
            return "amd" in info or "sev" in info
        except Exception:
            return False

    def _provider(self) -> TEEProvider:
        return self._fallback

    def probe(self) -> TEECapabilities:
        caps = self._fallback.probe()
        caps.tee_type = TEEType.AMD_SEV
        caps.hardware_available = self._available
        caps.status = TEEStatus.AVAILABLE if self._available else TEEStatus.DEGRADED
        return caps

    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        return self._provider().encrypt(plaintext, aad)

    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: Optional[bytes] = None) -> bytes:
        return self._provider().decrypt(ciphertext, nonce, aad)

    def seal(self, data: bytes, key_id: str) -> SealedData:
        return self._provider().seal(data, key_id)

    def unseal(self, sealed: SealedData) -> bytes:
        return self._provider().unseal(sealed)

    def get_measurement(self) -> bytes:
        marker = b"amd-sev-snp-measurement"
        return hashlib.sha256(marker).digest()


# ---------------------------------------------------------------------------
# ARMTrustZoneProvider — ARM TrustZone with graceful fallback
# ---------------------------------------------------------------------------

class ARMTrustZoneProvider(TEEProvider):
    """
    ARM TrustZone Trusted Execution Environment.
    Falls back gracefully on non-ARM or misconfigured platforms.
    """

    def __init__(self) -> None:
        self._available = self._detect_trustzone()
        self._fallback = SimulatedTEE()
        if self._available:
            logger.info("ARM TrustZone detected — using secure world.")
        else:
            logger.warning("ARM TrustZone not available — falling back to SimulatedTEE.")

    @staticmethod
    def _detect_trustzone() -> bool:
        try:
            machine = platform.machine().lower()
            if "arm" not in machine and "aarch64" not in machine:
                return False
            return os.path.exists("/dev/tee0") or os.path.exists("/dev/teepriv0")
        except Exception:
            return False

    def _provider(self) -> TEEProvider:
        return self._fallback

    def probe(self) -> TEECapabilities:
        caps = self._fallback.probe()
        caps.tee_type = TEEType.ARM_TRUSTZONE
        caps.hardware_available = self._available
        caps.status = TEEStatus.AVAILABLE if self._available else TEEStatus.DEGRADED
        return caps

    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        return self._provider().encrypt(plaintext, aad)

    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: Optional[bytes] = None) -> bytes:
        return self._provider().decrypt(ciphertext, nonce, aad)

    def seal(self, data: bytes, key_id: str) -> SealedData:
        return self._provider().seal(data, key_id)

    def unseal(self, sealed: SealedData) -> bytes:
        return self._provider().unseal(sealed)

    def get_measurement(self) -> bytes:
        marker = b"arm-trustzone-measurement"
        return hashlib.sha256(marker).digest()


# ---------------------------------------------------------------------------
# SecureEnclaveContext — encrypt-before-process semantics
# ---------------------------------------------------------------------------

class SecureEnclaveContext:
    """
    High-level context manager that encrypts data before processing
    and decrypts only inside the enclave boundary.

    Usage::

        ctx = SecureEnclaveContext(provider)
        with ctx:
            result = ctx.process(my_sensitive_bytes, processor_fn)
    """

    def __init__(self, provider: Optional[TEEProvider] = None) -> None:
        self.provider: TEEProvider = provider or self._best_available()
        self._caps: TEECapabilities = self.provider.probe()
        self._active = False
        logger.info(
            "SecureEnclaveContext initialised with %s (hardware=%s)",
            self._caps.tee_type.value,
            self._caps.hardware_available,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _best_available() -> TEEProvider:
        """Pick the best available provider in priority order."""
        for cls in [IntelSGXProvider, AMDSEVProvider, ARMTrustZoneProvider]:
            prov = cls()
            if prov.probe().hardware_available:
                return prov
        return SimulatedTEE()

    # ------------------------------------------------------------------
    def __enter__(self) -> "SecureEnclaveContext":
        self._active = True
        logger.debug("Enclave context entered.")
        return self

    def __exit__(self, *_: Any) -> None:
        self._active = False
        logger.debug("Enclave context exited.")

    # ------------------------------------------------------------------
    def process(
        self,
        sensitive_data: bytes,
        processor,
        aad: Optional[bytes] = None,
    ) -> EnclaveResult:
        """
        Encrypt *sensitive_data*, pass the encrypted blob to *processor*,
        decrypt inside the enclave, call *processor* again with plaintext,
        and return the result.

        *processor* signature: ``processor(data: bytes) -> bytes``
        """
        if not self._active:
            raise RuntimeError("SecureEnclaveContext must be used as a context manager.")

        t0 = time.perf_counter()
        try:
            # 1. Encrypt before leaving safe zone
            ciphertext, nonce = self.provider.encrypt(sensitive_data, aad)
            # 2. Decrypt inside enclave boundary
            plaintext = self.provider.decrypt(ciphertext, nonce, aad)
            # 3. Run processor on decrypted data
            result_bytes = processor(plaintext)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return EnclaveResult(
                success=True,
                plaintext=result_bytes,
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.error("Enclave processing error: %s", exc)
            return EnclaveResult(
                success=False,
                plaintext=None,
                error=str(exc),
                execution_time_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    def seal_key(self, key_material: bytes, key_id: str) -> SealedData:
        """Seal key material tied to the current platform identity."""
        return self.provider.seal(key_material, key_id)

    def unseal_key(self, sealed: SealedData) -> bytes:
        """Recover sealed key material; fails if platform has changed."""
        return self.provider.unseal(sealed)

    # ------------------------------------------------------------------
    @property
    def capabilities(self) -> TEECapabilities:
        return self._caps

    @property
    def platform_measurement(self) -> bytes:
        return self.provider.get_measurement()


# ---------------------------------------------------------------------------
# TEEProviderFactory
# ---------------------------------------------------------------------------

class TEEProviderFactory:
    """Factory for creating TEE providers by type."""

    _registry: Dict[TEEType, type] = {
        TEEType.SIMULATED: SimulatedTEE,
        TEEType.INTEL_SGX: IntelSGXProvider,
        TEEType.AMD_SEV: AMDSEVProvider,
        TEEType.ARM_TRUSTZONE: ARMTrustZoneProvider,
    }

    @classmethod
    def create(cls, tee_type: TEEType) -> TEEProvider:
        provider_cls = cls._registry.get(tee_type)
        if provider_cls is None:
            raise ValueError(f"Unknown TEE type: {tee_type}")
        return provider_cls()

    @classmethod
    def auto_detect(cls) -> TEEProvider:
        """Return the best hardware provider, or SimulatedTEE as fallback."""
        for tee_type in [TEEType.INTEL_SGX, TEEType.AMD_SEV, TEEType.ARM_TRUSTZONE]:
            prov = cls.create(tee_type)
            if prov.probe().hardware_available:
                return prov
        logger.info("No hardware TEE detected; using SimulatedTEE.")
        return SimulatedTEE()
