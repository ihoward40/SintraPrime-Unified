# CI-BASELINE-RECOVERY — Phase 1: Evidence & Root-Cause Classification

**Branch:** `chore/ci-baseline-recovery`
**Base:** `origin/main` @ `e2ada66e22f7992fec83c884fd6f7aa9329ccb25`
**Mission:** Independent of and separate from PR #280 (`feat/sp-voice-002-federated-speech-runtime`,
frozen at `2f9f26b409dae0c38407c6869d8e5aea1e3abecf`, HOLD FOR REVIEW). No
files in this worktree overlap with PR #280's changes. No code has been
modified in this pass — Phase 1 is evidence-gathering and classification
only, per authorization.

## Method

For each failing check on `main` tip (`e2ada66e...`), the exact-head
check-runs were fetched live via the GitHub API, cross-referenced to their
underlying Actions run/job IDs, and the **raw job logs** (not just
summaries) were pulled and inspected line-by-line to find the actual
failing assertion/exception, not just the job-level pass/fail signal.

## Baseline check-run inventory (main tip, before any PR-280 or
CI-BASELINE-RECOVERY work existed)

| Check | Conclusion | Job ID | Failing step |
|---|---|---|---|
| `security` | success | 92867422553 | — |
| `smoke` | success | (separate workflow run 31178969177) | — |
| `claims-validation` | success | 92867422447 | — |
| `auth-tenant-rbac-certification` | success | 92867422416 | — |
| `audit-correlation-non-http-certification` | success | 92867422592 | — |
| `lint` | **failure** | 92867422514 | `Run ruff check . --output-format=github` |
| `test` | **failure** | 92867422408 | `Run full test suite` |
| `postgresql-race` | **failure** | 92867422386 | `Prepare PostgreSQL schema` |
| `postgresql-bootstrap-certification` | **failure** | 92867422430 | `Run raw-SQL PostgreSQL bootstrap certification` |
| `http-correlation-ws-hardening-certification` | **failure** | 92867422470 | `Run HTTP correlation and WebSocket hardening certification suite` |
| `verify` | **failure** | 92867421081 | `Run full test suite` (separate workflow, same underlying pytest invocation) |
| `Sigma Quality Gate` | **failure** | 92867421176 | `Run tests with coverage` |

## Root-cause classification

### Category A — Genuine code defect: UUID vs. VARCHAR(36) foreign-key type mismatch

**Affects:** `postgresql-race`, `postgresql-bootstrap-certification` (2 of 6 failing checks)

**Exact evidence:** `postgresql-race`'s "Prepare PostgreSQL schema" step
raises, at real-PostgreSQL `CREATE TABLE` time:

```
asyncpg.exceptions.DatatypeMismatchError: foreign key constraint
"memory_vault_tenant_id_fkey" cannot be implemented
DETAIL:  Key columns "tenant_id" and "id" are of incompatible types:
uuid and character varying.
```

`postgresql-bootstrap-certification`'s own repo-authored guard test
(`portal/tests/test_postgresql_bootstrap_schema_authority.py::
test_postgresql_orm_foreign_key_column_types_are_internally_consistent`)
independently confirms and enumerates **7** mismatched FK column pairs, all
in `portal/models/orchestration.py`, all declared as PostgreSQL-native
`UUID(as_uuid=True)` while their referenced target columns
(`tenants.id`, `users.id`, both defined in `portal/models/user.py` as
`String(36)`) are `VARCHAR(36)`:

```
orchestration_runs.tenant_id UUID -> tenants.id VARCHAR(36)
orchestration_runs.created_by UUID -> users.id VARCHAR(36)
orchestration_approval_requests.principal_id UUID -> users.id VARCHAR(36)
orchestration_linkages.tenant_id UUID -> tenants.id VARCHAR(36)
orchestration_principal_authorities.tenant_id UUID -> tenants.id VARCHAR(36)
orchestration_principal_authorities.user_id UUID -> users.id VARCHAR(36)
memory_vault.tenant_id UUID -> tenants.id VARCHAR(36)
```

