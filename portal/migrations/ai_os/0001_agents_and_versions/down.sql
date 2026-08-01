-- DOWN migration for AI-OS 0001_agents_and_versions.
-- Removes every object created by up.sql. No AI-OS residue may remain.
DROP INDEX ix_ai_os_agent_versions_agent;
DROP TABLE ai_os_agent_versions;
DROP INDEX ix_ai_os_agents_tenant_status;
DROP INDEX ix_ai_os_agents_tenant;
DROP TABLE ai_os_agents
