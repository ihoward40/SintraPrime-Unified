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

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

*(None — each sub-agent package is a leaf module for now.)*