**Source file:** `portal/models/orchestration.py` — every affected column
across four classes: `OrchestrationRun` (lines ~111-112: `tenant_id`,
`created_by`), `ApprovalRequest` (line ~339: `principal_id`),
`OrchestrationLinkage` (line ~360: `tenant_id`), `PrincipalAuthority`
(lines ~376-377: `tenant_id`, `user_id`), and `MemoryVault` (line ~446:
`tenant_id`) — every one using `mapped_column(UUID(as_uuid=True), ForeignKey(...))`
against a target that is actually `String(36)`.

**Why it wasn't caught earlier:** SQLite (used by most local/unit test
runs) does not enforce column-type agreement across a foreign key the way
PostgreSQL does, so this defect is invisible except when the schema is
actually created against a real PostgreSQL instance — exactly what
`postgresql-race` and `postgresql-bootstrap-certification` do, and exactly
why the repo's own authors already wrote
`test_postgresql_orm_foreign_key_column_types_are_internally_consistent`
as a guard (it is present and already failing — it just isn't run by the
non-Postgres `test`/`verify`/`Sigma` jobs).

**Locally reproducible:** Yes — the guard test itself
(`portal/tests/test_postgresql_bootstrap_schema_authority.py`) can be run
against SQLAlchemy metadata without a live database (it compiles column
types via the PostgreSQL dialect, no connection needed) and already fails
locally, confirming this is a static/structural defect, not
environment-flakiness.

**Infra vs. code:** **Code defect.** The PostgreSQL container itself
initializes and starts correctly in both jobs (see full container startup
logs); the failure is purely in application-level schema definitions.

**Smallest corrective scope:** Change the seven affected columns'
type declarations in `portal/models/orchestration.py`
(`OrchestrationRun.tenant_id`, `OrchestrationRun.created_by`,
`ApprovalRequest.principal_id`, `OrchestrationLinkage.tenant_id`,
`PrincipalAuthority.tenant_id`, `PrincipalAuthority.user_id`,
`MemoryVault.tenant_id`) from `UUID(as_uuid=True)` to `String(36)` to match
`tenants.id`/`users.id`'s actual type — **or**, alternatively, migrate
`tenants.id`/`users.id` themselves to native `UUID`, which is a much larger
blast-radius change touching every other FK referencing those tables
repo-wide. The narrower, lower-risk fix is changing the 7 orchestration/
memory-vault columns to match the existing `String(36)` convention,
since that convention is already used consistently by every other table
in the codebase (confirmed: `portal/models/voice_command.py`,
`portal/models/user.py`, and others all use `String(36)` for
tenant/user/id foreign keys — `orchestration.py` is the outlier).

**Regression risk:** Low-to-moderate. Changing `Mapped[str]` column types
from `UUID(as_uuid=True)` to `String(36)` should be behaviorally
transparent to Python code already treating these as `str` (the `Mapped[str]`
type hints already assumed string semantics — the `UUID(as_uuid=True)`
SQLAlchemy column type was the anomaly, not the Python-level usage).
Requires verifying no code elsewhere does `isinstance(x, uuid.UUID)` on
these specific fields, and requires an Alembic migration for any
environment that already has these tables created with the wrong type
(no such environment currently exists in CI, since schema creation itself
fails first).

### Category B — Genuine code defect: authentication regression on previously-public/differently-scoped endpoints

**Affects:** `test`, `verify`, `Sigma Quality Gate` (3 of 6 failing checks) — all three run the **same** underlying pytest invocation and fail on the **same** two tests:

```
tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints
  - assert 401 == 200 (GET /jurisdictions/{code})
tests/test_legal_authority_phase_two_c_one.py::test_federal_read_only_api_endpoints
  - assert 401 == 200
```

