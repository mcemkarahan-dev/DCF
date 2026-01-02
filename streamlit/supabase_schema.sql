-- Supabase Schema for DCF Analyzer
-- Run this in the Supabase SQL Editor to create required tables

-- ==================== BATCH JOBS TABLE ====================
-- Stores batch screening jobs for background processing

CREATE TABLE IF NOT EXISTS batch_jobs (
    id SERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    job_name TEXT,
    filters_json TEXT NOT NULL,
    filter_hash BIGINT,
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    total_tickers INTEGER DEFAULT 0,
    processed_tickers INTEGER DEFAULT 0,
    matched_tickers INTEGER DEFAULT 0,
    current_ticker TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created ON batch_jobs(created_at);

-- ==================== ANALYSIS HISTORY TABLE ====================
-- (Already exists if you've been using the app)

CREATE TABLE IF NOT EXISTS analysis_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    run_date TIMESTAMPTZ NOT NULL,
    params_hash BIGINT,
    result_json TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_ticker ON analysis_history(ticker);
CREATE INDEX IF NOT EXISTS idx_analysis_date ON analysis_history(run_date);

-- ==================== CHECKED TICKERS TABLE ====================
-- (Already exists if you've been using the app)

CREATE TABLE IF NOT EXISTS checked_tickers (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    filter_hash BIGINT NOT NULL,
    matched BOOLEAN DEFAULT FALSE,
    checked_at TIMESTAMPTZ NOT NULL,
    UNIQUE(ticker, filter_hash)
);

CREATE INDEX IF NOT EXISTS idx_checked_filter ON checked_tickers(filter_hash);
CREATE INDEX IF NOT EXISTS idx_checked_at ON checked_tickers(checked_at);

-- ==================== ROW LEVEL SECURITY (Optional) ====================
-- Enable RLS if you want to restrict access

-- ALTER TABLE batch_jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analysis_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE checked_tickers ENABLE ROW LEVEL SECURITY;

-- Create policies as needed for your use case
