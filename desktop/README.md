# DCF Stock Analyzer

A powerful Python tool for mass DCF (Discounted Cash Flow) analysis of stocks to find mispriced opportunities across entire exchanges.

## Features

- **Mass DCF Analysis**: Analyze all stocks in an exchange (NYSE, NASDAQ, etc.)
- **Historical Tracking**: Store all DCF calculations to track intrinsic value trends over time
- **Configurable Models**: Multiple DCF parameter presets (conservative, moderate, aggressive)
- **Advanced Screening**: Filter stocks by discount %, intrinsic value, price, and more
- **Trending Analysis**: See how intrinsic values change over time
- **Multiple Data Sources**: Uses Financial Modeling Prep API (free tier available)

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Get a free API key from Financial Modeling Prep:
   - Visit: https://financialmodelingprep.com/developer/docs/
   - Sign up for free account (250 requests/day)
   - Copy your API key

## Quick Start

### 1. Analyze a Single Stock

```bash
python main.py --api-key YOUR_API_KEY analyze AAPL
```

This will:
- Fetch financial data for Apple
- Calculate DCF intrinsic value
- Compare to current price
- Save results to database

### 2. Analyze Multiple Stocks from an Exchange

```bash
# Analyze first 50 NASDAQ stocks
python main.py --api-key YOUR_API_KEY batch NASDAQ --limit 50
```

### 3. Screen for Opportunities

```bash
# Find stocks trading 15%+ below intrinsic value
python main.py screen --min-discount 15 --top 20
```

### 4. View Trending Analysis

```bash
# See how intrinsic value has changed over time
python main.py trending AAPL --periods 10
```

### 5. Export Results

```bash
# Export top opportunities to JSON
python main.py export --output opportunities.json --min-discount 20
```

## Usage Examples

### Custom DCF Parameters

```bash
# Use custom WACC and growth rates
python main.py --api-key YOUR_API_KEY analyze MSFT \
  --wacc 0.09 \
  --growth 0.12 \
  --terminal 0.03
```

### Advanced Screening

```python
from main import DCFAnalyzer

analyzer = DCFAnalyzer(api_key="YOUR_API_KEY")

# Custom screening filters
filters = {
    'min_discount_pct': 25,      # At least 25% discount
    'max_discount_pct': 70,       # But not extreme discounts (potential value traps)
    'min_intrinsic_value': 20,   # Minimum $20 intrinsic value
    'max_current_price': 100,    # Maximum $100 current price
    'calculation_recency_days': 7 # Calculated within last week
}

results = analyzer.screen_stocks(filters=filters)
```

### Batch Analysis with Custom Parameters

```python
from main import DCFAnalyzer

analyzer = DCFAnalyzer(api_key="YOUR_API_KEY")

# Conservative parameters for mature companies
params = {
    'wacc': 0.11,
    'terminal_growth_rate': 0.02,
    'revenue_growth_rate': 0.05,
    'conservative_adjustment': 0.15  # 15% margin of safety
}

analyzer.analyze_exchange('NYSE', limit=100, params=params)
```

## DCF Calculation Models

The tool supports two DCF models:

### 1. Simple FCF Growth Model
- Projects Free Cash Flow using constant growth rate
- Best for stable, predictable businesses

### 2. Revenue-Based Model (Default)
- Projects revenue growth
- Applies historical FCF margin
- More sophisticated for growing companies

## Configuration Presets

Built-in parameter presets in `config.py`:

- **Conservative**: High WACC (12%), low growth, 15% margin of safety
- **Moderate**: Balanced assumptions (10% WACC)
- **Aggressive**: Lower WACC (8%), higher growth for tech stocks
- **High Growth**: For fast-growing companies (20% revenue growth)
- **Value**: For mature, stable businesses

```python
from config import get_dcf_preset
from main import DCFAnalyzer

analyzer = DCFAnalyzer(api_key="YOUR_API_KEY")
params = get_dcf_preset('conservative')
analyzer.analyze_stock('AAPL', params=params)
```

## Database Schema

The tool uses SQLite to store:

- **stocks**: Company information
- **financial_data**: Historical financial statements
- **dcf_calculations**: All DCF calculations (with full history)
- **screening_results**: Saved screening sessions

Historical tracking allows you to:
- See how intrinsic value trends over time
- Identify improving vs. deteriorating businesses
- Track when opportunities emerge or disappear

## Screening Features

### Pre-built Screens

