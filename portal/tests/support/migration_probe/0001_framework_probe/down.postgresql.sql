-- DOWN migration for 0001_framework_probe (PostgreSQL dialect).
DROP INDEX IF EXISTS ix_migration_framework_probe_label;
DROP TABLE IF EXISTS migration_framework_probe
