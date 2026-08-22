# SP-LIVE-001 M1: First Real Mission Selection Package

## Program Context
- **Program**: SP-LIVE-001 (SintraPrime Governed Live Operating Loop)
- **Baseline**: e4d260da867a2e04375b2329cd680be3b8833e79 (C1 Certified)
- **I2 Baseline**: 86f192a4def0781c66d9592513ebacb12baec643 (I2 Verified)
- **Current State**: Live conversation certified, live reasoning certified, approval flow certified with mock action
- **Hard Constraint**: External execution remains mechanically disabled

## Authorization
- **Authorization**: SP_LIVE_001_M1_FIRST_REAL_MISSION_SELECTION
- **Authority Type**: Mission Selection + Threat Model + Acceptance-Plan Authoring ONLY
- **Implementation Authority**: NONE
- **Live Side Effect Authority**: NONE
- **Connector Expansion Authority**: NONE

---

## 1. CANDIDATE MISSION LIST

### Candidate A: Governed Repository Metadata Analysis
**Description**: Read metadata from a governed/local repository, analyze structure and compliance, generate internal certification artifact
- **Primary Action**: `read_repository_metadata` → `analyze_structure` → `generate_artifact`
- **External Dependency**: Local filesystem only (governed path)
- **Irreversibility**: Zero (read-only external, internal artifact only)

### Candidate B: Local Evidence Bundle Analysis
**Description**: Read existing C1/I2 evidence bundles, analyze completeness and integrity, generate Principal Brief artifact
- **Primary Action**: `read_evidence_bundle` → `analyze_integrity` → `generate_brief_artifact`
- **External Dependency**: Local filesystem only (certification artifacts)
- **Irreversibility**: Zero (read-only external, internal artifact only)

### Candidate C: Synthetic/Sandbox Provider Metadata Query
**Description**: Query a controlled mock/sandbox provider for capability metadata, summarize, create sandbox test artifact
- **Primary Action**: `query_sandbox_metadata` → `summarize_capabilities` → `create_sandbox_artifact`
- **External Dependency**: Local mock provider (in-process, no network)
- **Irreversibility**: Zero (in-memory mock, internal artifact only)

### Candidate D: Governed Memory Store Query
**Description**: Query governed memory store for session context, analyze patterns, create context summary artifact
- **Primary Action**: `query_governed_memory` → `analyze_patterns` → `create_summary_artifact`
- **External Dependency**: Local memory store (SQLite/file)
- **Irreversibility**: Zero (read-only, internal artifact only)

### Candidate E: Configuration Drift Detection
**Description**: Read current configuration from governed paths, compare to certified baseline, generate drift report artifact
- **Primary Action**: `read_config` → `compare_baseline` → `generate_drift_report`
- **External Dependency**: Local configuration files
- **Irreversibility**: Zero (read-only, internal artifact only)

---

## 2. RISK CLASSIFICATION

| Candidate | External Read | External Write | Network | Financial | Legal | Deployment | Account Mutation | Irreversible | **Overall Risk** |
|-----------|:-------------:|:--------------:|:-------:|:---------:|:-----:|:----------:|:----------------:|:------------:|:----------------:|
| A: Repo Metadata | ✓ Local | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **VERY LOW** |
| B: Evidence Bundle | ✓ Local | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **VERY LOW** |
| C: Sandbox Provider | ✓ Mock | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **VERY LOW** |
| D: Memory Query | ✓ Local | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **VERY LOW** |
| E: Config Drift | ✓ Local | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **VERY LOW** |

**Rejected / Deferred Candidates** (exceed risk threshold):
| Candidate | Reason for Rejection |
|-----------|---------------------|
| Send email | External write, network, irreversible |
| Modify GitHub | External write, network, account mutation, irreversible |
| Move Drive files | External write, network, account mutation, irreversible |
| Make payment | Financial, irreversible, legal implications |
| File legal document | Legal, irreversible, high consequence |
| Deploy software | Deployment, production impact, irreversible |
| Create real Drive file | External write, network, account mutation |
| Create real GitHub issue | External write, network, account mutation |
| OAuth flow initiation | Account connection, new OAuth activity |

---

