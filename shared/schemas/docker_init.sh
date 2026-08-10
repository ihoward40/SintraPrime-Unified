#!/bin/bash
# =============================================================================
# Docker PostgreSQL initialization script — R3-J canonical bootstrap
#
# Executes the full canonical migration sequence so the Docker database
# matches the same schema as CI, production-like, and test environments.
#
# This script is mounted at:
#   /docker-entrypoint-initdb.d/01-canonical-schema.sh
#
# The MIGRATION_DIR is relative to the repository root, which is mounted
# inside the container as /migrations (see docker-compose.yml).
#
# R1 security preservation:
#   sintraprime_app is the runtime role provisioned by the entrypoint.
#   The app role must not own tables; the provisioning user (POSTGRES_USER)
#   owns everything and grants SELECT/INSERT/UPDATE/DELETE to the app role.
# =============================================================================

set -euo pipefail

MIGRATION_DIR="/migrations/portal/migrations"
PSQL_CMD=(psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --single-transaction)

run_migration() {
    local file="$1"
    echo "[docker-init] applying: $file"
    "${PSQL_CMD[@]}" --file "$file"
}

# Canonical migration sequence — must match:
#   portal/scripts/postgresql_bootstrap.py:MIGRATION_SEQUENCE
#   portal/alembic/versions/a1b2c3d4e5f6_r3_canonical_baseline.py
run_migration "${MIGRATION_DIR}/portal_schema.sql"
run_migration "${MIGRATION_DIR}/add_evidence_snapshots.sql"
run_migration "${MIGRATION_DIR}/add_audit_records.sql"
run_migration "${MIGRATION_DIR}/add_legal_authority_rules.sql"
run_migration "${MIGRATION_DIR}/add_voice_command_ledger.sql"
run_migration "${MIGRATION_DIR}/add_mission_control_command_ledger.sql"
run_migration "${MIGRATION_DIR}/add_mission_control_run_control_projection.sql"
run_migration "${MIGRATION_DIR}/add_matter_intelligence.sql"
run_migration "${MIGRATION_DIR}/add_deadline_evidence_intelligence.sql"
run_migration "${MIGRATION_DIR}/add_permissions_rbac.sql"
run_migration "${MIGRATION_DIR}/add_blackstone_evidence_ledger.sql"
run_migration "${MIGRATION_DIR}/add_mission_control_outbox.sql"
run_migration "${MIGRATION_DIR}/runtime_schema_baseline.sql"
run_migration "${MIGRATION_DIR}/runtime_schema_integrity_2026_07_27.sql"

# =============================================================================
# Runtime role grants (R1 security preservation)
#
# sintraprime_app = runtime NOSUPERUSER NOBYPASSRLS role.
# This block is idempotent: DO blocks and IF NOT EXISTS guards are used.
# =============================================================================

"${PSQL_CMD[@]}" <<'EOSQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sintraprime_app') THEN
        CREATE ROLE sintraprime_app
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOBYPASSRLS
            LOGIN;
        RAISE NOTICE 'Created role sintraprime_app';
    END IF;
END
$$;

-- Grant runtime access on all current and future tables to the app role.
-- The app role reads and writes data; it does NOT own schema objects.
GRANT CONNECT ON DATABASE :POSTGRES_DB TO sintraprime_app;
GRANT USAGE ON SCHEMA public TO sintraprime_app;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public TO sintraprime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sintraprime_app;
EOSQL

echo "[docker-init] canonical schema bootstrap complete."
