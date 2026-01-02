#!/usr/bin/env python3
"""
Background Batch Worker for DCF Stock Screener

This script runs INDEPENDENTLY of the Streamlit UI and processes batch jobs
stored in Supabase. It can be:
1. Run manually: python batch_worker.py
2. Run via GitHub Actions on a schedule
3. Run on any server that stays awake

The worker picks up pending jobs from Supabase, processes them, and stores
results back in Supabase. The UI can then display results from the database.

Environment variables required:
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Your Supabase anon/service key
- ROIC_API_KEY: (optional) Your ROIC.ai API key
"""

import os
import sys
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables from command line args if provided
# Usage: python batch_worker.py --supabase-url=XXX --supabase-key=XXX --roic-key=XXX
for arg in sys.argv[1:]:
    if arg.startswith('--supabase-url='):
        os.environ['SUPABASE_URL'] = arg.split('=', 1)[1]
    elif arg.startswith('--supabase-key='):
        os.environ['SUPABASE_KEY'] = arg.split('=', 1)[1]
    elif arg.startswith('--roic-key='):
        os.environ['ROIC_API_KEY'] = arg.split('=', 1)[1]

# Import after setting env vars
import db_storage
from batch_screener import BatchScreener
from dcf_calculator import DCFAnalyzer
from config import PRESET_CONFIGS


def log(msg: str):
    """Print timestamped log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def process_job(job: dict) -> bool:
    """
    Process a single batch job.
    Returns True if completed successfully, False if failed.
    """
    job_id = job['job_id']
    filters = job.get('filters', {})

    log(f"Starting job {job_id}: {job.get('job_name', 'Unnamed')}")
    log(f"Filters: {filters}")

    # Mark job as running
    db_storage.update_batch_job(
        job_id,
        status='running',
        started_at=datetime.now().isoformat()
    )

    try:
        # Initialize screener
        roic_key = os.environ.get('ROIC_API_KEY')
        screener = BatchScreener(
            data_source="roic" if roic_key else "yahoo",
            api_key=roic_key
        )

        # Get recently checked tickers to skip
        recently_checked = db_storage.get_recently_checked_tickers(filters, days=7)
        log(f"Skipping {len(recently_checked)} already-checked tickers")

        # Track progress
        processed = 0
        matched = 0
        total = 0

        def on_progress(current, total_count, message, is_filtering):
            nonlocal total
            total = total_count
            if current % 50 == 0:  # Log every 50 tickers
                log(f"Progress: {current}/{total_count} - {message}")
                db_storage.update_batch_job(
                    job_id,
                    processed_tickers=current,
                    total_tickers=total_count,
                    current_ticker=message.replace('Checking ', '').replace('...', '')
                )

        def on_match(stock):
            nonlocal matched
            matched += 1
            log(f"MATCH: {stock['ticker']} - {stock.get('name', 'N/A')}")

            # Run DCF analysis on matched stocks
            try:
                analyzer = DCFAnalyzer()
                dcf_params = PRESET_CONFIGS['moderate']

                # Get financial data
                metrics = stock.get('metrics', {})
                full_data = metrics.get('full_data')

                if full_data:
                    result = analyzer.run_analysis(
                        stock['ticker'],
                        dcf_params,
                        existing_data=full_data
                    )
                    if result:
                        result['run_date'] = datetime.now().isoformat()
                        result['batch_job_id'] = job_id
                        db_storage.save_analysis(result)
                        log(f"Saved DCF analysis for {stock['ticker']}")
            except Exception as e:
                log(f"Error running DCF for {stock['ticker']}: {e}")

        def on_checked(ticker, passed):
            nonlocal processed
            processed += 1
            db_storage.save_checked_ticker(ticker, filters, passed)

        # Run the screening
        log("Starting stock screening...")
        results = list(screener.screen_stocks_streaming(
            filters=filters,
            progress_callback=on_progress,
            match_callback=on_match,
            checked_callback=on_checked,
            exclude_tickers=recently_checked
        ))

        # Mark job as completed
        db_storage.update_batch_job(
            job_id,
            status='completed',
            processed_tickers=processed,
            total_tickers=total,
            matched_tickers=matched,
            completed_at=datetime.now().isoformat()
        )

        log(f"Job {job_id} completed: {processed} processed, {matched} matched")
        return True

    except Exception as e:
        log(f"Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()

        db_storage.update_batch_job(
            job_id,
            status='failed',
            error_message=str(e),
            completed_at=datetime.now().isoformat()
        )
        return False


def run_worker(once: bool = False, max_jobs: int = None):
    """
    Run the batch worker.

    Args:
        once: If True, process pending jobs once and exit.
              If False, run continuously, checking for new jobs.
        max_jobs: Maximum number of jobs to process (None = unlimited)
    """
    log("=" * 60)
    log("DCF Batch Worker Started")
    log(f"Storage backend: {db_storage.get_storage_backend()}")
    log("=" * 60)

    if not db_storage.USE_SUPABASE:
        log("ERROR: Supabase not configured. Batch worker requires Supabase.")
        log("Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return

    jobs_processed = 0

    while True:
        # Get pending jobs
        jobs = db_storage.get_pending_batch_jobs()

        if not jobs:
            if once:
                log("No pending jobs. Exiting.")
                break
            else:
                log("No pending jobs. Waiting 60 seconds...")
                time.sleep(60)
                continue

        log(f"Found {len(jobs)} pending job(s)")

        for job in jobs:
            if max_jobs and jobs_processed >= max_jobs:
                log(f"Reached max jobs limit ({max_jobs}). Exiting.")
                return

            success = process_job(job)
            jobs_processed += 1

            if success:
                log(f"Job completed successfully")
            else:
                log(f"Job failed")

            # Small delay between jobs
            time.sleep(2)

        if once:
            break

    log("=" * 60)
    log(f"Worker finished. Processed {jobs_processed} job(s).")
    log("=" * 60)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='DCF Batch Worker')
    parser.add_argument('--once', action='store_true',
                       help='Process pending jobs once and exit')
    parser.add_argument('--max-jobs', type=int, default=None,
                       help='Maximum number of jobs to process')
    parser.add_argument('--supabase-url', type=str,
                       help='Supabase URL (or set SUPABASE_URL env var)')
    parser.add_argument('--supabase-key', type=str,
                       help='Supabase key (or set SUPABASE_KEY env var)')
    parser.add_argument('--roic-key', type=str,
                       help='ROIC API key (or set ROIC_API_KEY env var)')

    args = parser.parse_args()

    # Set env vars from args if provided
    if args.supabase_url:
        os.environ['SUPABASE_URL'] = args.supabase_url
    if args.supabase_key:
        os.environ['SUPABASE_KEY'] = args.supabase_key
    if args.roic_key:
        os.environ['ROIC_API_KEY'] = args.roic_key

    run_worker(once=args.once, max_jobs=args.max_jobs)
