-- Framework probe migration (test fixture only).
-- Creates a neutral table used to prove upgrade/downgrade of the migration
-- runner. This is NOT an AI-OS table and is never applied to a real database.
CREATE TABLE migration_framework_probe (
    id VARCHAR(36) PRIMARY KEY,
    label VARCHAR(64) NOT NULL
);
CREATE INDEX ix_migration_framework_probe_label ON migration_framework_probe (label)
