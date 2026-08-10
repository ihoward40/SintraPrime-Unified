"""R3 canonical schema baseline

Establishes the complete, authoritative SintraPrime Portal database schema from
a zero state.  This is the single migration that represents the full schema
history prior to the R3 migration authority recovery.

All existing raw-SQL migration files are executed in canonical dependency order.
Where SQL files contain valid schema logic (RLS policies, triggers, functions,
indexes, constraints, role grants), that logic is preserved verbatim rather than
re-expressed in SQLAlchemy's migration DSL.

Revision ID: a1b2c3d4e5f6
Revises: None (first revision)
Create Date: 2026-08-10

Covers:
  - portal/migrations/portal_schema.sql            (core portal schema, 25 tables)
  - portal/migrations/add_evidence_snapshots.sql   (evidence_snapshots)
  - portal/migrations/add_audit_records.sql        (audit_records + immutability trigger)
  - portal/migrations/add_legal_authority_rules.sql (legal_authorities, jurisdiction_rules, professional_reviews)
  - portal/migrations/add_voice_command_ledger.sql  (voice_commands, events, receipts)
  - portal/migrations/add_mission_control_command_ledger.sql (mc_commands, events, receipts)
  - portal/migrations/add_mission_control_run_control_projection.sql (mc_run_controls, events)
  - portal/migrations/add_matter_intelligence.sql   (matter_* tables x9)
  - portal/migrations/add_deadline_evidence_intelligence.sql (matter_deadlines, evidence x5)
  - portal/migrations/add_permissions_rbac.sql      (permissions, role_permissions, user_permissions)
  - portal/migrations/add_blackstone_evidence_ledger.sql (evidence_ledger, blackstone_evaluations + RLS)
  - portal/migrations/add_mission_control_outbox.sql (mission_control_outbox + RLS)
  - portal/migrations/runtime_schema_baseline.sql   (agents, swarms, skills, knowledge_entries,
                                                     execution_history, sessions + the runtime messages/users)
  - portal/migrations/runtime_schema_integrity_2026_07_27.sql (CHECK constraints, NOT NULL hardening)

Intentional SQL-only tables (no ORM model, authoritative by design):
  agents, swarms, skills, knowledge_entries, execution_history, sessions

R1 security preservation:
  The runtime role (sintraprime_app) is not created here — it is created by the
  infrastructure provisioning layer (Terraform / init scripts) before migrations
  run.  This migration does not ALTER or GRANT ownership of any table to the
  runtime role, preserving the R1 boundary:
    admin/migration role = schema owner / privileged provisioning
    sintraprime_app      = runtime NOSUPERUSER NOBYPASSRLS role
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None

# ── Canonical SQL migration sequence ──────────────────────────────────────────
# Dependency order: every file may only reference tables defined in earlier files.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SQL_SEQUENCE = (
    "portal/migrations/portal_schema.sql",
    "portal/migrations/add_evidence_snapshots.sql",
    "portal/migrations/add_audit_records.sql",
    "portal/migrations/add_legal_authority_rules.sql",
    "portal/migrations/add_voice_command_ledger.sql",
    "portal/migrations/add_mission_control_command_ledger.sql",
    "portal/migrations/add_mission_control_run_control_projection.sql",
    "portal/migrations/add_matter_intelligence.sql",
    "portal/migrations/add_deadline_evidence_intelligence.sql",
    "portal/migrations/add_permissions_rbac.sql",
    "portal/migrations/add_blackstone_evidence_ledger.sql",
    "portal/migrations/add_mission_control_outbox.sql",
    "portal/migrations/runtime_schema_baseline.sql",
    "portal/migrations/runtime_schema_integrity_2026_07_27.sql",
)


def upgrade() -> None:
    """Apply the canonical schema baseline by executing SQL migration files in order."""
    for relative_path in _SQL_SEQUENCE:
        sql = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
        # Execute each migration file as a single batch.
        # IF NOT EXISTS guards in the SQL ensure idempotency for fresh databases.
        op.execute(sql)  # type: ignore[arg-type]


def downgrade() -> None:
    """Downgrade is intentionally NOT supported for the canonical baseline.

    Rolling back the full schema baseline would drop all data.  Production
    databases should be restored from backups, not downgraded via Alembic.

    For disposable test databases, drop and recreate the schema instead.
    """
    raise NotImplementedError(
        "Downgrade of the R3 canonical baseline is not supported. "
        "Restore from a backup or recreate the schema from scratch."
    )
