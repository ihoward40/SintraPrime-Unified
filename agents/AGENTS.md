# agents — Autonomous Agent System

## Purpose

Owns the autonomous agent system comprising four agent families:

- **Nova** — Real-world execution engine. Dispatches legal/financial actions via pluggable providers with human-in-the-loop approval and immutable audit trail.
- **Sigma** — Mandatory test-gating guardian. Runs test suites, coverage checks, security scans, and type checking on PRs. Blocks merges below quality thresholds.
- **Zero** — Self-healing maintenance agent. Continuously monitors for broken imports, failing tests, and code health issues. Applies patches autonomously with rollback support.
- **Chat Agent** — General-purpose chat interface for user interaction.
- **Howard Agents** — Domain-specific agents for intake, recovery, and template processing (consumer evidence workflows).

## Ownership

- All files in `agents/` top-level (Howard agents, `__init__.py`)
- Sub-agent packages: `agents/nova/`, `agents/sigma/`, `agents/zero/`, `agents/chat/`
- Agent-level tests (e.g., `agents/chat/tests/`)

## Local Contracts

- Each agent runs as an autonomous module — no agent imports another agent's internals
- Agents communicate via the portal API, file-system drop zones (`intake/`, `processed/`, `errors/`, `exports/`), or the shared database
- Nova: every action must route through `approval_gateway.py` and log to `execution_ledger.py`
- Sigma: enforces coverage thresholds defined in `pyproject.toml` or `.safety-policy.yml`
- Zero: all auto-patches must be revertible (`git revert` compliant)

**Howard agents — approval-gated by default:**
Howard recovery/intake/template agents must remain evidence-intake-only unless explicit approval is given. They may create local drafts, receipts, summaries, exports, and case packets. They may not send, file, email, mail, serve, post, delete, or contact third parties.

**B2-B11 containment convention (all agents + operator):**
- Legacy mutation edges (`sigma.post_github_status`, `nova.execute_action`, `chat.execute_task_autonomously`, `operator/browser_controller` click/type_text/submit_form) require a governed B2 context (`b2_governed_context` set; `None` by default).
- Ungoverned mutation fails closed with `PermissionError("LEGACY_BYPASS_DENIED")`; unknown surface IDs fail with `LEGACY_SURFACE_UNKNOWN`.
- Inventory status alone is not execution authority. B2 containment precedes legacy execution gates (e.g. `NOVA_ALLOW_DYNAMIC_EXEC`).

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `agents/chat/AGENTS.md` | Chat Agent public API and governed inference routing | `chat_agent.py`, `__init__.py`, `tests/` |
| `agents/zero/AGENTS.md` | Zero Agent self-healing behavior and governed inference routing | `zero_agent.py`, `health_monitor.py`, `__init__.py`, `tests/` |
| `agents/sigma/AGENTS.md` | Sigma Agent CI gating and governed inference routing | `sigma_agent.py`, `ci_enforcer.py`, `__init__.py`, `tests/` |

*(Other sub-agent packages are leaf modules without child DOX for now.)*
