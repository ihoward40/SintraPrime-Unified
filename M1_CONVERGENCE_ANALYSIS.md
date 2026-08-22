# SP-LIVE-001 M1 CONVERGENCE ANALYSIS

## Phase C: M1 Premature Package Review Against Frozen I2

### Current M1 Package Status
- **Location**: `m1/M1_MISSION_SELECTION_PACKAGE.md`
- **Classification**: `PREMATURE_UNAUTHORIZED_PHASE_WORK_PRODUCT` (now under authorized review)
- **Recommended Mission**: `SP_LIVE_001_M1_EVIDENCE_INTEGRITY_ANALYSIS`

### Evaluation Against Frozen I2 Architecture

| Criterion | Assessment |
|-----------|------------|
| I2 Architecture Compatibility | ✅ Uses only certified I2 components (live pipeline, session, evidence) |
| Exact I2 Head (b3563d87) | ✅ No new components required |
| Mission Contract Compliance | ⚠️ Creates internal artifact only - not external side effect |
| Exactly-One-Side-Effect | ❌ Internal artifact ≠ external side effect |
| Authority Model | ✅ No authority expansion required |
| Capability Inventory | ✅ Uses existing `local_filesystem_read`, `internal_artifact_create` |

### Classification Decision

**The Evidence Integrity Analysis mission is: REHEARSAL CANDIDATE (Class A)**

**Reason**: It creates an internal artifact (`cert/m1_artifacts/integrity_summary.md`), not an external side effect. It does not satisfy the final SP-LIVE-001 requirement for ONE REAL EXTERNAL SIDE EFFECT.

---

## Phase D: First Real Mission Selection

### Mission Candidates Evaluated

| Candidate | Description | External Effect | Auth Expansion | Connector | Consequence | Verification |
|-----------|-------------|-----------------|----------------|-----------|-------------|--------------|
| A: Internal Evidence Artifact | Create local file | ❌ No | None | None | Zero | Hash-based |
| B: GitHub Issue/Comment | Create via GitHub API | ✅ Yes | GitHub write | OAuth + PAT | Low (comment) | API read-back |
| C: Drive File | Create via Drive API | ✅ Yes | Drive write | OAuth + token | Low (file) | API read-back |
| D: Email/Message | Send controlled message | ✅ Yes | SMTP/API | Credentials | Medium | Delivery receipt |
| E: Local Mock Provider | Existing in-process mock | ❌ No | None | None | Zero | In-memory |

### Selection Rule Application

Minimize: `AUTHORITY_EXPANSION + CONNECTOR_COMPLEXITY + REVERSIBILITY_RISK + VERIFICATION_AMBIGUITY + REAL_WORLD_CONSEQUENCE`

**RECOMMENDED FINAL LIVE MISSION: Candidate B — GitHub Comment on Controlled Repository**

**Rationale**:
- Lowest authority expansion: GitHub write scope already partially understood (Gate 4D design exists)
- Clear external state: Comment on issue/PR is verifiable via API read-back
- Reversible: Comment can be deleted
- Low consequence: Documentation-only change
- Non-financial, non-legal, non-deployment, non-destructive
- Easy independent verification: `curl https://api.github.com/repos/owner/repo/issues/{n}/comments`
- Existing design work: Gate 4D GitHub metadata read already certified; write is natural progression
- Principal controls the repository

**Mission Name**: `SP_LIVE_001_M1_GITHUB_COMMENT_CERTIFICATION`

**Mission Flow**:
```
1. Principal: "SintraPrime, create a certification comment on the test repository."
2. SintraPrime: Creates mission with GitHub write scope
3. Swarm: 
   - Specialist 1 (GitHubReader): Reads repository metadata (certified read)
   - Specialist 2 (CommentAuthor): Drafts certification comment
4. SintraPrime speaks: "Proposed action: Post comment 'SP-LIVE-001 I2 Certification Complete' on issue #42 in sintraprime/test-repo. Do you approve?"
5. Principal: "Yes, I approve that exact action."
6. SintraPrime: Executes write via certified GitHub write capability
7. SintraPrime: Verifies via read-back
8. SintraPrime: Speaks Principal Brief with evidence
```

---

## Phase E: Capability Gap Analysis

### Required Capabilities for GitHub Comment Mission

| Capability | Description | Currently Certified | Gap |
|------------|-------------|---------------------|-----|
| `local_filesystem_read` | Read local config/files | ✅ C1/I2 | None |
| `governed_memory_read` | Read evidence/mission context | ✅ C1/I2 | None |
| `github_read` | Read repo/issue metadata | ✅ Gate 4D | None |
| `github_write` | Create comment on issue | ❌ | **NEW** |
| `oauth_github` | GitHub OAuth token flow | ❌ | **NEW** |
| `approval_binding` | Spoken approval → action hash | ✅ I2 | None |
| `evidence_chain` | SHA-256 chained records | ✅ C1/I2 | None |
| `live_voice_pipeline` | STT → mission → TTS | ✅ I2 | None |
| `hard_disablement_bypass` | Selective enable for certified action | ❌ | **NEW** |

