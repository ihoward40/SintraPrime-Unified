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
| `backend/lead-router/tests/test_router.py` | C | `No module named 'models'` (TEST_IMPORT_PATH) | COLLECTED — fixed via conftest sys.path (RC-001) |
| `phase19/revenue_smoke_test/test_config.py` | C | `No module named 'test_config'` (TEST_PACKAGE_LAYOUT) | COLLECTED — fixed via phase19/conftest sys.path (RC-002) |
| `phase19/trust_compliance_gateway/tests/test_trust_compliance_gateway.py` | C | `No module named 'tool_registry'` (TEST_IMPORT_PATH) | COLLECTED — fixed via conftest sys.path (RC-003) |

### Resolved during provisioning (dependency gaps, now collected)
- `discord` (third-party) missing → provisioned `discord.py` (discord-py 2.7.1) → `core/tests/test_slack_integration.py` + `core/universe/tests/test_discord_integration.py` now COLLECTED.
- `bs4` (BeautifulSoup) undeclared → provisioned `beautifulsoup4` 4.15.0 → `integrations/case_law/tests/test_case_law_engine.py` now COLLECTED.
- `apscheduler` / `aiohttp` missing from initial install → completed via `uv pip install -r requirements.txt`.

### G0-R3 findings (record only; do not fix here)
| ID | Lane | Module | Evidence | Blocker class | Likely owner |
|----|------|--------|----------|---------------|-------------|
| RC-001 | C | backend/lead-router | `No module named 'models'` → classified TEST_IMPORT_PATH; fixed via package conftest sys.path (no source change) | RESOLVED (G0-R3.1, test-infra) |
| RC-002 | C | phase19/revenue_smoke_test | `No module named 'test_config'` → classified TEST_PACKAGE_LAYOUT; fixed via phase19/conftest sys.path (no source change) | RESOLVED (G0-R3.1, test-infra) |
| RC-003 | C | phase19/trust_compliance_gateway | `No module named 'tool_registry'` → classified TEST_IMPORT_PATH; fixed via package conftest sys.path (no source change) | RESOLVED (G0-R3.1, test-infra) |

### Final state
```
G0_RUNTIME_COLLECTION        = PASS      (all four lanes collect with 0 errors; RC-001..003 resolved in G0-R3.1)
RUNTIME_COLLECTION_VERIFIED  = TRUE      (all mandatory release-bearing modules represented; RC-001..003 clear; no new errors)
BASE_SHA_VERIFIED            = TRUE      (c0c29a0e; 4830c25 still absent)
ENVIRONMENT_PROVISIONED      = TRUE      (deps installed via uv; Postgres/Redis not started — not required for collection)
FOUR_LANES_IMPLEMENTED       = TRUE      (conftest 'release' gate + certify.py 4 RC targets + --collect-only)
ALL_RELEASE_MODULES_ADDRESSED= TRUE      (every release module assigned to ≥1 lane or flagged REVIEW_REQUIRED)
AUTH_IDENTITY_COLLECTION     = COLLECTED (99 files, portal+tests)
TENANT_DATA_COLLECTION       = COLLECTED (66 files, portal/tests)
EXECUTION_CORRECTNESS_COLLECTION = COLLECTED (31 modules, 0 collection errors; RC-001..003 resolved via test-runner path config)
RELEASE_CERT_COLLECTION      = COLLECTED (28 files, tests/ + scripts/ci/tests)
APPLICATION_SOURCE_MUTATION  = NONE
TEST_INFRA_MUTATION          = conftest.py (release lane gate), scripts/certify.py (4 RC lanes + --collect-only), 3 package conftest.py (backend/lead-router, trust_compliance_gateway, phase19) for sys.path insertion
COMMIT_CREATED               = TRUE (on rc/g0r3-collection, test-infra only)
PUSH_PERFORMED               = FALSE
REALITY_GATE                 = CLOSED
```

**Strict-bar note (updated G0-R3.1):** the acceptance criterion "all mandatory release-bearing
modules represented in successful collection" is now MET. RC-001..003 were all classified as
`TEST_IMPORT_PATH` / `TEST_PACKAGE_LAYOUT` (runner-path-config defects, not application defects)
and cleared in G0-R3.1 by adding three `conftest.py` sys.path insertions — no application or
test-logic source was modified. All four lanes (`auth_identity`, `tenant_data`,
`execution_correctness`, `release_cert`) now collect with **0 errors** and every mandatory
release-bearing module is represented. `RUNTIME_COLLECTION_VERIFIED = TRUE`. The decisive G0-R2
concern — that the default lane went green while the entire execution/payment/durable-mission
surface was invisible — is resolved: that surface is collected and represented. Execution
(running the suites) remains separately authorized and will additionally require PostgreSQL/Redis
only for the lanes that need them.
