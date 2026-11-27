# orchestration — Runtime Orchestration

## Purpose

Owns the standalone orchestration runtime: durable workflows, A2A messaging, governed agent commons persistence, supervisor delegation, and the standalone FastAPI orchestration API.

## Ownership

- `a2a_protocol.py`, `durable_execution.py`, `langgraph_engine.py`, `orchestration_api.py`
- Agent Commons runtime modules and persistence under `orchestration/`
- Orchestration-specific tests under `orchestration/tests/`
- `ORCHESTRATION.md`

## Local Contracts

- Durable workflow behavior must remain restart-safe for file-backed SQLite stores.
- Agent Commons persistence must enforce tenant scope on reads and writes and preserve append-only task lifecycle events.
- Supervisor flows may recommend and coordinate work, but must stop for owner approval on material disagreement or governed decision gates.
- Adapter contracts must expose `health()`, `capabilities()`, `invoke(task, context)`, `cancel(run_id)`, and `stream_events(run_id)`.
- Stored traces must keep externally observable messages, evidence, approvals, and concise rationale only; never hidden chain-of-thought.

## Work Guidance

- Prefer deterministic mock behavior for tests and default runtime paths unless live-provider wiring is explicitly configured.
- Keep A2A message envelopes and stored thread messages correlated by task/thread/run metadata.
- Preserve compatibility with existing orchestration workflow and A2A tests when extending the API.

## Verification

- Run `python -m pytest orchestration/tests/test_orchestration.py -q` after changing the standalone orchestration stack.
- Run focused orchestration tests for any new commons or supervisor behavior.
- Run Ruff on changed orchestration files before closeout.

## Child DOX Index

*(None — modules and tests in this subtree are currently leaf work items.)*
