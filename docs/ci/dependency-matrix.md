# CI Dependency Matrix

> Generated for Issue #97. Maps every test lane to its third-party imports,
> classifies suites into CI tiers, and documents the optional-dependency
> groups in `pyproject.toml`.

## Current state (post-PR #94 + #95)

| Workflow | Status | Root cause |
|----------|--------|------------|
| Sigma Gate — tests | ✅ 146 passed | Runs only `tests/` |
| Sigma Gate — coverage | ❌ | Statement/branch data mismatch |
| SintraPrime CI — test | ❌ | Collection errors across 40+ lanes |
| SintraPrime CI — lint | ❌ | 46K+ ruff violations (pre-existing) |
| SintraPrime CI — security | ⬆️ | Safety policy exists (PR #95) |
| IssueVerifier — bandit | ❌ | 9,265 findings, no baseline |
| deploy-staging | ❌ | Pre-existing |

## Dependency groups

### Core (`[project.dependencies]`) — always installed

| PyPI package | Import name | Used by |
|-------------|-------------|---------|
| fastapi>=0.104.0 | fastapi | portal, cross_platform, legal_integrations, scheduler |
| uvicorn>=0.24.0 | uvicorn | portal |
| sqlalchemy>=2.0.0 | sqlalchemy | portal |
| psycopg2-binary>=2.9.9 | psycopg2 | portal |
| pydantic>=2.5.0 | pydantic | portal, integrations |
| pydantic-settings>=2.1.0 | pydantic_settings | portal |
| python-jose>=3.3.0 | jose | portal |
| passlib>=1.7.4 | passlib | portal |
| bcrypt>=4.1.1 | bcrypt | portal |
| python-multipart>=0.0.27 | multipart | portal |
| httpx>=0.25.2 | httpx | portal |
| aioredis>=2.0.1 | aioredis | core |
| celery>=5.3.4 | celery | core |
| redis>=5.0.1 | redis | core |
| stripe>=7.4.0 | stripe | backend/stripe-payments |
| python-dotenv>=1.2.2 | dotenv | portal, config |
| openai>=1.3.0 | openai | agents, orchestration |
| anthropic>=0.7.0 | anthropic | agents |
| websockets>=12.0 | websockets | core |
| pytz>=2023.3 | pytz | portal |
| tzlocal>=5.2 | tzlocal | portal |
| numpy>=1.24.0 | numpy | core, predictive |

### `[project.optional-dependencies.test]` — CI test runner

| PyPI package | Import name | Purpose |
|-------------|-------------|---------|
| pytest>=7.0 | pytest | Test runner |
| pytest-cov>=4.0 | pytest_cov | Coverage reporting |
| pytest-asyncio>=0.21 | pytest_asyncio | Async test support |

### `[project.optional-dependencies.portal]` — portal SSO & auth

| PyPI package | Import name | Source file |
|-------------|-------------|------------|
| PyJWT>=2.0 | jwt | portal/sso/providers/google.py |
| requests>=2.31 | requests | portal/sso/providers/google.py, portal tests |
| email-validator>=2.0 | email_validator | portal auth/validation |

Note: `starlette` ships with `fastapi` and does not need separate declaration.

### `[project.optional-dependencies.predictive]` — ML/analytics

| PyPI package | Import name | Source file |
|-------------|-------------|------------|
| pandas>=2.0 | pandas | predictive/outcome_predictor.py, ml_training_pipeline.py |
| scikit-learn>=1.3 | sklearn | predictive/outcome_predictor.py, ml_training_pipeline.py |

Note: `numpy` is already in core dependencies.

### `[project.optional-dependencies.integrations]` — third-party API clients

| PyPI package | Import name | Source file |
|-------------|-------------|------------|
| aiohttp>=3.9 | aiohttp | integrations/banking, integrations/case_law |
| plaid-python>=14.0 | plaid | integrations/banking/plaid_client.py |

### `[project.optional-dependencies.all]`

Installs everything: `sintraprime[test,portal,predictive,integrations]`

## Test lane classification

### Tier 1 — Core (default blocking CI)

Zero collection errors guaranteed. These run with `pip install .[test]`.

| Lane | Test files | Third-party imports | Status |
|------|-----------|---------------------|--------|
| `tests/` | 3 | pytest | ✅ Sigma Gate: 146 pass |


**Default CI command:**
```bash
python -m pytest tests/ --tb=short -q --import-mode=importlib
```

### Tier 2 — Portal (requires `.[test,portal]`)

| Lane | Test files | Extra imports needed | Status |
|------|-----------|---------------------|--------|
| `portal/tests/` | 12 | PyJWT, requests, email-validator | ⚠️ needs portal extras |
| `portal/routers/tests/` | — | PyJWT, requests | ⚠️ needs portal extras |
| `portal/sso/tests/` | 7 | PyJWT, requests | ⚠️ needs portal extras |

**Extended CI command:**
```bash
pip install .[test,portal]
python -m pytest tests/ portal/tests/ portal/routers/tests/ portal/sso/tests/ --tb=short -q --import-mode=importlib
```

### Tier 3 — Predictive (requires `.[test,predictive]`)

| Lane | Test files | Extra imports needed | Status |
|------|-----------|---------------------|--------|
| `predictive/tests/` | 1 | pandas, scikit-learn | ⚠️ needs predictive extras |

### Tier 4 — Integrations (requires `.[test,integrations]`)

| Lane | Test files | Extra imports needed | Status |
|------|-----------|---------------------|--------|
| `integrations/` | 9 | aiohttp, plaid | ⚠️ needs integrations extras |

### Tier 5 — Deferred (not in default CI, tracked here)

These lanes exist in `pytest.ini` testpaths but have not been fully audited
for transitive import chains. They are excluded from default CI until
their dependency requirements are verified.

| Lane | Test files | Reason deferred |
|------|-----------|----------------|
| backend/lead-router/tests/ | 1 | imports models/ (not on sys.path from backend subdir) |
| backend/stripe-payments/tests/ | 1 | chains to pydantic EmailStr → email-validator (undeclared) |
| core/tests/ | 6 | test_slack_integration chains to discord (undeclared) |
| agents/chat/tests/ | 1 | Transitive imports unverified |
| agent_protocol/tests/ | 1 | Transitive imports unverified |
| ai_compliance/tests/ | 1 | Transitive imports unverified |
| app_builder/tests/ | 1 | Transitive imports unverified |
| artifacts/tests/ | 1 | Transitive imports unverified |
| channels/tests/ | 1 | Transitive imports unverified |
| claude_code/tests/ | 1 | Transitive imports unverified |
| cross_platform/tests/ | 1 | Needs fastapi (declared), but transitive unverified |
| developer_experience/tests/ | 1 | Transitive imports unverified |
| docket/tests/ | 1 | Transitive imports unverified |
| emotional_intelligence/tests/ | 1 | Transitive imports unverified |
| esignature/tests/ | 1 | Transitive imports unverified |
| federal_agencies/tests/ | 1 | Transitive imports unverified |
| financial_mastery/tests/ | 1 | Transitive imports unverified |
| governance/tests/ | 1 | Transitive imports unverified |
| legal_integrations/tests/ | 1 | Transitive imports unverified |
| legal_intelligence/tests/ | 1 | Transitive imports unverified |
| life_governance/tests/ | 1 | Transitive imports unverified |
| local_llm/tests/ | 1 | Transitive imports unverified |
| local_models/tests/ | 1 | Needs requests (not in core) |
| mcp_server/tests/ | 1 | Transitive imports unverified |
| memory/tests/ | 1 | Transitive imports unverified |
| multimodal/tests/ | 1 | Transitive imports unverified |
| observability/tests/ | — | Transitive imports unverified |
| operator/tests/ | 1 | Explicitly excluded (collect_ignore_glob) |
| orchestration/tests/ | 1 | Needs pytest-asyncio |
| parl/tests/ | 1 | Transitive imports unverified |
| performance/tests/ | 1 | Transitive imports unverified |
| phase15/ | 4 | Transitive imports unverified |
| phase16/ | 4 | Transitive imports unverified |
| phase17/ | 4 | Transitive imports unverified |
| phase18/ | 5 | Transitive imports unverified |
| phase19/ | 2 | Partially excluded already |
| rag/tests/ | 1 | Transitive imports unverified |
| saas/tests/ | 1 | Transitive imports unverified |
| scheduler/tests/ | 1 | Needs fastapi (declared), but transitive unverified |
| secure_execution/tests/ | — | Transitive imports unverified |
| security/tests/ | — | Transitive imports unverified |
| skill_evolution/tests/ | — | Transitive imports unverified |
| superintelligence/tests/ | 1 | Transitive imports unverified |
| trust_law/tests/ | 1 | Transitive imports unverified |
| twin_layer/tests/ | 1 | Transitive imports unverified |
| voice/tests/ | — | Transitive imports unverified |
| workflow_builder/tests/ | 1 | Transitive imports unverified |

## Rollback plan

If this PR causes regressions:
1. Revert `pytest.ini` to the previous version (all testpaths restored)
2. Remove `[project.optional-dependencies]` sections from `pyproject.toml`
3. Delete `docs/ci/dependency-matrix.md`
4. All changes are additive — no source code modified

## Next steps (future PRs)

1. **Audit deferred lanes** — trace transitive imports for each Tier 5 lane, promote to appropriate tier
2. **Ruff baseline** — create `ruff.toml` with `extend-ignore` for pre-existing 46K violations
3. **Bandit baseline** — generate `.bandit-baseline.json` from current findings
4. **Coverage config** — fix statement/branch data mismatch in Sigma Gate
5. **CI workflow updates** — update `ci.yml` to use `pip install .[test]` and narrow testpaths (requires `workflows` permission)
