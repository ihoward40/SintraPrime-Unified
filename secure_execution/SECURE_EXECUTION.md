# Secure Execution Layer — SintraPrime-Unified

A production-grade security hardening module providing Trusted Execution
Environment (TEE) abstraction, remote attestation, zero-trust networking,
and an encrypted document vault.

---

## Architecture Overview

```
secure_execution/
├── tee_manager.py        # TEE abstraction layer (SGX / SEV / TrustZone / Simulated)
├── attestation.py        # Remote attestation (challenge-response, quote generation)
├── zero_trust.py         # Zero-trust gateway (JWT, policy engine, micro-segmentation)
├── document_vault.py     # AES-256-GCM encrypted document storage
├── secure_api.py         # FastAPI router exposing all capabilities
├── SECURE_EXECUTION.md   # This file
└── tests/
    └── test_secure_execution.py   # 75+ pytest tests
```

---

## Components

### 1. TEE Manager (`tee_manager.py`)

Provides a unified interface over four TEE backends:

| Provider | Hardware Required | Fallback |
|---|---|---|
| `SimulatedTEE` | None (software only) | — |
| `IntelSGXProvider` | Intel SGX | SimulatedTEE |
| `AMDSEVProvider` | AMD SEV-SNP | SimulatedTEE |
| `ARMTrustZoneProvider` | ARM TrustZone | SimulatedTEE |

**Key classes:**
- `TEEProvider` — abstract base class all providers implement
- `SecureEnclaveContext` — context manager; encrypts data before processing,
  decrypts only inside the enclave boundary
- `TEEProviderFactory` — auto-detects best available provider

**Quick start:**
```python
from secure_execution.tee_manager import SecureEnclaveContext, SimulatedTEE

ctx = SecureEnclaveContext(SimulatedTEE())
with ctx:
    result = ctx.process(b"sensitive data", lambda d: d.upper())
print(result.plaintext)  # b"SENSITIVE DATA"
```

**Key sealing:**
```python
with ctx:
    sealed = ctx.seal_key(my_key_bytes, key_id="root-key")
    recovered = ctx.unseal_key(sealed)  # fails if platform changes
```

---

### 2. Attestation System (`attestation.py`)

Implements a full challenge-response remote attestation protocol.

**Flow:**
1. Verifier calls `issue_challenge()` → receives `AttestationChallenge` with nonce
2. Prover calls `generate_response(challenge, enclave_id, measurement)` → `AttestationReport`
3. Verifier calls `verify_response(challenge, report, expected_measurement)` → `VerificationResult`

**Features:**
- ECDSA-signed quotes (P-256 / SHA-256)
- Attestation cache (configurable TTL, default 5 min) prevents repeat verification overhead
- `PlatformIntegrityVerifier` checks secure boot status and debug flags
- `AttestationType` enum supports: `SIMULATED`, `INTEL_SGX_DCAP`, `AMD_SEV_SNP`, `ARM_TRUSTZONE`

```python
from secure_execution.attestation import RemoteAttestationProtocol

proto = RemoteAttestationProtocol()
challenge = proto.issue_challenge()
report = proto.generate_response(challenge, enclave_id="my-enclave", measurement=b"\xab"*32)
result = proto.verify_response(challenge, report)
print(result.status)  # AttestationStatus.VALID
```

---

### 3. Zero-Trust Security Model (`zero_trust.py`)

Enforces "never trust, always verify" — every request is re-authenticated and
re-authorized regardless of origin.

**Components:**

| Class | Responsibility |
|---|---|
| `ZeroTrustGateway` | Central enforcement point; orchestrates all checks |
| `IdentityVerifier` | HMAC-SHA256 JWT verification + certificate pinning |
| `PolicyEngine` | Priority-ordered ALLOW / DENY / MFA_REQUIRED rules |
| `MicroSegmentation` | Per-module action/role/resource ACLs |
| `ContinuousAuthorizer` | Background thread re-verifies sessions every 5 minutes |

