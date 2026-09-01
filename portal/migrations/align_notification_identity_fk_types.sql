-- =============================================================================
-- Align Notification FK types to match canonical String(36) identity columns.
-- Issue #291: Notification.tenant_id and Notification.user_id were UUID(as_uuid=True)
-- while Tenant.id and User.id are String(36) in ORM metadata. This caused
-- Base.metadata.create_all() to fail on PostgreSQL due to type mismatch.
--
-- This migration is idempotent: it only alters columns if they are currently UUID.
-- For raw-SQL bootstrapped databases (where all columns are UUID), this is a no-op
-- because the ALTER COLUMN ... TYPE VARCHAR(36) using id::text is safe.
-- =============================================================================

-- Align notifications.tenant_id: UUID -> VARCHAR(36)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notifications'
          AND column_name = 'tenant_id'
          AND data_type = 'uuid'
    ) THEN
        ALTER TABLE notifications ALTER COLUMN tenant_id TYPE VARCHAR(36) USING tenant_id::text;
    END IF;
END $$;

-- Align notifications.user_id: UUID -> VARCHAR(36)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notifications'
          AND column_name = 'user_id'
          AND data_type = 'uuid'
    ) THEN
        ALTER TABLE notifications ALTER COLUMN user_id TYPE VARCHAR(36) USING user_id::text;
    END IF;
END $$;