-- =============================================================================
-- Runtime Schema Integrity Migration — DOWN migration
-- Reverts all changes made by runtime_schema_integrity_2026_07_27.sql
-- =============================================================================

-- Indexes
DROP INDEX IF EXISTS idx_knowledge_entries_source;
DROP INDEX IF EXISTS idx_users_is_active;
DROP INDEX IF EXISTS idx_sessions_user_id;
DROP INDEX IF EXISTS idx_execution_history_swarm_id;
DROP INDEX IF EXISTS idx_execution_history_agent_id;
DROP INDEX IF EXISTS idx_messages_recipient_id;
DROP INDEX IF EXISTS idx_messages_sender_id;

-- NOT NULL reversions
ALTER TABLE users ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE users ALTER COLUMN is_active DROP NOT NULL;
ALTER TABLE swarms ALTER COLUMN updated_at DROP NOT NULL;
ALTER TABLE swarms ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE swarms ALTER COLUMN agent_ids DROP NOT NULL;
ALTER TABLE swarms ALTER COLUMN config DROP NOT NULL;
ALTER TABLE swarms ALTER COLUMN status DROP NOT NULL;
ALTER TABLE skills ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE skills ALTER COLUMN enabled DROP NOT NULL;
ALTER TABLE skills ALTER COLUMN version DROP NOT NULL;
ALTER TABLE skills ALTER COLUMN parameters DROP NOT NULL;
ALTER TABLE sessions ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE messages ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE messages ALTER COLUMN processed DROP NOT NULL;
ALTER TABLE messages ALTER COLUMN priority DROP NOT NULL;
ALTER TABLE knowledge_entries ALTER COLUMN updated_at DROP NOT NULL;
ALTER TABLE knowledge_entries ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE knowledge_entries ALTER COLUMN confidence DROP NOT NULL;
ALTER TABLE execution_history ALTER COLUMN started_at DROP NOT NULL;
ALTER TABLE execution_history ALTER COLUMN status DROP NOT NULL;
ALTER TABLE agents ALTER COLUMN updated_at DROP NOT NULL;
ALTER TABLE agents ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE agents ALTER COLUMN config DROP NOT NULL;
ALTER TABLE agents ALTER COLUMN status DROP NOT NULL;

-- CHECK constraints
ALTER TABLE knowledge_entries DROP CONSTRAINT IF EXISTS ck_knowledge_entries_confidence;
ALTER TABLE messages DROP CONSTRAINT IF EXISTS ck_messages_priority;
ALTER TABLE swarms DROP CONSTRAINT IF EXISTS ck_swarms_status;
ALTER TABLE execution_history DROP CONSTRAINT IF EXISTS ck_execution_history_status;
ALTER TABLE agents DROP CONSTRAINT IF EXISTS ck_agents_status;
