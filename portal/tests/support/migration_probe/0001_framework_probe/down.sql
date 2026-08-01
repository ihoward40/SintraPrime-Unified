-- DOWN migration for 0001_framework_probe.
DROP INDEX ix_migration_framework_probe_label;
DROP TABLE migration_framework_probe
