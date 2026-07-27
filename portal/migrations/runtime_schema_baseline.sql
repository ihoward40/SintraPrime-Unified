-- =============================================================================
-- Runtime Schema Baseline (PostgreSQL)
-- Captured from live sintraprime-postgres container on 2026-07-27.
-- This is the starting state for Phase Two Option C migration tests.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS swarms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'initializing',
    config JSONB DEFAULT '{}',
    agent_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(320) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    code TEXT,
    parameters JSONB DEFAULT '{}',
    version VARCHAR(50) DEFAULT '1.0.0',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(500) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    source VARCHAR(255),
    confidence DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    agent_id UUID REFERENCES agents(id),
    swarm_id UUID REFERENCES swarms(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(100) NOT NULL,
    priority VARCHAR(50) DEFAULT 'NORMAL',
    sender_id UUID,
    recipient_id UUID,
    content JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed a single admin user matching the live container
INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at)
VALUES (
    'c3909dab-fbbf-4470-afaa-1bfe4dab5790'::uuid,
    'admin',
    'admin@sintraprime.local',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'admin',
    TRUE,
    '2026-05-21 21:35:42.397119+00'
)
ON CONFLICT (username) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS idx_execution_history_status ON execution_history(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_key ON knowledge_entries USING gin (key gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_messages_processed ON messages(processed);
CREATE INDEX IF NOT EXISTS idx_swarms_status ON swarms(status);
