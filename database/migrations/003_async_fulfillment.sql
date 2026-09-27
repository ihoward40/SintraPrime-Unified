CREATE TABLE IF NOT EXISTS async_jobs (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    callback_url TEXT,
    run_after TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_attempts (
    attempt_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES async_jobs(task_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    screenshots TEXT NOT NULL DEFAULT '[]',
    browser_log TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS filing_records (
    filing_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES async_jobs(task_id) ON DELETE CASCADE,
    document_hash TEXT NOT NULL,
    filing_status TEXT NOT NULL,
    court_receipt TEXT,
    filed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_async_jobs_status ON async_jobs(status);
CREATE INDEX IF NOT EXISTS idx_async_jobs_ready ON async_jobs(status, run_after, created_at);
CREATE INDEX IF NOT EXISTS idx_execution_attempts_job_id ON execution_attempts(job_id);
CREATE INDEX IF NOT EXISTS idx_filing_records_document_hash ON filing_records(document_hash);
CREATE INDEX IF NOT EXISTS idx_filing_records_job_id ON filing_records(job_id);