## 3. REQUIRED CAPABILITIES / CONNECTORS PER CANDIDATE

| Candidate | Read Capability | Write Capability | Connector Required | Model Routing | Specialist Count |
|-----------|----------------|------------------|-------------------|---------------|------------------|
| A: Repo Metadata | `local_filesystem_read` | `internal_artifact_create` | None (native) | Standard (analysis) | 2 (reader, analyzer) |
| B: Evidence Bundle | `local_filesystem_read` | `internal_artifact_create` | None (native) | Standard (analysis) | 2 (reader, analyzer) |
| C: Sandbox Provider | `mock_provider_query` | `internal_artifact_create` | Mock (in-process) | Light (summary) | 1 (analyzer) |
| D: Memory Query | `governed_memory_read` | `internal_artifact_create` | None (native) | Standard (analysis) | 2 (memory, analyzer) |
| E: Config Drift | `local_filesystem_read` | `internal_artifact_create` | None (native) | Light (comparison) | 2 (reader, comparator) |

**All candidates require**: Principal session, approval flow, evidence chain, spoken brief

---

## 4. READ / WRITE AUTHORITY SEPARATION

### Read Authority (GRANTED for M1→M2)
| Authority | Scope | Justification |
|-----------|-------|---------------|
| `local_filesystem_read` | Governed paths only (`cert/`, `i2/`, `.git/`, `sintra_live/`) | Required for all candidates |
| `governed_memory_read` | Current session + certified evidence | Required for Candidates B, D |
| `mock_provider_query` | In-process mock only | Required for Candidate C |
| `certified_baseline_read` | Git tree at e4d260da... | Required for Candidate E |

### Write Authority (NOT GRANTED in M1, REQUESTED for M2)
| Authority | Scope | Candidate Need |
|-----------|-------|----------------|
| `internal_artifact_create` | `cert/m1_artifacts/` directory only | All candidates |
| `principal_brief_write` | Session-scoped brief artifact | All candidates |
| `evidence_record_write` | Evidence chain append | All candidates |

### Write Authority (EXPLICITLY DENIED - Frozen)
| Authority | Scope | Reason |
|-----------|-------|--------|
| `external_filesystem_write` | Outside governed paths | Violates hard disablement |
| `network_write` | Any external endpoint | Violates hard disablement |
| `email_send` | SMTP/API | Prohibited |
| `github_write` | GitHub API | Prohibited |
| `drive_write` | Google Drive API | Prohibited |
| `financial_write` | Payment/ledger | Prohibited |
| `legal_write` | Filing systems | Prohibited |
| `deployment_write` | CI/CD/production | Prohibited |

---

## 5. PRINCIPAL APPROVAL POINT AND FLOW

### Approval Point
```
LIVE VOICE INTERACTION
         ↓
PRINCIPAL REQUESTS MISSION
         ↓
MISSION CREATED (read-only scope)
         ↓
SWARM EXECUTES READ + ANALYSIS
         ↓
SINTRAPRIME SPEAKS: "Analysis complete. Proposed internal artifact: [description]. Do you approve creation?"
         ↓
PRINCIPAL SPEAKS APPROVAL/REJECTION
         ↓
APPROVAL BOUND TO ACTION HASH
         ↓
IF APPROVED: ARTIFACT CREATED (internal only)
         ↓
SINTRAPRIME SPEAKS PRINCIPAL BRIEF
```

### Approval Binding Requirements
- Action hash includes: mission_id, artifact_path, artifact_content_hash, timestamp
- Principal identity bound via active session
- Approval confidence ≥ 0.7 (voice)
- Approval expires if not executed within 300 seconds
- Rejection → no artifact created, mission COMPLETE

---

## 6. FAILURE / ROLLBACK MODEL

### Failure Scenarios & Responses

| Scenario | Detection | Response | Rollback |
|----------|-----------|----------|----------|
| Read permission denied | Exception at read | Report to Principal, mission INCOMPLETE | None needed (no write) |
| Analysis error | Exception in specialist | Report to Principal, mission INCOMPLETE | None needed (no write) |
| Approval timeout (300s) | Timer expiry | Mission CANCELLED, no artifact | None needed |
| Approval rejection | Phrase classification | Mission REJECTED, no artifact | None needed |
| Artifact write failure | Exception at write | Report to Principal, mission FAILED | Delete partial artifact if created |
| Evidence chain failure | Verification fails | Mission INCOMPLETE, alert | None (evidence is append-only) |
| Voice pipeline failure | STT/TTS error | Fallback to text mode, continue | None |

