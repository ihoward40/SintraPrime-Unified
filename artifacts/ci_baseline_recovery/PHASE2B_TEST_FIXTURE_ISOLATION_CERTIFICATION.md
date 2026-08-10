# CI-BASELINE-RECOVERY — Phase 2B Certification: Test/Fixture Isolation (Category C)

**Branch:** `chore/ci-baseline-recovery`
**Prior checkpoint:** `56609fd3792e21964dfc9890f3d2a5028799a4e2` (Phase 2A —
PostgreSQL FK type consistency, certified)
**Scope:** Category C only — the test/fixture database-dependency leak in
`tests/test_matter_export_phase_two_c_five.py`. No Category A (already
done), B, or D work performed.

## Root cause (traced before editing)

`tests/test_matter_export_phase_two_c_five.py::test_export_route_returns_hash_headers`
monkeypatches `matter_export.service.build_packet` with a fake async
function that ignores its arguments and returns a canned
`MatterExportResult`. It then calls `TestClient(create_app()).post(...)`
against the real route:

```python
# portal/routers/matter_export.py
@router.post("/{matter_id}/exports")
async def export_matter_packet(
    matter_id: str,
    body: MatterExportRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_EXPORT)),
    db: AsyncSession = Depends(get_db),
):
    result = await service.build_packet(db, matter_id=..., ...)
    ...
```

The route depends on `db: AsyncSession = Depends(get_db)` purely to pass
it through to `service.build_packet` — which is fully mocked in this test
and never touches `db` at all. The problem is **not** in the mocked
service call; it is in `get_db` itself:

```python
# portal/database.py
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        ...
        await _set_rls_context(session, ...)  # executes a real SQL statement
        yield session
        ...
```

`get_db` opens a real `AsyncSessionLocal()` and **executes a real SQL
statement** (`SELECT set_config('app.current_tenant_id', ...)`) to
establish row-level-security context, *before* the route body — and
therefore the mocked `service.build_packet` call — ever runs. Because
this test never overrode the `get_db` dependency, every request through
this route attempted a genuine PostgreSQL connection at `127.0.0.1:5432`,
which does not exist in the `test`/`verify`/`Sigma Quality Gate` CI jobs
(unlike `postgresql-race`/`postgresql-bootstrap-certification`, which
explicitly provision a Postgres service container).

Two sibling tests in the *same file*
(`test_export_route_requires_auth_and_registers_scope`,
`test_export_route_rejects_client_without_export_permission`) do **not**
fail, because they are rejected by the auth/permission dependency
(`require_permissions`) *before* FastAPI's dependency resolution ever
reaches `get_db` — they never got far enough to hit the DB layer at all,
which is why this defect was invisible in those two tests and only
surfaced in the one test that supplies valid auth and permissions.

## Why this is a test/fixture defect, not a production code defect

- The route's own logic is correct: it needs *some* DB session type to
  satisfy its dependency signature, and in real production use, a real
  session and real RLS context are exactly what's required.
- The defect is that this **specific unit test** — which exists to verify
  request/response wiring (headers, status code, JSON body shape) given
  an already-mocked service layer — never isolated itself from the real
  `get_db` dependency, unlike every comparable route-level test elsewhere
  in this codebase.

## Established repository pattern (used, not invented)

This repository already has a strong, consistent convention for exactly
this situation: overriding `get_db` via FastAPI's
`app.dependency_overrides` mechanism. Confirmed present in at least 10
other test files, including `portal/tests/test_router_coverage.py`,
`portal/tests/test_mission_control_commands.py`,
`portal/tests/test_first_run_setup.py`,
`portal/tests/test_document_export_endpoint.py`, and others — e.g.:

```python
app.dependency_overrides[get_db] = lambda: mock_db
```

or, for async-generator-style overrides:

```python
async def _override_get_db():
    yield fake_session
app.dependency_overrides[get_db] = _override_get_db
```

The fix applies this exact, already-established pattern — it does not
invent a new isolation mechanism.

## Fix applied

**File:** `tests/test_matter_export_phase_two_c_five.py`
**Function:** `test_export_route_returns_hash_headers` (only this one test
function was changed; no other test in the file, and no production code,
was touched)

Added an `app.dependency_overrides[get_db]` override supplying the
`_FakeDB` fixture class **already defined in this same file** (used a few
lines above by the service-level unit test
`test_packet_contains_required_redacted_sections_hashes_and_pdf`), instead
of a brand-new fixture — reusing existing, already-reviewed test
infrastructure rather than adding new surface area:

