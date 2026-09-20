# SP-RC-RUNTIME-COLLECTION-MATRIX-001
## G0-R3 — Runtime Collection Verification (module-representation proof)

**Immutable RC base:** `c0c29a0eb8f404e2bb748be33b8edb9ffff1fc7d`
**Branch (isolated cert):** `rc/g0r3-collection`  (test-infra delta only; no app source changed)
**Python:** 3.11.9  **pytest:** 9.1.1  **venv:** `.venv` (uv-provisioned)
**Reality Gate:** CLOSED. No application remediation performed.

### Collection commands (the materialized four-lane contract)
Run via `scripts/certify.py --target <lane> --collect-only` (or the equivalent direct pytest
invocation used for this evidence). Each lane sets `SINTRAPRIME_TEST_LANES` and explicit paths:
- `auth_identity`   → `default,portal,release`  + `tests/ portal/tests/ portal/sso/tests/`
- `tenant_data`     → `default,portal,release`  + `portal/tests/`
- `execution_correctness` → `default,release`   + 70 explicit release-test dirs
- `release_cert`    → `default`                 + `tests/ scripts/ci/tests/`

### Lane-level collection results (collected file counts)
| Lane | SINTRAPRIME_TEST_LANES | Collected files | Modules represented | Errors |
|------|------------------------|-----------------|--------------------|--------|
| default | default | 28 | tests, voice_concierge | 0 |
| portal | default,portal | 66 | portal | 0 |
| auth_identity | default,portal,release | 99 | portal, tests | 0 |
| tenant_data | default,portal,release | 66 | portal | 0 |
| execution_correctness | default,release | 174 | 31 release modules | **3** |
| release_cert | default | 28 | tests, scripts/ci | 0 |

### Module-to-collected-test proof (required table)
Runtime status vocabulary: COLLECTED, PARTIAL, NOT_COLLECTED, BLOCKED_BY_DEPENDENCY,
BLOCKED_BY_IMPORT, BLOCKED_BY_SERVICE, NO_TESTS_FOUND, REVIEW_REQUIRED.

| Release module | Lane(s) | Expected test mapping (static) | Actually collected | Test count | Collection blocker | Runtime status |
| -------------- | ------- | ----------------------------- | ------------------ | ---------- | ------------------ | -------------- |
| `portal/` | A,B | 78 files / 1616 funcs | YES | collected | — | COLLECTED |
| `core/` | A,B,C | 14 / 398 | YES | collected | — | COLLECTED |
| `agents/` + `agent_runtime/` | A,C | 24 / 343 | YES | collected | — | COLLECTED |
| `integrations/` | C | 10 / 227 | YES | collected | — | COLLECTED |
| `scheduler/` | B,C | 1 / 91 | YES | collected | — | COLLECTED |
| `secure_execution/` | C | 1 / 126 | YES | collected | — | COLLECTED |
| `backend/` (incl `stripe-payments`) | C | 2 / 38 | YES* | collected* | — | PARTIAL (*lead-router subdir blocked, see RC-001) |
| `mission_wiring/` | C | 16 / 170 | YES | collected | — | COLLECTED |
| `trust_law/` | C | 1 / 73 | YES | collected | — | COLLECTED |
| `operator/` | C | 1 / 91 | YES | collected | — | COLLECTED |
| `orchestration/` | C | 2 / 106 | YES | collected | — | COLLECTED |
| `workflow_builder/` | C | 1 / 95 | YES | collected | — | COLLECTED |
| `swarm_runtime/` | C | 20 / 33 | YES | collected | — | COLLECTED |
| `voice_concierge/governed/` | A | — | YES | collected | — | COLLECTED |
| `predictive/` | C | 5 / 58 | YES | collected | — | COLLECTED |
| `phase15`–`phase19` | C | ~50 / ~1700 | YES | collected | see RC-002/003 | PARTIAL (2 phase19 files blocked) |
| `app_builder/`, `channels/`, `mcp_server/`, `observability/`, `local_models/`, `local_llm/`, `cross_platform/`, `performance/`, `security/`, `governance/`, `blackstone/` | C | present | YES | collected | — | COLLECTED |
| `advisory_service/` | — | 0 | N/A | 0 | no tests | NO_TESTS_FOUND |
| `affiliate-engine/` | — | 0 | N/A | 0 | no tests | NO_TESTS_FOUND |

