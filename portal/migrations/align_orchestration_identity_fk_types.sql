-- Align orchestration references with the deployed tenant/user parent types.
--
-- The repository supports two PostgreSQL creation paths: the authoritative raw
-- SQL bootstrap uses native UUID identity columns, while the ORM create_all test
-- path uses VARCHAR(36).  This migration derives each child type from its actual
-- parent instead of coercing an existing deployment to one representation.

DO $migration$
DECLARE
    mapping RECORD;
    child_rel REGCLASS;
    parent_rel REGCLASS;
    child_attnum SMALLINT;
    parent_type TEXT;
    child_type TEXT;
    fk_name TEXT;
BEGIN
    FOR mapping IN
        SELECT *
        FROM (VALUES
            ('orchestration_runs', 'tenant_id', 'tenants', 'id', 'NO ACTION'),
            ('orchestration_runs', 'created_by', 'users', 'id', 'NO ACTION'),
            ('orchestration_approval_requests', 'principal_id', 'users', 'id', 'NO ACTION'),
            ('orchestration_linkages', 'tenant_id', 'tenants', 'id', 'NO ACTION'),
            ('orchestration_principal_authorities', 'tenant_id', 'tenants', 'id', 'NO ACTION'),
            ('orchestration_principal_authorities', 'user_id', 'users', 'id', 'NO ACTION'),
            ('memory_vault', 'tenant_id', 'tenants', 'id', 'CASCADE')
        ) AS identity_fk(child_table, child_column, parent_table, parent_column, delete_action)
    LOOP
        child_rel := to_regclass('public.' || mapping.child_table);
        parent_rel := to_regclass('public.' || mapping.parent_table);

        IF child_rel IS NULL OR parent_rel IS NULL THEN
            CONTINUE;
        END IF;

        SELECT a.attnum, format_type(a.atttypid, a.atttypmod)
          INTO child_attnum, child_type
          FROM pg_attribute a
         WHERE a.attrelid = child_rel
           AND a.attname = mapping.child_column
           AND NOT a.attisdropped;

        SELECT format_type(a.atttypid, a.atttypmod)
          INTO parent_type
          FROM pg_attribute a
         WHERE a.attrelid = parent_rel
           AND a.attname = mapping.parent_column
           AND NOT a.attisdropped;

        IF child_attnum IS NULL OR parent_type IS NULL THEN
            CONTINUE;
        END IF;

        IF child_type <> parent_type THEN
            FOR fk_name IN
                SELECT c.conname
                  FROM pg_constraint c
                 WHERE c.conrelid = child_rel
                   AND c.contype = 'f'
                   AND child_attnum = ANY(c.conkey)
            LOOP
                EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', child_rel, fk_name);
            END LOOP;

            IF parent_type = 'uuid' THEN
                EXECUTE format(
                    'ALTER TABLE %s ALTER COLUMN %I TYPE uuid USING NULLIF(%I::text, '''')::uuid',
                    child_rel,
                    mapping.child_column,
                    mapping.child_column
                );
            ELSIF parent_type = 'character varying(36)' THEN
                EXECUTE format(
                    'ALTER TABLE %s ALTER COLUMN %I TYPE varchar(36) USING %I::text',
                    child_rel,
                    mapping.child_column,
                    mapping.child_column
                );
            ELSE
                RAISE EXCEPTION
                    'unsupported parent identity type %.%: %',
                    mapping.parent_table,
                    mapping.parent_column,
                    parent_type;
            END IF;
        END IF;

        IF NOT EXISTS (
            SELECT 1
              FROM pg_constraint c
             WHERE c.conrelid = child_rel
               AND c.confrelid = parent_rel
               AND c.contype = 'f'
               AND child_attnum = ANY(c.conkey)
        ) THEN
            EXECUTE format(
                'ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %s(%I) ON DELETE %s',
                child_rel,
                mapping.child_table || '_' || mapping.child_column || '_fkey',
                mapping.child_column,
                parent_rel,
                mapping.parent_column,
                mapping.delete_action
            );
        END IF;
    END LOOP;
END
$migration$;

-- RLS comparisons use text-normalized identity values so the policy is valid
-- for both native UUID and VARCHAR(36) parent-authority deployments.
DROP POLICY IF EXISTS orchestration_runs_tenant_isolation ON orchestration_runs;
CREATE POLICY orchestration_runs_tenant_isolation
    ON orchestration_runs
    USING (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''))
    WITH CHECK (tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), ''));

-- DOWN migration notes:
-- This compatibility migration intentionally has no automatic type-reversal.
-- It derives child types from their referenced parents and is therefore
-- idempotent.  Roll back by restoring the prior constraint/policy definitions;
-- do not change column types without first verifying every stored identifier.
