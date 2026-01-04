#!/usr/bin/env python3
"""
Enrich Market Cap Data

Focuses specifically on getting market cap for tickers that already have
sector data but are missing market cap. Uses yfinance fast_info for speed.

Usage:
    python enrich_market_cap.py [--batch-size 500] [--workers 8]
"""

import os
import sys
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

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


def ticker_variants(ticker: str) -> list:
    """Generate ticker variants to try (handles BRK.B vs BRK-B)"""
    base = ticker.upper()
    variants = [base]
    if '.' in base:
        variants.append(base.replace('.', '-'))
    if '-' in base:
        variants.append(base.replace('-', '.'))
    return list(dict.fromkeys(variants))  # Remove duplicates, preserve order


def get_market_cap_yahoo(ticker: str) -> Tuple[str, Optional[int]]:
    """Get market cap from Yahoo Finance using fast_info"""
    import yfinance as yf

    for variant in ticker_variants(ticker):
        try:
            stock = yf.Ticker(variant)

            # Try fast_info first (faster and more reliable)
            try:
                fast = stock.fast_info
                if hasattr(fast, 'market_cap') and fast.market_cap:
                    mkt_cap = int(fast.market_cap)
                    if mkt_cap > 0:
                        return (ticker, mkt_cap)
            except Exception:
                pass

            # Fallback to info dict
            try:
                info = stock.info
                if info and info.get('marketCap'):
                    mkt_cap = int(info['marketCap'])
                    if mkt_cap > 0:
                        return (ticker, mkt_cap)
            except Exception:
                pass

        except Exception:
            continue

    return (ticker, None)


def enrich_market_caps(batch_size: int = 500, num_workers: int = 8, max_tickers: int = None):
    """Main enrichment function for market cap"""

    from supabase import create_client

    secrets = load_secrets()
    supabase_url = secrets.get('SUPABASE_URL')
    supabase_key = secrets.get('SUPABASE_KEY')

    if not all([supabase_url, supabase_key]):
        log("ERROR: Missing credentials in .streamlit/secrets.toml")
        return False

    supabase = create_client(supabase_url, supabase_key)

    # Get tickers that have sector but missing market cap
    log("Fetching tickers with sector but missing market cap...")

    all_tickers = []
    offset = 0
    page_size = 1000
    us_exchanges = ['NYSE', 'NASDAQ', 'AMEX']

    while True:
        # Get tickers where sector is set but market_cap is 0 or null
        query = supabase.table('tickers') \
            .select('ticker,exchange') \
            .neq('sector', 'N/A') \
            .or_('market_cap.is.null,market_cap.eq.0')

        response = query.range(offset, offset + page_size - 1).execute()
        batch = response.data if response.data else []

        if not batch:
            break

        for t in batch:
            # Only US exchanges
            if t.get('exchange') in us_exchanges:
                all_tickers.append(t['ticker'])

        if len(batch) < page_size:
            break
        offset += page_size

    log(f"Found {len(all_tickers)} tickers needing market cap data")

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

        results = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(get_market_cap_yahoo, ticker): ticker
                      for ticker in batch_tickers}

            for future in as_completed(futures):
                ticker, mkt_cap = future.result()
                if mkt_cap and mkt_cap > 0:
                    results.append({
                        'ticker': ticker,
                        'market_cap': mkt_cap,
                        'market_cap_universe': get_market_cap_universe(mkt_cap)
                    })

        # Update Supabase
        if results:
            try:
                for r in results:
                    supabase.table('tickers') \
                        .update({
                            'market_cap': r['market_cap'],
                            'market_cap_universe': r['market_cap_universe']
                        }) \
                        .eq('ticker', r['ticker']) \
                        .execute()

                total_enriched += len(results)
                log(f"  Updated {len(results)} tickers with market cap")
            except Exception as e:
                log(f"  ERROR updating batch: {e}")

        failed_count = len(batch_tickers) - len(results)
        total_failed += failed_count

        if failed_count > 0:
            log(f"  Could not get market cap for {failed_count} tickers")

        # Progress
        elapsed = time.time() - start_time
        processed = batch_start + len(batch_tickers)
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (len(all_tickers) - processed) / rate if rate > 0 else 0

        log(f"  Progress: {processed}/{len(all_tickers)} | "
            f"Rate: {rate:.1f}/sec | "
            f"ETA: {remaining/60:.1f} min")

        # Small delay between batches
        time.sleep(0.5)

    elapsed_total = time.time() - start_time
    log(f"\nDone! Enriched {total_enriched} tickers with market cap in {elapsed_total/60:.1f} minutes")
    log(f"Failed to get market cap: {total_failed} tickers")

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enrich tickers with market cap data')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--max', type=int, default=None, help='Max tickers to process')

    args = parser.parse_args()

    log(f"Starting market cap enrichment with batch_size={args.batch_size}, workers={args.workers}")
    success = enrich_market_caps(
        batch_size=args.batch_size,
        num_workers=args.workers,
        max_tickers=args.max
    )
    sys.exit(0 if success else 1)
