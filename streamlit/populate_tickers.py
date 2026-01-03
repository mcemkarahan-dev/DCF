#!/usr/bin/env python3
"""
Populate Tickers Table

This script fetches all tickers from ROIC.AI and populates the Supabase
tickers table. Run periodically (daily/weekly) to keep the universe current.

Usage:
    python populate_tickers.py

Credentials: Set via environment variables OR .streamlit/secrets.toml
    SUPABASE_URL, SUPABASE_KEY, ROIC_API_KEY
"""

import os
import sys
from datetime import datetime

# Add current directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_secrets_from_toml():
    """Try to load secrets from .streamlit/secrets.toml"""
    secrets_path = os.path.join(SCRIPT_DIR, '.streamlit', 'secrets.toml')
    if not os.path.exists(secrets_path):
        return {}

    secrets = {}
    try:
        with open(secrets_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    secrets[key] = value
        log(f"Loaded secrets from {secrets_path}")
    except Exception as e:
        log(f"Could not load secrets.toml: {e}")
    return secrets


def populate_tickers():
    """Fetch tickers from ROIC.AI and upsert into Supabase"""

    # Import after path setup
    from supabase import create_client
    import requests

    # Get credentials - try environment first, then secrets.toml
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    roic_key = os.environ.get('ROIC_API_KEY')

    # If not in environment, try secrets.toml
    if not all([supabase_url, supabase_key, roic_key]):
        secrets = load_secrets_from_toml()
        supabase_url = supabase_url or secrets.get('SUPABASE_URL')
        supabase_key = supabase_key or secrets.get('SUPABASE_KEY')
        roic_key = roic_key or secrets.get('ROIC_API_KEY')

    if not all([supabase_url, supabase_key, roic_key]):
        log("ERROR: Missing SUPABASE_URL, SUPABASE_KEY, or ROIC_API_KEY")
        return False

    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)

    log("Fetching all tickers from ROIC.AI...")

    # Fetch tickers from ROIC.AI using the correct endpoint: /v2/tickers/list
    try:
        url = f"https://api.roic.ai/v2/tickers/list?apikey={roic_key}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        tickers = response.json()
    except Exception as e:
        log(f"ERROR fetching from ROIC.AI: {e}")
        return False

    if not tickers:
        log("ERROR: No tickers returned from ROIC.AI")
        return False

    log(f"Fetched {len(tickers)} tickers from ROIC.AI")

    # Prepare data for upsert
    # ROIC.AI response format: {symbol, name, exchange_name, exchange, type}
    now = datetime.now().isoformat()
    records = []

    # Helper to classify market cap
    def get_market_cap_universe(mkt_cap):
        if not mkt_cap or mkt_cap == 0:
            return "Unknown"
        if mkt_cap >= 200e9:
            return "Mega Cap"
        elif mkt_cap >= 10e9:
            return "Large Cap"
        elif mkt_cap >= 2e9:
            return "Mid Cap"
        elif mkt_cap >= 300e6:
            return "Small Cap"
        elif mkt_cap >= 50e6:
            return "Micro Cap"
        else:
            return "Nano Cap"

    # Track types for debugging
    types_seen = set()

    for t in tickers:
        symbol = t.get('symbol') or t.get('ticker')
        if not symbol:
            continue

        stock_type = t.get('type', '')
        types_seen.add(stock_type)

        # Skip ETFs, funds, etc. - keep stocks only
        skip_types = ['ETF', 'Fund', 'Trust', 'Index', 'Warrant', 'Right', 'Preferred']
        should_skip = any(skip in stock_type for skip in skip_types if stock_type)

        if should_skip:
            continue

        # Only include US exchanges
        exchange = t.get('exchange', '')
        us_exchanges = ['NYSE', 'NASDAQ', 'AMEX', 'NYSEArca', 'BATS', 'CBOE']
        if exchange and not any(us in exchange.upper() for us in [e.upper() for e in us_exchanges]):
            continue

        mkt_cap = t.get('marketCap') or t.get('market_cap') or 0

        records.append({
            'ticker': symbol,
            'name': t.get('name', ''),
            'sector': t.get('sector', 'N/A'),
            'exchange': t.get('exchange', 'N/A'),
            'market_cap': mkt_cap,
            'market_cap_universe': get_market_cap_universe(mkt_cap),
            'last_updated': now
        })

    log(f"Types seen in data: {types_seen}")

    log(f"Prepared {len(records)} records for upsert")

    # Upsert in batches (Supabase has limits)
    batch_size = 500
    total_upserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            response = supabase.table('tickers').upsert(
                batch,
                on_conflict='ticker'
            ).execute()
            total_upserted += len(batch)
            log(f"Upserted batch {i//batch_size + 1}: {len(batch)} records (total: {total_upserted})")
        except Exception as e:
            log(f"ERROR upserting batch: {e}")
            # Continue with next batch

    log(f"Done! Total tickers in database: {total_upserted}")

    # Verify count
    try:
        count_response = supabase.table('tickers').select('ticker', count='exact').execute()
        count = len(count_response.data) if hasattr(count_response, 'data') else 0
        log(f"Verified: {count} tickers in tickers table")
    except Exception as e:
        log(f"Could not verify count: {e}")

    return True


if __name__ == '__main__':
    success = populate_tickers()
    sys.exit(0 if success else 1)