```python
from screener import StockScreener
from database import DCFDatabase

db = DCFDatabase()
screener = StockScreener(db)

# Top opportunities by discount
top = screener.get_top_opportunities(n=20, min_discount=15)

# Stocks with improving intrinsic values
improving = screener.get_improving_stocks(min_avg_change=5.0, min_periods=3)

# Value traps (trading way above intrinsic value)
overvalued = screener.get_value_traps(max_discount=-30)
```

### Custom Screening Functions

```python
def my_custom_screen(calc):
    """Example: Find high-quality discounts"""
    return (
        calc['discount_pct'] > 20 and           # 20%+ discount
        calc['intrinsic_value'] > 50 and        # $50+ intrinsic value
        calc['wacc'] < 0.11                     # Reasonable risk
    )

results = screener.custom_screen(my_custom_screen)
```

## API Rate Limits

Free tier of Financial Modeling Prep:
- 250 requests per day
- Each stock analysis uses ~5-7 API calls
- Can analyze ~35-50 stocks per day on free tier

**Tip**: Use `--delay` parameter to avoid hitting rate limits:
```bash
python main.py batch NASDAQ --limit 30 --delay 2.0
```

For production use, consider upgrading to paid tier for unlimited requests.

## Data Sources

Currently supports Financial Modeling Prep API. Easy to extend to other sources:

1. Create new fetcher class in `data_fetcher.py`
2. Implement required methods: `get_financial_data_complete()`
3. Update `main.py` to use new fetcher

Alternative data sources you could integrate:
- Alpha Vantage
- Yahoo Finance (yfinance)
- Polygon.io
- IEX Cloud

## Output Examples

### Analysis Output
```
============================================================
Analyzing AAPL
============================================================
Fetching data for AAPL...

Company: Apple Inc.
Sector: Technology
Current Price: $180.50
Intrinsic Value: $225.30
Discount/Premium: +24.8%
*** UNDERVALUED - Trading 24.8% below intrinsic value ***
```

### Screening Report
```
================================================================================
DCF STOCK SCREENING REPORT
Generated: 2024-01-15 10:30:00
================================================================================

SUMMARY STATISTICS:
  Total stocks analyzed: 150
  Undervalued: 45
  Overvalued: 62
  Fairly valued: 43
  Average discount: -5.2%

TOP 20 OPPORTUNITIES:

Ticker     Current    Intrinsic    Discount   Model          
--------------------------------------------------------------------------------
XYZ        $45.20     $72.50       +60.4%     revenue_based  
ABC        $28.75     $42.30       +47.1%     revenue_based  
...
```

## Advanced Features

### Trend Analysis
Track how intrinsic value changes over time:

```python
trend = analyzer.screener.analyze_trending('AAPL', periods=10)
print(f"Intrinsic Value Trend: {trend['intrinsic_value_trend']}")
print(f"Average Change: {trend['avg_iv_change_pct']:.2f}%")
```

### Export to Excel (Future Enhancement)
While currently exports to JSON, you can easily extend to Excel:

```python
import pandas as pd

results = screener.get_top_opportunities(n=50)
df = pd.DataFrame(results)
df.to_excel('dcf_analysis.xlsx', index=False)
```

## Best Practices

1. **Run Regular Updates**: Analyze stocks weekly/monthly to track changes
2. **Use Conservative Parameters**: Better to underestimate than overestimate
3. **Combine with Other Analysis**: DCF is powerful but not the only tool
4. **Verify Assumptions**: Check if growth rates and margins are realistic
5. **Consider Quality**: A 50% discount on a failing business is still expensive

## Troubleshooting

### "Error fetching data"
- Check API key is valid
- Ensure you haven't exceeded rate limits
- Verify ticker symbol is correct

### "Could not calculate DCF"
- Stock may lack sufficient financial history
- Check if company is too new or has unusual financials
- Try different parameters

### "Database locked"
- Close any other programs accessing the database
- Ensure only one instance is running

## Contributing

Feel free to extend this tool:
- Add new DCF models (3-stage, H-model)
- Integrate additional data sources
- Build web interface
- Add more screening criteria
- Implement machine learning for parameter optimization

## License

MIT License - feel free to use and modify as needed.

## Disclaimer

This tool is for educational and research purposes only. DCF valuations are based on assumptions and projections that may not materialize. Always do your own research and consult with a financial advisor before making investment decisions.

## Support

For issues or questions:
1. Check the documentation above
2. Review example code in each module
3. Test with demo API key first (limited to AAPL, GOOGL, MSFT)
