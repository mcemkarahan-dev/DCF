#!/usr/bin/env python3
"""
Example Usage Script
Demonstrates key features of the DCF Analyzer
"""

from main import DCFAnalyzer
from config import get_dcf_preset, get_screening_preset, list_presets
import time


def demo_single_stock_analysis(analyzer):
    """Demo: Analyze a single stock"""
    print("\n" + "="*60)
    print("DEMO 1: Single Stock Analysis")
    print("="*60)
    
    # Analyze with default parameters
    print("\nAnalyzing Apple (AAPL) with moderate parameters...")
    result = analyzer.analyze_stock('AAPL', params=get_dcf_preset('moderate'))
    
    if result:
        print(f"\nResult: {'UNDERVALUED' if result['discount'] > 0 else 'OVERVALUED'}")
        print(f"Recommendation: {'BUY' if result['discount'] > 20 else 'HOLD' if result['discount'] > -10 else 'SELL'}")


def demo_multiple_analyses(analyzer):
    """Demo: Analyze multiple stocks with different parameter sets"""
    print("\n" + "="*60)
    print("DEMO 2: Multiple Stocks with Different Parameters")
    print("="*60)
    
    stocks = ['AAPL', 'MSFT', 'GOOGL']
    
    for ticker in stocks:
        print(f"\n--- {ticker} ---")
        try:
            # Analyze with conservative parameters
            result = analyzer.analyze_stock(ticker, params=get_dcf_preset('conservative'))
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"Error: {e}")


def demo_screening(analyzer):
    """Demo: Screen for opportunities"""
    print("\n" + "="*60)
    print("DEMO 3: Screening for Opportunities")
    print("="*60)
    
    # Use preset screening criteria
    filters = get_screening_preset('moderate_value')
    
    print(f"\nApplying filters: {filters}")
    results = analyzer.screen_stocks(filters=filters, top_n=10)
    
    if results:
        print(f"\nFound {len(results)} opportunities!")


def demo_trending_analysis(analyzer):
    """Demo: Analyze trends over time"""
    print("\n" + "="*60)
    print("DEMO 4: Trending Analysis")
    print("="*60)
    
    ticker = 'AAPL'
    print(f"\nAnalyzing historical trend for {ticker}...")
    
    # First, create some historical data by running multiple analyses
    # In real usage, this would be from running the analyzer over days/weeks
    
    analyzer.show_trending(ticker, periods=5)


def demo_export(analyzer):
    """Demo: Export results"""
    print("\n" + "="*60)
    print("DEMO 5: Export Results to JSON")
    print("="*60)
    
    filters = {'min_discount_pct': 10.0}
    analyzer.export_results(filename='demo_export.json', filters=filters)


def demo_custom_parameters(analyzer):
    """Demo: Use custom DCF parameters"""
    print("\n" + "="*60)
    print("DEMO 6: Custom DCF Parameters")
    print("="*60)
    
    # Define custom parameters for a high-growth tech stock
    custom_params = {
        'wacc': 0.08,                    # 8% discount rate
        'terminal_growth_rate': 0.03,    # 3% perpetual growth
        'projection_years': 10,          # 10-year projection
        'revenue_growth_rate': 0.18,     # 18% annual revenue growth
        'conservative_adjustment': 0.10  # 10% margin of safety
    }
    
    print("\nCustom parameters for high-growth stock:")
    for key, value in custom_params.items():
        print(f"  {key}: {value}")
    
    print("\nAnalyzing with custom parameters...")
    result = analyzer.analyze_stock('AAPL', params=custom_params)


def interactive_demo():
    """Interactive demo mode"""
    print("""
╔════════════════════════════════════════════════════════════╗
║          DCF STOCK ANALYZER - INTERACTIVE DEMO             ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Check for API key
    api_key = input("\nEnter your Financial Modeling Prep API key (or 'demo' for limited testing): ").strip()
    
    if not api_key:
        api_key = 'demo'
        print("\nUsing demo key (limited to AAPL, MSFT, GOOGL)")
    
    analyzer = DCFAnalyzer(api_key=api_key)
    
    while True:
        print("\n" + "="*60)
        print("DEMO OPTIONS:")
        print("="*60)
        print("1. Single stock analysis")
        print("2. Multiple stocks with different parameters")
        print("3. Screen for opportunities")
        print("4. Trending analysis")
        print("5. Export results")
        print("6. Custom parameters")
        print("7. Show available presets")
        print("8. Run all demos")
        print("0. Exit")
        print("="*60)
        
        choice = input("\nSelect option (0-8): ").strip()
        
        if choice == '1':
            demo_single_stock_analysis(analyzer)
        elif choice == '2':
            demo_multiple_analyses(analyzer)
        elif choice == '3':
            demo_screening(analyzer)
        elif choice == '4':
            demo_trending_analysis(analyzer)
        elif choice == '5':
            demo_export(analyzer)
        elif choice == '6':
            demo_custom_parameters(analyzer)
        elif choice == '7':
            list_presets()
        elif choice == '8':
            print("\nRunning all demos...")
            demo_single_stock_analysis(analyzer)
            time.sleep(2)
            demo_multiple_analyses(analyzer)
            time.sleep(2)
            demo_screening(analyzer)
            time.sleep(2)
            demo_trending_analysis(analyzer)
            time.sleep(2)
            demo_export(analyzer)
            time.sleep(2)
            demo_custom_parameters(analyzer)
        elif choice == '0':
            print("\nExiting demo. Happy analyzing!")
            break
        else:
            print("\nInvalid option. Please try again.")
        
        input("\nPress Enter to continue...")


def quick_start_example():
    """Quick start example - no interaction needed"""
    print("""
╔════════════════════════════════════════════════════════════╗
║          DCF STOCK ANALYZER - QUICK START EXAMPLE          ║
╚════════════════════════════════════════════════════════════╝

This example shows basic usage. You'll need an API key from:
https://financialmodelingprep.com/developer/docs/
    """)
    
    # Initialize with demo key
    analyzer = DCFAnalyzer(api_key='demo')
    
    # Example 1: Analyze single stock
    print("\n1. Analyzing Apple with moderate parameters...")
    result = analyzer.analyze_stock('AAPL', params=get_dcf_preset('moderate'))
    
    time.sleep(2)
    
    # Example 2: Screen for opportunities
    print("\n2. Screening for undervalued stocks...")
    stats = analyzer.screener.get_stats_summary()
    print(f"\nDatabase contains {stats['total_stocks']} analyzed stocks")
    
    if stats['total_stocks'] > 0:
        top_opportunities = analyzer.screener.get_top_opportunities(n=5)
        print(f"\nTop 5 opportunities:")
        for i, stock in enumerate(top_opportunities, 1):
            print(f"{i}. {stock['ticker']}: {stock['discount_pct']:.1f}% discount")
    
    # Example 3: Export results
    print("\n3. Exporting results...")
    analyzer.export_results(filename='quick_start_results.json')
    
    print("\n" + "="*60)
    print("Quick start complete! Check README.md for more examples.")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_start_example()
    else:
        interactive_demo()