### Rollback Guarantees
- **No external state modified** before approval
- **Internal artifacts** are idempotent (overwrite safe)
- **Evidence chain** is append-only, tamper-evident
- **Mission state** reversible to RECEIVED until approval

---

## 7. EVIDENCE REQUIREMENTS AND CONTRACT

### Required Evidence Records (per mission)

| Record Type | Timing | Content | Hash Chain |
|-------------|--------|---------|------------|
| `mission_created` | Mission start | mission_id, scope, read_authorities | ✓ |
| `principal_identity_bound` | Session start | principal_id, session_id, binding_method | ✓ |
| `read_executed` | After each read | path, bytes_read, content_hash, duration_ms | ✓ |
| `specialist_dispatched` | Per specialist | specialist_role, input_hash, output_hash | ✓ |
| `analysis_complete` | After swarm | summary_hash, confidence, findings | ✓ |
| `approval_requested` | Before approval | action_hash, artifact_preview, expiry | ✓ |
| `approval_received` | Principal speaks | approval_id, phrase_type, confidence, hash_binding | ✓ |
| `artifact_created` | After approval | path, content_hash, size_bytes | ✓ |
| `brief_generated` | Final | brief_hash, spoken_brief_hash | ✓ |
| `mission_complete` | End | final_state, evidence_root_hash | ✓ |

### Evidence Contract
- All records SHA-256 chained
- Missing required record = INCOMPLETE
- Tampered chain = FAIL
- Evidence bundle delivered with Principal Brief

---

## 8. EXACT SUCCESS CRITERIA

### M1_SUCCESS (This Phase)
- [ ] One lowest-risk real mission selected
- [ ] Required capabilities identified and bounded
- [ ] Read/write authority separated
- [ ] Principal approval point defined
- [ ] Rollback model defined
- [ ] Evidence contract defined
- [ ] M2 certification requirements defined

### M2_SUCCESS (Next Phase - Capability Certification)
- [ ] Selected capability certified against C1+I2 adversarial suite
- [ ] Read path verified (no write leakage)
- [ ] Artifact creation verified (idempotent, bounded path)
- [ ] Approval binding verified (hash, expiry, identity)
- [ ] Evidence chain verified (complete, tamper-evident)
- [ ] Hard disablement re-verified (no external write reachable)

### M3_SUCCESS (Dry Run)
- [ ] Mission executes with real reads, zero writes
- [ ] Principal approval flow completes
- [ ] Artifact created in dry-run mode (simulated)
- [ ] Evidence chain complete
- [ ] Spoken brief delivered

### M4_SUCCESS (First Real Side Effect)
- [ ] Single real internal artifact created after approval
- [ ] Evidence chain sealed
- [ ] Independent verification passes
- [ ] Spoken + written Principal Brief delivered
- [ ] No external side effects

### M5_SUCCESS (Verification)
- [ ] Artifact independently verified
- [ ] Evidence bundle verified
- [ ] Regression suite passes
- [ ] Certification frozen

---

## 9. RECOMMENDED FIRST REAL MISSION

### SELECTION: **Candidate B — Local Evidence Bundle Analysis**

**Mission Name**: `SP_LIVE_001_M1_EVIDENCE_INTEGRITY_ANALYSIS`

**Rationale**:
1. **Zero external dependency** — reads only local certification artifacts already produced by C1/I2
2. **Self-referential validation** — proves the system can analyze its own governance evidence
3. **Natural Principal Brief** — output is a spoken/written brief about the system's own certification state
4. **Zero risk** — read-only local files, internal artifact only
5. **Demonstrates full loop** — memory (evidence) → swarm (analysis) → approval → artifact → brief
6. **Reusable artifact** — the generated brief becomes part of the certification record
7. **No new connectors** — uses existing governed memory and filesystem primitives