```python
app = create_app()

async def _override_get_db():
    yield _FakeDB()

app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)
```

`db` is never actually queried in this test path (the mocked
`build_packet` ignores it), so `_FakeDB` — which the file already uses
purely as an inert stand-in with a no-op `.flush`/`.execute` — is
sufficient. No new class, no new fixture file, no changes to
`get_db`/`_set_rls_context`/`AsyncSessionLocal`/lifespan/startup behavior
anywhere in `portal/`.

## What was explicitly NOT done

- **Production startup/lifespan behavior was not touched or weakened.**
  `get_db`, `_set_rls_context`, and `AsyncSessionLocal` in
  `portal/database.py` are byte-for-byte unchanged. Real deployments still
  get a real session and real RLS context exactly as before.
- **Category B (auth regression) was not touched.** The two 401-vs-200
  failures remain, unaffected, confirming this fix is isolated to Category
  C only (see verification below).
- **No lint/style cleanup was performed** beyond what the one changed test
  function required to be correct; the file's existing lint status was
  re-verified unchanged (clean, both before and after).
- **No dependency injection or fixture changes were made to any other
  test file.** Only the one specific test function that reached the DB
  layer was touched.

## Test results

### 1. Target test file, no PostgreSQL available (matches CI's `test`/`verify`/`Sigma` environment)

```
python -m pytest tests/test_matter_export_phase_two_c_five.py -v
→ 7 passed
```

Before the fix: 6 passed, 1 failed
(`test_export_route_returns_hash_headers` —
`OSError: ... Connect call failed 127.0.0.1:5432`).

### 2. Target test file, WITH PostgreSQL available (proves no inverse hidden dependency)

A dedicated, isolated, throwaway `postgres:16-alpine` container (distinct
port `55433`, destroyed immediately after use — no shared or other-session
containers touched) was started, and `DATABASE_URL` was set to point at
it:

```
python -m pytest tests/test_matter_export_phase_two_c_five.py -v
→ 7 passed   (identical result to the no-Postgres run above)
```

This confirms the fix is a genuine isolation fix, not an accidental
skip/xfail — the test exercises exactly the same code path and produces
the same passing result whether or not a real PostgreSQL instance is
reachable, because it no longer depends on one either way.

### 3. Shared `test`/`verify`/`Sigma Quality Gate` invocation (bare `pytest`, full default testpaths)

```
python -m pytest -q
→ 2 failed:
    tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints
    tests/test_legal_authority_phase_two_c_one.py::test_federal_read_only_api_endpoints
```

Before this fix (and before Phase 2A): 3 failed (the above 2, plus
`tests/test_matter_export_phase_two_c_five.py::test_export_route_returns_hash_headers`).
**Category C has disappeared from the shared invocation. Category B (the
two remaining 401-vs-200 failures) is unchanged and still visible**,
exactly as required — confirming this fix did not accidentally mask or
interact with the separate Category B defect.

### 4. Lint check on the changed file (exact CI-pinned ruff==0.15.20)

```
ruff check tests/test_matter_export_phase_two_c_five.py
→ All checks passed!
```

No lint regressions introduced.

## Follow-up risk carried forward (not addressed here)

Per Phase 2A's finding, `portal/migrations/add_adaptive_orchestration_domain.sql`
still contains a latent UUID-vs-VARCHAR(36) foreign-key type mismatch
identical in kind to the one fixed in Phase 2A, but in the **raw-SQL**
migration rather than the ORM model. It remains unexercised by any
certified bootstrap path (confirmed not part of `MIGRATION_SEQUENCE`) and
was correctly out of scope for both Phase 2A and this Phase 2B pass. It is
recorded here again, explicitly, as a standing, separate follow-up risk in
the deficiency register — it should not be forgotten simply because nothing
currently exercises it; a future change to `MIGRATION_SEQUENCE` or a new
raw-SQL bootstrap path could reactivate it without warning.

## Next step

Per the authorized sequence (A ✓ → C ✓ → B → re-verify shared jobs → D),
Category B (the auth regression causing 401 instead of 200/404 on
previously-public read-only endpoints) is next. It requires a design
decision (restore public access vs. update stale tests) before
implementation and was explicitly deferred pending that decision. No push,
no PR opened in this pass — this work remains local-only on
`chore/ci-baseline-recovery`, on top of `56609fd3`, pending explicit
authorization to commit/push/continue.
