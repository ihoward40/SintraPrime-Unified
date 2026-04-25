# Operator Runbook (v1)

This runbook is the practical operating procedure for running the system without breaking the constitutional invariants.

## Roles (O1 / O2 / O3)

### O1 — Viewer
- May run the Operator UI (read-only views of `runs/**`).
- May verify exported audit bundles.
- Must not run live commands.
- Must not possess secrets.

### O2 — Read Operator
- May run **read-only live adapters** (e.g. Notion live read).
- May export audit bundles for executions.
- Has a scoped Notion token.
- Must not approve writes.

### O3 — Approver (explicitly delegated)
- May run `/approve <execution_id>`.
- Must be trained on policy denial vs approval-required behavior.
- Must maintain an audit trail of approvals.

## Golden rules (never break)

- Do not edit artifacts in `runs/**`.
- If something fails: re-run with a clean terminal environment; do not hot-patch evidence.
- Any external write must pass the approval gate; no bypasses.
- Every execution must produce a receipt and at least one artifact (“no silent work”).
- Treat `docs/CONSTITUTION.v1.md` as supreme.

## Safe terminal hygiene

Use a fresh terminal for live runs. Do not carry CI/smoke variables into live sessions.

For live runs, do **not** set:
- `SMOKE_VECTORS_USE_REMOTE`
- smoke-runner vars (anything you only use for smoke harness)

## Local personal/WIP files

Put personal notes, scratch output, and other WIP files under `local/` at the repo root.

`local/` is intentionally ignored by git, so it won’t show up in `git status` and can’t be accidentally committed.

## Live Notion read (O2)

### Required env
Set only what you need (never commit these):

```powershell
$env:WEBHOOK_SECRET="..."                 # if validator/planner require a secret
$env:NOTION_TOKEN="secret_..."            # real Notion integration token (scoped)
$env:NOTION_API_BASE="https://api.notion.com"
$env:NOTION_API_VERSION="2022-06-28"
$env:NOTION_REDACT_KEYS="title,name,email,phone,address"
$env:AUTONOMY_MODE="OFF"
```

### Run commands
Database snapshot:

```bash
node --import tsx ./src/cli/run-command.ts "/notion live db <DATABASE_ID>"
```

Single page snapshot:

```bash
node --import tsx ./src/cli/run-command.ts "/notion live page <PAGE_ID>"
```

### If the command returns `ApprovalRequired`
Stop. You are not in a read-only posture. Do not proceed without O3 review.

## Export audit bundle (O2)

After you have an `execution_id` from the receipt/output:

```bash
node --import tsx ./src/cli/run-command.ts "/audit export <execution_id>"
```

## Court packet (O2)

Generate a clerk-ready folder packet from the execution:

```bash
node --import tsx ./scripts/make-court-packet.ts <execution_id> --run-type <db|page> --target-id <NOTION_ID>
```

This copies governance docs, receipt + hash, audit bundle zip + verify.js, and the redacted artifacts for that execution.

## Verifying an audit bundle (O1+)

If you have `audit_bundle_<execution_id>.zip`:
- Unzip it.
- In the unzipped folder, run:

```bash
node verify.js
```

A passing verification exits 0.

## Docker Operations (O2+)

### Starting and Stopping Services

**Start all services:**
```bash
docker-compose up -d
```

**Stop all services (preserves data):**
```bash
docker-compose down
```

**Restart specific service:**
```bash
docker-compose restart brain
docker-compose restart airlock
```

### Health Verification

**Check all container status:**
```bash
docker-compose ps
```

**Verify health endpoints:**
```bash
curl http://localhost:3000/health  # Airlock
curl http://localhost:8011/health  # Brain
curl http://localhost:8000/health  # FastAPI
curl http://localhost:3002/health  # WebApp
```

### Viewing Logs

**View all logs:**
```bash
docker-compose logs
```

**Follow specific service logs (live):**
```bash
docker-compose logs -f brain
docker-compose logs -f airlock
```

**View last 100 lines:**
```bash
docker-compose logs --tail=100 brain
```

### Database Operations

**Access MySQL shell:**
```bash
docker-compose exec mysql mysql -u root -p
```

**Backup database:**
```bash
docker-compose exec mysql mysqldump -u root -p sintraprime > backup.sql
```

**Restore database:**
```bash
docker-compose exec -T mysql mysql -u root -p sintraprime < backup.sql
```

### Resource Monitoring

**Real-time resource usage:**
```bash
docker stats
```

**Check disk usage:**
```bash
docker system df
```

### Troubleshooting

**Container won't start - check logs:**
```bash
docker-compose logs <service-name>
```

**Service unhealthy - restart:**
```bash
docker-compose restart <service-name>
```

**Database connection issues - verify MySQL:**
```bash
docker-compose exec mysql mysqladmin ping
```

**Full reset (⚠️ WARNING: Deletes all data):**
```bash
docker-compose down -v
docker-compose up -d
```

### Related Documentation

For comprehensive Docker deployment documentation, see:
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Full deployment guide
- [docs/DOCKER_BEST_PRACTICES.md](docs/DOCKER_BEST_PRACTICES.md) - Best practices
- [docs/snapshots/phase3-baseline/](docs/snapshots/phase3-baseline/) - Baseline metrics
