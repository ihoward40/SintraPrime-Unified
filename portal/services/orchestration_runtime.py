"""Canonical runtime owner for the durable workflow execution substrate.

This module is execution infrastructure only.  It knows nothing about Principal
identity, approval policy, Mission Control, or RBAC.  Every portal consumer in
one application process obtains the same engine and persistent SQLite store.
Gunicorn's policy is one recovery worker per application process; SQLite's
atomic dispatch lease excludes duplicate ownership across those processes.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from orchestration.durable_execution import DurableWorkflowEngine
from portal.config import get_settings


# One canonical durable engine per application process.
_engine: DurableWorkflowEngine | None = None


@lru_cache(maxsize=1)
def _durable_db_path() -> str:
    """Return the configured persistent durable-execution SQLite path."""
    settings = get_settings()
    configured = settings.DURABLE_WORKFLOW_STORE_PATH
    if configured:
        if configured == ":memory:" and settings.ENVIRONMENT.lower() not in {
            "test",
            "testing",
        }:
            raise RuntimeError("IN_MEMORY_DURABLE_STORE_FORBIDDEN")
        return configured

    app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if app_data:
        return str(Path(app_data) / "SintraPrime" / "durable_workflows.db")
    return str(Path.home() / ".sintraprime" / "durable_workflows.db")


def _ensure_parent_dir(db_path: str) -> None:
    if db_path == ":memory:":
        return
    Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def get_canonical_durable_engine() -> DurableWorkflowEngine:
    """Return the process-wide engine, creating it from portal settings once.

    On first call, also registers the production legal workflow handler so it
    is available for governed Mission Control activation.
    """
    global _engine
    if _engine is None:
        from .legal_workflow_handler import LEGAL_WORKFLOW_TYPE, legal_workflow_handler

        settings = get_settings()
        db_path = _durable_db_path()
        _ensure_parent_dir(db_path)
        _engine = DurableWorkflowEngine(
            db_path=db_path,
            dispatch_lease_seconds=settings.DURABLE_WORKFLOW_DISPATCH_LEASE_SECONDS,
        )
        # Register the first and only production capability.
        _engine.register_workflow(LEGAL_WORKFLOW_TYPE, legal_workflow_handler)
    return _engine


def reset_canonical_durable_engine_for_tests(
    engine: DurableWorkflowEngine | None = None,
) -> DurableWorkflowEngine | None:
    """Replace the process singleton for tests after explicit engine cleanup."""
    global _engine
    _engine = engine
    _durable_db_path.cache_clear()
    return _engine
