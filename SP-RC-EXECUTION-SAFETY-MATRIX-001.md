# SP-RC-EXECUTION-SAFETY-MATRIX-001
## G0-R4.1 — Execution Safety Unblocking (ER-001 / ER-002 / ER-003)

**Governing lineage:** `c0c29a0e` → `78e36a4d` → `818a6d00` → `eec680b1` (verified; delta remains docs + test-infra only)
**No certification lane executed. No application source mutated. Reality Gate CLOSED.**

## 1. ER-001 — external-service risk classification
Full sweep of every lane test file referencing an outbound-capable library (Stripe, OpenAI/Anthropic,
HTTP clients, cloud SDKs, Slack/Discord/Telegram/Plaid, email/SMS, webhooks, object storage):
**zero outbound client construction and zero non-loopback network I/O exist anywhere in the
certification lanes.** Every "unmocked" hit was a string reference, an assertion on a value, or
in-memory state (e.g. `phase16/stripe_billing/billing_portal.py::create_portal_session` builds a
`BillingPortalSession` uuid object — no API call). LLM-provider tests register providers in
in-memory routers (`register_provider`/`mark_timeout`/`get_health`) — no client is ever built.

| Test/file | Lane | External service | Network classification | Destructive action | Containment | Timeout coverage | Safe to execute? |
|---|---|---|---|---|---|---|---|
| `phase16/stripe_billing/tests/test_billing_portal.py` | EXEC | Stripe-named only | `MOCKED_SAFE` (no outbound path) | none | in-memory impl | pytest-timeout 120s | **SAFE** |
| `phase18/stripe_webhooks/tests/test_webhook_handler.py` | EXEC | webhook logic only | `MOCKED_SAFE` | none | n/a | pytest-timeout | **SAFE** |
| `backend/stripe-payments/tests/test_stripe.py` | EXEC | Stripe-named only | `MOCKED_SAFE` (mocked ×3 files in family) | none | mocks | pytest-timeout | **SAFE** |
| `phase17/integration_tests/tests/test_cross_stack.py` | EXEC | none live | `MOCKED_SAFE` | none | n/a | pytest-timeout | **SAFE** |
| `security/tests/test_security.py` | EXEC | payload strings only | `NETWORK_BLOCKED_SAFE` | SQL-injection *strings* (not executed) | payloads only | pytest-timeout | **SAFE** |
| `core/tests/test_analytics.py`, `swarm_runtime/tests/test_governed_router_failover.py`, `test_provider_health_persistence.py` | EXEC | LLM-provider names only | `MOCKED_SAFE` (in-memory router state) | none | n/a | pytest-timeout | **SAFE** |
| `agent_runtime/tests/test_w46_certification_generation.py`, `predictive/tests/test_predictive.py` | EXEC | none live | `MOCKED_SAFE` | none | n/a | pytest-timeout | **SAFE** |

`LIVE_EXTERNAL_CALLS_REMAIN = FALSE` — and independently, the default-deny guard (below) makes a
forgotten mock fail loudly instead of reaching a live service.

## 2. Network default-deny policy (implemented, self-tested)
`conftest.py` installs a **certification network guard** when `SINTRAPRIME_CERT_NET_GUARD=1`
(set by `scripts/certify.py` for certification execution only): `socket.socket.connect`,
`connect_ex`, `sendto` and `socket.create_connection` raise `ConnectionAbortedError` for every
destination except loopback (`127.0.0.1/8`, `::1`, `localhost`, `*.localhost`). Real credentials
are not consumed by any lane test; the guard is defense-in-depth.
Self-test (`artifacts/selftest_guard/`): loopback connect **succeeds**; outbound IP connect and
outbound DNS connect both **denied** with the guard error (3/3 passed).

## 3. ER-002 — destructive/high-risk tests

