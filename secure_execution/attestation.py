"""
attestation.py — Remote Attestation System

Implements challenge-response attestation, quote generation/verification,
platform integrity verification, and an attestation cache.

Simulated attestation is always available for development.
Production paths stub out SGX/SEV SDK calls with clear markers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AttestationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    PENDING = "pending"


class AttestationType(Enum):
    SIMULATED = "simulated"
    INTEL_SGX_DCAP = "intel_sgx_dcap"
    AMD_SEV_SNP = "amd_sev_snp"
    ARM_TRUSTZONE = "arm_trustzone"


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class AttestationReport:
    """A signed statement about the trustworthiness of an enclave."""
    enclave_id: str
    measurement: str          # hex-encoded SHA-256 of enclave code
    timestamp: float
    signature: str            # hex-encoded ECDSA signature
    nonce: str                # hex-encoded challenge nonce
    attestation_type: str = AttestationType.SIMULATED.value
    platform_id: str = ""
    report_data: str = ""     # arbitrary additional context (hex)
    version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttestationReport":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AttestationChallenge:
    challenge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nonce: str = field(default_factory=lambda: secrets.token_hex(32))
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300)  # 5 min TTL

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class VerificationResult:
    status: AttestationStatus
    report: Optional[AttestationReport]
    reason: str = ""
    verified_at: float = field(default_factory=time.time)
    cache_hit: bool = False


# ---------------------------------------------------------------------------
# Signing key management
# ---------------------------------------------------------------------------

class AttestationKeyManager:
    """Manages ECDSA keys used to sign and verify attestation reports."""

    def __init__(self) -> None:
        self._private_key: EllipticCurvePrivateKey = ec.generate_private_key(
            SECP256R1(), backend=default_backend()
        )
        self._public_key: EllipticCurvePublicKey = self._private_key.public_key()

    def sign(self, data: bytes) -> bytes:
        return self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    def verify(self, signature: bytes, data: bytes) -> bool:
        try:
            self._public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    def public_key_pem(self) -> bytes:
        return self._public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


# ---------------------------------------------------------------------------
# Quote generation
# ---------------------------------------------------------------------------

class QuoteGenerator:
    """Generates hardware-style attestation quotes (simulated for dev)."""

    def __init__(self, key_manager: AttestationKeyManager) -> None:
        self._km = key_manager

    def _build_quote_body(
        self,
        enclave_id: str,
        measurement: bytes,
        nonce: str,
        report_data: bytes,
        platform_id: str,
    ) -> bytes:
        """Canonical byte representation of the quote body (deterministic)."""
        parts = [
            enclave_id.encode(),
            b"|",
            measurement,
            b"|",
            nonce.encode(),
            b"|",
            report_data,
            b"|",
            platform_id.encode(),
        ]
        return b"".join(parts)

    def generate(
        self,
        enclave_id: str,
        measurement: bytes,
        nonce: str,
        report_data: bytes = b"",
        platform_id: str = "",
        attestation_type: AttestationType = AttestationType.SIMULATED,
    ) -> AttestationReport:
        body = self._build_quote_body(
            enclave_id, measurement, nonce, report_data, platform_id
        )
        sig_bytes = self._km.sign(body)
        return AttestationReport(
            enclave_id=enclave_id,
            measurement=measurement.hex(),
            timestamp=time.time(),
            signature=sig_bytes.hex(),
            nonce=nonce,
            attestation_type=attestation_type.value,
            platform_id=platform_id,
            report_data=report_data.hex(),
        )

    def verify_quote(self, report: AttestationReport) -> bool:
        measurement = bytes.fromhex(report.measurement)
        report_data = bytes.fromhex(report.report_data) if report.report_data else b""
        body = self._build_quote_body(
            report.enclave_id,
            measurement,
            report.nonce,
            report_data,
            report.platform_id,
        )
        sig_bytes = bytes.fromhex(report.signature)
        return self._km.verify(sig_bytes, body)


# ---------------------------------------------------------------------------
# Attestation Cache
# ---------------------------------------------------------------------------

class AttestationCache:
    """LRU-style cache that avoids repeated verification for recent reports."""

    def __init__(self, ttl_seconds: float = 300, max_size: int = 1000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: Dict[str, Tuple[VerificationResult, float]] = {}

    def _key(self, report: AttestationReport) -> str:
        return hashlib.sha256(
            f"{report.enclave_id}:{report.measurement}:{report.nonce}".encode()
        ).hexdigest()

    def get(self, report: AttestationReport) -> Optional[VerificationResult]:
        k = self._key(report)
        entry = self._store.get(k)
        if entry is None:
            return None
        result, cached_at = entry
        if time.time() - cached_at > self._ttl:
            del self._store[k]
            return None
        result.cache_hit = True
        return result

    def put(self, report: AttestationReport, result: VerificationResult) -> None:
        if len(self._store) >= self._max_size:
            # Evict oldest entry
            oldest = min(self._store.items(), key=lambda x: x[1][1])
            del self._store[oldest[0]]
        self._store[self._key(report)] = (result, time.time())

    def invalidate(self, enclave_id: str) -> int:
        to_del = [
            k for k, (r, _) in self._store.items()
            if r.report and r.report.enclave_id == enclave_id
        ]
        for k in to_del:
            del self._store[k]
        return len(to_del)

    def size(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Platform Integrity Verifier
# ---------------------------------------------------------------------------

class PlatformIntegrityVerifier:
    """Checks OS-level indicators of platform integrity."""

    def verify(self) -> Tuple[bool, List[str]]:
        """Return (is_trusted, list_of_issues)."""
        issues: List[str] = []

        # Check for common debug indicators
        if os.environ.get("TEE_DEBUG_MODE") == "1":
            issues.append("TEE_DEBUG_MODE is set — platform in debug mode")

        # Check for secure boot (Linux)
        try:
            sb_path = "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
            if os.path.exists(sb_path):
                with open(sb_path, "rb") as f:
                    content = f.read()
                if len(content) >= 5 and content[4] != 1:
                    issues.append("Secure Boot is disabled")
            else:
                logger.debug("Secure Boot EFI variable not found (non-EFI or permission denied).")
        except PermissionError:
            logger.debug("Cannot read Secure Boot status (permission denied).")
        except Exception as exc:
            logger.debug("Secure Boot check skipped: %s", exc)

        # Check for hypervisor (may indicate nested virtualisation risks)
        try:
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read().lower()
            if "hypervisor" in cpuinfo:
                logger.debug("Running inside a hypervisor.")
        except Exception:
            pass

        return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Remote Attestation Protocol
# ---------------------------------------------------------------------------

class RemoteAttestationProtocol:
    """
    Implements the verifier side of a challenge-response attestation protocol.

    Flow:
      1. Verifier issues challenge (nonce).
      2. Prover generates an AttestationReport including the nonce.
      3. Verifier calls verify_response() to check signature + freshness.
    """

    def __init__(
        self,
        key_manager: Optional[AttestationKeyManager] = None,
        cache_ttl: float = 300,
        max_report_age: float = 60,
    ) -> None:
        self._km = key_manager or AttestationKeyManager()
        self._quote_gen = QuoteGenerator(self._km)
        self._cache = AttestationCache(ttl_seconds=cache_ttl)
        self._active_challenges: Dict[str, AttestationChallenge] = {}
        self._max_report_age = max_report_age

    # ------------------------------------------------------------------
    def issue_challenge(self) -> AttestationChallenge:
        challenge = AttestationChallenge()
        self._active_challenges[challenge.challenge_id] = challenge
        logger.debug("Challenge issued: %s", challenge.challenge_id)
        return challenge

    # ------------------------------------------------------------------
    def generate_response(
        self,
        challenge: AttestationChallenge,
        enclave_id: str,
        measurement: bytes,
        platform_id: str = "",
        report_data: bytes = b"",
        attestation_type: AttestationType = AttestationType.SIMULATED,
    ) -> AttestationReport:
        """Prover calls this to generate an attestation report in response to a challenge."""
        if challenge.is_expired():
            raise ValueError("Challenge has expired.")
        return self._quote_gen.generate(
            enclave_id=enclave_id,
            measurement=measurement,
            nonce=challenge.nonce,
            report_data=report_data,
            platform_id=platform_id,
            attestation_type=attestation_type,
        )

    # ------------------------------------------------------------------
    def verify_response(
        self,
        challenge: AttestationChallenge,
        report: AttestationReport,
        expected_measurement: Optional[bytes] = None,
    ) -> VerificationResult:
        """Verifier calls this to validate the prover's attestation report."""

        # Check cache first
        cached = self._cache.get(report)
        if cached is not None:
            logger.debug("Cache hit for report from enclave %s", report.enclave_id)
            return cached

        # Challenge validity
        if challenge.is_expired():
            result = VerificationResult(
                status=AttestationStatus.EXPIRED,
                report=report,
                reason="Challenge has expired",
            )
            return result

        # Nonce freshness
        if report.nonce != challenge.nonce:
            result = VerificationResult(
                status=AttestationStatus.INVALID,
                report=report,
                reason="Nonce mismatch",
            )
            return result

        # Report age
        age = time.time() - report.timestamp
        if age > self._max_report_age:
            result = VerificationResult(
                status=AttestationStatus.EXPIRED,
                report=report,
                reason=f"Report is too old ({age:.1f}s > {self._max_report_age}s)",
            )
            return result

        # Signature verification
        if not self._quote_gen.verify_quote(report):
            result = VerificationResult(
                status=AttestationStatus.INVALID,
                report=report,
                reason="Signature verification failed",
            )
            return result

        # Optional measurement check
        if expected_measurement is not None:
            if report.measurement != expected_measurement.hex():
                result = VerificationResult(
                    status=AttestationStatus.INVALID,
                    report=report,
                    reason="Measurement mismatch — enclave code may have been tampered with",
                )
                return result

        result = VerificationResult(
            status=AttestationStatus.VALID,
            report=report,
            reason="All checks passed",
        )
        self._cache.put(report, result)
        logger.info("Attestation VALID for enclave %s", report.enclave_id)
        return result

    # ------------------------------------------------------------------
    def get_current_report(
        self,
        enclave_id: str,
        measurement: bytes,
        platform_id: str = "",
    ) -> AttestationReport:
        """Generate a fresh report with a newly issued challenge (self-attesting)."""
        challenge = self.issue_challenge()
        return self.generate_response(
            challenge=challenge,
            enclave_id=enclave_id,
            measurement=measurement,
            platform_id=platform_id,
        )

    @property
    def cache(self) -> AttestationCache:
        return self._cache

    @property
    def key_manager(self) -> AttestationKeyManager:
        return self._km
