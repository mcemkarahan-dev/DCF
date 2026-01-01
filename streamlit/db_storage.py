"""
Persistent storage for DCF Analyzer
Uses Supabase (cloud) when configured, falls back to SQLite (local)
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

# Try to import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Try to get Supabase credentials from Streamlit secrets or environment
SUPABASE_URL = None
SUPABASE_KEY = None

try:
    import streamlit as st
    SUPABASE_URL = st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
except:
    pass

if not SUPABASE_URL:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
if not SUPABASE_KEY:
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Determine which backend to use
USE_SUPABASE = SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY

# SQLite fallback path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dcf_analyzer.db')

# Supabase client (initialized lazily)
_supabase_client: Optional[Client] = None


def _get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ==================== SUPABASE IMPLEMENTATION ====================

def _supabase_save_analysis(result: Dict, params_hash: int = None):
    """Save analysis to Supabase"""
    if not result or 'ticker' not in result:
        return

    client = _get_supabase()
    ticker = result['ticker']
    run_date = result.get('run_date', datetime.now().isoformat())

    data = {
        'ticker': ticker,
        'run_date': run_date,
        'params_hash': params_hash,
        'result_json': json.dumps(result),
    }

    # Upsert - update if exists, insert if not
    client.table('analysis_history').upsert(data, on_conflict='ticker').execute()


def _supabase_load_all_history(limit: int = 100) -> List[Dict]:
    """Load all history from Supabase"""
    client = _get_supabase()

    response = client.table('analysis_history') \
        .select('result_json') \
        .order('run_date', desc=True) \
        .limit(limit) \
        .execute()

    history = []
    for row in response.data:
        try:
            result = json.loads(row['result_json'])
            history.append(result)
        except (json.JSONDecodeError, KeyError):
            pass

    return history


def _supabase_get_analysis(ticker: str) -> Optional[Dict]:
    """Get analysis for specific ticker from Supabase"""
    client = _get_supabase()

    response = client.table('analysis_history') \
        .select('result_json') \
        .eq('ticker', ticker) \
        .execute()

    if response.data and len(response.data) > 0:
        try:
            return json.loads(response.data[0]['result_json'])
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def _supabase_delete_analysis(ticker: str):
    """Delete analysis from Supabase"""
    client = _get_supabase()
    client.table('analysis_history').delete().eq('ticker', ticker).execute()


def _supabase_clear_all_history():
    """Clear all history from Supabase"""
    client = _get_supabase()
    # Delete all rows - Supabase requires a filter, so we use a truthy condition
    client.table('analysis_history').delete().neq('ticker', '').execute()


def _supabase_get_history_count() -> int:
    """Get count from Supabase"""
    client = _get_supabase()
    response = client.table('analysis_history').select('ticker', count='exact').execute()
    return response.count if response.count else 0


# ==================== SQLITE IMPLEMENTATION ====================

def _sqlite_get_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_init_db():
    """Initialize SQLite database tables"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            run_date TEXT NOT NULL,
            params_hash INTEGER,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ticker ON analysis_history(ticker)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_run_date ON analysis_history(run_date)
    ''')

    conn.commit()
    conn.close()


def _sqlite_save_analysis(result: Dict, params_hash: int = None):
    """Save analysis to SQLite"""
    if not result or 'ticker' not in result:
        return

    conn = _sqlite_get_connection()
    cursor = conn.cursor()

    ticker = result['ticker']
    run_date = result.get('run_date', datetime.now().isoformat())
    result_json = json.dumps(result)

    cursor.execute('''
        INSERT OR REPLACE INTO analysis_history
        (ticker, run_date, params_hash, result_json, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (ticker, run_date, params_hash, result_json))

    conn.commit()
    conn.close()


def _sqlite_load_all_history(limit: int = 100) -> List[Dict]:
    """Load all history from SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT result_json FROM analysis_history
        ORDER BY run_date DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        try:
            result = json.loads(row['result_json'])
            history.append(result)
        except json.JSONDecodeError:
            pass

    return history


def _sqlite_get_analysis(ticker: str) -> Optional[Dict]:
    """Get analysis for specific ticker from SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT result_json FROM analysis_history
        WHERE ticker = ?
    ''', (ticker,))

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            return json.loads(row['result_json'])
        except json.JSONDecodeError:
            return None
    return None


def _sqlite_delete_analysis(ticker: str):
    """Delete analysis from SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM analysis_history WHERE ticker = ?', (ticker,))
    conn.commit()
    conn.close()


def _sqlite_clear_all_history():
    """Clear all history from SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM analysis_history')
    conn.commit()
    conn.close()


def _sqlite_get_history_count() -> int:
    """Get count from SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as cnt FROM analysis_history')
    row = cursor.fetchone()
    conn.close()
    return row['cnt'] if row else 0


# ==================== PUBLIC API ====================
# Routes to appropriate backend based on configuration

def save_analysis(result: Dict, params_hash: int = None):
    """Save analysis result to database"""
    if USE_SUPABASE:
        _supabase_save_analysis(result, params_hash)
    else:
        _sqlite_save_analysis(result, params_hash)


def load_all_history(limit: int = 100) -> List[Dict]:
    """Load all analysis history from database"""
    if USE_SUPABASE:
        return _supabase_load_all_history(limit)
    else:
        return _sqlite_load_all_history(limit)


def get_analysis(ticker: str) -> Optional[Dict]:
    """Get analysis for a specific ticker"""
    if USE_SUPABASE:
        return _supabase_get_analysis(ticker)
    else:
        return _sqlite_get_analysis(ticker)


def delete_analysis(ticker: str):
    """Delete analysis for a specific ticker"""
    if USE_SUPABASE:
        _supabase_delete_analysis(ticker)
    else:
        _sqlite_delete_analysis(ticker)


def clear_all_history():
    """Clear all analysis history"""
    if USE_SUPABASE:
        _supabase_clear_all_history()
    else:
        _sqlite_clear_all_history()


def get_history_count() -> int:
    """Get count of analyses in history"""
    if USE_SUPABASE:
        return _supabase_get_history_count()
    else:
        return _sqlite_get_history_count()


def get_storage_backend() -> str:
    """Return which storage backend is being used"""
    return "Supabase" if USE_SUPABASE else "SQLite (local)"


# Initialize SQLite on import (for local development)
if not USE_SUPABASE:
    _sqlite_init_db()
    print("Using SQLite for local storage")
else:
    print("Using Supabase for cloud storage")