| Test/file | Lane | Destructive action | Containment | Classification | Safe to execute? |
|---|---|---|---|---|---|
| `agents/chat/tests/test_chat_agent.py` | EXEC | `os.unlink(tmp_path)` ×4 | pytest `tmp_path` | `TEMP_DIR_CONTAINED` | **SAFE** |
| `core/tests/test_marketplace.py` | EXEC | `os.remove(db_path)` | `tempfile` | `TEMP_DIR_CONTAINED` | **SAFE** |
| `portal/tests/test_orchestration_runtime_acceptance.py` | EXEC | `process.terminate()` | own `multiprocessing` child, joined + exitcode asserted | `CHILD_PROCESS_CONTAINED` | **SAFE** |
| `agent_runtime/tests/test_capability_resolver.py` | EXEC | git `diff`/`status` — **read-only** | no mutation; env-coupled asserts (note) | read-only | **SAFE** (env-coupling note) |
| `channels/tests/test_channels.py`, `cross_platform/tests/test_cross_platform.py`, `phase18/security/tests/test_security_hardening.py` | EXEC | tmp/mocks | `tmp_path` + mocks | `TEMP_DIR_CONTAINED` | **SAFE** |
| `portal/tests/test_mission_control_review_corrections.py` | EXEC | `DROP TABLE` string only | injection payload, not executed | none | **SAFE** |
| `swarm_runtime/tests/test_acceptance_003.py` | EXEC | host `%LOCALAPPDATA%\SintraPrime\swarm-runs\` writes; real child workers vs **governing repo** | none | `HOST_MUTATION_POSSIBLE` | `EXCLUDED_PENDING_REVIEW` |
| `swarm_runtime/tests/test_acceptance_003_real.py` | EXEC | + `shutil.rmtree(run_dir)` (host), kills spawned worker, stale `base_sha=eeb55ffb` | none | `HOST_MUTATION_POSSIBLE` | `EXCLUDED_PENDING_REVIEW` |
| `swarm_runtime/tests/test_acceptance_004.py` | EXEC | host run-dir writes; worktree ops vs governing repo | none | `HOST_MUTATION_POSSIBLE` | `EXCLUDED_PENDING_REVIEW` |
| `swarm_runtime/tests/test_acceptance_004_real.py` | EXEC | **mutates governing repo git config + branches (`git branch -D`, `worktree add`), user's GLOBAL git config, sibling worktree dir, `rmtree`** | none | `HOST_MUTATION_POSSIBLE` | `EXCLUDED_PENDING_REVIEW` |
| `swarm_runtime/tests/test_acceptance_005b.py` | EXEC | host run-dir writes + rmtree; controller vs governing repo | none | `HOST_MUTATION_POSSIBLE` | `EXCLUDED_PENDING_REVIEW` |

### Exclusion justification (per §12 — not silent)
- **Why acceptable:** the five swarm acceptance files are operator-facing end-to-end harnesses
  (print-driven `run_*()` scripts with `__main__` entries) that mutate host `%LOCALAPPDATA%`,
  the governing worktree (`artifacts/`, local git config, branches) and the user's **global**
  git config, against a stale `base_sha` from a foreign lineage. Running them inside
  certification would violate §5 (git containment) outright.
- **Coverage impact:** the durable-correctness logic surface (crash/restart/reconciliation) keeps
  full automated coverage via `mission_wiring/tests` (16 files/170 funcs) and the remaining 25
  `swarm_runtime` unit-test files. Lost only: *real-OS-process + real-git-worktree E2E* proof.
- **Equivalent evidence:** unit-level equivalents exist for the durable engine and controller
  logic; no in-repo equivalent exists for the real-worktree E2E path.
- **Residual gap (explicit):** SwarmController real-process/worktree E2E must be re-run as a
  **manual acceptance protocol inside a disposable clone** (never the governing worktree) after
  certification. Recorded as a certification gap, not silently dropped.

`MANDATORY_COVERAGE_LOST = FALSE` (mandatory lane surfaces remain covered; residual E2E gap is documented and routed).

## 4. ER-003 — timeout policy (implemented, self-tested)
- **Per-test:** `pytest-timeout` 2.4.0 installed (test-infra); `--timeout=120 --timeout-method=thread` applied by `certify.py` to every certification run.
- **Lane wall-clock:** `certify.py` enforces `timeout=1800s` on the pytest subprocess; expiry → `[certify] LANE WALL-CLOCK TIMEOUT … CERTIFICATION FAILURE`, exit code 3 — a clear failure, never silent.
- **Exemptions:** none; `slow`-marked tests must fit the 120s window or be re-marked.
- **Evidence on timeout:** pytest output + receipt retained in `artifacts/cert-receipts/`.
- **Self-test:** sleeping test killed at 2s with `+++ Timeout +++` and non-zero exit (rc=1).

## 5. Parallelism
`PARALLELISM = 1` — serial, deterministic; `pytest-xdist` deliberately not installed.

## 6. PKG-001 carry-forward
`phase19/revenue_smoke_test`: `SCRIPT_TOPOLOGY_SUPPORTED` / `REPO_PACKAGE_IMPORT = INCONSISTENT`.
Certification execution imports it via explicit path + script topology (verified collectible);
no execution path depends on repo-package import semantics → `PKG_001_EXECUTION_BLOCKER = FALSE`. Not remediated.

## 7. Readiness verdict
`G0_EXECUTION_READINESS = PASS` — with the five-file swarm-acceptance exclusion above documented
and the residual E2E gap explicitly routed to post-certification acceptance. Git/process/filesystem
containment holds for every test that will execute; network is default-deny; timeouts are active;
execution is serial; no mandatory lane surface lost coverage.
