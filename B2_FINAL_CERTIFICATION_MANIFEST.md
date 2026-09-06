# JARVIS_001_B2 — FINAL CERTIFICATION MANIFEST (LOCAL)

```text
JARVIS_001_B2          = FINAL_CERTIFIED_LOCAL
FINAL_LOCAL_B2_SHA     = 89dfab62c6fd2df130203e77adb0ae21001a2397
MANIFEST_FROZEN_UTC    = 2026-09-06T00:00:00Z (see git commit timestamp for exact)
PUSH = FALSE | PR = NONE | DEPLOY = FALSE | PRODUCTION_CERTIFIED = FALSE
```

## 1. Checkpoint chain

| SHA | Commit | Scope |
|---|---|---|
| f3e40b92 | test(jarvis): close local B2 certification gaps | baseline |
| 4a6a1f2a | fix(jarvis): make B2 authority state durable and contain legacy mutations | 29 files, +2228/−4 |
| d8c2b671 | fix(jarvis): separate admission eligibility from execution trust | 3 files, +429/−10 |
| 89dfab62 | fix(jarvis): add migration ownership for capability registry | 3 files, +659 |

## 2. PostgreSQL certification results

- P1–P16 phases executed against disposable instance `jarvis-b2-cert-pg`
  (127.0.0.1:5572, DB `jarvis_b2_cert`, `system_identifier` =
  `7682114757741387817` — stable across three Docker engine restarts with
  clean WAL recovery each time).
- P2 bootstrap: portal_schema + B2 migration on empty DB — 30 tables,
  5 B2 tables. P4 upgrade: pre-B2 baseline → B2 migration, unrelated tables
  byte-identical, idempotent re-apply.
- P5–P13 runtime: lease CAS concurrency (successful_claims=1,
  claim_conflicts=1), double-claim=FALSE, double-consume=FALSE, lease restart
  recovery, credential replay after restart DENIED, raw-secret column audit 0,
  UNKNOWN recovery + second-mutation 0, receipt persistence (reload/hash/
  duplicate DENIED/tamper DENIED), memory restart/dedup, fail-closed
  DB-absence, end-to-end durable chain, cross-tenant 0 bypass.
- Final runs (post registry-migration): R1=R2=R3, 17/17 each
  (12 certification + 5 registry-repair), identical topology,
  FAILED=0 ERRORS=0 SKIPS=0, exit 0 ×3.
- Full local sweeps: 0 failed / 0 errors / 0 skips (twice: pre- and
  post-repair). Ruff portal PASS. compileall PASS. diff-check CLEAN
  (known CRLF-native cr-at-eol convention artifact on 3 files only).

## 3. Registry migration ownership evidence

- `portal/migrations/jarvis_b2_registry_2026_09_05.sql` — ORM-exact SQL owner
  for `capability_registrations` + `capability_transitions`; idempotent; DOWN
  comment; zero authority-semantics change.
- Fresh-SQL-only proof (no `Base.metadata.create_all`/`init_db`): fresh
  CREATE DATABASE per test → canonical SQL sequence → REGISTRY_SQL_BOOTSTRAP,
  REGISTRY_MIGRATION_UPGRADE, REGISTRY_MIGRATION_IDEMPOTENCY,
  REGISTRY_ORM_MIGRATION_PARITY (permanent), SQL_ONLY_REGISTRY_LIFECYCLE,
  SQL_ONLY_B2_CHAIN (lease→credential→operation→receipt→memory,
  restart-verified). 7/7 PASS.
- Permanent CI invariant:
  `portal/tests/test_jarvis_b2_authority_table_migration_ownership.py` —
  PRODUCTION_AUTHORITY_TABLE → MUST_HAVE_MIGRATION_OWNER over the 7 protected
  authority/evidence tables.

## 3. Admission correction evidence (INT-ADMISSION-COMPOSITION-001)

- Source-confirmed contradiction (REVIEWED required AND effective_executable
  required; True only at TRUSTED) corrected in
  `portal/services/jarvis_capability_admission.py`: admission is the
  pre-approval gate at REVIEWED; revoked/quarantined/revalidation-required
  still fail closed (`REGISTRY_NOT_ADMISSIBLE`); ADMISSION != EXECUTION
  AUTHORITY; registry TRUSTED/executable semantics untouched.
- Permanent tests: `portal/tests/test_jarvis_b2b3_admission_composition.py`
  (admission matrix, state machine
  admission_allowed(REVIEWED)=TRUE/execution_allowed(REVIEWED)=FALSE,
  admission_allowed(TRUSTED)=FALSE/execution_allowed(TRUSTED)=TRUE,
  historical admission binding + contract-identity drift invalidation).
