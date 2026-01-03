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

        # Use pagination to get ALL tickers (Supabase may have response limits)
        all_tickers = set()
        page_size = 1000
        offset = 0

        while True:
            response = client.table('checked_tickers') \
                .select('ticker') \
                .eq('filter_hash', filter_hash) \
                .gte('checked_at', cutoff) \
                .order('ticker') \
                .range(offset, offset + page_size - 1) \
                .execute()

            if not response.data:
                break

            for row in response.data:
                all_tickers.add(row['ticker'])

            print(f"DEBUG: Page at offset {offset} returned {len(response.data)} tickers, total so far: {len(all_tickers)}")

            if len(response.data) < page_size:
                break  # Last page

            offset += page_size

        print(f"DEBUG: Total tickers retrieved: {len(all_tickers)}")
        if all_tickers:
            sorted_tickers = sorted(list(all_tickers))
            print(f"DEBUG: First 10 cached: {sorted_tickers[:10]}")
            print(f"DEBUG: Last 10 cached: {sorted_tickers[-10:]}")
        return all_tickers
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


# SQLite implementation for checked tickers - DEPRECATED
# When Supabase is not configured, checked tickers are NOT cached locally
# This ensures cloud-first architecture and no stale local data

def _sqlite_init_checked_tickers_table():
    """No-op: checked_tickers not cached without Supabase"""
    pass


def _sqlite_save_checked_ticker(ticker: str, filter_hash: int, matched: bool):
    """No-op: checked_tickers not cached without Supabase"""
    pass


def _sqlite_was_recently_checked(ticker: str, filter_hash: int, days: int = 7) -> bool:
    """No-op: always return False without Supabase"""
    return False


def _sqlite_get_recently_checked_tickers(filter_hash: int, days: int = 7) -> set:
    """No-op: return empty set without Supabase"""
    return set()


def _sqlite_clear_old_checked(days: int = 30):
    """No-op: nothing to clear without Supabase"""
    pass


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
    """Get total count of checked tickers (requires Supabase)"""
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
        # No local caching without Supabase
        return 0


def clear_all_checked_tickers():
    """Clear ALL checked tickers from cache (requires Supabase)"""
    if USE_SUPABASE:
        try:
            client = _get_supabase()
            # Delete all rows - Supabase requires a filter, use neq empty string
            client.table('checked_tickers').delete().neq('ticker', '').execute()
            print("Cleared all checked tickers from Supabase")
        except Exception as e:
            print(f"Supabase clear all checked error: {e}")
    else:
        # No local caching without Supabase
        pass


# ==================== TICKERS TABLE (NEW) ====================
# Pre-populated universe of stocks for fast filtering

def get_filtered_tickers(
    sectors: List[str] = None,
    exchanges: List[str] = None,
    market_caps: List[str] = None,
    limit: int = None
) -> List[Dict]:
    """
    Query the tickers table with filters.
    Returns list of ticker dicts matching the criteria.
    This is FAST - just a database query, no API calls.
    Uses pagination to fetch ALL matching tickers (Supabase defaults to 1000).
    """
    if not USE_SUPABASE:
        print("ERROR: Tickers table requires Supabase")
        return []

    try:
        client = _get_supabase()

        all_tickers = []
        batch_size = 1000
        offset = 0

        while True:
            # Build query with filters
            query = client.table('tickers').select('*')

            # Apply filters (empty list = no filter = all)
            if sectors and len(sectors) > 0:
                query = query.in_('sector', sectors)

            if exchanges and len(exchanges) > 0:
                query = query.in_('exchange', exchanges)

            if market_caps and len(market_caps) > 0:
                query = query.in_('market_cap_universe', market_caps)

            # Order by ticker for consistent pagination
            query = query.order('ticker')

            # Apply pagination
            query = query.range(offset, offset + batch_size - 1)

            response = query.execute()
            batch = response.data if response.data else []

            if not batch:
                break

            all_tickers.extend(batch)

            # If user specified a limit and we've reached it, stop
            if limit and len(all_tickers) >= limit:
                all_tickers = all_tickers[:limit]
                break

            # If we got less than batch_size, we've fetched everything
            if len(batch) < batch_size:
                break

            offset += batch_size

        print(f"get_filtered_tickers: returned {len(all_tickers)} tickers (paginated)")
        return all_tickers

    except Exception as e:
        print(f"Error querying tickers table: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_tickers_count(
    sectors: List[str] = None,
    exchanges: List[str] = None,
    market_caps: List[str] = None
) -> int:
    """Get count of tickers matching filters"""
    if not USE_SUPABASE:
        return 0

    try:
        client = _get_supabase()
        query = client.table('tickers').select('*', count='exact', head=True)

        if sectors and len(sectors) > 0:
            query = query.in_('sector', sectors)
        if exchanges and len(exchanges) > 0:
            query = query.in_('exchange', exchanges)
        if market_caps and len(market_caps) > 0:
            query = query.in_('market_cap_universe', market_caps)

        response = query.execute()
        return response.count if response.count else 0

    except Exception as e:
        print(f"Error counting tickers: {e}")
        return 0


