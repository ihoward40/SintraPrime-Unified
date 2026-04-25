# Changelog

This project treats releases as evidence-grade freezes. See `docs/CONSTITUTION.v1.md` for the invariants.

## Unreleased (v1.1)

Allowed without constitutional amendment (if `npm run smoke:vectors` stays green):
- New read-only adapters
- New deterministic redacted artifacts
- UI improvements (operator console, timeline, explain)
- Stronger redaction rules
- Additional smoke vectors (never fewer)

Requires a minor-version constitutional amendment process:
- Receipt schema changes
- Hashing / verification semantics changes
- Approval persistence semantics changes
- Policy code / denial semantics changes

## Phase 3 Complete: Docker Deployment Baseline (2026-02-17)

Phase 3 achieves full containerization of the SintraPrime stack with Docker Compose orchestration.

**Achievements:**
- ✅ 5-service containerized architecture deployed (MySQL, Airlock, Brain, FastAPI, WebApp)
- ✅ 100% first-attempt deployment success rate
- ✅ Zero manual intervention required
- ✅ All health checks passing on first attempt
- ✅ Baseline resource metrics captured
- ✅ Production-ready configuration established

**New Documentation:**
- `DOCKER_DEPLOYMENT.md` - Comprehensive deployment guide with architecture overview, quick start, health checks, port mappings, environment configuration, and troubleshooting
- `docs/DOCKER_BEST_PRACTICES.md` - Container management, health checks, resource limits, logging, backup/restore, and rollback procedures
- `docs/snapshots/phase3-baseline/` - Baseline deployment snapshot with metrics and configuration
- Docker operations section added to `OPERATOR_RUNBOOK.md`
- Docker deployment quick start added to `README.md`

**Infrastructure:**
- Docker Compose orchestration for 5 services
- Comprehensive health check endpoints for all services
- Port mappings: MySQL (3306), Airlock (3000), Brain (8011), FastAPI (8000), WebApp (3002)
- Resource limits and reservations configured for all containers
- `.env.docker` environment configuration template

**Baseline Metrics:**
- Total deployment time: 30 seconds (first attempt)
- Resource allocation: 7.5 CPU cores / 6.75 GB memory (limits)
- Idle usage: ~0.5 CPU cores / ~2.8 GB memory
- All services healthy with dependency checks passing

## v1.0.0 — freeze/v1.0.0 (2026-01-11)

- Verifier contract hardened (zip-or-dir, strict mode, JSON-last-line, stable exit codes, optional expect compare).
- Constitution v1 published with explicit determinism invariants (including “no global tail inference”).
- Tier freeze checklist published.
- Deterministic audit execution bundles (Tier-15.1) with bundle-local verifier + canonical verifier script.
- Operator UI improvements for reading runs, timeline, and verify command copy.
