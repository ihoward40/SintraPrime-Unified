"""Apply the authoritative raw-SQL PostgreSQL fresh-bootstrap sequence.

This is a CI verifier/runner for disposable or empty PostgreSQL databases. It is
not an Alembic replacement and does not certify upgrades from unknown schemas.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SEQUENCE = (
    Path("portal/migrations/portal_schema.sql"),
    Path("portal/migrations/add_evidence_snapshots.sql"),
    Path("portal/migrations/add_audit_records.sql"),
    Path("portal/migrations/add_tenant_principal.sql"),
    Path("portal/migrations/add_mission_control_command_ledger.sql"),
    Path("portal/migrations/add_mission_control_mission_runs.sql"),
    Path("portal/migrations/add_mission_control_run_control_projection.sql"),
    Path("portal/migrations/add_mission_control_run_approvals.sql"),
)
EXPECTED_TABLES = (
    "tenants",
    "tenant_principals",
    "roles",
    "users",
    "clients",
    "matters",
    "cases",
    "evidence_snapshots",
    "audit_records",
    "audit_logs",
    "mission_control_commands",
    "mission_control_command_events",
    "mission_control_command_receipts",
    "missions",
    "runs",
    "mission_control_run_controls",
    "mission_control_run_control_events",
    "mission_control_run_approvals",
    "orchestration_runs",
    "orchestration_nodes",
    "orchestration_events",
    "orchestration_approval_requests",
)
