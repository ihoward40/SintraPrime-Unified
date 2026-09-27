CREATE TABLE IF NOT EXISTS async_jobs (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    payload JSONB NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    callback_url TEXT,
    run_after TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_attempts (
    attempt_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES async_jobs(task_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    screenshots JSONB NOT NULL DEFAULT '[]'::jsonb,
    browser_log JSONB NOT NULL DEFAULT '[]'::jsonb,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS filing_records (
    filing_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES async_jobs(task_id) ON DELETE CASCADE,
    document_hash TEXT NOT NULL,
    filing_status TEXT NOT NULL,
    court_receipt JSONB,
    filed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_async_jobs_status ON async_jobs(status);
CREATE INDEX IF NOT EXISTS idx_execution_attempts_job_id ON execution_attempts(job_id);
CREATE INDEX IF NOT EXISTS idx_filing_records_document_hash ON filing_records(document_hash);
CREATE INDEX IF NOT EXISTS idx_filing_records_job_id ON filing_records(job_id);
