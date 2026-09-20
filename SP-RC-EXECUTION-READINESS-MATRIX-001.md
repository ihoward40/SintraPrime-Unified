# SP-RC-EXECUTION-READINESS-MATRIX-001
## G0-R4 — Execution Readiness (readiness / environment / execution-plan verification)

**Governing branch:** `rc/g0r3-collection` · **Commits:** `78e36a4d` → `818a6d00`
**Immutable production base:** `c0c29a0eb8f404e2bb748be33b8edb9ffff1fc7d` (= local `main` = `origin/main`)
**No test execution performed. No application source mutation. Reality Gate CLOSED.**

## 1. Provenance re-freeze
- HEAD `818a6d00` on `rc/g0r3-collection`; `c0c29a0e` verified ancestor; lineage `c0c29a0e → 78e36a4d → 818a6d00` exactly as expected.
- Changed-file set since `c0c29a0e` (7 files): 2 evidence docs, root `conftest.py`, `scripts/certify.py`, 3 package `conftest.py`. **Zero production-source delta → no STOP condition.**

## 2. Lane execution-requirements matrix

| Lane | Test paths | DB required | Redis required | External APIs | Credentials | Filesystem/state | Network required | Optional deps | Isolation requirement | Ready? |
| ---- | ---------- | ----------- | -------------- | ------------- | ----------- | ---------------- | ---------------- | ------------- | --------------------- | ------ |
| RELEASE_CERT | `tests/`, `scripts/ci/tests/` | NO (sqlite ×1, rest none) | NO | LLM refs ×3 (mocked) | none required | tmp dirs only | NO | none | none beyond tmp | **YES** |
| AUTH_IDENTITY | `tests/`, `portal/tests/`, `portal/sso/tests/` | NO by default (sqlite ×27); PG only for `postgresql`-marked subset (env-gated) | NO by default (3 refs, mocked/guarded) | LLM ×3, email/SMS refs (mocked) | `OPENAI_API_KEY` referenced in mocked tests → TEST_PLACEHOLDER_ALLOWED | tmp | NO | none | sqlite per-test tmp DB | **YES** |
| TENANT_DATA | `portal/tests/`, `portal/routers/tests/` | NO by default (same profile as AUTH) | NO by default | none live | none | tmp | NO | none | sqlite per-test tmp DB | **YES** |
| EXECUTION_CORRECTNESS | 68 release-test dirs | PARTIAL — `postgresql`-marked + `POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL`/`MISSION_CONTROL_PG_RACE_REQUIRED` gated subset (2 files) | PARTIAL — 3 refs, mocked/guarded | stripe ×8, llm ×15, http_out ×21, cloud ×12, slack ×4, discord ×5 — **mostly mocked, see ER-001** | `SECRET_KEY`/`API_KEY` (placeholders in tests) | see ER-002 (swarm "real" acceptance) | only via mocked/loopback | none beyond installed extras | see ER-002 | **BLOCKED → ER-001/ER-002** |

Evidence basis: static sweep of 514 lane test files + 6 conftests (`artifacts/rc_r4_scan.json`); `pytest.ini` markers (`postgresql`, `integration`, `slow`, `smoke`, `experimental`).

## 3. Infrastructure dependency classification
| Dependency | Classification | Evidence |
|---|---|---|
| PostgreSQL | **NOT_REQUIRED for lanes by default**; REQUIRED_FOR_EXECUTION only for `postgresql`-marked / env-gated subset (2 test files) | markers in `pytest.ini`; env gates in `portal/tests/test_mission_control_run_controls.py`, `test_postgresql_bootstrap_schema_authority.py` |
| Redis | NOT_REQUIRED / MOCKED (3 refs per lane, guarded) | scan |
| Filesystem persistence | MOCKED/tmp (destructive FS ops confined to 5 files → ER-002) | scan |
| Subprocess execution | PARTIALLY MOCKED (17 files; 9 mocked → ER-004) | scan |
| Docker/testcontainers | NOT_REQUIRED (1 incidental ref) | scan |
| HTTP/network | MOCKED_SAFE majority (17/21); 4 files UNKNOWN → ER-001 | scan |
| Stripe | MOCKED_SAFE ×3; **5 files UNKNOWN → ER-001** | scan |
| Slack/Discord/Telegram/Plaid | MOCKED_SAFE (refs inside mocked channel tests) | scan |
| OpenAI/LLM providers | MOCKED_SAFE ×11/15; 4 UNKNOWN → ER-001 | scan |
| Email/SMS | MOCKED_SAFE | scan |
| Cloud/object storage | MOCKED_SAFE ×8/12; 4 UNKNOWN → ER-001 | scan |
| Scheduler workers / background queues | in-process; not external | scan |

