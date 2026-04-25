-- Discord Integration Database Schema for SintraPrime UniVerse
-- Version 1.0.0
-- Date: April 21, 2026

-- ============================================================================
-- GUILD/SERVER CONFIGURATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_servers (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) UNIQUE NOT NULL,
    guild_name VARCHAR(255) NOT NULL,
    prefix VARCHAR(10) DEFAULT '!',
    enabled_features JSONB DEFAULT '{"prefix_commands": true, "slash_commands": true, "reactions": true, "auto_logs": true}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS discord_channels (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    channel_id VARCHAR(30) NOT NULL,
    channel_name VARCHAR(255),
    channel_type VARCHAR(30),  -- control, logs, alerts, results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_channel (guild_id, channel_type),
    INDEX idx_guild_id (guild_id),
    INDEX idx_channel_type (channel_type)
);

-- ============================================================================
-- ROLE-BASED PERMISSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_roles (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    role_id VARCHAR(30) NOT NULL,
    role_name VARCHAR(255),
    permission_level INT NOT NULL,  -- 0=guest, 1=user, 2=mod, 3=admin, 4=owner
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_role (guild_id, role_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_permission_level (permission_level)
);

CREATE TABLE IF NOT EXISTS discord_user_permissions (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    user_id VARCHAR(30) NOT NULL,
    permission_level INT NOT NULL,
    set_by VARCHAR(30),
    set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_user (guild_id, user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_user_id (user_id)
);

-- ============================================================================
-- COMMAND EXECUTION HISTORY
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_commands (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    user_id VARCHAR(30) NOT NULL,
    username VARCHAR(255),
    command VARCHAR(50) NOT NULL,  -- agent, swarm, skill, etc
    subcommand VARCHAR(50),
    args TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    execution_time_ms INT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    INDEX idx_guild_id (guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_command (command),
    INDEX idx_executed_at (executed_at)
);

-- ============================================================================
-- AGENT INTEGRATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_agents (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    role VARCHAR(50),
    created_by VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    status VARCHAR(20) DEFAULT 'idle',  -- active, idle, offline, error
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_agent (guild_id, agent_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS discord_agent_stats (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    guild_id VARCHAR(30) NOT NULL,
    tasks_executed INT DEFAULT 0,
    tasks_successful INT DEFAULT 0,
    tasks_failed INT DEFAULT 0,
    total_execution_time_s FLOAT DEFAULT 0,
    avg_execution_time_ms INT,
    success_rate DECIMAL(5,2) DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_agent (guild_id, agent_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_success_rate (success_rate)
);

-- ============================================================================
-- SWARM INTEGRATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_swarms (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    swarm_id VARCHAR(255) NOT NULL,
    swarm_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_guild_swarm (guild_id, swarm_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS discord_swarm_agents (
    id SERIAL PRIMARY KEY,
    swarm_id VARCHAR(255) NOT NULL,
    guild_id VARCHAR(30) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (swarm_id) REFERENCES discord_swarms(swarm_id) ON DELETE CASCADE,
    UNIQUE KEY unique_swarm_agent (swarm_id, agent_id),
    INDEX idx_swarm_id (swarm_id),
    INDEX idx_agent_id (agent_id)
);

-- ============================================================================
-- TASK TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_tasks (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(30) NOT NULL,
    agent_id VARCHAR(255),
    command VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT,
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    UNIQUE KEY unique_task (guild_id, task_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- GUILD STATISTICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_guild_stats (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL UNIQUE,
    commands_executed INT DEFAULT 0,
    agents_spawned INT DEFAULT 0,
    swarms_created INT DEFAULT 0,
    tasks_created INT DEFAULT 0,
    tasks_successful INT DEFAULT 0,
    tasks_failed INT DEFAULT 0,
    total_uptime_hours FLOAT DEFAULT 0,
    last_activity TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    INDEX idx_guild_id (guild_id),
    INDEX idx_last_activity (last_activity)
);

-- ============================================================================
-- INTERACTIONS LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_interactions (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30) NOT NULL,
    user_id VARCHAR(30) NOT NULL,
    interaction_type VARCHAR(50),  -- button, select, modal, reaction, etc
    interaction_data JSONB,
    handled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE CASCADE,
    INDEX idx_guild_id (guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_interaction_type (interaction_type),
    INDEX idx_handled_at (handled_at)
);

-- ============================================================================
-- ERROR TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_errors (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(30),
    user_id VARCHAR(30),
    error_type VARCHAR(100),
    error_message TEXT,
    traceback TEXT,
    context JSONB,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES discord_servers(guild_id) ON DELETE SET NULL,
    INDEX idx_guild_id (guild_id),
    INDEX idx_error_type (error_type),
    INDEX idx_reported_at (reported_at)
);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

CREATE VIEW discord_active_servers AS
SELECT 
    ds.guild_id,
    ds.guild_name,
    COUNT(DISTINCT dc.user_id) as unique_users,
    COUNT(dc.id) as total_commands,
    MAX(dc.executed_at) as last_activity
FROM discord_servers ds
LEFT JOIN discord_commands dc ON ds.guild_id = dc.guild_id
WHERE dc.executed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY ds.guild_id, ds.guild_name;

CREATE VIEW discord_top_agents AS
SELECT 
    agent_id,
    guild_id,
    tasks_executed,
    tasks_successful,
    tasks_failed,
    success_rate,
    last_updated
FROM discord_agent_stats
ORDER BY success_rate DESC, tasks_executed DESC
LIMIT 100;

CREATE VIEW discord_command_stats AS
SELECT 
    command,
    COUNT(*) as total_executions,
    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(execution_time_ms), 2) as avg_execution_ms,
    MAX(execution_time_ms) as max_execution_ms
FROM discord_commands
WHERE executed_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY command;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_discord_servers_updated ON discord_servers(updated_at DESC);
CREATE INDEX idx_discord_commands_guild_time ON discord_commands(guild_id, executed_at DESC);
CREATE INDEX idx_discord_agents_status_guild ON discord_agents(status, guild_id);
CREATE INDEX idx_discord_tasks_status_guild ON discord_tasks(status, guild_id);

-- ============================================================================
-- INITIALIZATION PROCEDURES
-- ============================================================================

-- Trigger to update discord_servers.updated_at timestamp
CREATE TRIGGER discord_servers_update_timestamp
BEFORE UPDATE ON discord_servers
FOR EACH ROW
SET NEW.updated_at = CURRENT_TIMESTAMP;

CREATE TRIGGER discord_channels_update_timestamp
BEFORE UPDATE ON discord_channels
FOR EACH ROW
SET NEW.created_at = CURRENT_TIMESTAMP;

CREATE TRIGGER discord_agents_update_timestamp
BEFORE UPDATE ON discord_agents
FOR EACH ROW
SET NEW.updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================

CREATE TABLE IF NOT EXISTS discord_schema_version (
    version VARCHAR(20) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO discord_schema_version (version, description) 
VALUES ('1.0.0', 'Initial Discord integration schema');