**Mission Flow**:
```
1. Principal: "SintraPrime, analyze the C1 and I2 evidence bundles and brief me on integrity."
2. SintraPrime: Creates mission with read-only scope to cert/ directory
3. Swarm: 
   - Specialist 1 (EvidenceReader): Reads C1_CERTIFICATION_BUNDLE.json, C1_CERTIFICATION_REPORT.json
   - Specialist 2 (IntegrityAnalyzer): Verifies hashes, checks completeness, validates chain
4. SintraPrime speaks: "Analysis complete. C1 bundle hash verified. 169/169 tests pass. I2 bundle hash verified. 40/40 tests pass. 614/614 regression pass. No anomalies. Proposed artifact: integrity_summary_20260822.md in cert/m1_artifacts/. Do you approve creation?"
5. Principal: "Yes, approved."
6. SintraPrime: Creates artifact, seals evidence, speaks Principal Brief.
```

---

## 10. M2 CERTIFICATION REQUIREMENTS

### Capability to Certify
```
CAPABILITY = LOCAL_FILESYSTEM_READ + INTEGRITY_ANALYSIS + INTERNAL_ARTIFACT_CREATE
SCOPE = cert/ directory (read) + cert/m1_artifacts/ directory (write)
```

### M2 Certification Test Families (Additional to C1/I2)
| Family | Focus | Tests Required |
|--------|-------|----------------|
| M2-A | Path confinement | 10 (escape attempts, symlink attacks, traversal) |
| M2-B | Read integrity | 8 (hash verification, partial reads, encoding) |
| M2-C | Write atomicity | 6 (idempotency, partial write, crash recovery) |
| M2-D | Artifact validation | 5 (schema, size limits, content validation) |
| M2-E | Approval binding | 8 (hash binding, expiry, replay, mutation) |
| M2-F | Evidence integration | 7 (chain append, root hash, verification) |
| M2-G | Voice approval flow | 10 (confidence, ambiguity, timeout, interruption) |

**Total M2 Tests**: ~54 additional tests

### M2 Static Analysis Requirements
- Path confinement proof (no escape from `cert/`)
- No network syscalls in read/write path
- No capability escalation in specialist code
- Mock provider remains only execution path

---

## 11. M1 PACKAGE SUMMARY

### M1_RESULT
```
PASS
```

### RECOMMENDED_FIRST_REAL_MISSION
```
SP_LIVE_001_M1_EVIDENCE_INTEGRITY_ANALYSIS
```

### M2_REQUIRED_CAPABILITY
```
LOCAL_FILESYSTEM_READ (cert/ scope) 
+ INTEGRITY_ANALYSIS (hash verification, completeness check)
+ INTERNAL_ARTIFACT_CREATE (cert/m1_artifacts/ scope)
```

### M2_REQUIRED_AUTHORITY
```
READ: local_filesystem_read(cert/), governed_memory_read(evidence)
WRITE: internal_artifact_create(cert/m1_artifacts/), principal_brief_write, evidence_record_write
APPROVAL: Spoken approval bound to action_hash with 300s expiry
EVIDENCE: Full chain per contract in Section 7
```

### LIVE_SIDE_EFFECT_AUTHORIZED
```
FALSE
```

### ACTION
```
STOP FOR PRINCIPAL REVIEW
```

---

## APPENDIX: THREAT MODEL FOR RECOMMENDED MISSION

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Path traversal read | Low | Medium | Path confinement, allowlist `cert/` only |
| Symlink escape read | Low | Medium | Resolve realpath, verify prefix |
| Large file DoS | Low | Low | Size limit (10MB), streaming read |
| Hash collision | Negligible | High | SHA-256, 256-bit security |
| Approval replay | Medium | High | Action hash binding, expiry, nonce |
| Artifact overwrite | Low | Low | Idempotent write, versioned naming |
| Evidence tampering | Low | High | Hash chain, append-only, verification |
| Voice ambiguity | Medium | Medium | Confidence threshold, clarification loop |

---

**Generated**: 2026-08-22
**M1 Package Version**: 1.0
**Next Phase**: SP_LIVE_001_M2_CAPABILITY_CERTIFICATION (upon Principal authorization)