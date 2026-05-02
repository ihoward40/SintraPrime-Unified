"""
test_secure_execution.py — Comprehensive test suite for the Secure Execution Layer

Covers:
  - TEE abstraction (SimulatedTEE, IntelSGXProvider, AMDSEVProvider, ARMTrustZoneProvider)
  - SecureEnclaveContext
  - Attestation system (quotes, challenge-response, cache, integrity)
  - Zero-Trust security model (identity, policy, segmentation, continuous auth)
  - Document Vault (store, retrieve, shred, temp tokens, access log)

Run with:
    python -m pytest secure_execution/tests/ -v
"""

from __future__ import annotations

import base64
import os
import sys
import time
import uuid

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ---------------------------------------------------------------------------
# TEE Manager Tests
# ---------------------------------------------------------------------------

from secure_execution.tee_manager import (
    SimulatedTEE,
    IntelSGXProvider,
    AMDSEVProvider,
    ARMTrustZoneProvider,
    SecureEnclaveContext,
    TEEProviderFactory,
    TEEType,
    TEEStatus,
    SealedData,
)


class TestSimulatedTEE:

    def setup_method(self):
        self.tee = SimulatedTEE()

    def test_probe_returns_capabilities(self):
        caps = self.tee.probe()
        assert caps.tee_type == TEEType.SIMULATED

    def test_probe_status_available(self):
        caps = self.tee.probe()
        assert caps.status == TEEStatus.AVAILABLE

    def test_probe_no_hardware(self):
        caps = self.tee.probe()
        assert caps.hardware_available is False

    def test_probe_attestation_supported(self):
        caps = self.tee.probe()
        assert caps.attestation_supported is True

    def test_probe_sealing_supported(self):
        caps = self.tee.probe()
        assert caps.sealing_supported is True

    def test_encrypt_returns_ciphertext_and_nonce(self):
        ct, nonce = self.tee.encrypt(b"hello world")
        assert isinstance(ct, bytes)
        assert isinstance(nonce, bytes)
        assert len(nonce) == 12

    def test_encrypt_ciphertext_differs_from_plaintext(self):
        pt = b"secret data"
        ct, _ = self.tee.encrypt(pt)
        assert ct != pt

    def test_encrypt_decrypt_roundtrip(self):
        pt = b"my secret message"
        ct, nonce = self.tee.encrypt(pt)
        recovered = self.tee.decrypt(ct, nonce)
        assert recovered == pt

    def test_encrypt_decrypt_with_aad(self):
        pt = b"authenticated data"
        aad = b"context-info"
        ct, nonce = self.tee.encrypt(pt, aad)
        recovered = self.tee.decrypt(ct, nonce, aad)
        assert recovered == pt

    def test_decrypt_fails_with_wrong_aad(self):
        pt = b"data"
        ct, nonce = self.tee.encrypt(pt, b"correct-aad")
        with pytest.raises(Exception):
            self.tee.decrypt(ct, nonce, b"wrong-aad")

    def test_decrypt_fails_with_tampered_ciphertext(self):
        pt = b"important data"
        ct, nonce = self.tee.encrypt(pt)
        tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
        with pytest.raises(Exception):
            self.tee.decrypt(tampered, nonce)

    def test_each_encrypt_produces_unique_nonce(self):
        pt = b"same plaintext"
        _, n1 = self.tee.encrypt(pt)
        _, n2 = self.tee.encrypt(pt)
        assert n1 != n2

    def test_seal_returns_sealed_data(self):
        sealed = self.tee.seal(b"key material", "key-1")
        assert isinstance(sealed, SealedData)
        assert sealed.key_id == "key-1"

    def test_seal_unseal_roundtrip(self):
        original = b"secret key bytes"
        sealed = self.tee.seal(original, "my-key")
        recovered = self.tee.unseal(sealed)
        assert recovered == original

    def test_unseal_fails_wrong_platform(self):
        sealed = self.tee.seal(b"data", "key")
        # Tamper platform_id
        sealed.platform_id = "wrong-platform-000"
        with pytest.raises(RuntimeError):
            self.tee.unseal(sealed)

    def test_get_measurement_returns_bytes(self):
        m = self.tee.get_measurement()
        assert isinstance(m, bytes)
        assert len(m) == 32  # SHA-256

    def test_measurement_is_deterministic(self):
        m1 = self.tee.get_measurement()
        m2 = self.tee.get_measurement()
        assert m1 == m2