**No external live service is contacted merely because credentials exist** — no lane requires a real secret at collection; ER-001 lists the unknowns.

## 4. Environment-variable map (consumed inside lane test paths)
| Variable | Lane(s) | Required? | Secret? | Safe test value | Failure if missing |
|---|---|---|---|---|---|
| `DATABASE_URL` | AUTH/TENANT/EXEC | optional (sqlite fallback) | non-secret (test URL) | `sqlite+aiosqlite:///:memory:` | falls back / skips PG-only tests |
| `POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL` | EXEC (1 file) | optional gate | non-secret (disposable test DB) | unset → skip | test skipped |
| `MISSION_CONTROL_PG_RACE_REQUIRED` | AUTH/TENANT/EXEC (1 gate file) | optional gate | non-secret | unset → skip | test skipped |
| `NOVA_ALLOW_DYNAMIC_EXEC` | AUTH/EXEC/RELEASE_CERT | security gate | non-secret | unset (deny) | gated path not exercised |
| `OPENAI_API_KEY` | AUTH/EXEC/RELEASE_CERT (mocked LLM tests) | TEST_PLACEHOLDER_ALLOWED (mocked) | secret-shaped, never live | `"sk-test-placeholder"` | mock used; no call |
| `SECRET_KEY`, `API_KEY` | EXEC | TEST_PLACEHOLDER_ALLOWED | placeholder | test constants | test constants |
| `DURABLE_WORKFLOW_*` (3) | AUTH/TENANT/EXEC | optional tunables | non-secret | defaults | defaults |
| `LOCALAPPDATA` | EXEC (1 file) | platform | non-secret | OS default | n/a |

**REAL_SECRET_REQUIRED: none** for any mandatory lane, provided ER-001's unknown subset is resolved or excluded. `OMNIROUTE_API_KEY` is not consumed by any lane test.

## 5. Production-import fidelity (PYTEST vs PRODUCTION topology)
Probes ran with **no repo-root `PYTHONPATH` and no pytest augmentation**:
| Surface | PYTEST_IMPORTABLE | PRODUCTION_RUNTIME_IMPORTABLE | Verdict |
|---|---|---|---|
| `backend/lead-router` | TRUE (via conftest sys.path = service-root) | **TRUE** — self-contained service root (`python -c "import models.lead, utils.matching, services.agent_service"` from its own dir → OK). Not importable as `backend.lead_router` from repo root, but that is not its runtime topology (standalone service with own `main.py`/`requirements.txt`) | faithful — no camouflage |
| `phase19/revenue_smoke_test` | TRUE (via `phase19/conftest.py`) | **TRUE in script topology** (cwd = package dir: `import test_config, scenarios` → OK); **FALSE as repo subpackage** (`import phase19.revenue_smoke_test` → `No module named 'test_config'`) | **PKG-001** recorded |
| `phase19/trust_compliance_gateway` | TRUE | **TRUE** (module dir topology imports OK) | faithful |

`PKG-001` (recorded, NOT fixed per directive): `phase19.revenue_smoke_test` mixes relative (`from .test_config`) and absolute (`from test_config`) imports; it is executable as a script in its own directory but not importable as a repo-root subpackage. The pytest fix mirrors the true runtime topology, so collection is not masking a broken production path — but the mixed style should be normalized in G1.

## 6. Database / Redis readiness
- **PostgreSQL** (only the `postgresql`-marked subset): bootstrap via `portal/scripts/postgresql_bootstrap.py` + `POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL`; disposable per-run DB implied by marker semantics; race-condition subset gated by `MISSION_CONTROL_PG_RACE_REQUIRED`. Not started in this phase (no harmless probe required — subset is env-gated and skipped without it).
- **Redis**: no lane requires it; references are mocked/guarded.

## 7–8. External-service safety & destructive-operation audit
- **ER-001 (blocker, medium severity):** 5 stripe-referencing, 4 http_out, 4 cloud, 4 llm test files contain **no visible mock/stub** → `UNKNOWN` live-call risk until inspected or explicitly excluded (e.g. via `integration` marker deselection if so marked).
- **ER-002 (blocker, high severity):** `swarm_runtime/tests/test_acceptance_00{3,4,4_real,5b}.py` and `agents/chat/tests/test_chat_agent.py`, `core/tests/test_marketplace.py` perform FS deletion / process-kill / git-state operations with **no mocks** → containment unverified.
- **ER-003 (blocker, low severity):** no `pytest-timeout` installed and no timeout configured → a hanging test stalls the lane; add timeout policy or accept serial wall-clock caps.
- **ER-004 (note):** 8 subprocess-using files unmocked — command scope unverified (overlaps ER-002).
- **ER-005 (note):** PKG-001 above.

