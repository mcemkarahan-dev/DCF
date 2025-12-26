#!/usr/bin/env python3
"""
DCF Stock Analyzer - Main Application
Mass DCF analysis tool for finding mispriced stocks
"""

import argparse
import json
import os
from datetime import datetime
from typing import List, Dict
from database import DCFDatabase
from dcf_calculator import DCFCalculator
from screener import StockScreener


def format_value(value):
    """Format large numbers with T/B/M notation"""
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.1f}T"
    elif abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"


class DCFAnalyzer:
    def __init__(self, api_key: str = None, db_path: str = "dcf_analysis.db", data_source: str = "yahoo"):
        """
        Initialize DCF Analyzer
        
        data_source options:
        - "yahoo": Yahoo Finance (free, 4-5 years of data, no API key needed)
        - "roic": Roic.ai (paid, 30+ years of data, requires API key)
        """
        self.db = DCFDatabase(db_path)
        self.data_source = data_source
        
        # Initialize appropriate data fetcher
        if data_source == "roic":
            from data_fetcher_roic import RoicDataFetcher
            self.fetcher = RoicDataFetcher(api_key)
            print("Using Roic.ai data source (30+ years of history)")
        else:  # yahoo (default)
            from data_fetcher_yahoo import YahooFinanceFetcher
            self.fetcher = YahooFinanceFetcher(api_key)
            print("Using Yahoo Finance data source (4-5 years of history)")
        
        self.calculator = DCFCalculator()
        self.screener = StockScreener(self.db)
    
    def analyze_stock(self, ticker: str, params: Dict = None, save: bool = True, years_back: int = None) -> Dict:
        """
        Analyze a single stock with DCF
        years_back: Number of years of historical data to fetch (only used with roic.ai)
        """
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker}")
        print(f"{'='*60}")
        
        # Determine years_back based on data source and parameters
        if years_back is None:
            if self.data_source == "roic":
                # For roic, use projection_years from params or default to 10
                years_back = params.get('projection_years', 10) if params else 10
            else:
                # Yahoo Finance only has 4-5 years anyway
                years_back = 5
        
        # Fetch data - roic supports years_back parameter
        if hasattr(self.fetcher, 'get_financial_data_complete'):
            if self.data_source == "roic":
                financial_data = self.fetcher.get_financial_data_complete(ticker, years_back=years_back)
            else:
                financial_data = self.fetcher.get_financial_data_complete(ticker)
        else:
            financial_data = self.fetcher.get_financial_data_complete(ticker)
        
        if not financial_data['profile']:
            print(f"Error: Could not fetch data for {ticker}")
            return None
        
        # Save company info
        profile = financial_data['profile']
        self.db.add_stock(
            ticker=ticker,
            company_name=profile.get('companyName'),
            exchange=profile.get('exchangeShortName'),
            sector=profile.get('sector'),
            industry=profile.get('industry')
        )
        
        # Save financial data
        if financial_data['cash_flows']:
            for cf in financial_data['cash_flows'][:5]:
                # Get matching income statement and balance sheet
                period_date = cf.get('date')
                
                # Find matching statements
                income = next((i for i in financial_data['income_statements'] 
                             if i.get('date') == period_date), {})
                balance = next((b for b in financial_data['balance_sheets'] 
                              if b.get('date') == period_date), {})
                
                fcf = self.fetcher.calculate_fcf_from_statements(cf)
                
                self.db.add_financial_data(
                    ticker=ticker,
                    period_date=period_date,
                    period_type=cf.get('period', 'annual'),
                    revenue=income.get('revenue', 0) or 0,
                    operating_income=income.get('operatingIncome', 0) or 0,
                    net_income=income.get('netIncome', 0) or 0,
                    free_cash_flow=fcf,
                    total_debt=balance.get('totalDebt', 0) or 0,
                    cash_and_equivalents=balance.get('cashAndCashEquivalents', 0) or 0,
                    shares_outstanding=balance.get('commonStock', 0) or 0
                )
        
        # Run DCF
        dcf_result = self.calculator.run_full_dcf(financial_data, params=params)
        
        if not dcf_result:
            print(f"Error: Could not calculate DCF for {ticker}")
            return None
        
        # Extract results
        intrinsic_value = dcf_result['intrinsic_value_per_share']
        current_price = financial_data['current_price']
        
        # Section 1: Company Info
        print(f"\nCompany: {profile.get('companyName')}")
        print(f"Sector: {profile.get('sector')}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Intrinsic Value: ${intrinsic_value:.2f}")
        
        discount = ((intrinsic_value - current_price) / current_price * 100) if current_price else 0
        print(f"Discount/Premium: {discount:+.2f}%")
        
        if discount > 20:
            print(f"*** UNDERVALUED - Trading {abs(discount):.1f}% below intrinsic value ***")
        elif discount < -20:
            print(f"*** OVERVALUED - Trading {abs(discount):.1f}% above intrinsic value ***")
        else:
            print(f"*** FAIRLY VALUED ***")
        
        # Section 2: DCF Parameters Used
        print(f"\nDCF Parameters:")
        
        # Show input type
        input_type = dcf_result.get('input_type', 'fcf')
        input_label = "EPS from Continuing Ops" if input_type == 'eps_cont_ops' else "Free Cash Flow per Share"
        print(f"  Input Type: {input_label}")
        
        print(f"  WACC (Discount Rate): {dcf_result['params']['wacc']*100:.1f}%")
        print(f"  Terminal Growth Rate: {dcf_result['params']['terminal_growth_rate']*100:.1f}%")
        
        # Show growth rate with historical comparison
        fcf_growth = dcf_result['params'].get('fcf_growth_rate', 0)
        historical_growth = dcf_result.get('historical_fcf_growth', 0)
        years_used = dcf_result.get('historical_years_used', 0)
        growth_label = "EPS Growth Rate" if input_type == 'eps_cont_ops' else "FCF Growth Rate"
        if historical_growth != 0 and years_used > 0:
            print(f"  {growth_label}: {fcf_growth*100:.1f}% (Historical {years_used}-yr: {historical_growth*100:.1f}%)")
        else:
            print(f"  {growth_label}: {fcf_growth*100:.1f}%")
        
        print(f"  Projection Years: {dcf_result['params']['projection_years']}")
        
        # Conservative adjustment is actually margin of safety
        margin_of_safety = dcf_result['params'].get('conservative_adjustment', 0.0)
        if margin_of_safety > 0:
            print(f"  Margin of Safety: {margin_of_safety*100:.1f}%")
        
        # Section 3: Valuation Breakdown
        print(f"\nValuation Breakdown:")
        
        # PV of future cash flows
        pv_fcf = dcf_result.get('pv_fcf', 0)
        total_fcf = sum(dcf_result.get('fcf_projections', []))
        projection_years = dcf_result['params']['projection_years']
        print(f"  PV of {projection_years} Years of FCF: {format_value(pv_fcf)} (Total FCF: {format_value(total_fcf)})")
        
        # Terminal value
        terminal_value_pv = dcf_result.get('pv_terminal', dcf_result['terminal_value'])
        terminal_value_actual = dcf_result['terminal_value']
        print(f"  PV of Terminal Value: {format_value(terminal_value_pv)} (Terminal Value: {format_value(terminal_value_actual)})")
        
        # Total equity value with market cap (before margin of safety)
        total_equity_value = dcf_result.get('equity_value', dcf_result['enterprise_value'])
        shares_outstanding = dcf_result.get('shares_outstanding', 1)
        market_cap = current_price * shares_outstanding if current_price and shares_outstanding > 0 else 0
        print(f"  Total Equity Value: {format_value(total_equity_value)} (Market Cap: {format_value(market_cap)})")
        
        # Equity value per share - use the intrinsic value which has margin of safety applied
        # This matches the "Intrinsic Value" shown above
        print(f"  Total Equity Value per Share: ${intrinsic_value:.2f} (Current Price: ${current_price:.2f})")
        
        # Save DCF calculation
        if save:
            self.db.save_dcf_calculation(
                ticker=ticker,
                model_type=params.get('model_type', 'revenue_based') if params else 'revenue_based',
                parameters=dcf_result['params'],
                intrinsic_value=intrinsic_value,
                current_price=current_price,
                wacc=dcf_result['params']['wacc'],
                terminal_growth_rate=dcf_result['params']['terminal_growth_rate'],
                projection_years=dcf_result['params']['projection_years'],
                fcf_projections=dcf_result['fcf_projections'],
                terminal_value=dcf_result['terminal_value'],
                enterprise_value=dcf_result['enterprise_value'],
                equity_value=dcf_result['equity_value'],
                shares_outstanding=dcf_result['shares_outstanding']
            )
        
        return {
            'ticker': ticker,
            'intrinsic_value': intrinsic_value,
            'current_price': current_price,
            'discount': discount,
            'dcf_result': dcf_result
        }
    
    def analyze_exchange(self, exchange: str, limit: int = None, 
                        params: Dict = None, delay: float = 1.0):
        """
        Analyze all stocks in an exchange
        """
        import time
        
        print(f"\nFetching tickers for {exchange}...")
        tickers = self.fetcher.get_exchange_tickers(exchange, limit=limit)
        
        print(f"Found {len(tickers)} tickers")
        print(f"Starting analysis... (this will take a while)")
        
        successful = 0
        failed = 0
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
            
            try:
                result = self.analyze_stock(ticker, params=params)
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error analyzing {ticker}: {e}")
                failed += 1
            
            # Rate limiting
            time.sleep(delay)
        
        print(f"\n{'='*60}")
        print(f"Analysis Complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"{'='*60}")
    
    def screen_stocks(self, filters: Dict = None, top_n: int = 20):
        """
        Screen stocks based on criteria
        """
        print(f"\n{'='*60}")
        print("STOCK SCREENING")
        print(f"{'='*60}")
        
        report = self.screener.generate_report(filters=filters, top_n=top_n)
        print(report)
        
        return self.screener.filter_by_criteria(filters) if filters else self.screener.get_top_opportunities(top_n)
    
    def show_trending(self, ticker: str, periods: int = 5):
        """
        Show trending analysis for a stock
        """
        trend = self.screener.analyze_trending(ticker, periods=periods)
        
        print(f"\n{'='*60}")
        print(f"TRENDING ANALYSIS: {ticker}")
        print(f"{'='*60}")
        print(f"Intrinsic Value Trend: {trend['intrinsic_value_trend']}")
        print(f"Average Change: {trend['avg_iv_change_pct']:.2f}%")
        print(f"Current Intrinsic Value: ${trend['current_intrinsic_value']:.2f}")
        print(f"Current Discount: {trend['current_discount']:.2f}%" if trend['current_discount'] else "N/A")
        print(f"\nHistorical Values:")
        
        for i, hist in enumerate(reversed(trend['history']), 1):
            calc_date = datetime.fromisoformat(hist['calculation_date']).strftime('%Y-%m-%d')
            print(f"  {i}. {calc_date}: ${hist['intrinsic_value']:.2f} "
                  f"(Current: ${hist['current_price']:.2f}, "
                  f"Discount: {hist['discount_pct']:.1f}%)")
    
    def export_results(self, filename: str = None, filters: Dict = None):
        """
        Export screening results to JSON
        """
        if filename is None:
            filename = f"dcf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if filters:
            results = self.screener.filter_by_criteria(filters)
        else:
            results = self.screener.get_top_opportunities(n=100)
        
        # Convert to serializable format
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'filters': filters,
            'results': results
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\nExported {len(results)} results to {filename}")


def main():
    parser = argparse.ArgumentParser(description='DCF Stock Analyzer')
    parser.add_argument('--api-key', help='API key (required for Roic.ai, optional for Yahoo Finance)')
    parser.add_argument('--db', default='dcf_analysis.db', help='Database path')
    parser.add_argument('--data-source', choices=['yahoo', 'roic'], default='yahoo',
                       help='Data source: yahoo (free, 4-5 years) or roic (paid, 30+ years)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze stock(s)')
    analyze_parser.add_argument('ticker', help='Stock ticker')
    analyze_parser.add_argument('--preset', help='Use a parameter preset from config.py')
    analyze_parser.add_argument('--wacc', type=float, help='WACC (default: 0.10)')
    analyze_parser.add_argument('--growth', type=float, help='FCF/EPS growth rate')
    analyze_parser.add_argument('--terminal', type=float, help='Terminal growth rate')
    analyze_parser.add_argument('--input-type', choices=['fcf', 'eps_cont_ops'], default='fcf', help='DCF input: fcf or eps_cont_ops (default: fcf)')
    analyze_parser.add_argument('--years-back', type=int, help='Years of historical data to fetch (roic.ai only, default: 10)')
    
    # Batch analyze command
    batch_parser = subparsers.add_parser('batch', help='Analyze multiple stocks')
    batch_parser.add_argument('exchange', help='Exchange (NYSE, NASDAQ, etc.)')
    batch_parser.add_argument('--limit', type=int, help='Limit number of stocks')
    batch_parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests')
    
    # Screen command
    screen_parser = subparsers.add_parser('screen', help='Screen stocks')
    screen_parser.add_argument('--min-discount', type=float, default=15.0, help='Minimum discount percentage')
    screen_parser.add_argument('--top', type=int, default=20, help='Show top N results')
    
    # Trending command
    trend_parser = subparsers.add_parser('trending', help='Show trending analysis')
    trend_parser.add_argument('ticker', help='Stock ticker')
    trend_parser.add_argument('--periods', type=int, default=5, help='Number of periods')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export results to JSON')
    export_parser.add_argument('--output', help='Output filename')
    export_parser.add_argument('--min-discount', type=float, help='Minimum discount percentage')
    
    # Save API key command
    save_key_parser = subparsers.add_parser('save-key', help='Save API key to file')
    save_key_parser.add_argument('key', help='API key to save')
    save_key_parser.add_argument('--source', choices=['yahoo', 'roic'], default='roic',
                                 help='Which data source this key is for (default: roic)')
    
    args = parser.parse_args()
    
    # Auto-load API key from file if not provided
    api_key = args.api_key
    if not api_key:
        # Try to load from source-specific file first
        if args.data_source == "roic" and os.path.exists("roic_api_key.txt"):
            with open("roic_api_key.txt", "r") as f:
                api_key = f.read().strip()
            print("Loaded API key from roic_api_key.txt")
        elif os.path.exists("api_key.txt"):
            with open("api_key.txt", "r") as f:
                api_key = f.read().strip()
            print("Loaded API key from api_key.txt")
    
    # Handle save-key command first (doesn't need analyzer)
    if args.command == 'save-key':
        filename = f"{args.source}_api_key.txt" if args.source == "roic" else "api_key.txt"
        with open(filename, "w") as f:
            f.write(args.key)
        print(f"✓ API key saved to {filename}")
        print(f"You can now run commands without --api-key flag")
        return
    
    # Initialize analyzer
    analyzer = DCFAnalyzer(api_key=api_key, db_path=args.db, data_source=args.data_source)
    
    # Execute command
    if args.command == 'analyze':
        params = {}
        
        # Check if preset is specified
        if args.preset:
            from config import get_dcf_preset
            preset_params = get_dcf_preset(args.preset)
            if preset_params:
                params = preset_params.copy()
                print(f"Using preset: {args.preset}")
            else:
                print(f"Warning: Preset '{args.preset}' not found, using defaults")
        
        # Individual parameters override preset
        if args.wacc:
            params['wacc'] = args.wacc
        if args.growth:
            params['fcf_growth_rate'] = args.growth
        if args.terminal:
            params['terminal_growth_rate'] = args.terminal
        # Note: argparse converts --input-type to args.input_type
        if hasattr(args, 'input_type') and args.input_type:
            params['dcf_input_type'] = args.input_type
            print(f"Using DCF input type: {args.input_type}")
        
        # Pass years_back if specified
        years_back = args.years_back if hasattr(args, 'years_back') else None
        
        analyzer.analyze_stock(args.ticker, params=params if params else None, years_back=years_back)
    
    elif args.command == 'batch':
        analyzer.analyze_exchange(args.exchange, limit=args.limit, delay=args.delay)
    
    elif args.command == 'screen':
        filters = {'min_discount_pct': args.min_discount}
        analyzer.screen_stocks(filters=filters, top_n=args.top)
    
    elif args.command == 'trending':
        analyzer.show_trending(args.ticker, periods=args.periods)
    
    elif args.command == 'export':
        filters = {}
        if args.min_discount:
            filters['min_discount_pct'] = args.min_discount
        analyzer.export_results(filename=args.output, filters=filters if filters else None)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
