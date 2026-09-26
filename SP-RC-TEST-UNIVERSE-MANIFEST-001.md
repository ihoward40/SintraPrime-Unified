# SP-RC-TEST-UNIVERSE-MANIFEST-001
## G0-R2 — Release Test Universe Definition (READ-ONLY / EVIDENCE-ONLY)

**Immutable RC base:** `c0c29a0eb8f404e2bb748be33b8edb9ffff1fc7d`
**Reality Gate:** CLOSED. No source/config/commit/push/install/test-execution performed.
**pytest availability:** ABSENT in this environment (E1) → all "collected" columns are
**config-inferred / static**, NOT executed. `RUNTIME_COLLECTION_VERIFIED = FALSE`.

---

## A. Pytest control-surface map (section 2 evidence)

| Mechanism | Location | Behavior |
|-----------|----------|----------|
| Config file | `pytest.ini` (PREVAILS over `pyproject.toml` `[tool.pytest.ini_options]`) | `testpaths = tests, portal/tests, voice_concierge/governed/tests`; `addopts = --tb=short -q --import-mode=importlib -m "not experimental"`; `norecursedirs` incl. `operator`, `apps`, `deployment`, `web`, `mobile`, `models`, `shared`, `docs`, `.github`, `node_modules`, `artifacts`, `phase19/revenue_smoke_test`; markers: experimental, integration, **postgresql**, slow, **smoke** |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` | Superseded by `pytest.ini`; identical `testpaths`/`addopts` minus `--import-mode=importlib` and the `postgresql`/`smoke` markers |
| Collection gate | root `conftest.py` `collect_ignore_glob` | Unconditionally excludes ~56 dirs (core, agents, scheduler, secure_execution, backend, trust_law, operator, integrations, orchestration, workflow_builder, app_builder, channels, mcp_server, observability, local_models, local_llm, cross_platform, performance, security, governance, phase15–19, …). **Only `portal`, `predictive`, `integrations` are conditionally re-enabled** when their lane keyword is in `SINTRAPRIME_TEST_LANES`. |
| Lane runner | `scripts/certify.py` `TARGETS` | **Only three targets exist:** `default`→`tests/`,`voice_concierge/governed/tests/`; `portal`→`portal/tests/`; `swarm`→`swarm_runtime/tests/`. `LANE_ENV`: default→`default`, portal→`default,portal`, swarm→`default,swarm`. **`predictive`/`integrations` are referenced in conftest but NOT defined in certify.py (dead lanes).** |
| CI invocations | `.github/workflows/ci.yml` | `test` job: `python -m pytest --tb=short -q` (default universe). Dedicated jobs: `auth-tenant-rbac-certification`, `audit-correlation-non-http-certification`, `http-correlation-ws-hardening-certification`, `postgresql-race`, `postgresql-bootstrap-certification` (all explicit `pytest portal/tests/*.py` file paths, with Postgres service). `lint` (ruff), `claims-validation`, `security` (bandit+safety). |
| CI invocations | `portal-ci.yml` | `scripts/certify.py --target portal` with `SINTRAPRIME_TEST_LANES=default,portal` + Postgres. |
| CI invocations | `sigma-gate.yml` | `pytest --cov=. --cov-report=json` (default universe only) + bandit. |
| CI invocations | `swarm-runtime-ci.yml` | `swarm_runtime/tests/` via certify target `swarm`. |
| CI invocations | `smoke.yml` | `scripts/smoke/e2e_skills_smoke.py` (not module tests). |
| Makefile `test` | `Makefile` | `cd core && pytest` + `cd tests/integration && pytest` (paths that do not exist as collectible under root config; `core/` is ignored and `tests/integration` is outside `testpaths`). |

**Net effective collectible universe (any automation):** `tests/`, `voice_concierge/governed/tests/`, `portal/tests/` (+ `portal/sso/tests`, `portal/websocket`), `swarm_runtime/tests/`. Nothing else.

---

## B. Release module × lane inventory (section 3)

Classification: **A** = Auth/Identity, **B** = Tenant/Data isolation, **C** = Execution/Payment/Correctness, **D** = CI/Release cert.

| Release module | Lane(s) | Test location(s) | Test files/funcs (static) |
|---------------|---------|-----------------|---------------------------|
| `portal/` | A,B | `portal/tests/`, `portal/sso/tests/` | 78 files / 1,616 |
| `portal/routers` (messages,documents,jurisdictions) | B | `portal/tests/test_messages.py`, `test_documents.py`, `test_document_export_*`, `test_message_persistence_certification.py` | subset of above |
| `core/` | A,B,C | `core/tests/` | 14 / 398 |
| `agents/` + `agent_runtime/` | A,C | `agent_runtime/tests/` (19/246), `agents/*` (5/97) | — |
| `integrations/` | C | `integrations/*/tests/` | 10 / 227 |
| `scheduler/` | B,C | `scheduler/` (1/91), `tests/test_scheduler_executor.py` | — |
| `secure_execution/` | C | `secure_execution/tests/` (1/126) | — |
| `backend/` (incl `stripe-payments`) | C | `backend/stripe-payments/tests/test_stripe.py` (NOT collected), `portal/tests/test_billing.py` (collected) | 2 / 38 |
| `mission_wiring/` | C | `mission_wiring/tests/` (16/170: crash matrix, restart, reconciliation, approval, envelope) | 16 / 170 |
| `trust_law/` | C | `trust_law/` (1/73) | — |
| `operator/` | C | `operator/tests/` (1/91) | — |
| `orchestration/` | C | `orchestration/tests/` (2/106) | — |
| `workflow_builder/` | C | `workflow_builder/` (1/95) | — |
| `swarm_runtime/` | C | `swarm_runtime/tests/` (20/33) | — |
| `voice_concierge/governed/` | A | `voice_concierge/governed/tests/` | — |
| `advisory_service/` | (design-only) | **none** | 0 / 0 |
| `affiliate-engine/` | (out of RC scope) | **none** | 0 / 0 |

---

## C. Collection-coverage manifest (section 6 — required table)

Certification status vocabulary applied: `COVERED`, `PARTIAL`, `EXCLUDED_FROM_DEFAULT`,
`NO_TEST_MAPPING_FOUND`, `COLLECTION_UNPROVEN`, `REVIEW_REQUIRED`.

| Release module | Risk lane | Test location | Default collected? | Explicitly excluded? | Req. marker | Req. extras/services | CI lane exists? | Cert status |
| -------------- | --------- | ------------- | ------------------ | -------------------- | ----------- | -------------------- | --------------- | ------------ |
| `tests/` (Tier1) | A,B,C,D | `tests/` | **YES** | No | `not experimental` | main deps | YES (ci.yml `test`) | PARTIAL |
| `voice_concierge/governed/` | A | `voice_concierge/governed/tests/` | **YES** | No (not in glob) | `not experimental` | main | YES (default) | PARTIAL |
| `portal/` | A,B | `portal/tests/` | NO | YES (un-ignored by `portal` lane) | `not experimental` | .[portal], **Postgres**, Redis | YES (portal-ci + 6 dedicated jobs) | EXCLUDED_FROM_DEFAULT |
| `portal/routers` (tenant) | B | `portal/tests/test_messages.py` etc. | NO | YES (portal lane) | `not experimental` | Postgres | PARTIAL (rides portal-ci; no dedicated job) | EXCLUDED_FROM_DEFAULT |
| `core/` | A,B,C | `core/tests/` | NO | YES (unconditional glob) | `not experimental` | Postgres | **NO** | EXCLUDED_FROM_DEFAULT |
| `agents/` | A,C | `agents/*` | NO | YES (unconditional glob) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `agent_runtime/` | A,C | `agent_runtime/tests/` (19/246) | NO | **Invisible** (not in glob, not in testpaths) | — | Postgres, Redis | **NO** | COLLECTION_UNPROVEN |
| `integrations/` | C | `integrations/*/tests/` (10/227) | NO | YES (unconditional; `integrations` lane dead in certify) | `integration` | .[integrations]=plaid | **NO** | EXCLUDED_FROM_DEFAULT |
| `scheduler/` | B,C | `scheduler/` (1/91) | NO | YES (unconditional glob) | `integration`? | Redis | **NO** | EXCLUDED_FROM_DEFAULT |
| `secure_execution/` | C | `secure_execution/tests/` (1/126) | NO | YES (unconditional glob) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `backend/stripe-payments/` | C | `backend/stripe-payments/tests/test_stripe.py` | NO | YES (unconditional glob) | — | Postgres | **NO** (only `portal/tests/test_billing.py` collected) | EXCLUDED_FROM_DEFAULT |
| `mission_wiring/` | C | `mission_wiring/tests/` (16/170) | NO | **Invisible** (not in glob, not in testpaths) | — | Postgres | **NO** | COLLECTION_UNPROVEN |
| `trust_law/` | C | `trust_law/` (1/73) | NO | YES (unconditional glob) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `operator/` | C | `operator/tests/` (1/91) | NO | YES (glob + norecursedirs) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `orchestration/` | C | `orchestration/tests/` (2/106) | NO | YES (unconditional glob) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `workflow_builder/` | C | `workflow_builder/` (1/95) | NO | YES (unconditional glob) | — | — | **NO** | EXCLUDED_FROM_DEFAULT |
| `swarm_runtime/` | C | `swarm_runtime/tests/` (20/33) | NO (default) | No (not in glob) | `not experimental` | main | YES (certify `swarm` + swarm-runtime-ci) | EXCLUDED_FROM_DEFAULT |
| `advisory_service/` | — | none | NO | n/a | — | — | **NO** | NO_TEST_MAPPING_FOUND |
| `affiliate-engine/` | — | none | NO | n/a | — | — | **NO** | NO_TEST_MAPPING_FOUND |

**Summary of the table:** Only `tests/` and `voice_concierge/governed/` are collected by the
default lane. `portal/` and `swarm_runtime/` are collected only via explicit lane/CI. **Every
other release-bearing module — including the entire execution/SSRF/payment/durable-mission
surface — has no automated collection path.** Tests for those surfaces exist on disk but are
never discovered by any current workflow.

---

## D. Release-universe gaps (section 7)

```
STATICALLY_PROVEN (read-only conclusions):
  total release-bearing packages evaluated : 28
  packages with mapped tests               : 26  (advisory_service, affiliate-engine = 0)
  packages excluded from DEFAULT collection: 26 of 28
  packages with NO mapped tests            : 2   (advisory_service, affiliate-engine)
  packages requiring optional extras       : integrations (plaid), predictive (pandas/sklearn)
  packages requiring Postgres              : portal, core, agent_runtime, backend, mission_wiring
  packages requiring Redis                 : portal, scheduler, agent_runtime
  packages requiring other infra           : none beyond PG/Redis
  CI workflows exercising a lane           : ci.yml(default), portal-ci.yml(portal),
                                             sigma-gate(default+coverage), swarm-runtime-ci(swarm),
                                             ci.yml dedicated: auth/audit/ws/pg-race/pg-bootstrap
  release lanes with NO verified CI path   : TENANT_DATA (rides portal-ci, no dedicated job),
                                             EXECUTION_CORRECTNESS (agent_runtime/secure_execution/
                                             operator/mission_wiring uncollected),
                                             PAYMENT (backend/phase16/phase18 uncollected)

