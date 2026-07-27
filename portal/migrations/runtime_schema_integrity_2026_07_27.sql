-- =============================================================================
-- Runtime Schema Integrity Migration
-- Phase Two — Option C: stabilize live PostgreSQL runtime schema
-- Date: 2026-07-27
-- =============================================================================

-- This migration applies additive integrity improvements to the live 8-table
-- runtime schema (agents, execution_history, knowledge_entries, messages,
-- sessions, skills, swarms, users).  All changes are compatible with an empty
-- or lightly populated database.  The single existing users row satisfies the
-- new NOT NULL constraints because it has values for all affected columns.

-- =============================================================================
-- 1. CHECK constraints (application invariants)
-- =============================================================================

ALTER TABLE agents
    DROP CONSTRAINT IF EXISTS ck_agents_status;
ALTER TABLE agents
    ADD CONSTRAINT ck_agents_status
    CHECK (status IN ('idle', 'active', 'paused', 'stopped', 'failed'));

ALTER TABLE execution_history
    DROP CONSTRAINT IF EXISTS ck_execution_history_status;
ALTER TABLE execution_history
    ADD CONSTRAINT ck_execution_history_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

ALTER TABLE swarms
    DROP CONSTRAINT IF EXISTS ck_swarms_status;
ALTER TABLE swarms
    ADD CONSTRAINT ck_swarms_status
    CHECK (status IN ('initializing', 'active', 'paused', 'dissolved', 'failed'));

ALTER TABLE messages
    DROP CONSTRAINT IF EXISTS ck_messages_priority;
ALTER TABLE messages
    ADD CONSTRAINT ck_messages_priority
    CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'));

ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS ck_knowledge_entries_confidence;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT ck_knowledge_entries_confidence
    CHECK (confidence >= 0.0 AND confidence <= 1.0);

-- =============================================================================
-- 2. NOT NULL enforcement (columns with sensible defaults)
-- =============================================================================

-- agents
ALTER TABLE agents ALTER COLUMN status SET NOT NULL;
ALTER TABLE agents ALTER COLUMN config SET NOT NULL;
ALTER TABLE agents ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE agents ALTER COLUMN updated_at SET NOT NULL;

-- execution_history
ALTER TABLE execution_history ALTER COLUMN status SET NOT NULL;
ALTER TABLE execution_history ALTER COLUMN started_at SET NOT NULL;

-- knowledge_entries
ALTER TABLE knowledge_entries ALTER COLUMN confidence SET NOT NULL;
ALTER TABLE knowledge_entries ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE knowledge_entries ALTER COLUMN updated_at SET NOT NULL;

-- messages
ALTER TABLE messages ALTER COLUMN priority SET NOT NULL;
ALTER TABLE messages ALTER COLUMN processed SET NOT NULL;
ALTER TABLE messages ALTER COLUMN created_at SET NOT NULL;

-- sessions
ALTER TABLE sessions ALTER COLUMN created_at SET NOT NULL;

-- skills
ALTER TABLE skills ALTER COLUMN parameters SET NOT NULL;
ALTER TABLE skills ALTER COLUMN version SET NOT NULL;
ALTER TABLE skills ALTER COLUMN enabled SET NOT NULL;
ALTER TABLE skills ALTER COLUMN created_at SET NOT NULL;

-- swarms
ALTER TABLE swarms ALTER COLUMN status SET NOT NULL;
ALTER TABLE swarms ALTER COLUMN config SET NOT NULL;
ALTER TABLE swarms ALTER COLUMN agent_ids SET NOT NULL;
ALTER TABLE swarms ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE swarms ALTER COLUMN updated_at SET NOT NULL;

-- users
ALTER TABLE users ALTER COLUMN is_active SET NOT NULL;
ALTER TABLE users ALTER COLUMN created_at SET NOT NULL;

-- =============================================================================
-- 3. Indexes for FK and common lookups
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient_id ON messages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_execution_history_agent_id ON execution_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_execution_history_swarm_id ON execution_history(swarm_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source ON knowledge_entries(source);

-- =============================================================================
-- 4. DOWN migration (inline comments — run these statements to reverse)
-- =============================================================================
--
-- Indexes:
--   DROP INDEX IF EXISTS idx_knowledge_entries_source;
--   DROP INDEX IF EXISTS idx_users_is_active;
--   DROP INDEX IF EXISTS idx_sessions_user_id;
--   DROP INDEX IF EXISTS idx_execution_history_swarm_id;
--   DROP INDEX IF EXISTS idx_execution_history_agent_id;
--   DROP INDEX IF EXISTS idx_messages_recipient_id;
--   DROP INDEX IF EXISTS idx_messages_sender_id;
--
-- NOT NULL reversions:
--   ALTER TABLE users ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE users ALTER COLUMN is_active DROP NOT NULL;
--   ALTER TABLE swarms ALTER COLUMN updated_at DROP NOT NULL;
--   ALTER TABLE swarms ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE swarms ALTER COLUMN agent_ids DROP NOT NULL;
--   ALTER TABLE swarms ALTER COLUMN config DROP NOT NULL;
--   ALTER TABLE swarms ALTER COLUMN status DROP NOT NULL;
--   ALTER TABLE skills ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE skills ALTER COLUMN enabled DROP NOT NULL;
--   ALTER TABLE skills ALTER COLUMN version DROP NOT NULL;
--   ALTER TABLE skills ALTER COLUMN parameters DROP NOT NULL;
--   ALTER TABLE sessions ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE messages ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE messages ALTER COLUMN processed DROP NOT NULL;
--   ALTER TABLE messages ALTER COLUMN priority DROP NOT NULL;
--   ALTER TABLE knowledge_entries ALTER COLUMN updated_at DROP NOT NULL;
--   ALTER TABLE knowledge_entries ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE knowledge_entries ALTER COLUMN confidence DROP NOT NULL;
--   ALTER TABLE execution_history ALTER COLUMN started_at DROP NOT NULL;
--   ALTER TABLE execution_history ALTER COLUMN status DROP NOT NULL;
--   ALTER TABLE agents ALTER COLUMN updated_at DROP NOT NULL;
--   ALTER TABLE agents ALTER COLUMN created_at DROP NOT NULL;
--   ALTER TABLE agents ALTER COLUMN config DROP NOT NULL;
--   ALTER TABLE agents ALTER COLUMN status DROP NOT NULL;
--
-- CHECK constraints:
--   ALTER TABLE knowledge_entries DROP CONSTRAINT IF EXISTS ck_knowledge_entries_confidence;
--   ALTER TABLE messages DROP CONSTRAINT IF EXISTS ck_messages_priority;
--   ALTER TABLE swarms DROP CONSTRAINT IF EXISTS ck_swarms_status;
--   ALTER TABLE execution_history DROP CONSTRAINT IF EXISTS ck_execution_history_status;
--   ALTER TABLE agents DROP CONSTRAINT IF EXISTS ck_agents_status;
--
-- =============================================================================
