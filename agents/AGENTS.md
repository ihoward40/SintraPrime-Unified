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
- Agents communicate via the portal API, file-system drop zones (`intake/`, `processed/`, `errors/`, `exports/`), the shared database, or the governed PARL orchestration facade
- New multi-agent orchestration MUST prefer `parl.GovernedPARLOrchestrator`; elevated capabilities are admitted centrally before any worker is spawned
- God Mode / Principal Command is a Principal capability, never an agent capability; agents must not self-elevate, bypass approvals, or infer elevated authority from task text
- Nova: every action must route through `approval_gateway.py` and log to `execution_ledger.py`
- Sigma: enforces coverage thresholds defined in `pyproject.toml` or `.safety-policy.yml`
- Zero: all auto-patches must be revertible (`git revert` compliant)

**Howard agents — approval-gated by default:**
Howard recovery/intake/template agents must remain evidence-intake-only unless explicit approval is given. They may create local drafts, receipts, summaries, exports, and case packets. They may not send, file, email, mail, serve, post, delete, or contact third parties.

## Work Guidance

- When adding a new agent to shared orchestration, register it through the governed PARL facade and declare its task risk/capability metadata rather than granting broad ambient authority.

## Verification

- Principal Command behavior: `pytest parl/tests/test_god_mode.py parl/tests/test_governed_orchestrator.py`

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `agents/chat/AGENTS.md` | Chat Agent public API and governed inference routing | `chat_agent.py`, `__init__.py`, `tests/` |
| `agents/zero/AGENTS.md` | Zero Agent self-healing behavior and governed inference routing | `zero_agent.py`, `health_monitor.py`, `__init__.py`, `tests/` |
| `agents/sigma/AGENTS.md` | Sigma Agent CI gating and governed inference routing | `sigma_agent.py`, `ci_enforcer.py`, `__init__.py`, `tests/` |

*(Other sub-agent packages are leaf modules without child DOX for now.)*