## 9. Execution order (evidence-based; matches default preference)
1. **RELEASE_CERT** (no services, fastest signal) → 2. **AUTH_IDENTITY** (sqlite-only by default) → 3. **TENANT_DATA** (same profile) → 4. **EXECUTION_CORRECTNESS** (broadest; last). No inter-lane dependency beyond shared venv.

## 10. Exact execution contracts (NOT executed)
All lanes: interpreter `.venv/Scripts/python.exe`; `python -m pytest` (or `scripts/certify.py --target <lane>`); serial (no `-n`); `-p no:cacheprovider`; `-m "not experimental"`; env: `SINTRAPRIME_TEST_LANES` per lane, `DATABASE_URL=sqlite+aiosqlite:///:memory:` (or unset), PG/Redis vars unset; wall-clock cap 1800 s/lane (external watchdog, since no pytest-timeout); evidence → `artifacts/cert-receipts/`. Commands reproducible from `rc/g0r3-collection`.
- `RELEASE_CERT`: `pytest tests/ scripts/ci/tests/ -m "not experimental"`
- `AUTH_IDENTITY`: `pytest tests/ portal/tests/ portal/sso/tests/ -m "not experimental"` (LANES=`default,portal,release`)
- `TENANT_DATA`: `pytest portal/tests/ -m "not experimental"` (LANES=`default,portal,release`)
- `EXECUTION_CORRECTNESS`: the 68-dir contract via `certify.py --target execution_correctness` (LANES=`default,release`) — **blocked until ER-001/ER-002 resolved or a documented exclusion set is applied.**

## 11. Resource sizing
`pytest-xdist` **not installed** and parallelism unproven → **serial deterministic certification** (default). No DB/Redis contention by default (sqlite tmp). Memory-sensitive: none identified. Hang risk: ER-003 (mitigate with external wall-clock cap).

## 13. Readiness gate
`G0_EXECUTION_READINESS = BLOCKED`
Three lanes (RELEASE_CERT, AUTH_IDENTITY, TENANT_DATA) are fully ready. EXECUTION_CORRECTNESS is blocked by ER-001 (unknown live-call subset) and ER-002 (uncontained destructive "real" acceptance tests) until each is inspected and either confirmed `MOCKED_SAFE`/`SANDBOX_SAFE` or formally excluded with governance sign-off. ER-003 applies to all lanes (timeout policy). No remediation performed in this phase.

## 14. Terminal state
```
BASE_PROVENANCE_VERIFIED        = TRUE
RUNTIME_COLLECTION_VERIFIED     = TRUE
LANE_REQUIREMENTS_MAPPED        = TRUE
POSTGRES_REQUIRED               = PARTIAL (postgresql-marked env-gated subset only; not lane-wide)
REDIS_REQUIRED                  = FALSE
EXTERNAL_SERVICE_RISK_MAPPED    = TRUE (ER-001 unknowns identified)
ENVIRONMENT_VARIABLES_MAPPED    = TRUE (no REAL_SECRET_REQUIRED for mandatory lanes)
DESTRUCTIVE_TESTS_MAPPED        = TRUE (ER-002 containment unverified)
PRODUCTION_IMPORT_FIDELITY_CHECKED = TRUE (PKG-001 recorded, not fixed)
EXECUTION_COMMANDS_DEFINED      = TRUE
EXECUTION_ORDER_DEFINED         = TRUE
G0_EXECUTION_READINESS          = BLOCKED
TEST_EXECUTION_PERFORMED        = FALSE
APPLICATION_SOURCE_MUTATION     = NONE
TEST_INFRA_MUTATION             = NONE
COMMIT_CREATED                  = TRUE (documentation-only readiness matrix)
PUSH_PERFORMED                  = FALSE
REALITY_GATE                    = CLOSED
```

**Unblocking path:** resolve ER-001/ER-002 by inspection + explicit classification (or documented exclusion set), and adopt a timeout policy (ER-003) — then re-issue this matrix as PASS and proceed to "start only the infrastructure proven necessary and execute the four lanes sequentially with per-lane receipts."