RUNTIME_UNPROVEN (cannot assert without pytest + services + deps):
  actual collected counts per lane
  pass/fail of any lane
  whether experimental-marked RC tests exist and are excluded
  whether tests import/execute under required extras
  sigma-gate coverage % reliability (--cov=. over default-only execution)
```

---

## E. Certification law (section 8)

A release candidate **cannot** be certified from the default pytest lane alone if that lane
excludes release-bearing modules. Release certification MUST require:

1. exact candidate SHA frozen (`c0c29a0e…`);
2. release-test universe explicitly defined (the four lanes below);
3. collection performed against that exact SHA;
4. all release-bearing modules mapped to an included lane or formally justified;
5. required dependencies/services available;
6. all mandatory lanes executed;
7. failures resolved or explicitly dispositioned;
8. evidence retained for the exact candidate;
9. no code changes between certification and release without invalidating certification.

---

## F. Proposed `SINTRAPRIME_TEST_LANES` (section 5 — DRAFT, not implemented)

A "lane" = **paths + markers + dependencies + infrastructure + environment + CI invocation**
(not merely a marker). Proposed four certification contracts:

```
AUTH_IDENTITY
  paths:     portal/tests/ (+ portal/sso/tests/) ; tests/ auth/legal-authority
  markers:   -m 'not experimental'
  extras:    .[portal] (PyJWT/requests already in main deps)
  services:  Postgres, Redis
  env:       DATABASE_URL, REDIS_URL, SINTRAPRIME_TEST_LANES=default,portal
  surfaces:  B1 auth/legal-route, WS revocation, JTI, refresh rotation, audit/correlation
  collect:   scripts/certify.py --target auth_identity   (AFTER extending TARGETS)
  PASS ev:   rbac/audit/ws-hardening cert files + cross-process revocation + forged-header negatives = 0 fail

