-- UniVerse Agent Communication System Database Migrations
-- Phase 2 Swarm 1: Message Bus, Hive Mind, and Skill Management

-- ============================================
-- Agent Messages Table
-- ============================================

CREATE TABLE IF NOT EXISTS agent_messages (
    id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK(message_type IN (
        'request', 'response', 'notification', 'skill_share', 
        'knowledge_update', 'failure_report', 'success_report', 'urgent'
    )),
    priority TEXT NOT NULL CHECK(priority IN ('low', 'normal', 'high', 'critical')),
    content TEXT NOT NULL,  -- JSON
    encrypted BOOLEAN DEFAULT 0,
    signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    requires_response BOOLEAN DEFAULT 0,
    response_timeout INTEGER DEFAULT 30,
    delivery_status TEXT DEFAULT 'pending' CHECK(delivery_status IN ('pending', 'delivered', 'failed', 'recovered')),
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_sender_recipient ON agent_messages(sender_id, recipient_id);
CREATE INDEX IF NOT EXISTS idx_message_type ON agent_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_priority ON agent_messages(priority);
CREATE INDEX IF NOT EXISTS idx_delivery_status ON agent_messages(delivery_status);
CREATE INDEX IF NOT EXISTS idx_created_at ON agent_messages(created_at);

-- ============================================
-- Skills Table
-- ============================================

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'general',
    status TEXT NOT NULL CHECK(status IN ('draft', 'active', 'deprecated', 'archived', 'failed')),
    success_rate REAL DEFAULT 0.0,
    failure_rate REAL DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_execution_time_ms REAL DEFAULT 0.0,
    parameters TEXT,  -- JSON
    tags TEXT,  -- JSON array
    checksum TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skill_status ON skills(status);
CREATE INDEX IF NOT EXISTS idx_agent_id ON skills(agent_id);
CREATE INDEX IF NOT EXISTS idx_skill_category ON skills(category);

-- ============================================
-- Skill Dependencies Table
-- ============================================

CREATE TABLE IF NOT EXISTS skill_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    min_version INTEGER DEFAULT 1,
    required BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE INDEX IF NOT EXISTS idx_skill_depends ON skill_dependencies(skill_id);
CREATE INDEX IF NOT EXISTS idx_depends_on ON skill_dependencies(depends_on);

-- ============================================
-- Learning Sessions Table
-- ============================================

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    iterations INTEGER DEFAULT 10,
    success_rate REAL DEFAULT 0.0,
    completed BOOLEAN DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    feedback TEXT,
    performance_score REAL DEFAULT 0.0,
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE INDEX IF NOT EXISTS idx_learner_id ON learning_sessions(learner_id);
CREATE INDEX IF NOT EXISTS idx_learning_skill_id ON learning_sessions(skill_id);
CREATE INDEX IF NOT EXISTS idx_session_status ON learning_sessions(completed);

-- ============================================
-- Knowledge Base Table
-- ============================================

CREATE TABLE IF NOT EXISTS knowledge_base (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,  -- JSON
    source_agent TEXT NOT NULL,
    scope TEXT DEFAULT 'public' CHECK(scope IN ('public', 'team', 'private')),
    category TEXT,
    tags TEXT,  -- JSON array
    relevance_score REAL DEFAULT 0.0,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_key ON knowledge_base(key);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_base(source_agent);
CREATE INDEX IF NOT EXISTS idx_knowledge_scope ON knowledge_base(scope);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_base(category);

-- ============================================
-- Message Bus Metrics Table
-- ============================================

CREATE TABLE IF NOT EXISTS message_bus_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_sent INTEGER DEFAULT 0,
    total_received INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    total_recovered INTEGER DEFAULT 0,
    avg_latency_ms REAL DEFAULT 0.0,
    throughput_msgs_per_sec REAL DEFAULT 0.0,
    queue_size INTEGER DEFAULT 0,
    dead_letter_count INTEGER DEFAULT 0,
    encryption_enabled BOOLEAN DEFAULT 0,
    active_agents INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON message_bus_metrics(timestamp);

-- ============================================
-- Agent Performance Metrics Table
-- ============================================

CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, metric_name, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics ON agent_performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_metric_name ON agent_performance_metrics(metric_name);

-- ============================================
-- Hive Mind State Table
-- ============================================

CREATE TABLE IF NOT EXISTS hive_mind_state (
    id TEXT PRIMARY KEY DEFAULT '1',  -- Singleton
    shared_knowledge_count INTEGER DEFAULT 0,
    learned_skills_count INTEGER DEFAULT 0,
    learning_sessions_count INTEGER DEFAULT 0,
    performance_metrics_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state_snapshot TEXT  -- JSON backup
);

-- ============================================
-- Dead Letter Queue Table
-- ============================================

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    content TEXT NOT NULL,
    reason TEXT,
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recovery_attempts INTEGER DEFAULT 0,
    last_recovery_attempt TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dlq_failed_at ON dead_letter_queue(failed_at);
CREATE INDEX IF NOT EXISTS idx_dlq_reason ON dead_letter_queue(reason);

-- ============================================
-- Initialization Script
-- ============================================

-- Insert initial hive mind state
INSERT OR IGNORE INTO hive_mind_state (id) VALUES ('1');

-- Create function to update hive mind counters
-- (This would be application-level in most systems)

-- ============================================
-- Views for Common Queries
-- ============================================

-- View: Recent messages by priority
CREATE VIEW IF NOT EXISTS recent_messages_by_priority AS
SELECT 
    id,
    sender_id,
    recipient_id,
    message_type,
    priority,
    created_at,
    delivery_status
FROM agent_messages
ORDER BY 
    CASE priority 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'normal' THEN 3
        WHEN 'low' THEN 4
    END,
    created_at DESC;

-- View: Skill usage statistics
CREATE VIEW IF NOT EXISTS skill_usage_stats AS
SELECT 
    id,
    name,
    version,
    agent_id,
    status,
    success_rate,
    usage_count,
    failure_count,
    avg_execution_time_ms,
    created_at,
    last_used_at
FROM skills
WHERE status = 'active'
ORDER BY usage_count DESC;

-- View: Active learning sessions
CREATE VIEW IF NOT EXISTS active_learning_sessions AS
SELECT 
    id,
    learner_id,
    skill_id,
    iterations,
    success_rate,
    started_at,
    performance_score
FROM learning_sessions
WHERE completed = 0
ORDER BY started_at DESC;

-- View: Message delivery summary
CREATE VIEW IF NOT EXISTS message_delivery_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_messages,
    SUM(CASE WHEN delivery_status = 'delivered' THEN 1 ELSE 0 END) as delivered,
    SUM(CASE WHEN delivery_status = 'failed' THEN 1 ELSE 0 END) as failed,
    SUM(CASE WHEN delivery_status = 'recovered' THEN 1 ELSE 0 END) as recovered
FROM agent_messages
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- View: Top performing skills
CREATE VIEW IF NOT EXISTS top_performing_skills AS
SELECT 
    name,
    version,
    agent_id,
    success_rate,
    usage_count,
    avg_execution_time_ms,
    category
FROM skills
WHERE status = 'active'
ORDER BY success_rate DESC, usage_count DESC
LIMIT 50;