and `http-correlation-ws-hardening-certification` fails on a related but
distinct instance of the same status-code-mismatch pattern:

```
portal/tests/test_http_correlation_ws_hardening_certification.py::
TestResponseHeaderCoverage::test_404_has_request_id - assert 401 == 404
```

**Root cause (not yet fully isolated to a single commit, but the pattern
is unambiguous):** these tests call `TestClient(create_app())` and hit
endpoints expecting either an unauthenticated 200 (read-only
jurisdiction/legal-authority endpoints) or a 404 (for a nonexistent
resource), but the application now returns 401 Unauthorized first — i.e.
some global authentication/authorization dependency or middleware is now
being applied to routes these tests assumed were public, or a
correlation-ID/request-ID middleware ordering change causes the 401 check
to run before routing can even determine 404-vs-not-found. This is
consistent with the many recent "Phase N hardening/certification"
merges (`#263` Adaptive Orchestration, `#266` Phase 4 Autonomous Execution
Plane, `#273`/`#274` OmniBrain/God Mode) visible in `main`'s recent commit
history, several of which explicitly added auth/tenant/RBAC enforcement
layers.

**Locally reproducible:** Not yet attempted in this pass (Phase 1 is
evidence/classification only) — but the failure is deterministic (same
result in `test`, `verify`, and `Sigma Quality Gate`, all on the same
commit), so it should reproduce on-demand with `pytest tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints`
locally without any special environment.

**Infra vs. code:** **Code defect** (or a legitimately-intentional
behavior change that the affected tests were never updated for — either
way, a code-level fix, not an infrastructure one).

**Smallest corrective scope:** Identify which middleware/dependency now
requires authentication on `/jurisdictions/{code}`, `/jurisdictions/{code}/rules`,
`/legal-rules/compare`, and the federal read-only endpoints, and either
(a) restore public access to these specific read-only routes if that was
the intended design, or (b) update the three affected tests to supply a
valid bearer token if the endpoints are now correctly gated and the tests
are simply stale. Requires reading `portal/main.py`'s middleware stack and
the routers registered for `legal_authority`/jurisdiction endpoints to
determine which is correct before touching either side.

**Regression risk:** Depends entirely on which direction (a) vs (b) is
correct — this requires a design decision, not just a mechanical fix, and
should not be guessed at without further investigation (deferred to
Phase 2 of this recovery track, not resolved in this classification pass).

### Category C — Test/environment mismatch: Postgres-dependent test runs in a job with no Postgres service

**Affects:** `test`, `verify`, `Sigma Quality Gate` (same 3 jobs as
Category B, contributing a third, distinct failing test each)

**Exact evidence:**

