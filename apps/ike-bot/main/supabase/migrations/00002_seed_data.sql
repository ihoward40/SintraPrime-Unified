-- Seed data for beneficiaries
INSERT INTO beneficiaries (first_name, last_name, email, phone, relationship)
VALUES
    ('John', 'Doe', 'john.doe@example.com', '555-0100', 'Primary'),
    ('Jane', 'Smith', 'jane.smith@example.com', '555-0101', 'Spouse'),
    ('Robert', 'Johnson', 'robert.j@example.com', '555-0102', 'Child')
ON CONFLICT (id) DO NOTHING;

-- Seed data for credit_disputes (references beneficiaries)
-- Note: This assumes beneficiaries were just created. In production, you'd use actual IDs.
INSERT INTO credit_disputes (beneficiary_id, creditor_name, account_number, dispute_reason, dispute_type, status)
SELECT 
    id,
    'Example Credit Corp',
    'ACC-' || substr(md5(random()::text), 0, 10),
    'This account does not belong to me',
    'not_mine',
    'pending'
FROM beneficiaries
LIMIT 1
ON CONFLICT (id) DO NOTHING;

-- Seed data for agent_logs (example log entries)
INSERT INTO agent_logs (trace_id, level, message, action, request_method, request_path, response_status)
VALUES
    (uuid_generate_v4(), 'info', 'Application started', 'startup', NULL, NULL, NULL),
    (uuid_generate_v4(), 'info', 'Database connection established', 'db_connect', NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;