def get_all_sectors() -> List[str]:
    """Get list of unique sectors from tickers table"""
    if not USE_SUPABASE:
        return []

    try:
        client = _get_supabase()
        # Get distinct sectors
        response = client.table('tickers').select('sector').execute()
        sectors = set(row['sector'] for row in response.data if row.get('sector'))
        return sorted(list(sectors))
    except Exception as e:
        print(f"Error getting sectors: {e}")
        return []


def get_all_exchanges() -> List[str]:
    """Get list of unique exchanges from tickers table"""
    if not USE_SUPABASE:
        return []

    try:
        client = _get_supabase()
        response = client.table('tickers').select('exchange').execute()
        exchanges = set(row['exchange'] for row in response.data if row.get('exchange'))
        return sorted(list(exchanges))
    except Exception as e:
        print(f"Error getting exchanges: {e}")
        return []


def get_all_market_caps() -> List[str]:
    """Get list of unique market cap universes from tickers table"""
    if not USE_SUPABASE:
        return []

    try:
        client = _get_supabase()
        response = client.table('tickers').select('market_cap_universe').execute()
        caps = set(row['market_cap_universe'] for row in response.data if row.get('market_cap_universe'))
        # Return in logical order
        order = ['Mega Cap', 'Large Cap', 'Mid Cap', 'Small Cap', 'Micro Cap']
        return [c for c in order if c in caps] + [c for c in sorted(caps) if c not in order]
    except Exception as e:
        print(f"Error getting market caps: {e}")
        return []


# ==================== USER CONFIGURATIONS (NEW) ====================
# Unified settings: DCF params + Filters in one config

DEFAULT_USER_ID = "default"  # Temporary until we have auth

def save_user_config(config_name: str, config_data: Dict, user_id: str = None, is_default: bool = False) -> bool:
    """
    Save a user configuration (DCF params + filters).
    config_data should have: { dcf_params: {...}, filters: {...} }
    """
    if not USE_SUPABASE:
        print("ERROR: User configs require Supabase")
        return False

    user_id = user_id or DEFAULT_USER_ID

    try:
        client = _get_supabase()

        # If setting as default, clear other defaults for this user
        if is_default:
            client.table('user_configurations') \
                .update({'is_default': False}) \
                .eq('user_id', user_id) \
                .execute()

        data = {
            'user_id': user_id,
            'config_name': config_name,
            'config_json': json.dumps(config_data),
            'is_default': is_default,
            'updated_at': datetime.now().isoformat()
        }

        response = client.table('user_configurations').upsert(
            data,
            on_conflict='user_id,config_name'
        ).execute()

        print(f"Saved config '{config_name}' for user {user_id}")
        return True

    except Exception as e:
        print(f"Error saving user config: {e}")
        return False


def load_user_config(config_name: str, user_id: str = None) -> Optional[Dict]:
    """Load a specific user configuration by name"""
    if not USE_SUPABASE:
        return None

    user_id = user_id or DEFAULT_USER_ID

    try:
        client = _get_supabase()
        response = client.table('user_configurations') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('config_name', config_name) \
            .execute()

        if response.data and len(response.data) > 0:
            row = response.data[0]
            config = json.loads(row['config_json'])
            config['_name'] = row['config_name']
            config['_is_default'] = row['is_default']
            return config
        return None

    except Exception as e:
        print(f"Error loading user config: {e}")
        return None


def load_default_config(user_id: str = None) -> Optional[Dict]:
    """Load the user's default configuration"""
    if not USE_SUPABASE:
        return None

    user_id = user_id or DEFAULT_USER_ID

    try:
        client = _get_supabase()
        response = client.table('user_configurations') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('is_default', True) \
            .execute()

        if response.data and len(response.data) > 0:
            row = response.data[0]
            config = json.loads(row['config_json'])
            config['_name'] = row['config_name']
            config['_is_default'] = True
            return config
        return None

    except Exception as e:
        print(f"Error loading default config: {e}")
        return None


def list_user_configs(user_id: str = None) -> List[Dict]:
    """List all configurations for a user"""
    if not USE_SUPABASE:
        return []

    user_id = user_id or DEFAULT_USER_ID

    try:
        client = _get_supabase()
        response = client.table('user_configurations') \
            .select('config_name, is_default, created_at, updated_at') \
            .eq('user_id', user_id) \
            .order('config_name') \
            .execute()

        return response.data if response.data else []

    except Exception as e:
        print(f"Error listing user configs: {e}")
        return []


def delete_user_config(config_name: str, user_id: str = None) -> bool:
    """Delete a user configuration"""
    if not USE_SUPABASE:
        return False

    user_id = user_id or DEFAULT_USER_ID

    try:
        client = _get_supabase()
        client.table('user_configurations') \
            .delete() \
            .eq('user_id', user_id) \
            .eq('config_name', config_name) \
            .execute()

        print(f"Deleted config '{config_name}' for user {user_id}")
        return True

    except Exception as e:
        print(f"Error deleting user config: {e}")
        return False