**Quick start:**
```python
from secure_execution.zero_trust import ZeroTrustGateway, PolicyRule, PolicyDecision

gw = ZeroTrustGateway()
gw.add_policy_rule(PolicyRule(
    description="Allow users to read vault",
    required_roles=["user"],
    resource_pattern="vault",
    decision=PolicyDecision.ALLOW,
    priority=10,
))

token = gw.identity_verifier.issue_token("alice", ["user"])
decision = gw.verify_request(token, resource="vault", action="read")
print(decision.decision)  # PolicyDecision.ALLOW
```

**Continuous authorization:**
```python
gw.start_continuous_auth()   # spawns daemon thread
# ... sessions re-verified every 5 min automatically
gw.stop_continuous_auth()
```

---

### 4. Document Vault (`document_vault.py`)

AES-256-GCM encrypted document storage with PBKDF2 key derivation.

**Key hierarchy:**
```
master_key = PBKDF2-SHA256(password, random_salt, 260_000 iterations)
dek        = random 256-bit Data Encryption Key per document
ciphertext = AES-256-GCM(dek, plaintext, aad=doc_id)
wrapped_dek= AES-256-GCM(master_key, dek)
```

Only `ciphertext`, `wrapped_dek`, `nonces`, and `salt` are persisted — the
master key is **never stored**.

**Features:**
- Per-document random DEK; DEK wiped from memory after use
- Secure shredding: `SecureShredder` overwrites bytes with random data × 3 passes before deletion
- `DocumentAccessLog`: append-only audit trail with per-document, per-user queries
- `TemporaryAccessToken`: auto-expiring, use-limited tokens for document sharing

```python
from secure_execution.document_vault import DocumentVault

vault = DocumentVault()

# Store
doc_id = vault.store(b"Legal contract text", name="contract.txt",
                     owner="alice", password="strong-passphrase")

# Retrieve
plaintext = vault.retrieve(doc_id, password="strong-passphrase", subject="alice")

# Grant temporary access
token = vault.grant_temp_access(doc_id, owner="alice", granted_to="bob", ttl_seconds=3600)
vault.retrieve(doc_id, password="strong-passphrase", subject="bob",
               temp_token_id=token.token_id)

# Shred
vault.shred(doc_id, password="strong-passphrase", owner="alice")
```

---

### 5. Secure API (`secure_api.py`)

FastAPI router exposing all capabilities over HTTP.

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/secure/vault/store` | Encrypt and store a document |
| `POST` | `/secure/vault/retrieve` | Decrypt and retrieve a document |
| `GET` | `/secure/attestation/report` | Current platform attestation report |
| `POST` | `/secure/zerotrust/verify` | Verify identity + authorization |
| `GET` | `/secure/audit/access-log` | Document access history |

All write/read endpoints require `Authorization: Bearer <token>` and pass through
the `ZeroTrustGateway`.

**Mounting the router:**
```python
from fastapi import FastAPI
from secure_execution.secure_api import create_secure_router

app = FastAPI()
app.include_router(create_secure_router())
```

---

## Running Tests

```bash
pip install cryptography pytest fastapi
python -m pytest secure_execution/tests/ -v
```

Expected output: **75+ tests, all passing**.

---

## Security Notes

- **No hardcoded keys or secrets** — all keys are derived from passwords or generated randomly at runtime.
- **Graceful fallback** — hardware TEE providers fall back to `SimulatedTEE` when hardware is unavailable; functionality is preserved, but hardware isolation guarantees are not.
- **DEK memory hygiene** — Data Encryption Keys are overwritten with zeros after use via `SecureShredder.shred_bytes`.
- **PBKDF2 iterations** — set to 260,000 (OWASP 2023 recommendation for PBKDF2-SHA256); increase for higher security at the cost of latency.
- **Production deployment** — replace `SimulatedTEE` with a real SGX SDK (e.g., Gramine, SCONE) or AMD SEV driver wrapper; replace HMAC-JWT with a proper OIDC provider.

---

## Dependencies

```
cryptography>=41.0
fastapi>=0.110       # optional — only required for secure_api
pydantic>=2.0        # optional — only required for secure_api
pytest>=7.0          # test runner
```
