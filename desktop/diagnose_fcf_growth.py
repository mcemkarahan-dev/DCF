"""
Diagnostic script to show raw FCF data and growth calculation
Usage: python diagnose_fcf_growth.py TICKER
"""

import sys
from data_fetcher_roic import RoicDataFetcher

def diagnose_fcf_growth(ticker, api_key):
    """Show raw FCF data and growth calculation"""
    
    print(f"\n{'='*70}")
    print(f"FCF GROWTH DIAGNOSTIC FOR {ticker}")
    print(f"{'='*70}\n")
    
    # Fetch data
    fetcher = RoicDataFetcher(api_key)
    data = fetcher.get_financial_data_complete(ticker, years_back=10)
    
    cash_flows = data.get('cash_flows', [])
    
    if not cash_flows:
        print("ERROR: No cash flow data available")
        return
    
    print(f"Total periods fetched: {len(cash_flows)}\n")
    
    # Extract FCF values
    print("=== RAW FCF VALUES (newest to oldest) ===\n")
    fcf_values = []
    
    for i, cf in enumerate(cash_flows):
        date = cf.get('date')
        fcf = cf.get('freeCashFlow', 0)
        operating_cf = cf.get('operatingCashFlow', 0)
        capex = cf.get('capitalExpenditure', 0)
        
        fcf_values.append(fcf)
        
        print(f"Period {i}: {date}")
        print(f"  Operating CF: ${operating_cf:,.0f}")
        print(f"  CapEx: ${capex:,.0f}")
        print(f"  FCF: ${fcf:,.0f}")
        print()
    
    # Calculate 5-year growth
    print("\n=== 5-YEAR FCF GROWTH CALCULATION ===\n")
    
    # Use first 5 values
    fcf_5yr = fcf_values[:5]
    print(f"5-year FCF values (newest to oldest):")
    for i, fcf in enumerate(fcf_5yr):
        print(f"  Year {i}: ${fcf:,.0f}")
    
    # Filter positive
    positive_fcf = [fcf for fcf in fcf_5yr if fcf > 0]
    print(f"\nPositive FCF values: {len(positive_fcf)} periods")
    
    if len(positive_fcf) >= 2:
        ending_value = positive_fcf[0]  # Most recent
        beginning_value = positive_fcf[-1]  # Oldest
        years = len(positive_fcf) - 1
        
        print(f"\nEnding Value (most recent): ${ending_value:,.0f}")
        print(f"Beginning Value (oldest in 5-yr): ${beginning_value:,.0f}")
        print(f"Number of years: {years}")
        
        if beginning_value > 0 and years > 0:
            cagr = (ending_value / beginning_value) ** (1 / years) - 1
            
            print(f"\nCAGR Formula:")
            print(f"  ({ending_value:,.0f} / {beginning_value:,.0f}) ^ (1/{years}) - 1")
            print(f"  = ({ending_value/beginning_value:.4f}) ^ ({1/years:.4f}) - 1")
            print(f"  = {(ending_value/beginning_value)**(1/years):.4f} - 1")
            print(f"  = {cagr:.4f}")
            print(f"\n  RESULT: {cagr*100:.1f}%")
            
            # Show year-over-year for context
            print(f"\n=== YEAR-OVER-YEAR GROWTH (for context) ===\n")
            for i in range(len(positive_fcf)-1):
                curr = positive_fcf[i]
                prev = positive_fcf[i+1]
                yoy_growth = (curr - prev) / prev if prev != 0 else 0
                print(f"  Year {i} to {i+1}: {yoy_growth*100:+.1f}%  (${prev:,.0f} → ${curr:,.0f})")
        else:
            print("\nCannot calculate CAGR: beginning value <= 0")
    else:
        print("\nNot enough positive FCF values")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_fcf_growth.py TICKER")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    api_key = "1e702063f1534ee1b0485da8f461bda9"  # Your roic.ai key
    
    diagnose_fcf_growth(ticker, api_key)