class TestIntelSGXProvider:

    def setup_method(self):
        self.provider = IntelSGXProvider()

    def test_probe_returns_intel_sgx_type(self):
        caps = self.provider.probe()
        assert caps.tee_type == TEEType.INTEL_SGX

    def test_encrypt_decrypt_roundtrip(self):
        pt = b"sgx protected data"
        ct, nonce = self.provider.encrypt(pt)
        recovered = self.provider.decrypt(ct, nonce)
        assert recovered == pt

    def test_seal_unseal_roundtrip(self):
        data = b"sgx sealed key"
        sealed = self.provider.seal(data, "sgx-key-1")
        recovered = self.provider.unseal(sealed)
        assert recovered == data

    def test_get_measurement_bytes(self):
        m = self.provider.get_measurement()
        assert isinstance(m, bytes)


class TestAMDSEVProvider:

    def setup_method(self):
        self.provider = AMDSEVProvider()

    def test_probe_returns_amd_sev_type(self):
        caps = self.provider.probe()
        assert caps.tee_type == TEEType.AMD_SEV

    def test_encrypt_decrypt_roundtrip(self):
        pt = b"sev protected data"
        ct, nonce = self.provider.encrypt(pt)
        recovered = self.provider.decrypt(ct, nonce)
        assert recovered == pt

    def test_seal_unseal_roundtrip(self):
        data = b"sev sealed key"
        sealed = self.provider.seal(data, "sev-key-1")
        recovered = self.provider.unseal(sealed)
        assert recovered == data


class TestARMTrustZoneProvider:

    def setup_method(self):
        self.provider = ARMTrustZoneProvider()

    def test_probe_returns_arm_trustzone_type(self):
        caps = self.provider.probe()
        assert caps.tee_type == TEEType.ARM_TRUSTZONE

    def test_encrypt_decrypt_roundtrip(self):
        pt = b"tz protected data"
        ct, nonce = self.provider.encrypt(pt)
        recovered = self.provider.decrypt(ct, nonce)
        assert recovered == pt


class TestTEEProviderFactory:

    def test_create_simulated(self):
        p = TEEProviderFactory.create(TEEType.SIMULATED)
        assert isinstance(p, SimulatedTEE)

    def test_create_sgx(self):
        p = TEEProviderFactory.create(TEEType.INTEL_SGX)
        assert isinstance(p, IntelSGXProvider)

    def test_create_sev(self):
        p = TEEProviderFactory.create(TEEType.AMD_SEV)
        assert isinstance(p, AMDSEVProvider)

    def test_create_trustzone(self):
        p = TEEProviderFactory.create(TEEType.ARM_TRUSTZONE)
        assert isinstance(p, ARMTrustZoneProvider)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError):
            TEEProviderFactory.create("unknown_type")  # type: ignore

    def test_auto_detect_returns_provider(self):
        p = TEEProviderFactory.auto_detect()
        assert p is not None


class TestSecureEnclaveContext:

    def setup_method(self):
        self.ctx = SecureEnclaveContext(SimulatedTEE())

    def test_context_manager_enter_exit(self):
        with self.ctx as c:
            assert c._active is True
        assert self.ctx._active is False

    def test_process_success(self):
        with self.ctx as c:
            result = c.process(b"hello", lambda data: data.upper())
        assert result.success is True
        assert result.plaintext == b"HELLO"

    def test_process_returns_execution_time(self):
        with self.ctx as c:
            result = c.process(b"data", lambda d: d)
        assert result.execution_time_ms >= 0

    def test_process_outside_context_raises(self):
        with pytest.raises(RuntimeError):
            self.ctx.process(b"data", lambda d: d)

    def test_seal_unseal_key(self):
        key_material = os.urandom(32)
        with self.ctx:
            sealed = self.ctx.seal_key(key_material, "test-key-id")
            recovered = self.ctx.unseal_key(sealed)
        assert recovered == key_material

    def test_capabilities_available(self):
        caps = self.ctx.capabilities
        assert caps is not None

    def test_platform_measurement_bytes(self):
        m = self.ctx.platform_measurement
        assert isinstance(m, bytes)

    def test_process_processor_error_captured(self):
        def bad_processor(data: bytes) -> bytes:
            raise ValueError("intentional error")

        with self.ctx as c:
            result = c.process(b"data", bad_processor)
        assert result.success is False
        assert "intentional error" in result.error