```
tests/test_matter_export_phase_two_c_five.py::test_export_route_returns_hash_headers
  - OSError: Multiple exceptions: [Errno 111] Connect call failed
    ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

**Root cause:** this test mocks `matter_export.service.build_packet` and
does not appear, at the test-body level, to require a real database — yet
something reachable from `create_app()` (module-level import side effect,
a dependency-injected DB session, or an eagerly-constructed engine in
`legal_authority.repository.LegalAuthorityRepository` or
`portal.services.matter_export_service`) attempts a real PostgreSQL
connection at `127.0.0.1:5432`, which is simply not running in the `test`/
`verify`/`Sigma Quality Gate` jobs (unlike `postgresql-race`/
`postgresql-bootstrap-certification`, which explicitly provision a
Postgres service container). The exact trigger point (module import vs.
route dependency vs. lifespan) has not yet been isolated in this pass.

**Locally reproducible:** Should reproduce identically in any environment
without a local Postgres listening on 5432 — i.e., this is not
GitHub-Actions-specific flakiness, it is a structural test/fixture gap.

**Infra vs. code:** **Test/fixture defect** — the test should either be
marked with the repo's existing `@pytest.mark.postgresql` marker (already
defined in `pytest.ini`, used elsewhere in the repo to segregate
Postgres-dependent tests) so it is correctly excluded from
non-Postgres CI lanes, or the code path it exercises should be fixed to
not require a real DB connection when the relevant service call is already
mocked.

**Smallest corrective scope:** Trace exactly which import/dependency in
the request path to `POST /api/v1/matters/matter-1/exports` opens a real
DB connection despite `build_packet` being monkeypatched, then either (a)
add proper DB-session mocking/fixture isolation to this specific test, or
(b) mark it `@pytest.mark.postgresql` if a real DB is a genuine, unavoidable
requirement for this route.

**Regression risk:** Low — this is additive test-infrastructure work
(better isolation/marking), not behavior-changing production code, as long
as investigation confirms the route itself doesn't require a DB write for
this particular mocked-service test case.

### Category D — Pre-existing repo-wide lint debt (unrelated to any current feature branch)

**Affects:** `lint` (1 of 6 failing checks — the *only* overlap with
anything touched by PR #280, and that overlap has already been
independently fixed and verified on PR #280's own branch; see
`artifacts/voice/SP_VOICE_002_PHASE2A_CERTIFICATION.md` on that branch)

**Exact evidence:** the `lint` job runs `ruff check . --output-format=github`
against the entire repository. On `main` tip, this reports pre-existing
violations exclusively in files unrelated to any current feature branch:

```
scripts/phase_9_simulation.py — W293, RET505 (multiple)
scripts/q3_strategic_debate.py — I001, W293 (multiple)
scripts/remediation_and_research_simulation.py — I001, W291
portal/database.py — B008
portal/models/mission_control_outbox.py — I001, UP035, F401, UP006, UP045 (multiple)
portal/models/orchestration.py — I001, UP037 (multiple)
portal/routers/mission_control.py — I001
portal/services/auditable_trails.py — I001, W293 (multiple)
portal/services/autonomous_plane.py — I001, UP042, W291, W293, C401 (multiple)
```
(non-exhaustive — full local repro confirms dozens of additional findings
across `portal/`, `scripts/`, and likely other directories not yet fully
enumerated in this pass).

**Locally reproducible:** Yes, confirmed. Installing the exact CI-pinned
`ruff==0.15.20` (the locally-preinstalled `ruff` on PATH was an older 0.13.0
that did not surface all of these rules) and running
`ruff check . --output-format=github` from repo root reproduces every one
of these findings exactly.

**Infra vs. code:** **Code style/lint debt**, pre-existing, accumulated
across many prior "Phase N" feature merges that were evidently not run
through this exact pinned ruff version (or through `ruff check .` at
repo root at all) before merging.

**Smallest corrective scope:** This is the **largest-surface-area** of the
6 categories — potentially dozens of files across `scripts/`, `portal/models/`,
`portal/services/`, `portal/routers/`. The repo's own `pyproject.toml`
already has a documented convention for this exact situation: a
`[tool.ruff.lint.per-file-ignores]` "baseline" section explicitly
described as tracking "existing violations in active directories,
suppressed by path... as violations are fixed in a directory, remove its
entry here" (see `docs/ci/ruff-baseline.md`, referenced but not yet read
in this pass). The correct fix is very likely **not** to hand-fix every
finding in one giant commit, but to (a) confirm whether these specific
files are already supposed to be covered by the existing baseline
suppression list and simply aren't (a config gap), or (b) if they are
newly-written files never added to the baseline, fix them file-by-file or
add them to the baseline list matching existing convention, whichever the
project's established pattern prefers.

**Regression risk:** Low per-file (mostly whitespace/import-order/typing-
modernization findings), but broad in surface area — recommend treating
this as its own multi-commit sub-track rather than one large diff.

## Dependency graph between failure categories

```
Category A (UUID/VARCHAR FK mismatch)
    └── independently causes: postgresql-race, postgresql-bootstrap-certification
        (no downstream dependency on B/C — these jobs fail at schema
        creation time, before any application-level test logic runs)

