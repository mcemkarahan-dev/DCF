-- Supabase Schema for DCF Analyzer
-- Run this in the Supabase SQL Editor

-- ==================== TICKERS TABLE ====================
-- Pre-populated universe of stocks for fast filtering
-- Refreshed periodically (daily/weekly) via background job

CREATE TABLE IF NOT EXISTS tickers (
    id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT,
    sector TEXT,
    exchange TEXT,
    market_cap BIGINT,
    market_cap_universe TEXT,  -- Mega Cap, Large Cap, Mid Cap, Small Cap, Micro Cap
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickers_ticker ON tickers(ticker);
CREATE INDEX IF NOT EXISTS idx_tickers_sector ON tickers(sector);
CREATE INDEX IF NOT EXISTS idx_tickers_exchange ON tickers(exchange);
CREATE INDEX IF NOT EXISTS idx_tickers_market_cap_universe ON tickers(market_cap_universe);

-- ==================== USER CONFIGURATIONS TABLE ====================
-- Unified settings: DCF params + Filters in one config
-- Cloud-based, accessible from any device

CREATE TABLE IF NOT EXISTS user_configurations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,              -- Future: Supabase Auth UUID, for now: email or temp ID
    config_name TEXT NOT NULL,          -- "My Tech Screener", "Conservative", etc.
    config_json TEXT NOT NULL,          -- { dcf_params: {...}, filters: {...} }
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, config_name)
);

CREATE INDEX IF NOT EXISTS idx_user_configs_user ON user_configurations(user_id);

-- ==================== ANALYSIS HISTORY TABLE ====================
-- DCF analysis results (already exists, keeping for reference)

CREATE TABLE IF NOT EXISTS analysis_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    user_id TEXT,                       -- Future: link to user
    run_date TIMESTAMPTZ NOT NULL,
    config_name TEXT,                   -- Which config was used
    result_json TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, user_id)             -- One result per ticker per user
);

CREATE INDEX IF NOT EXISTS idx_analysis_ticker ON analysis_history(ticker);
CREATE INDEX IF NOT EXISTS idx_analysis_user ON analysis_history(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_date ON analysis_history(run_date);

-- ==================== DROP OLD TABLES (optional cleanup) ====================
-- Run these manually if you want to remove the old caching system
-- DROP TABLE IF EXISTS checked_tickers;
