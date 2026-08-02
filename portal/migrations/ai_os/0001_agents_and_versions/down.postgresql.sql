-- DOWN migration for AI-OS 0001_agents_and_versions (PostgreSQL dialect).
-- Drops the deferred foreign key first, then the tables. Indexes owned by a
-- dropped table are removed with it, so they are not dropped separately.
ALTER TABLE ai_os_agents DROP CONSTRAINT IF EXISTS fk_ai_os_agents_current_version;
DROP TABLE IF EXISTS ai_os_agent_versions;
DROP TABLE IF EXISTS ai_os_agents
