# Rollback Plan

If this certification increment must be reverted:

## Authoritative rollback method (post-merge)

PR #215 was merged via merge commit `a0d9900bc40e01941acfe1f49f6bacad7189aeb7`. To revert the entire increment:

```
git revert -m 1 a0d9900bc40e01941acfe1f49f6bacad7189aeb7
```

The `-m 1` flag selects parent 1 (the main branch mainline) as the reference for the revert. Without it, `git revert` on a merge commit will error with "is a merge but no -m option was given."

## Component-commit alternative

If a granular rollback is required, revert the two increment commits in reverse order:

```
git revert cee14531513cd5ccf7316118867b0cbafd953c42
git revert f4613e9e4b4ec715d9447d4efa34da44a10c1f07
```

The evidence commit must be reverted before the implementation commit. Reverting in the wrong order may leave evidence files describing controls that no longer exist.

## What is reverted — 20 files total

PR #215 changed exactly 20 files: 8 implementation/configuration files and 12 certification-evidence files.

### 8 implementation/configuration files

1. `portal/auth/correlation.py` (new file)
2. `portal/auth/audit_envelope.py` (new file)
3. `portal/auth/websocket_auth.py` (new file)
4. `portal/admin/dashboard.py` (modified: auth/audit controls)
5. `portal/main.py` (modified: dashboard router mount)
6. `portal/tests/test_audit_correlation_non_http_certification.py` (new file)
7. `.github/workflows/ci.yml` (modified: new CI job)
8. `pyproject.toml` (modified: B008 ignore for portal/admin)

### 12 certification-evidence files

All under `docs/certification/audit-correlation-non-http/increment-1/`:

1. `certification-report.md`
2. `correlation-authority.json`
3. `audit-event-schema.json`
4. `websocket-authorization-matrix.json`
5. `non-http-entrypoint-matrix.json`
6. `background-service-identity.json`
7. `webhook-security.json`
8. `cli-admin-boundaries.json`
9. `negative-test-results.json`
10. `known-limitations.json`
11. `decision-log.json`
12. `rollback.md`

## Warnings against partial manual rollback

Do not partially revert this increment. A partial rollback could leave:

- the admin WebSocket router mounted in `portal/main.py` without its authentication/authorization/correlation support modules (`portal/auth/websocket_auth.py`, `portal/auth/correlation.py`, `portal/auth/audit_envelope.py`);
- a CI job in `.github/workflows/ci.yml` referencing a certification test file that no longer exists;
- a `pyproject.toml` B008 exception for `portal/admin/**` without the associated FastAPI Depends code;
- certification evidence files describing security controls that have been removed from the runtime;
- audit/correlation modules partially installed with missing dependencies.

Always use `git revert` on the merge commit or both component commits in reverse order.

## Correction notice

The former version of this document grouped the 12-file evidence directory as a single line item and did not state the total file count explicitly. The PR #215 body referenced "19 files" which was inaccurate. The former rollback commands used placeholders (`git revert <evidence-commit>` / `git revert <implementation-commit>`) rather than concrete commit SHAs, making them non-actionable until filled in. The corrected version replaces placeholders with real commit SHAs, adds the `-m 1` flag for merge-commit reversion, and explicitly enumerates all 20 files. The rollback approach was always conceptually complete (revert the commits), but the former document did not provide actionable commands or an accurate file inventory. This was corrected in the post-merge governance wrap.