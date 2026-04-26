"""SintraPrime-Unified — Secure Execution Layer"""
from secure_execution.tee_manager import (
    TEEProvider,
    SimulatedTEE,
    IntelSGXProvider,
    AMDSEVProvider,
    ARMTrustZoneProvider,
    SecureEnclaveContext,
    TEEProviderFactory,
    TEEType,
    TEEStatus,
)
from secure_execution.attestation import (
    AttestationReport,
    RemoteAttestationProtocol,
    AttestationCache,
    PlatformIntegrityVerifier,
)
from secure_execution.zero_trust import (
    ZeroTrustGateway,
    IdentityVerifier,
    MicroSegmentation,
    ContinuousAuthorizer,
    PolicyEngine,
    PolicyDecision,
)
from secure_execution.document_vault import DocumentVault, DocumentAccessLog

__all__ = [
    "TEEProvider", "SimulatedTEE", "IntelSGXProvider", "AMDSEVProvider",
    "ARMTrustZoneProvider", "SecureEnclaveContext", "TEEProviderFactory",
    "TEEType", "TEEStatus",
    "AttestationReport", "RemoteAttestationProtocol", "AttestationCache",
    "PlatformIntegrityVerifier",
    "ZeroTrustGateway", "IdentityVerifier", "MicroSegmentation",
    "ContinuousAuthorizer", "PolicyEngine", "PolicyDecision",
    "DocumentVault", "DocumentAccessLog",
]
