"""
SQLite-based persistent storage for DCF Analyzer
Stores analysis history so it survives app restarts
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# Database file location (same directory as the app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dcf_analyzer.db')


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # Analysis history table
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

    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ticker ON analysis_history(ticker)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_run_date ON analysis_history(run_date)
    ''')

    conn.commit()
    conn.close()


def save_analysis(result: Dict, params_hash: int = None):
    """Save analysis result to database"""
    if not result or 'ticker' not in result:
        return

    conn = get_connection()
    cursor = conn.cursor()

    ticker = result['ticker']
    run_date = result.get('run_date', datetime.now().isoformat())
    result_json = json.dumps(result)

    # Upsert - replace existing entry for same ticker
    cursor.execute('''
        INSERT OR REPLACE INTO analysis_history
        (ticker, run_date, params_hash, result_json, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (ticker, run_date, params_hash, result_json))

    conn.commit()
    conn.close()


def load_all_history(limit: int = 100) -> List[Dict]:
    """Load all analysis history from database"""
    conn = get_connection()
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


def get_analysis(ticker: str) -> Optional[Dict]:
    """Get analysis for a specific ticker"""
    conn = get_connection()
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


def delete_analysis(ticker: str):
    """Delete analysis for a specific ticker"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM analysis_history WHERE ticker = ?
    ''', (ticker,))

    conn.commit()
    conn.close()


def clear_all_history():
    """Clear all analysis history"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM analysis_history')

    conn.commit()
    conn.close()


def get_history_count() -> int:
    """Get count of analyses in history"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as cnt FROM analysis_history')
    row = cursor.fetchone()
    conn.close()

    return row['cnt'] if row else 0


# Initialize database on import
init_db()