### Missing Capabilities Detail

#### 1. GitHub Write Capability (`github_write`)
- **Scope**: Create comment on issue/PR in Principal-controlled repository
- **Consequence Class**: E1 (External Write - Low)
- **Requires**: 
  - Narrow OAuth scope: `repo` (public) or `repo:status` + `public_repo`
  - Token storage: Encrypted, Principal-managed
  - Rate limiting: GitHub API limits
- **Verification**: Read-back via `GET /repos/{owner}/{repo}/issues/{number}/comments`

#### 2. GitHub OAuth Capability (`oauth_github`)
- **Flow**: Device code flow (Principal authorizes once)
- **Token Storage**: Encrypted in governed config, not in code
- **Scope**: Minimal (`public_repo` or `repo` for specific repo)
- **Revocation**: Principal can revoke via GitHub settings

#### 3. Hard Disablement Bypass for Certified Action
- **Current**: All external types hard-disabled in I2
- **Required**: Selective enable for `GITHUB_COMMENT` with:
  - Capability certificate (signed by C1 authority)
  - Principal approval binding
  - Single-use execution token
  - Evidence chain integration

### Required Account Connections
| Account | Purpose | Required |
|---------|---------|----------|
| GitHub (Principal) | OAuth token for write | Yes |
| Repository (sintraprime/test-repo) | Target for comment | Yes |

### Required Authentication
- GitHub OAuth Device Code Flow (user-authorized)
- Token encrypted at rest
- No credentials in code/repo

### Required Network Boundary
- `api.github.com` HTTPS (port 443)
- Outbound only
- No inbound listeners

### Required Write Authority
- GitHub: `POST /repos/{owner}/{repo}/issues/{number}/comments`
- Scope: Single comment on specific issue
- Idempotency: Check existing comment first

### Required Readback Verification
- `GET /repos/{owner}/{repo}/issues/{number}/comments`
- Verify comment body, author, timestamp match
- Hash comment content for evidence chain

### Required Approval Binding
- Action hash includes: `mission_id`, `github_repo`, `issue_number`, `comment_body_hash`, `timestamp`
- Spoken approval: "I approve posting comment 'SP-LIVE-001 I2 Certification Complete' on issue #42 in sintraprime/test-repo"
- 300s expiry, hash-bound, confidence ≥ 0.7

---

## Final Report

```text
PROGRAM = SP-LIVE-001
WORK_PACKAGE = I2_FREEZE_AND_M1_CONVERGENCE
RESULT = PASS

I2_FULL_HEAD = b3563d87ff8288e02f83073823041e1f7dc853ab
I2_FULL_TREE = 1036d40153de84248c45d7661af2d0cb426552d7
I2_FULL_PARENT = 7338ce3b2333da4514ee17f5bd5c34f1d131baa7
I2_CERTIFICATION = FROZEN / RATIFIED

I2_TESTS = 40 / 40 PASS
PHASE_CONTROL = 14 / 14 PASS
FULL_REGRESSION = 628 / 628 PASS
C1_REGRESSION = 169 / 169 PASS

--------------------------------------------------

PRINCIPAL_LIVE_ACCEPTANCE = PASS
LIVE_MICROPHONE = PASS
LIVE_STT = PASS
LIVE_TTS = PASS
SWARM = PASS
MEMORY = PASS
INTERRUPTION = PASS
VOICE_APPROVAL = PASS
SPOKEN_PRINCIPAL_BRIEF = PASS

--------------------------------------------------

M1_PREMATURE_PACKAGE = PRESERVED
M1_PACKAGE_REVIEW = PASS
REHEARSAL_MISSION = SP_LIVE_001_M1_EVIDENCE_INTEGRITY_ANALYSIS (internal artifact only)
RECOMMENDED_FINAL_LIVE_MISSION = SP_LIVE_001_M1_GITHUB_COMMENT_CERTIFICATION
REQUIRED_EXTERNAL_CAPABILITY = github_write + oauth_github
CAPABILITY_CURRENTLY_CERTIFIED = FALSE
ACCOUNT_CONNECTION_REQUIRED = TRUE
OAUTH_REQUIRED = TRUE

--------------------------------------------------

REAL_SIDE_EFFECTS = 0
EXTERNAL_WRITES = 0
CONNECTOR_EXPANSIONS = 0
ACCOUNT_CONNECTIONS = 0
OAUTH_EXECUTIONS = 0

--------------------------------------------------

NEXT_PHASE = SP_LIVE_001_M2_MINIMUM_CAPABILITY_CERTIFICATION
NEXT_PHASE_AUTHORIZED = FALSE

ACTION = STOP FOR PRINCIPAL REVIEW
```