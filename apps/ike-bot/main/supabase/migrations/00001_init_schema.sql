-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create beneficiaries table
CREATE TABLE IF NOT EXISTS beneficiaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    ssn_last_four CHAR(4),
    date_of_birth DATE,
    relationship VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create credit_disputes table
CREATE TABLE IF NOT EXISTS credit_disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    creditor_name VARCHAR(200) NOT NULL,
    account_number VARCHAR(100),
    dispute_reason TEXT NOT NULL,
    dispute_type VARCHAR(50) NOT NULL CHECK (dispute_type IN ('identity_theft', 'not_mine', 'inaccurate', 'duplicate', 'paid', 'other')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'investigating', 'resolved', 'rejected')),
    amount_disputed DECIMAL(10, 2),
    date_submitted DATE,
    date_resolved DATE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create billing_events table
CREATE TABLE IF NOT EXISTS billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID REFERENCES beneficiaries(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL,
    stripe_event_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create enforcement_packets table
CREATE TABLE IF NOT EXISTS enforcement_packets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    packet_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'sent', 'completed', 'failed')),
    target_agency VARCHAR(200),
    documents JSONB,
    tracking_number VARCHAR(100),
    date_sent DATE,
    date_completed DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create agent_logs table
CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id UUID NOT NULL,
    correlation_id UUID,
    level VARCHAR(20) NOT NULL CHECK (level IN ('debug', 'info', 'warn', 'error', 'fatal')),
    message TEXT NOT NULL,
    action VARCHAR(100),
    user_id UUID,
    beneficiary_id UUID REFERENCES beneficiaries(id) ON DELETE SET NULL,
    request_method VARCHAR(10),
    request_path TEXT,
    response_status INTEGER,
    duration_ms INTEGER,
    metadata JSONB,
    error_stack TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_beneficiaries_email ON beneficiaries(email);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_created_at ON beneficiaries(created_at);

CREATE INDEX IF NOT EXISTS idx_credit_disputes_beneficiary_id ON credit_disputes(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_credit_disputes_status ON credit_disputes(status);
CREATE INDEX IF NOT EXISTS idx_credit_disputes_created_at ON credit_disputes(created_at);

CREATE INDEX IF NOT EXISTS idx_billing_events_beneficiary_id ON billing_events(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_billing_events_event_type ON billing_events(event_type);
CREATE INDEX IF NOT EXISTS idx_billing_events_created_at ON billing_events(created_at);

CREATE INDEX IF NOT EXISTS idx_enforcement_packets_beneficiary_id ON enforcement_packets(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_enforcement_packets_status ON enforcement_packets(status);
CREATE INDEX IF NOT EXISTS idx_enforcement_packets_created_at ON enforcement_packets(created_at);

CREATE INDEX IF NOT EXISTS idx_agent_logs_trace_id ON agent_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_correlation_id ON agent_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_level ON agent_logs(level);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at columns
CREATE TRIGGER update_beneficiaries_updated_at BEFORE UPDATE ON beneficiaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_credit_disputes_updated_at BEFORE UPDATE ON credit_disputes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_enforcement_packets_updated_at BEFORE UPDATE ON enforcement_packets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