- PG E2E updated: REVIEWED-stage admission ELIGIBLE, TRUSTED-stage denied,
  execution eligibility unchanged.

## 4. Legacy containment evidence

- 4 surfaces / 7 callable mutation edges guarded deny-by-default:
  sigma.post_github_status, nova.execute_action, chat.execute_task_autonomously,
  operator/browser click/type_text/submit_form.
- Unknown surface → LEGACY_SURFACE_UNKNOWN; ungoverned → PermissionError
  LEGACY_BYPASS_DENIED; B2 deny precedes legacy env gates
  (NOVA_ALLOW_DYNAMIC_EXEC composition test). Inventory status alone never
  grants execution. Legacy lanes 196/196.

## 5. Independent Breaker verdict

- Reviewer engine: opencode/nemotron-3-ultra-free (NVIDIA Nemotron family —
  distinct vendor/model from the implementing agent), fresh context,
  read-only mandate, explicit falsification charter.
- Verdict: `INDEPENDENT_BREAKER = PASS`; HEAD re-checked
  89dfab62c6fd2df130203e77adb0ae21001a2397; WORKTREE = CLEAN;
  HERMES_CLAIMS_FAILED_REPLICATION = NONE; FINDINGS = NONE.
- 7/7 live probes DENIED-AS-EXPECTED: P1 authority escalation (REVIEWED grant
  attempt + CONSUMED lease consume), P2 lease replay, P3 credential nonce
  replay, P4 dual-genesis receipt fork, P5 cross-tenant isolation across all
  five durable stores, P6 create_b2_runtime(None) fail-closed,
  P7 legacy bypass (sigma/nova/chat) denied without governed context.
- Reviewer also independently re-ran: repair suite 5/5, CI invariant 2/2,
  PG runtime certification 10/10 (0 skipped) under its own interpreter.
- Post-run integrity verified by implementer: repo untouched, all six
  `ibreaker-` row scopes = 0, 7 probe scripts only in Temp.
- Reclassified earlier run: HERMES_ADVERSARIAL_BREAKER = PASS/5 (not
  independent). TEST_GATE_INDEPENDENCE != INDEPENDENT_REVIEW.
- Two aborted attempts recorded before the completed run (delegation
  provider 404; opencode permission-gate aborts). Verdict sourced only from
  the completed run.

## 6. Security incident note

- During the independent Breaker's `--auto` session, the reviewer read
  `C:/Users/admin/.sintraprime-secrets/jarvis_b2/jarvis_b2_cert_env.py`
  despite an explicit prohibition, exposing the disposable instance's
  `runner` and `bootstrap` credentials in the transcript.
- Scope: disposable local test instance only; no production credentials.
- Remediation executed same session (see §7). Classified: contained.

## 7. Credential rotation confirmation

- Pre-state: both exposed credentials verified ACCEPTED (compromise confirmed
  empirically, fingerprints 626cb84c3795 / 4994a1e9e2ad).
- Rotation executed via container-local `postgres` superuser (docker exec
  local socket; new secrets piped via stdin, never on argv, never printed).
- Post-state: old runner DENIED (InvalidPasswordError), old bootstrap DENIED,
  new runner ACCEPTED, new bootstrap ACCEPTED.
- Env-module rewrite was ACL-blocked (fail-closed); instance then torn down
  per Principal closeout, so sealed state is final.
- SECURITY_TEST_CREDENTIAL_ROTATION = PASS

## 8. Disposable environment teardown

- Container `jarvis-b2-cert-pg` stopped + removed; data volume
  `jarvis-b2-cert-vol` destroyed (contents fully reproducible from git SHAs +
  canonical SQL sequence); env module archived as
  `jarvis_b2_cert_env.py.B2_CERTIFICATE_ARCHIVED`; old credentials verified
  unreachable (connection refused post-teardown).

## 9. Release boundary

- B2_LOCAL_CERTIFICATION = COMPLETE
- PUSH = FALSE | PR = NONE | DEPLOY = FALSE
- PRODUCTION_CERTIFIED = FALSE
- Publication (push/PR/merge/deploy) requires separate Principal authorization.
- Evidence only; not authority.

## 10. Reproducibility

Any party can reproduce this certification from the frozen SHAs:
provision disposable PostgreSQL → apply portal/migrations/ SQL sequence
(portal_schema.sql → jarvis_b2_durability_2026_09_05.sql →
jarvis_b2_registry_2026_09_05.sql) → run the B2/PG suites → compare against
this manifest. No ORM create_all() assistance is required at any step.