# ---------------------------------------------------------------------------
# Attestation Tests
# ---------------------------------------------------------------------------

from secure_execution.attestation import (
    AttestationReport,
    AttestationChallenge,
    AttestationCache,
    AttestationKeyManager,
    QuoteGenerator,
    VerificationResult,
    AttestationStatus,
    AttestationType,
    RemoteAttestationProtocol,
    PlatformIntegrityVerifier,
)


class TestAttestationKeyManager:

    def setup_method(self):
        self.km = AttestationKeyManager()

    def test_sign_returns_bytes(self):
        sig = self.km.sign(b"test data")
        assert isinstance(sig, bytes)

    def test_verify_valid_signature(self):
        data = b"important message"
        sig = self.km.sign(data)
        assert self.km.verify(sig, data) is True

    def test_verify_rejects_tampered_data(self):
        sig = self.km.sign(b"original")
        assert self.km.verify(sig, b"tampered") is False

    def test_verify_rejects_tampered_signature(self):
        data = b"data"
        sig = bytearray(self.km.sign(data))
        sig[0] ^= 0xFF
        assert self.km.verify(bytes(sig), data) is False

    def test_public_key_pem(self):
        pem = self.km.public_key_pem()
        assert b"PUBLIC KEY" in pem


class TestQuoteGenerator:

    def setup_method(self):
        self.km = AttestationKeyManager()
        self.qg = QuoteGenerator(self.km)
        self.enclave_id = "enclave-test-001"
        self.measurement = b"\xab" * 32
        self.nonce = "deadbeef" * 8

    def test_generate_returns_report(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        assert isinstance(report, AttestationReport)

    def test_report_contains_correct_enclave_id(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        assert report.enclave_id == self.enclave_id

    def test_report_measurement_hex(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        assert report.measurement == self.measurement.hex()

    def test_report_nonce_matches(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        assert report.nonce == self.nonce

    def test_verify_valid_quote(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        assert self.qg.verify_quote(report) is True

    def test_verify_rejects_tampered_measurement(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        report.measurement = "ff" * 32
        assert self.qg.verify_quote(report) is False

    def test_verify_rejects_tampered_enclave_id(self):
        report = self.qg.generate(self.enclave_id, self.measurement, self.nonce)
        report.enclave_id = "evil-enclave"
        assert self.qg.verify_quote(report) is False


class TestAttestationCache:

    def setup_method(self):
        self.cache = AttestationCache(ttl_seconds=60)
        self.km = AttestationKeyManager()
        self.qg = QuoteGenerator(self.km)
        self.report = self.qg.generate("enc-1", b"\x00" * 32, "nonce-abc")
        self.result = VerificationResult(
            status=AttestationStatus.VALID,
            report=self.report,
            reason="test",
        )

    def test_get_miss_returns_none(self):
        assert self.cache.get(self.report) is None

    def test_put_then_get_returns_result(self):
        self.cache.put(self.report, self.result)
        cached = self.cache.get(self.report)
        assert cached is not None
        assert cached.status == AttestationStatus.VALID

    def test_cache_hit_flag_set(self):
        self.cache.put(self.report, self.result)
        cached = self.cache.get(self.report)
        assert cached.cache_hit is True

    def test_expired_entry_not_returned(self):
        cache = AttestationCache(ttl_seconds=0.01)
        cache.put(self.report, self.result)
        time.sleep(0.05)
        assert cache.get(self.report) is None

    def test_size_increases_on_put(self):
        assert self.cache.size() == 0
        self.cache.put(self.report, self.result)
        assert self.cache.size() == 1


class TestRemoteAttestationProtocol:

    def setup_method(self):
        self.protocol = RemoteAttestationProtocol(max_report_age=60)
        self.measurement = b"\xcc" * 32
        self.enclave_id = "test-enclave-001"

    def test_issue_challenge_returns_challenge(self):
        challenge = self.protocol.issue_challenge()
        assert isinstance(challenge, AttestationChallenge)
        assert not challenge.is_expired()

    def test_challenge_has_nonce(self):
        challenge = self.protocol.issue_challenge()
        assert len(challenge.nonce) == 64  # 32 bytes hex

    def test_full_challenge_response_valid(self):
        challenge = self.protocol.issue_challenge()
        report = self.protocol.generate_response(
            challenge, self.enclave_id, self.measurement
        )
        result = self.protocol.verify_response(challenge, report, self.measurement)
        assert result.status == AttestationStatus.VALID

    def test_verify_fails_on_nonce_mismatch(self):
        challenge = self.protocol.issue_challenge()
        report = self.protocol.generate_response(
            challenge, self.enclave_id, self.measurement
        )
        report.nonce = "wrongnonce" * 6
        result = self.protocol.verify_response(challenge, report)
        assert result.status == AttestationStatus.INVALID

    def test_verify_fails_on_measurement_mismatch(self):
        challenge = self.protocol.issue_challenge()
        report = self.protocol.generate_response(
            challenge, self.enclave_id, self.measurement
        )
        result = self.protocol.verify_response(challenge, report, b"\xdd" * 32)
        assert result.status == AttestationStatus.INVALID

    def test_get_current_report(self):
        report = self.protocol.get_current_report(
            self.enclave_id, self.measurement
        )
        assert isinstance(report, AttestationReport)
        assert report.enclave_id == self.enclave_id

    def test_cache_hit_on_repeated_verification(self):
        challenge = self.protocol.issue_challenge()
        report = self.protocol.generate_response(
            challenge, self.enclave_id, self.measurement
        )
        r1 = self.protocol.verify_response(challenge, report, self.measurement)
        r2 = self.protocol.verify_response(challenge, report, self.measurement)
        assert r2.cache_hit is True


class TestPlatformIntegrityVerifier:

    def test_verify_returns_tuple(self):
        piv = PlatformIntegrityVerifier()
        result = piv.verify()
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)


# ---------------------------------------------------------------------------
# Zero-Trust Tests
# ---------------------------------------------------------------------------

from secure_execution.zero_trust import (
    ZeroTrustGateway,
    IdentityVerifier,
    MicroSegmentation,
    SegmentPolicy,
    ContinuousAuthorizer,
    PolicyEngine,
    PolicyRule,
    PolicyDecision,
    TrustLevel,
    TokenManager,
    CertificatePinner,
    Identity,
    AccessRequest,
)


class TestTokenManager:

    def setup_method(self):
        self.tm = TokenManager()

    def test_issue_returns_string(self):
        token = self.tm.issue("user1", ["user"])
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_verify_valid_token(self):
        token = self.tm.issue("alice", ["admin", "user"])
        payload = self.tm.verify(token)
        assert payload is not None
        assert payload["sub"] == "alice"

    def test_verify_includes_roles(self):
        token = self.tm.issue("alice", ["admin"])
        payload = self.tm.verify(token)
        assert "admin" in payload["roles"]

    def test_verify_expired_token_returns_none(self):
        token = self.tm.issue("user", ["user"], ttl=-1)
        assert self.tm.verify(token) is None

    def test_verify_tampered_token_returns_none(self):
        token = self.tm.issue("user", ["user"])
        parts = token.split(".")
        parts[1] = parts[1] + "tamper"
        assert self.tm.verify(".".join(parts)) is None

    def test_verify_wrong_format(self):
        assert self.tm.verify("not.a.valid.jwt.token.here") is None


class TestCertificatePinner:

    def test_empty_pinner_allows_all(self):
        pinner = CertificatePinner()
        assert pinner.is_pinned("any-thumbprint") is True

    def test_pinned_thumbprint_allowed(self):
        pinner = CertificatePinner()
        pinner.add_pin("AABBCC")
        assert pinner.is_pinned("aabbcc") is True

    def test_unknown_thumbprint_denied(self):
        pinner = CertificatePinner()
        pinner.add_pin("AABBCC")
        assert pinner.is_pinned("DDEEFF") is False

    def test_remove_pin(self):
        pinner = CertificatePinner()
        pinner.add_pin("AABBCC")
        pinner.remove_pin("AABBCC")
        assert pinner.pin_count() == 0


class TestIdentityVerifier:

    def setup_method(self):
        self.verifier = IdentityVerifier()

    def test_verify_valid_token(self):
        token = self.verifier.issue_token("bob", ["user"])
        identity = self.verifier.verify_token(token)
        assert identity is not None
        assert identity.subject == "bob"

    def test_verify_invalid_token_returns_none(self):
        assert self.verifier.verify_token("not-a-token") is None

    def test_verify_with_pinned_cert(self):
        self.verifier.pinner.add_pin("CERT1234")
        token = self.verifier.issue_token("carol", ["user"])
        identity = self.verifier.verify_token(token, cert_thumbprint="CERT1234")
        assert identity is not None

    def test_verify_with_unpinned_cert_denied(self):
        self.verifier.pinner.add_pin("CERT1234")
        token = self.verifier.issue_token("carol", ["user"])
        identity = self.verifier.verify_token(token, cert_thumbprint="WRONGCERT")
        assert identity is None


class TestPolicyEngine:

    def setup_method(self):
        self.engine = PolicyEngine()
        self.tm = TokenManager()

    def _make_request(self, subject: str, roles: list, resource: str, action: str) -> AccessRequest:
        identity = Identity(
            subject=subject,
            roles=roles,
            trust_level=TrustLevel.MEDIUM,
            expires_at=time.time() + 3600,
        )
        return AccessRequest(identity=identity, resource=resource, action=action)

    def test_default_deny_all(self):
        req = self._make_request("user1", ["user"], "vault", "read")
        decision = self.engine.evaluate(req)
        assert decision.decision == PolicyDecision.DENY

    def test_allow_rule_grants_access(self):
        self.engine.add_rule(PolicyRule(
            description="Allow users",
            required_roles=["user"],
            decision=PolicyDecision.ALLOW,
            priority=1,
        ))
        req = self._make_request("user1", ["user"], "vault", "read")
        decision = self.engine.evaluate(req)
        assert decision.decision == PolicyDecision.ALLOW

    def test_mfa_required_rule(self):
        self.engine.add_rule(PolicyRule(
            description="Require MFA for admin",
            required_roles=["admin"],
            require_mfa=True,
            decision=PolicyDecision.ALLOW,
            priority=1,
        ))
        req = self._make_request("admin1", ["admin"], "vault", "delete")
        req.identity.mfa_verified = False
        decision = self.engine.evaluate(req)
        assert decision.decision == PolicyDecision.MFA_REQUIRED

    def test_mfa_verified_allows(self):
        self.engine.add_rule(PolicyRule(
            description="Require MFA for admin",
            required_roles=["admin"],
            require_mfa=True,
            decision=PolicyDecision.ALLOW,
            priority=1,
        ))
        req = self._make_request("admin1", ["admin"], "vault", "delete")
        req.identity.mfa_verified = True
        decision = self.engine.evaluate(req)
        assert decision.decision == PolicyDecision.ALLOW

    def test_rule_count(self):
        initial = self.engine.rule_count()
        self.engine.add_rule(PolicyRule(decision=PolicyDecision.ALLOW, priority=50))
        assert self.engine.rule_count() == initial + 1


class TestMicroSegmentation:

    def setup_method(self):
        self.seg = MicroSegmentation()
        self.seg.register_module(SegmentPolicy(
            module="vault",
            allowed_actions={"read", "write"},
            allowed_roles={"user", "admin"},
            allowed_resources=set(),
        ))

    def test_allowed_access_returns_true(self):
        assert self.seg.check_access("vault", "read", "user", "vault/doc-1") is True

    def test_disallowed_action_returns_false(self):
        assert self.seg.check_access("vault", "delete", "user", "vault/doc-1") is False

    def test_disallowed_role_returns_false(self):
        assert self.seg.check_access("vault", "read", "guest", "vault/doc-1") is False

    def test_unknown_module_returns_false(self):
        assert self.seg.check_access("unknown-module", "read", "user", "x") is False

    def test_list_modules(self):
        assert "vault" in self.seg.list_modules()


class TestContinuousAuthorizer:

    def setup_method(self):
        self.verifier = IdentityVerifier()
        self.ca = ContinuousAuthorizer(self.verifier, interval_seconds=999)

    def test_register_session(self):
        token = self.verifier.issue_token("user", ["user"])
        self.ca.register_session("sess-001", token)
        assert self.ca.active_session_count() == 1

    def test_valid_session_passes_check(self):
        token = self.verifier.issue_token("user", ["user"])
        self.ca.register_session("sess-002", token)
        assert self.ca.check_session("sess-002") is True

    def test_revoke_session(self):
        token = self.verifier.issue_token("user", ["user"])
        self.ca.register_session("sess-003", token)
        self.ca.revoke_session("sess-003")
        assert self.ca.is_revoked("sess-003") is True

    def test_invalid_session_id_returns_false(self):
        assert self.ca.check_session("nonexistent-session") is False


class TestZeroTrustGateway:

    def setup_method(self):
        self.gateway = ZeroTrustGateway()
        self.gateway.add_policy_rule(PolicyRule(
            description="Allow users",
            required_roles=["user"],
            decision=PolicyDecision.ALLOW,
            priority=1,
        ))

    def test_authenticate_valid_token(self):
        token = self.gateway.identity_verifier.issue_token("alice", ["user"])
        identity = self.gateway.authenticate(token)
        assert identity is not None
        assert identity.subject == "alice"

    def test_authenticate_invalid_token(self):
        assert self.gateway.authenticate("bad-token") is None

    def test_verify_request_allow(self):
        token = self.gateway.identity_verifier.issue_token("alice", ["user"])
        decision = self.gateway.verify_request(token, "vault", "read")
        assert decision.decision == PolicyDecision.ALLOW

    def test_verify_request_deny_on_bad_token(self):
        decision = self.gateway.verify_request("badtoken", "vault", "read")
        assert decision.decision == PolicyDecision.DENY

    def test_audit_log_populated(self):
        token = self.gateway.identity_verifier.issue_token("alice", ["user"])
        self.gateway.verify_request(token, "vault", "read")
        log = self.gateway.get_audit_log()
        assert len(log) >= 1

    def test_audit_log_entry_has_expected_fields(self):
        token = self.gateway.identity_verifier.issue_token("bob", ["user"])
        self.gateway.verify_request(token, "audit", "read")
        log = self.gateway.get_audit_log()
        entry = log[-1]
        assert "subject" in entry
        assert "resource" in entry
        assert "decision" in entry


# ---------------------------------------------------------------------------
# Document Vault Tests
# ---------------------------------------------------------------------------

from secure_execution.document_vault import (
    DocumentVault,
    VaultKeyManager,
    DocumentAccessLog,
    TemporaryTokenStore,
    SecureShredder,
    VaultOperation,
    TemporaryAccessToken,
)


class TestVaultKeyManager:

    def setup_method(self):
        self.km = VaultKeyManager()

    def test_derive_master_key_length(self):
        salt = self.km.new_salt()
        key = self.km.derive_master_key("password", salt)
        assert len(key) == 32

    def test_same_password_salt_same_key(self):
        salt = b"\x01" * 32
        k1 = self.km.derive_master_key("password", salt)
        k2 = self.km.derive_master_key("password", salt)
        assert k1 == k2

    def test_different_password_different_key(self):
        salt = b"\x01" * 32
        k1 = self.km.derive_master_key("password1", salt)
        k2 = self.km.derive_master_key("password2", salt)
        assert k1 != k2

    def test_wrap_unwrap_dek(self):
        salt = self.km.new_salt()
        master = self.km.derive_master_key("secret", salt)
        dek = self.km.generate_dek()
        wrapped, nonce = self.km.wrap_dek(dek, master)
        recovered = self.km.unwrap_dek(wrapped, nonce, master)
        assert recovered == dek

    def test_unwrap_fails_wrong_master(self):
        salt = self.km.new_salt()
        master = self.km.derive_master_key("correct", salt)
        wrong_master = self.km.derive_master_key("wrong", salt)
        dek = self.km.generate_dek()
        wrapped, nonce = self.km.wrap_dek(dek, master)
        with pytest.raises(ValueError):
            self.km.unwrap_dek(wrapped, nonce, wrong_master)

    def test_encrypt_decrypt_document(self):
        dek = self.km.generate_dek()
        plaintext = b"Legal document content goes here."
        ct, nonce = self.km.encrypt_document(plaintext, dek)
        recovered = self.km.decrypt_document(ct, nonce, dek)
        assert recovered == plaintext


class TestDocumentAccessLog:

    def setup_method(self):
        self.log = DocumentAccessLog()

    def test_record_creates_entry(self):
        self.log.record("doc-1", "alice", VaultOperation.STORE)
        assert self.log.entry_count() == 1

    def test_query_by_doc_id(self):
        self.log.record("doc-A", "alice", VaultOperation.STORE)
        self.log.record("doc-B", "bob", VaultOperation.RETRIEVE)
        entries = self.log.query(doc_id="doc-A")
        assert all(e.doc_id == "doc-A" for e in entries)

    def test_query_by_subject(self):
        self.log.record("doc-1", "alice", VaultOperation.STORE)
        self.log.record("doc-2", "bob", VaultOperation.RETRIEVE)
        entries = self.log.query(subject="alice")
        assert all(e.subject == "alice" for e in entries)

    def test_query_limit(self):
        for i in range(20):
            self.log.record(f"doc-{i}", "user", VaultOperation.RETRIEVE)
        entries = self.log.query(limit=5)
        assert len(entries) <= 5


class TestTemporaryTokenStore:

    def setup_method(self):
        self.store = TemporaryTokenStore()

    def test_issue_returns_token(self):
        token = self.store.issue("doc-1", "alice", ttl_seconds=60)
        assert isinstance(token, TemporaryAccessToken)

    def test_consume_valid_token(self):
        token = self.store.issue("doc-1", "alice", ttl_seconds=60)
        consumed = self.store.consume(token.token_id, "alice")
        assert consumed is not None
        assert consumed.doc_id == "doc-1"

    def test_consume_wrong_subject_fails(self):
        token = self.store.issue("doc-1", "alice", ttl_seconds=60)
        assert self.store.consume(token.token_id, "bob") is None

    def test_consume_exhausted_token_fails(self):
        token = self.store.issue("doc-1", "alice", ttl_seconds=60, max_uses=1)
        self.store.consume(token.token_id, "alice")
        assert self.store.consume(token.token_id, "alice") is None

    def test_revoke_token(self):
        token = self.store.issue("doc-1", "alice", ttl_seconds=60)
        self.store.revoke(token.token_id)
        assert self.store.consume(token.token_id, "alice") is None

    def test_active_count(self):
        self.store.issue("doc-1", "alice", ttl_seconds=60)
        self.store.issue("doc-2", "bob", ttl_seconds=60)
        assert self.store.active_count() == 2


class TestDocumentVault:

    def setup_method(self):
        self.vault = DocumentVault()
        self.password = "super_secret_password_123!"
        self.owner = "alice"
        self.content = b"This is a confidential legal document."

    def test_store_returns_doc_id(self):
        doc_id = self.vault.store(self.content, "doc.txt", self.owner, self.password)
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_retrieve_correct_plaintext(self):
        doc_id = self.vault.store(self.content, "doc.txt", self.owner, self.password)
        recovered = self.vault.retrieve(doc_id, self.password, self.owner)
        assert recovered == self.content

    def test_retrieve_wrong_password_fails(self):
        doc_id = self.vault.store(self.content, "doc.txt", self.owner, self.password)
        with pytest.raises((ValueError, Exception)):
            self.vault.retrieve(doc_id, "wrong-password", self.owner)

    def test_retrieve_nonexistent_doc_raises(self):
        with pytest.raises(FileNotFoundError):
            self.vault.retrieve("nonexistent-id", self.password, self.owner)

    def test_shred_removes_document(self):
        doc_id = self.vault.store(self.content, "shred-me.txt", self.owner, self.password)
        self.vault.shred(doc_id, self.password, self.owner)
        with pytest.raises(FileNotFoundError):
            self.vault.retrieve(doc_id, self.password, self.owner)

    def test_document_count_increments(self):
        before = self.vault.document_count()
        self.vault.store(self.content, "new-doc.txt", self.owner, self.password)
        assert self.vault.document_count() == before + 1

    def test_list_documents_returns_owner_docs(self):
        self.vault.store(self.content, "alice-doc.txt", "alice", self.password)
        self.vault.store(self.content, "bob-doc.txt", "bob", self.password)
        docs = self.vault.list_documents("alice")
        assert all(d.owner == "alice" for d in docs)

    def test_grant_temp_access_allows_retrieve(self):
        doc_id = self.vault.store(self.content, "shared.txt", self.owner, self.password)
        token = self.vault.grant_temp_access(doc_id, self.owner, "bob", ttl_seconds=60)
        recovered = self.vault.retrieve(doc_id, self.password, "bob", token.token_id)
        assert recovered == self.content

    def test_access_log_records_store(self):
        self.vault.store(self.content, "logged.txt", self.owner, self.password)
        entries = self.vault.access_log.query(operation=VaultOperation.STORE)
        assert len(entries) >= 1

    def test_get_metadata_returns_info(self):
        doc_id = self.vault.store(self.content, "meta-test.txt", self.owner, self.password)
        meta = self.vault.get_metadata(doc_id)
        assert meta is not None
        assert meta.name == "meta-test.txt"
        assert meta.owner == self.owner


class TestSecureShredder:

    def test_shred_bytes_zeros_data(self):
        data = bytearray(b"sensitive data")
        SecureShredder.shred_bytes(data)
        assert all(b == 0 for b in data)
