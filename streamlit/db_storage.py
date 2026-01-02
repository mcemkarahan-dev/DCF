"""
Persistent storage for DCF Analyzer
Uses Supabase (cloud) when configured, falls back to SQLite (local)
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
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

_last_db_error = None  # Store last error for UI display

def get_last_db_error():
    """Get the last database error for UI display"""
    return _last_db_error

def _supabase_save_analysis(result: Dict, params_hash: int = None):
    """Save analysis to Supabase"""
    global _last_db_error
    if not result or 'ticker' not in result:
        _last_db_error = "No ticker in result"
        return

    try:
        client = _get_supabase()
        ticker = result['ticker']
        run_date = result.get('run_date', datetime.now().isoformat())

        data = {
            'ticker': ticker,
            'run_date': run_date,
            'params_hash': params_hash,
            'result_json': json.dumps(result),
        }

        # Try delete first
        try:
            client.table('analysis_history').delete().eq('ticker', ticker).execute()
        except:
            pass

        # Insert and check response
        response = client.table('analysis_history').insert(data).execute()

        # Check if insert actually worked
        if response.data and len(response.data) > 0:
            _last_db_error = None  # Success
        else:
            _last_db_error = f"Insert returned no data. Response: {response}"
    except Exception as e:
        _last_db_error = f"Save exception: {str(e)}"


def _supabase_load_all_history(limit: int = 100) -> List[Dict]:
    """Load all history from Supabase"""
    try:
        client = _get_supabase()

        response = client.table('analysis_history') \
            .select('result_json') \
            .order('run_date', desc=True) \
            .limit(limit) \
            .execute()

        print(f"Supabase load: got {len(response.data)} rows")

        history = []
        for row in response.data:
            try:
                result = json.loads(row['result_json'])
                history.append(result)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Supabase parse error: {e}")

        return history
    except Exception as e:
        print(f"Supabase load error: {e}")
        import traceback
        traceback.print_exc()
        return []


def _supabase_get_analysis(ticker: str) -> Optional[Dict]:
    """Get analysis for specific ticker from Supabase"""
    try:
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
    except Exception as e:
        print(f"Supabase get error: {e}")
        return None


def _supabase_delete_analysis(ticker: str):
    """Delete analysis from Supabase"""
    try:
        client = _get_supabase()
        client.table('analysis_history').delete().eq('ticker', ticker).execute()
    except Exception as e:
        print(f"Supabase delete error: {e}")


def _supabase_clear_all_history():
    """Clear all history from Supabase"""
    try:
        client = _get_supabase()
        # Delete all rows - Supabase requires a filter, so we use a truthy condition
        client.table('analysis_history').delete().neq('ticker', '').execute()
    except Exception as e:
        print(f"Supabase clear error: {e}")


def _supabase_get_history_count() -> int:
    """Get count from Supabase"""
    try:
        client = _get_supabase()
        response = client.table('analysis_history').select('ticker', count='exact').execute()
        return response.count if response.count else 0
    except Exception as e:
        print(f"Supabase count error: {e}")
        return 0


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


# ==================== CHECKED TICKERS TRACKING ====================
# Track which tickers have been checked (even non-matches) to avoid re-checking

def _get_filter_hash(filters: Dict) -> int:
    """Create a deterministic hash of filter parameters.
    Uses hashlib instead of Python's hash() which is randomized per session.
    """
    import hashlib
    if not filters:
        return 0
    # Sort keys for consistent hashing
    filter_str = json.dumps(filters, sort_keys=True)
    # Use MD5 for deterministic hash, convert to int (take first 8 bytes)
    hash_bytes = hashlib.md5(filter_str.encode()).digest()[:8]
    result = int.from_bytes(hash_bytes, byteorder='big', signed=True)
    print(f"DEBUG _get_filter_hash: filters={filter_str[:100]}... -> hash={result}")
    return result


# Supabase implementation for checked tickers
def _supabase_save_checked_ticker(ticker: str, filter_hash: int, matched: bool):
    """Save a checked ticker to Supabase"""
    try:
        client = _get_supabase()
        data = {
            'ticker': ticker,
            'filter_hash': filter_hash,
            'matched': matched,
            'checked_at': datetime.now().isoformat(),
        }
        response = client.table('checked_tickers').upsert(
            data, on_conflict='ticker,filter_hash'
        ).execute()
        # Verify save worked
        if not response.data:
            print(f"WARNING: Save returned no data for {ticker}")
    except Exception as e:
        print(f"Supabase save checked ticker error for {ticker}: {e}")


def _supabase_was_recently_checked(ticker: str, filter_hash: int, days: int = 7) -> bool:
    """Check if ticker was checked with same filters in last N days"""
    try:
        client = _get_supabase()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        response = client.table('checked_tickers') \
            .select('checked_at') \
            .eq('ticker', ticker) \
            .eq('filter_hash', filter_hash) \
            .gte('checked_at', cutoff) \
            .execute()

        return len(response.data) > 0
    except Exception as e:
        print(f"Supabase check recently checked error: {e}")
        return False


def _supabase_get_recently_checked_tickers(filter_hash: int, days: int = 7) -> set:
    """Get all tickers checked with same filters in last N days"""
    try:
        client = _get_supabase()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        print(f"DEBUG: Querying checked_tickers with filter_hash={filter_hash}, cutoff={cutoff}")

        # Supabase defaults to 1000 rows - override with higher limit
        response = client.table('checked_tickers') \
            .select('ticker') \
            .eq('filter_hash', filter_hash) \
            .gte('checked_at', cutoff) \
            .limit(50000) \
            .execute()

        tickers = set(row['ticker'] for row in response.data)
        print(f"DEBUG: Query returned {len(tickers)} tickers")
        if tickers:
            sample = sorted(list(tickers))[:10]
            print(f"DEBUG: First 10 cached tickers: {sample}")
        return tickers
    except Exception as e:
        print(f"Supabase get recently checked error: {e}")
        import traceback
        traceback.print_exc()
        return set()


def _supabase_clear_old_checked(days: int = 30):
    """Clear checked tickers older than N days"""
    try:
        client = _get_supabase()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        client.table('checked_tickers').delete().lt('checked_at', cutoff).execute()
    except Exception as e:
        print(f"Supabase clear old checked error: {e}")


# SQLite implementation for checked tickers
def _sqlite_init_checked_tickers_table():
    """Initialize checked_tickers table in SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checked_tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            filter_hash INTEGER NOT NULL,
            matched INTEGER DEFAULT 0,
            checked_at TEXT NOT NULL,
            UNIQUE(ticker, filter_hash)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_checked_filter ON checked_tickers(filter_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_checked_at ON checked_tickers(checked_at)')
    conn.commit()
    conn.close()


def _sqlite_save_checked_ticker(ticker: str, filter_hash: int, matched: bool):
    """Save a checked ticker to SQLite"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO checked_tickers (ticker, filter_hash, matched, checked_at)
        VALUES (?, ?, ?, ?)
    ''', (ticker, filter_hash, 1 if matched else 0, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _sqlite_was_recently_checked(ticker: str, filter_hash: int, days: int = 7) -> bool:
    """Check if ticker was checked with same filters in last N days"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor.execute('''
        SELECT 1 FROM checked_tickers
        WHERE ticker = ? AND filter_hash = ? AND checked_at >= ?
    ''', (ticker, filter_hash, cutoff))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def _sqlite_get_recently_checked_tickers(filter_hash: int, days: int = 7) -> set:
    """Get all tickers checked with same filters in last N days"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor.execute('''
        SELECT ticker FROM checked_tickers
        WHERE filter_hash = ? AND checked_at >= ?
    ''', (filter_hash, cutoff))
    rows = cursor.fetchall()
    conn.close()
    return set(row[0] for row in rows)


def _sqlite_clear_old_checked(days: int = 30):
    """Clear checked tickers older than N days"""
    conn = _sqlite_get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor.execute('DELETE FROM checked_tickers WHERE checked_at < ?', (cutoff,))
    conn.commit()
    conn.close()


# Public API for checked tickers
def save_checked_ticker(ticker: str, filters: Dict, matched: bool):
    """Save that a ticker was checked with given filters"""
    filter_hash = _get_filter_hash(filters)
    if USE_SUPABASE:
        _supabase_save_checked_ticker(ticker, filter_hash, matched)
    else:
        _sqlite_save_checked_ticker(ticker, filter_hash, matched)


def was_recently_checked(ticker: str, filters: Dict, days: int = 7) -> bool:
    """Check if ticker was checked with same filters in last N days"""
    filter_hash = _get_filter_hash(filters)
    if USE_SUPABASE:
        return _supabase_was_recently_checked(ticker, filter_hash, days)
    else:
        return _sqlite_was_recently_checked(ticker, filter_hash, days)


def get_recently_checked_tickers(filters: Dict, days: int = 7) -> set:
    """Get all tickers checked with same filters in last N days"""
    filter_hash = _get_filter_hash(filters)
    print(f"DEBUG: Looking for recently checked tickers with filter_hash={filter_hash}")
    if USE_SUPABASE:
        result = _supabase_get_recently_checked_tickers(filter_hash, days)
    else:
        result = _sqlite_get_recently_checked_tickers(filter_hash, days)
    print(f"DEBUG: Found {len(result)} recently checked tickers")
    return result


def clear_old_checked_tickers(days: int = 30):
    """Clear checked tickers older than N days"""
    if USE_SUPABASE:
        _supabase_clear_old_checked(days)
    else:
        _sqlite_clear_old_checked(days)


# Initialize storage on import
if not USE_SUPABASE:
    _sqlite_init_db()
    _sqlite_init_checked_tickers_table()
    print("Storage: SQLite (local) - cache is NOT shared across environments")
else:
    print("Storage: Supabase (cloud) - cache IS shared across environments")


def get_checked_tickers_count(filters: Dict = None) -> int:
    """Get total count of checked tickers (for debugging)"""
    if USE_SUPABASE:
        try:
            client = _get_supabase()
            # Use count='exact' and select only id to get true count (not limited by default 1000)
            if filters:
                filter_hash = _get_filter_hash(filters)
                response = client.table('checked_tickers').select('*', count='exact', head=True).eq('filter_hash', filter_hash).execute()
            else:
                response = client.table('checked_tickers').select('*', count='exact', head=True).execute()
            return response.count if response.count else 0
        except Exception as e:
            print(f"Supabase checked count error: {e}")
            return 0
    else:
        conn = _sqlite_get_connection()
        cursor = conn.cursor()
        if filters:
            filter_hash = _get_filter_hash(filters)
            cursor.execute('SELECT COUNT(*) FROM checked_tickers WHERE filter_hash = ?', (filter_hash,))
        else:
            cursor.execute('SELECT COUNT(*) FROM checked_tickers')
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0


def clear_all_checked_tickers():
    """Clear ALL checked tickers from cache (both local and cloud)"""
    if USE_SUPABASE:
        try:
            client = _get_supabase()
            # Delete all rows - Supabase requires a filter, use neq empty string
            client.table('checked_tickers').delete().neq('ticker', '').execute()
            print("Cleared all checked tickers from Supabase")
        except Exception as e:
            print(f"Supabase clear all checked error: {e}")
    else:
        conn = _sqlite_get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM checked_tickers')
        conn.commit()
        conn.close()
        print("Cleared all checked tickers from SQLite")


# ==================== BATCH JOB TRACKING ====================
# For background processing that continues even when UI disconnects

def create_batch_job(filters: Dict, job_name: str = None) -> Optional[str]:
    """
    Create a new batch screening job. Returns job_id.
    Job state is stored in Supabase so a separate worker can process it.
    """
    if not USE_SUPABASE:
        print("Batch jobs require Supabase - not available locally")
        return None

    try:
        import uuid
        client = _get_supabase()
        job_id = str(uuid.uuid4())[:8]
        filter_hash = _get_filter_hash(filters)

        data = {
            'job_id': job_id,
            'job_name': job_name or f"Batch {job_id}",
            'filters_json': json.dumps(filters),
            'filter_hash': filter_hash,
            'status': 'pending',  # pending, running, completed, failed
            'total_tickers': 0,
            'processed_tickers': 0,
            'matched_tickers': 0,
            'current_ticker': None,
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'error_message': None,
        }

        response = client.table('batch_jobs').insert(data).execute()
        if response.data:
            print(f"Created batch job: {job_id}")
            return job_id
        return None
    except Exception as e:
        print(f"Error creating batch job: {e}")
        return None


def get_batch_job(job_id: str) -> Optional[Dict]:
    """Get batch job status and details"""
    if not USE_SUPABASE:
        return None

    try:
        client = _get_supabase()
        response = client.table('batch_jobs') \
            .select('*') \
            .eq('job_id', job_id) \
            .execute()

        if response.data and len(response.data) > 0:
            job = response.data[0]
            # Parse filters back from JSON
            if job.get('filters_json'):
                job['filters'] = json.loads(job['filters_json'])
            return job
        return None
    except Exception as e:
        print(f"Error getting batch job: {e}")
        return None


def get_pending_batch_jobs() -> List[Dict]:
    """Get all pending or running batch jobs (for worker to process)"""
    if not USE_SUPABASE:
        return []

    try:
        client = _get_supabase()
        response = client.table('batch_jobs') \
            .select('*') \
            .in_('status', ['pending', 'running']) \
            .order('created_at', desc=False) \
            .execute()

        jobs = []
        for job in response.data:
            if job.get('filters_json'):
                job['filters'] = json.loads(job['filters_json'])
            jobs.append(job)
        return jobs
    except Exception as e:
        print(f"Error getting pending jobs: {e}")
        return []


def update_batch_job(job_id: str, **kwargs):
    """Update batch job status/progress"""
    if not USE_SUPABASE:
        return

    try:
        client = _get_supabase()

        # Build update dict from kwargs
        data = {}
        for key in ['status', 'total_tickers', 'processed_tickers', 'matched_tickers',
                    'current_ticker', 'started_at', 'completed_at', 'error_message']:
            if key in kwargs:
                data[key] = kwargs[key]

        if data:
            client.table('batch_jobs').update(data).eq('job_id', job_id).execute()
    except Exception as e:
        print(f"Error updating batch job: {e}")


def get_recent_batch_jobs(limit: int = 10) -> List[Dict]:
    """Get recent batch jobs for display"""
    if not USE_SUPABASE:
        return []

    try:
        client = _get_supabase()
        response = client.table('batch_jobs') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()

        jobs = []
        for job in response.data:
            if job.get('filters_json'):
                job['filters'] = json.loads(job['filters_json'])
            jobs.append(job)
        return jobs
    except Exception as e:
        print(f"Error getting recent jobs: {e}")
        return []


def delete_batch_job(job_id: str):
    """Delete a batch job"""
    if not USE_SUPABASE:
        return

    try:
        client = _get_supabase()
        client.table('batch_jobs').delete().eq('job_id', job_id).execute()
    except Exception as e:
        print(f"Error deleting batch job: {e}")
