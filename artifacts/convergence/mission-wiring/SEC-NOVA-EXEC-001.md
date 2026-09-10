# SEC-NOVA-EXEC-001 — Dynamic Execution & Provider Authority Audit

**Verdict: FINDING** (no CRITICAL) · **Worktree HEAD:** `05885aa2` · Read-only lane
**Provenance:** executed directly by the orchestrator after two subagent dispatches failed on provider connection errors (`deleg_4a18655e`, `deleg_469de835` — zero output, retried once more with same result). All evidence below is first-hand `rg`/file/AST output. Machine-readable twin: `SEC-NOVA-EXEC-001.json`. Raw hit inventory: `_sec_hits_raw.json` (380 hits).

## Executive result

```text
DYNAMIC_EXEC_PRESENT       = TRUE   (4 real sites outside tests; 2 are compile-only validators)
MODEL_TO_EXEC_PATH         = TRUE   (latent, default-deny, ORPHANED — zero production importers)
MODEL_TO_SHELL_PATH        = FALSE  (no model->shell path; shell executor is caller-supplied + shell=False)
MODEL_TO_IMPORT_PATH       = FALSE
MODEL_TO_BROWSER_BYPASS    = FALSE
MODEL_TO_AUTHORITY_BYPASS  = FALSE
PROVIDER_AUTHORITY_LEAKS   = 1      (MEDIUM — caller-supplied tenant_id, portal blackstone router)
REGISTRY BYPASS            = TRUE for all 3 live dynamic-execution surfaces
```

## Findings

| ID | File:line | Class | Severity | Essence |
|---|---|---|---|---|
| SEC-001 | `agents/nova/nova_agent.py:334` | MODEL_CONTROLLED (conditional) | **HIGH (conditional)** | Unknown action → OpenAI gpt-4o-mini → fence-stripped model output → `exec(code, globals(), local_env)` when `NOVA_ALLOW_DYNAMIC_EXEC=true` |
| SEC-002 | `scheduler/task_executor.py:195` | TRUSTED_INTERNAL + external enable | MEDIUM | `execute_python(code)` — caller-supplied string, gated by same env flag, dedicated `safe_globals`; `execute_shell` (206-224) uses `shlex.split` + `shell=False` + blocked-pattern list |
| SEC-003 | `skill_evolution/skill_runner.py:195` | EXTERNALLY_CONTROLLED | MEDIUM | `exec(compile(skill.code…))` behind a **substring blocklist** — bypassable (e.g. `getattr(__builtins__,'ev'+'al')`); timeout-capped sandbox |
| SEC-004 | `core/universe/skill_registry.py:111` | STATIC_SAFE | NONE | `compile()` used only as syntax validator |
| SEC-005 | `skill_evolution/auto_skill_creator.py:495` | STATIC_SAFE | NONE | same |
| SEC-006 | `portal/routers/blackstone.py` (82,100,215,268,375,391) | USER_CONTROLLED | **MEDIUM** | `tenant_id` taken from **request body/query** and persisted/queried; authenticated user's tenant never cross-checked → cross-tenant write/read possible. Correct pattern exists at `portal/middleware/auth_middleware.py:144` (`request.state.tenant_id` from verified JWT) but is unused here |
| SEC-007 | `saas/saas_api.py:226` | USER_CONTROLLED stub | LOW | hardcoded stub, zero production importers |
| SEC-008 | phase18/security scanner rule tables | SECURITY_SCANNER_SELF | NONE | literal detection patterns, not execution |

## SEC-001 detail — the Nova dynamic-exec chain (lines quoted)

```text
284  if action_type not in self._registry:                # unknown action
285      api_key = os.environ.get("OPENAI_API_KEY")
289      client = openai.OpenAI(api_key=api_key)
290      prompt = "Generate a Python function ... 'dynamic_handler(params)'"
291-299  client.chat.completions.create(model="gpt-4o-mini", ...)
300      code = response.choices[0].message.content.strip()
301-306      (strip ```python fences)
309-316  ActionSpec(... approval_level=ApprovalLevel.HUMAN)   # metadata only
320  if os.environ.get("NOVA_ALLOW_DYNAMIC_EXEC", "false") != "true":
325      raise PermissionError(...)                        # DEFAULT-DENY confirmed
334  exec(code.strip(), globals(), local_env)              # MODEL OUTPUT EXEC'D
335-338  dynamic_handler attached to self._registry
```

Answers to the directed questions:

- **Default-deny?** Yes — line 320 refuses unless the env var is exactly `true` (case-normalized). Verified by `tests/security/test_no_runtime_exec.py` (blocked for unset/false/0/empty).
- **Does env-var enablement alone permit exec of model output?** **Yes.** When the flag is on, no human approval, no allowlist, no sandboxing (note: it injects into module `globals()`, unlike the scheduler's dedicated namespace) precedes `exec`.
- **Does the generated spec's `HUMAN` approval level gate anything before exec?** **No.** The `ActionSpec(approval_level=HUMAN)` is constructed at line 315 and its approval level is never consulted before line 334; the first execution of the generated handler happens before any approval flow.
- **Production reachability:** rg finds **zero non-test importers** of `agents/nova/nova_agent.py` on this lineage (ZD-001 runtime map had classified `agents/` 0-reachable). The path is real but orphaned.

## Registry bypass (directed question 4)

```text
rg 'from agent_runtime|import agent_runtime' agents/ scheduler/ skill_evolution/ core/universe/  =>  ZERO hits
```

All three live dynamic-execution surfaces (Nova dynamic handler, scheduler `execute_python`/`execute_shell`, skill_evolution `skill_runner`) operate with **no consultation of `agent_runtime.capability_resolver` or `registry/capabilities/`**. The governed registry (W4-1..W4-4) currently covers `agent_runtime`/`mission_wiring` paths only; these bypass it entirely. Scheduler `execute_python`/`execute_shell` currently have **no non-test callers** — the surface is latent, not exercised.

## Remediation design (design only — no code changed)

**Governed Action/Plugin Registry** — model output never executes as code:

```text
LLM proposes {action_type, parameters}        (structured, schema-validated)
  → Action Registry lookup: action_type must be a REGISTERED handler
      (unregistered ⇒ UNKNOWN_ACTION refusal — replaces dynamic handler generation)
  → capability_resolver.resolve_capability(action_type) → CanonicalCapability
      (unknown/ambiguous/dormant/disabled/generation-mismatch ⇒ REFUSED pre-contact)
  → authority: DelegationAuthority + AuthorityApprovalService binding
      (mission/actor/tenant/capability/resource, expiry, exactly-once)
  → registered handler executes with capability-scoped params
  → MissionReceipt + evidence
```

Skill execution migrates to the same registry (skills become declarative action bundles). If raw-code skills are retained: process-isolated sandbox (subprocess/container — never shared `globals()`), same capability+authority pre-gate, and a written per-skill permission manifest. For SEC-006: bind tenant server-side (`request.state.tenant_id` from the verified JWT) and refuse body-supplied tenant values.

**Secrets:** none recorded; env vars referenced by NAME only (`OPENAI_API_KEY`, `NOVA_ALLOW_DYNAMIC_EXEC`).
