-- Second probe migration: proves ordered, incremental application.
ALTER TABLE migration_framework_probe ADD COLUMN note VARCHAR(255)