Category B (auth regression) ─┬── test job
Category C (Postgres-dependent test, no service) ─┤
                               ├── verify job
                               └── Sigma Quality Gate job
    (B and C are DISTINCT root causes that happen to co-occur in the same
    3 jobs, because all 3 jobs run the identical "full test suite"
    pytest invocation — fixing B does not fix C and vice versa; both must
    be resolved independently before these 3 jobs go green)

Category D (repo-wide lint debt)
    └── independently causes: lint
        (no dependency on A/B/C)
```

**Important finding:** there is **no single root cause** tying all 6
checks together. The task's working hypothesis ("several red jobs may be
downstream symptoms of the same broken database/bootstrap environment")
is **partially correct but not complete**: Category A does explain both
Postgres-specific jobs, and Category C explains one shared failing test
across the other three jobs, but Category B (auth regression) is an
entirely separate, unrelated defect that happens to surface in the same
3 jobs as Category C purely because they share one pytest invocation.
Fixing the Postgres/bootstrap layer alone (Category A) will **not** turn
`test`/`verify`/`Sigma Quality Gate` green — Categories B and C must each
also be resolved.

## Recommended fix order (per original priority: Postgres/bootstrap →
core test → verify → lint → Sigma → remaining lanes — refined with the
dependency graph above)

1. **Category A (Postgres FK type mismatch)** — fixes `postgresql-race`
   and `postgresql-bootstrap-certification` outright; also unblocks any
   future real-Postgres-backed work (including a real prerequisite for
   SP-VOICE-002 Phase 2A-2's eventual production wiring, though that is
   out of scope for this track).
2. **Category C (Postgres-dependent test lacking proper marker/isolation)**
   — smaller, more mechanical fix than Category B; resolving it first
   reduces noise so Category B's fix can be verified in isolation.
3. **Category B (auth regression)** — requires a design decision (restore
   public access vs. fix stale tests) before implementation; do this after
   C so the remaining failures in `test`/`verify`/`Sigma Quality Gate` are
   entirely attributable to B while it's being worked.
4. Re-verify `test`, `verify`, and `Sigma Quality Gate` all green together
   once B and C are both resolved (they share the same test invocation,
   so one verification pass covers all three).
5. **Category D (repo-wide lint debt)** — last, deliberately: fixing lint
   first would "make the dashboard prettier while leaving the real
   foundation busted" (this was explicitly the wrong order per the
   authorizing instruction), and its large surface area is best handled as
   its own dedicated sub-track once the functional defects (A/B/C) are
   resolved and confirmed stable.

## Explicitly not done in this pass

- No code changes were made to `main`, this new branch, or any other
  branch.
- No attempt was made to fix Categories A, B, C, or D yet — this document
  is the evidence/classification deliverable only, per the authorized
  scope of "CI-BASELINE-RECOVERY Phase 1."
- PR #280 (`feat/sp-voice-002-federated-speech-runtime`) was not touched,
  read, or referenced for any code changes in this pass — only cited for
  contrast (its own, already-fixed, narrowly-scoped `lint` finding).
- `docs/ci/ruff-baseline.md` (referenced by `pyproject.toml`'s comments)
  has not yet been read in full — recommended as the first step of a
  Category D sub-track to confirm whether the baseline-suppression
  mechanism is stale/misconfigured or whether these files are genuinely
  new/unlisted.
- The exact commit(s) that introduced Categories A, B, and C have not yet
  been bisected/identified by commit SHA — only the current defective
  state has been confirmed and classified. `git blame`/bisection is
  recommended as a next step if commit-level attribution is desired before
  fixing.

## Next authorized step

Per the standing instruction, this document stops at classification. The
next step (implementing the Category A/B/C/D fixes in the priority order
above) requires separate, explicit authorization — this is a distinct
mission from PR #280, which remains untouched and frozen at
`2f9f26b409dae0c38407c6869d8e5aea1e3abecf`.