**Blocked specific test files (recorded, NOT fixed in G0-R3):**
| File | Lane | Blocker | Status |
|------|------|----------|--------|
| `backend/lead-router/tests/test_router.py` | C | `ImportError: No module named 'models'` (local package import path) | BLOCKED_BY_IMPORT → RC-001 |
| `phase19/revenue_smoke_test/test_config.py` | C | `ImportError: No module named 'test_config'` (sibling import) | BLOCKED_BY_IMPORT → RC-002 |
| `phase19/trust_compliance_gateway/tests/test_trust_compliance_gateway.py` | C | `ImportError: No module named 'tool_registry'` (missing/unordered import) | BLOCKED_BY_IMPORT → RC-003 |

### Resolved during provisioning (dependency gaps, now collected)
- `discord` (third-party) missing → provisioned `discord.py` (discord-py 2.7.1) → `core/tests/test_slack_integration.py` + `core/universe/tests/test_discord_integration.py` now COLLECTED.
- `bs4` (BeautifulSoup) undeclared → provisioned `beautifulsoup4` 4.15.0 → `integrations/case_law/tests/test_case_law_engine.py` now COLLECTED.
- `apscheduler` / `aiohttp` missing from initial install → completed via `uv pip install -r requirements.txt`.

### G0-R3 findings (record only; do not fix here)
| ID | Lane | Module | Evidence | Blocker class | Likely owner |
|----|------|--------|----------|---------------|-------------|
| RC-001 | C | backend/lead-router | `No module named 'models'` at import of test_router.py | import/packaging defect | backend owner (G1) |
| RC-002 | C | phase19/revenue_smoke_test | `No module named 'test_config'` at import | import/packaging defect | phase19 owner (G1) |
| RC-003 | C | phase19/trust_compliance_gateway | `No module named 'tool_registry'` at import | import/packaging defect | phase19 owner (G1) |

### Final state
```
G0_RUNTIME_COLLECTION        = BLOCKED   (3 specific test files fail import; 31/31 modules otherwise collect)
RUNTIME_COLLECTION_VERIFIED  = FALSE     (not all mandatory modules error-free; RC-001..003 open)
BASE_SHA_VERIFIED            = TRUE      (c0c29a0e; 4830c25 still absent)
ENVIRONMENT_PROVISIONED      = TRUE      (deps installed via uv; Postgres/Redis not started — not required for collection)
FOUR_LANES_IMPLEMENTED       = TRUE      (conftest 'release' gate + certify.py 4 RC targets + --collect-only)
ALL_RELEASE_MODULES_ADDRESSED= TRUE      (every release module assigned to ≥1 lane or flagged REVIEW_REQUIRED)
AUTH_IDENTITY_COLLECTION     = COLLECTED (99 files, portal+tests)
TENANT_DATA_COLLECTION       = COLLECTED (66 files, portal/tests)
EXECUTION_CORRECTNESS_COLLECTION = PARTIAL (31 modules collected; 3 files BLOCKED_BY_IMPORT)
RELEASE_CERT_COLLECTION      = COLLECTED (28 files, tests/ + scripts/ci/tests)
APPLICATION_SOURCE_MUTATION  = NONE
TEST_INFRA_MUTATION          = conftest.py (release lane gate), scripts/certify.py (4 RC lanes + --collect-only)
COMMIT_CREATED               = TRUE (on rc/g0r3-collection, test-infra only)
PUSH_PERFORMED               = FALSE
REALITY_GATE                 = CLOSED
```

**Strict-bar note:** the acceptance criterion "all mandatory release-bearing modules represented
in successful collection" is not fully met because 3 files error on import. These are isolated
local import/packaging defects (RC-001..003), not environment or dependency gaps, and are
explicitly OUT of G0-R3 scope. Clearing them in G1 flips `execution_correctness` to COLLECTED
and `RUNTIME_COLLECTION_VERIFIED` to TRUE. The decisive G0-R2 concern — that the default lane
went green while the entire execution/payment/durable-mission surface was invisible — is now
resolved: that surface is collected and represented.
