# Lane A — DEPLOYMENT-READINESS REVIEW (read-only; NO migration applied, NO deploy)

**Date:** 2026-09-09 · **Read-only throughout** — no config writes, no migrations applied, no connection attempts against any production system, no secret disclosure.

```
REPOSITORY_CURRENT_MAIN           = 79deec881544a80105e0b45663740ad0f0fccf17 (Wave-2 + Wave-3)
DEPLOYMENT_CANDIDATE_UNDER_REVIEW = 32b5f4a97539146621cf960a0675dda46226b033 (Wave-2 published candidate)
ENVIRONMENT DRIFT                 = SEE GATE 16 (main has moved past the candidate — classified, not auto-authorized)
```

## Deployment matrix

| # | Gate | Finding |
|---|---|---|
| 1 | **Deployment target identified** | `deploy-production.yml` = workflow_dispatch targeting aws/azure/gcp — **all three jobs are `# TBD` placeholders** (echo only). `deploy-staging.yml` is real (48 lines, no TBD). **No concrete production environment is actually defined.** |
| 2 | **Currently deployed SHA/version** | `UNKNOWN` — no deployment record, no running-instance registry, no version endpoint tying a live instance to a SHA. |
| 3 | **Deployment mechanism** | Staging workflow exists (actions/checkout → app start); production workflow is a placeholder. Docker build verified in CI (`docker-build.yml`), Dockerfile usable as packaging. |
| 4 | **Rollback reference** | Previous-version image/SHA checkpoint: **none recorded** (nothing has ever been deployed — first-deploy case). Rollback = redeploy prior SHA once a history exists. |
| 5 | **DB reachable (read-only verification)** | **NOT VERIFIED** — no production DATABASE_URL/credentials in this session; no live connection attempted (per read-only + secret rules). Reachability remains unproven. |
| 6 | **Migration state (exact applied/pending chain)** | `UNKNOWN` for the real environment — no applied-migrations record exists to inspect. Repository chain: 17 SQL files in `portal/migrations/` (see gate 7). |
| 7 | **11-file canonical migration chain** | Wave-2 certified `postgresql_bootstrap.py` applies the chain idempotently (11 files / 35 tables proven in Wave-2 certification, receipt era `cert_20260908T063325Z`). Repository chain reconciled: `portal_schema.sql` + `runtime_schema_baseline` + `runtime_schema_integrity_2026_07_27` + 10 `add_*` domain migrations + `align_orchestration_identity_fk_types` = the canonical set; bootstrap is idempotent so re-application is safe by design. |
| 8 | **Voice-ledger migration** | `add_voice_command_ledger.sql` present in the canonical chain → **applied with the chain** (idempotent bootstrap); no separate pending state. |
| 9 | **DELEGATION_TTL_HOURS** | PRESENT: `portal/config.py` `DELEGATION_TTL_HOURS: int = 24` with a fail-closed validator (`>= 1`; zero/negative refused — immortal delegation prevented). Value classification: secure default 24h; env-overridable; no secret material. |
| 10 | **Required secrets (names/presence only)** | Config is pydantic-settings (`portal/config.py`); production gates exist (portal AGENTS.md: production must fail closed on default secrets/insecure MinIO/placeholder keys). Secret VALUES never stored/committed; presence of production values in the target env = **UNVERIFIED** (no env access). |
| 11 | **Startup prerequisites** | App entry `portal/main.py` (FastAPI lifespan), deps PostgreSQL(async)/Redis/MinIO; Python 3.13 venv + `pillow` now in manifests (W2-R1). Runtime prerequisites documented; live startup not executed in this review. |
| 12 | **Health endpoint/process** | `portal/routers/system_health.py` — multi-component health with healthy/degraded states (DB tables, kernel, channels, jobs). Read-only verification of a live instance: NOT POSSIBLE (nothing deployed). |
| 13 | **Post-deploy smoke commands (documented)** | `smoke.yml` CI lane (green on main); runtime smoke = `/system/health` endpoints + Wave-2 canonical certification lanes against the deployed instance. |
| 14 | **Rollback commands (documented)** | Certified per-increment rollback docs exist (e.g. `docs/certification/auth-tenant-rbac/increment-1/rollback.md`); DB DOWN path: `runtime_schema_integrity_2026_07_27_down.sql` explicit + inline DOWN comments in 13 of 17 migration files. |
| 15 | **Destructive action required** | **NO** for first deploy of an empty/fresh environment (idempotent bootstrap). `--reset-public-schema` EXISTS in the bootstrap tool and is destructive — must never be used against a populated env. |
| 16 | **Environment drift** | **DRIFT CLASSIFIED**: main has advanced to `79deec88` (Wave-3 merged) while the candidate under review is `32b5f4a9`. Recorded as drift, NOT as authorization to change the candidate. Any deploy decision should re-confirm which SHA to ship. |
| 17 | **Migration reversibility (the missed area)** | `DATABASE_ROLLBACK_READY = PARTIAL`: 1 explicit `_down.sql` + inline DOWN comments in 13/17 UP files, but no automated down-migration runner and no tested end-to-end down-chain. Application rollback is well-defined; schema rollback is manual SQL with untested completeness. |

## Conclusion

```
APPLICATION_ROLLBACK_READY = YES (redeploy prior SHA; per-increment rollback docs; code is versioned in git)
DATABASE_ROLLBACK_READY    = PARTIAL (DOWN convention present in 14/17 files; no automated down-runner; down-chain untested end-to-end)
CONFIG_ROLLBACK_READY      = YES (pydantic-settings, fail-closed production gates, no secret values in repo)
OVERALL_DEPLOYMENT_READY   = NOT_READY
```

### Blocking findings (all repairable, none architectural)

1. **Production deploy workflow is a placeholder** (`# TBD` in all three cloud jobs) — the actual deployment mechanism does not exist yet.
2. **No deployment-target definition** — no host/service/environment is specified anywhere; nothing is currently deployed; no deployed-version record exists.
3. **DB reachability/migration-state unverified** — requires target-environment access with credentials handled outside this review (presence-only evidence).
4. **Schema rollback chain untested** — down-migrations exist as convention, not as an executed, verified path.
5. **Drift** — candidate `32b5f4a9` vs current main `79deec88` (Wave-3 now merged); deploy decision must name its SHA explicitly.

### Readiness path (for the future deployment authorization)

1. Author a real `deploy-production.yml` (target env, image packaging via the verified Dockerfile, migration step = idempotent bootstrap, health-gate = `/system/health`).
2. Provision/define the target environment + secrets by name (values via the platform's secret store).
3. Run the idempotent bootstrap against the target DB (read-only pre-check first: applied-chain query).
4. Record pre-deploy SHA checkpoint → deploy → smoke (`/system/health`) → record deployed SHA (making gate 2 answerable next time).
5. Test the down-chain once on a disposable DB to close `DATABASE_ROLLBACK_READY`.
