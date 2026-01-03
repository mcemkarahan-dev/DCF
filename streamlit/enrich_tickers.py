#!/usr/bin/env python3
"""
Enrich Tickers with Sector and Market Cap Data

Uses multiple data sources (Yahoo Finance + ROIC.AI) in parallel
to speed up enrichment and handle throttling/failures.

Usage:
    python enrich_tickers.py [--batch-size 500] [--workers 4]
"""

import os
import sys
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Tuple

# Add current directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_secrets():
    """Load secrets from .streamlit/secrets.toml"""
    secrets_path = os.path.join(SCRIPT_DIR, '.streamlit', 'secrets.toml')
    secrets = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip().strip('"').strip("'")
    return secrets


def get_from_yahoo(ticker: str) -> Optional[Dict]:
    """Fetch sector and market cap from Yahoo Finance"""
    try:
        import yfinance as yf
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info

        if not info or info.get('regularMarketPrice') is None:
            return None

        return {
            'sector': info.get('sector', 'N/A'),
            'market_cap': info.get('marketCap', 0) or 0
        }
    except Exception as e:
        return None


def get_from_roic(ticker: str, api_key: str) -> Optional[Dict]:
    """Fetch sector and market cap from ROIC.AI company profile"""
    try:
        import requests
        url = f"https://api.roic.ai/v2/company/profile/{ticker}?apikey={api_key}"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data or len(data) == 0:
            return None

        profile = data[0] if isinstance(data, list) else data

        return {
            'sector': profile.get('sector', 'N/A'),
            'market_cap': profile.get('mktCap') or profile.get('marketCap') or 0
        }
    except Exception as e:
        return None


def get_market_cap_universe(mkt_cap: int) -> str:
    """Classify market cap into universe tier"""
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


def enrich_ticker(ticker: str, roic_key: str, use_roic: bool = True) -> Tuple[str, Optional[Dict]]:
    """
    Try to enrich a single ticker using multiple sources.
    Alternates primary source based on use_roic flag to distribute load.
    """
    result = None

    # Try primary source first
    if use_roic:
        result = get_from_roic(ticker, roic_key)
        if not result or result.get('sector') == 'N/A':
            result = get_from_yahoo(ticker)
    else:
        result = get_from_yahoo(ticker)
        if not result or result.get('sector') == 'N/A':
            result = get_from_roic(ticker, roic_key)

    return (ticker, result)


def enrich_tickers(batch_size: int = 500, num_workers: int = 4, max_tickers: int = None):
    """Main enrichment function"""

    from supabase import create_client

    # Load credentials
    secrets = load_secrets()
    supabase_url = secrets.get('SUPABASE_URL')
    supabase_key = secrets.get('SUPABASE_KEY')
    roic_key = secrets.get('ROIC_API_KEY')

    if not all([supabase_url, supabase_key, roic_key]):
        log("ERROR: Missing credentials in .streamlit/secrets.toml")
        return False

    supabase = create_client(supabase_url, supabase_key)

    # Get tickers that need enrichment (sector = 'N/A')
    log("Fetching tickers that need enrichment...")

    all_tickers = []
    offset = 0
    page_size = 1000

    while True:
        response = supabase.table('tickers') \
            .select('ticker') \
            .eq('sector', 'N/A') \
            .range(offset, offset + page_size - 1) \
            .execute()

        batch = response.data if response.data else []
        if not batch:
            break

        all_tickers.extend([t['ticker'] for t in batch])

        if len(batch) < page_size:
            break
        offset += page_size

    log(f"Found {len(all_tickers)} tickers needing enrichment")

    if max_tickers:
        all_tickers = all_tickers[:max_tickers]
        log(f"Limited to {max_tickers} tickers")

    if not all_tickers:
        log("No tickers to enrich!")
        return True

    # Process in batches
    total_enriched = 0
    total_failed = 0
    start_time = time.time()

    for batch_start in range(0, len(all_tickers), batch_size):
        batch_tickers = all_tickers[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(all_tickers) + batch_size - 1) // batch_size

        log(f"Processing batch {batch_num}/{total_batches} ({len(batch_tickers)} tickers)...")

        # Use ThreadPoolExecutor for parallel fetching
        results = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Alternate between ROIC and Yahoo as primary source
            futures = {
                executor.submit(enrich_ticker, ticker, roic_key, i % 2 == 0): ticker
                for i, ticker in enumerate(batch_tickers)
            }

            for future in as_completed(futures):
                ticker, data = future.result()
                if data and data.get('sector') != 'N/A':
                    results.append({
                        'ticker': ticker,
                        'sector': data['sector'],
                        'market_cap': data['market_cap'],
                        'market_cap_universe': get_market_cap_universe(data['market_cap'])
                    })

        # Update Supabase in batch
        if results:
            try:
                for r in results:
                    supabase.table('tickers') \
                        .update({
                            'sector': r['sector'],
                            'market_cap': r['market_cap'],
                            'market_cap_universe': r['market_cap_universe']
                        }) \
                        .eq('ticker', r['ticker']) \
                        .execute()

                total_enriched += len(results)
                log(f"  Updated {len(results)} tickers")
            except Exception as e:
                log(f"  ERROR updating batch: {e}")

        failed_count = len(batch_tickers) - len(results)
        total_failed += failed_count

        if failed_count > 0:
            log(f"  Could not enrich {failed_count} tickers (no data found)")

        # Progress update
        elapsed = time.time() - start_time
        processed = batch_start + len(batch_tickers)
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (len(all_tickers) - processed) / rate if rate > 0 else 0

        log(f"  Progress: {processed}/{len(all_tickers)} | "
            f"Rate: {rate:.1f}/sec | "
            f"ETA: {remaining/60:.1f} min")

        # Small delay between batches to be nice to APIs
        time.sleep(1)

    elapsed_total = time.time() - start_time
    log(f"\nDone! Enriched {total_enriched} tickers in {elapsed_total/60:.1f} minutes")
    log(f"Failed to enrich: {total_failed} tickers")

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enrich tickers with sector and market cap data')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size for processing')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--max', type=int, default=None, help='Max tickers to process (for testing)')

    args = parser.parse_args()

    log(f"Starting enrichment with batch_size={args.batch_size}, workers={args.workers}")
    success = enrich_tickers(
        batch_size=args.batch_size,
        num_workers=args.workers,
        max_tickers=args.max
    )
    sys.exit(0 if success else 1)