TENANT_DATA
  paths:     portal/tests/ (messages,documents,tenant)
  markers:   -m 'not experimental'
  extras:    .[portal]
  services:  Postgres
  env:       DATABASE_URL, SINTRAPRIME_TEST_LANES=default,portal
  surfaces:  B2 cross-tenant read/mutate/attach/ack + pagination + RLS
  collect:   scripts/certify.py --target tenant_data           (AFTER extending TARGETS)
  PASS ev:   tenant negative matrix 0 fail; RLS verified at DB

EXECUTION_CORRECTNESS
  paths:     agent_runtime/tests/ secure_execution/tests/ operator/tests/
             mission_wiring/tests/ backend/stripe-payments/tests/ orchestration/tests/
             (must be ADDED to testpaths or passed as explicit path args; currently invisible)
  markers:   -m 'not experimental'
  extras:    main + Postgres + Redis
  services:  Postgres, Redis
  env:       DATABASE_URL, REDIS_URL, SINTRAPRIME_TEST_LANES=default,execution
  surfaces:  B3 atomic/idempotent ledger, B4 SSRF/exec governance, B5 durable recovery
  collect:   scripts/certify.py --target execution_correctness  (AFTER extending TARGETS + conftest un-ignore + testpaths)
  PASS ev:   concurrency/idempotency, SSRF reject list, crash/restart reconciliation = 0 fail

