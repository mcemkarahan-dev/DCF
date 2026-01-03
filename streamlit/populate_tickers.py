#!/usr/bin/env python3
"""
Populate Tickers Table

This script fetches all tickers from ROIC.AI and populates the Supabase
tickers table. Run periodically (daily/weekly) to keep the universe current.

Usage:
    python populate_tickers.py

Environment variables required:
    SUPABASE_URL, SUPABASE_KEY, ROIC_API_KEY
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def populate_tickers():
    """Fetch tickers from ROIC.AI and upsert into Supabase"""

    # Import after path setup
    from supabase import create_client
    from data_fetcher_roic import RoicDataFetcher

    # Get credentials
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    roic_key = os.environ.get('ROIC_API_KEY')

    if not all([supabase_url, supabase_key, roic_key]):
        log("ERROR: Missing environment variables (SUPABASE_URL, SUPABASE_KEY, ROIC_API_KEY)")
        return False

    # Initialize clients
    supabase = create_client(supabase_url, supabase_key)
    fetcher = RoicDataFetcher(roic_key)

    log("Fetching all tickers from ROIC.AI...")

    # Fetch all tickers (no filters = get everything)
    try:
        tickers = fetcher.get_filtered_tickers(
            sectors=None,
            exchanges=None,
            market_cap_universes=None
        )
    except Exception as e:
        log(f"ERROR fetching from ROIC.AI: {e}")
        return False

    if not tickers:
        log("ERROR: No tickers returned from ROIC.AI")
        return False

    log(f"Fetched {len(tickers)} tickers from ROIC.AI")

    # Prepare data for upsert
    now = datetime.now().isoformat()
    records = []

    for t in tickers:
        ticker = t.get('ticker') or t.get('symbol')
        if not ticker:
            continue

        records.append({
            'ticker': ticker,
            'name': t.get('name', ''),
            'sector': t.get('sector', 'N/A'),
            'exchange': t.get('exchange', 'N/A'),
            'market_cap': t.get('market_cap') or t.get('marketCap') or 0,
            'market_cap_universe': t.get('market_cap_universe', 'Unknown'),
            'last_updated': now
        })

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
        count_response = supabase.table('tickers').select('*', count='exact', head=True).execute()
        log(f"Verified: {count_response.count} tickers in tickers table")
    except Exception as e:
        log(f"Could not verify count: {e}")

    return True


if __name__ == '__main__':
    success = populate_tickers()
    sys.exit(0 if success else 1)