RELEASE_CERT
  paths:     tests/ scripts/ci/tests/ (claims validation, smoke, lint, security)
  markers:   -m 'not experimental'
  extras:    dev (ruff, bandit, pytest-cov)
  services:  none (static)
  env:       n/a
  surfaces:  D — claims validation, import/startup checks, bandit, migration validation
  collect:   python -m pytest scripts/ci/tests/ ; python scripts/ci/validate_repository_claims.py
  PASS ev:   claims validated; bandit no new findings; lint clean
```

**Implementation note (recorded, not done):** making these lanes real requires (a) adding
`execution` to conftest conditional-unignore, (b) adding the dirs to `testpaths` or passing
explicit path args in `certify.py TARGETS`, and (c) adding matching CI workflows. Until then
the repo cannot collect the B3/B4/B5 surfaces at all.

---

## G. Recorded findings (section 9 — NOT fixed)

| ID | Evidence | Affected surface | Severity | Lane | Blocker |
|----|----------|-----------------|----------|------|---------|
| TU-001 | conftest unconditionally ignores ~56 dirs; only portal/predictive/integrations toggleable | all non-portal modules | blocker | D | yes |
| TU-002 | testpaths restricts traversal; un-ignoring a glob alone insufficient (certify works for portal only because portal/tests in testpaths) | all lanes | blocker | D | yes |
| TU-003 | mission_wiring/ & agent_runtime/ neither in testpaths nor in ignore glob → invisible to all collection | B5, B4/C | blocker | C | yes |
| TU-004 | pytest.ini ⊃ pyproject; `-m 'not experimental'` excludes experimental-marked tests from default; need to confirm RC tests so marked | A/B/C | medium | D | no |
| TU-005 | sigma-gate `--cov=.` over default-only execution → coverage metric misleading as a release gate | D | medium | D | no |
| TU-006 | `predictive`/`integrations` lanes referenced in conftest but absent from certify.py TARGETS (dead lanes); integrations (10/227) & predictive (5/58) never collected | C | high | C/D | yes |
| TU-007 | backend/stripe-payments, phase16/stripe_billing, phase18/stripe_webhooks payment tests exist but none collected; only portal/tests/test_billing.py | C (B3) | blocker | C | yes |
| TU-008 | mission_wiring durable-engine tests (crash/restart/reconciliation/approval) exist but uncollected; only portal/tests mission_control_* collected | C (B5) | blocker | C | yes |
| TU-009 | tenant negative-matrix tests exist in portal/tests but no dedicated CI job; ride portal-ci path-trigger only | B (B2) | medium-high | B | no |
| TU-010 | pytest absent; optional extras + Postgres/Redis unavailable → RUNTIME_COLLECTION_VERIFIED impossible here | all | blocker (runtime) | D | yes |
| TU-011 | advisory_service & affiliate-engine have 0 test files | — | low/REVIEW | — | no |
| TU-012 | 4830c25 (Telegram) not in this clone; keep as separate lineage, do not merge into baseline silently | provenance | info | — | no |

---

## H. Terminal state (section 10)

```
G0_TEST_UNIVERSE            = PASS        (universe fully definable from repo evidence; runtime not required for PASS)
RUNTIME_COLLECTION_VERIFIED = FALSE       (pytest absent; no collection executed)

BASE_SHA_VERIFIED           = TRUE        (HEAD=main=origin/main=c0c29a0e; 660b7314 34-commit ancestor; 4830c25 absent)
TEST_CONFIG_MAPPED          = TRUE
RELEASE_MODULES_MAPPED      = TRUE
TEST_LANES_DEFINED          = TRUE        (draft four-lane contract; not implemented)
COLLECTION_MANIFEST_CREATED= TRUE        (this file)
DEFAULT_SUITE_RELEASE_SUFFICIENT = FALSE  (default lane excludes all non-portal/non-tests surfaces)

SOURCE_MUTATION   = NONE
CONFIG_MUTATION   = NONE
COMMIT_CREATED    = FALSE
PUSH_PERFORMED    = FALSE
REALITY_GATE      = CLOSED
```

**Recommended next step (separate authorization):** implement the four-lane contract
(extend `certify.py TARGETS` + conftest un-ignore + `testpaths`/explicit paths + CI), then
provision the environment (deps + Postgres + Redis) and actually run each lane against
`c0c29a0e`. Do NOT advance to G1 remediation until `RUNTIME_COLLECTION_VERIFIED = TRUE`.
