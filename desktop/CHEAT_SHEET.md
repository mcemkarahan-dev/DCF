# DCF Analyzer - Quick Reference Cheat Sheet

## 🚀 First Time Setup (One-time only)

```bash
# 1. Install Python from python.org
# 2. Open terminal in dcf_analyzer folder
# 3. Install libraries:
pip install -r requirements.txt        # Windows
pip3 install -r requirements.txt       # Mac/Linux

# 4. Test installation:
python test_installation.py            # Windows
python3 test_installation.py           # Mac/Linux

# 5. Get free API key from:
# https://financialmodelingprep.com/developer/docs/
```

---

## 📝 Essential Commands

### Analyze Single Stock
```bash
# Windows
python main.py --api-key YOUR_KEY analyze TICKER

# Mac/Linux
python3 main.py --api-key YOUR_KEY analyze TICKER

# Examples:
python main.py --api-key abc123 analyze AAPL
python main.py --api-key abc123 analyze MSFT
python main.py --api-key abc123 analyze TSLA
```

### Analyze Multiple Stocks
```bash
# Analyze first 20 NASDAQ stocks
python main.py --api-key YOUR_KEY batch NASDAQ --limit 20

# Analyze first 50 NYSE stocks with 2-second delay
python main.py --api-key YOUR_KEY batch NYSE --limit 50 --delay 2.0

# Available exchanges: NASDAQ, NYSE, AMEX
```

### Screen for Opportunities
```bash
# Find stocks 15%+ undervalued, show top 20
python main.py screen --min-discount 15 --top 20

# Find stocks 25%+ undervalued, show top 10
python main.py screen --min-discount 25 --top 10

# Note: Must have analyzed stocks first!
```

### View Trending Analysis
```bash
# Show how intrinsic value has changed over time
python main.py trending AAPL --periods 5
python main.py trending MSFT --periods 10

# Note: Requires multiple analyses over time
```

### Export Results
```bash
# Export all undervalued stocks to JSON
python main.py export --output results.json --min-discount 15
```

---

## ⚙️ Custom Parameters

### Use Conservative Settings
```bash
python main.py --api-key YOUR_KEY analyze AAPL --wacc 0.12 --terminal 0.02
```

### Use Aggressive Growth Settings
```bash
python main.py --api-key YOUR_KEY analyze TSLA --wacc 0.08 --growth 0.15
```

### Parameter Meanings:
- `--wacc`: Discount rate (0.08 = 8%, 0.12 = 12%)
- `--growth`: Revenue growth rate (0.10 = 10%, 0.15 = 15%)
- `--terminal`: Terminal growth rate (0.02 = 2%, 0.03 = 3%)

---

## 🎯 Common Workflows

### Daily Watchlist Update
```bash
# Analyze your watchlist
python main.py --api-key YOUR_KEY analyze AAPL
python main.py --api-key YOUR_KEY analyze MSFT
python main.py --api-key YOUR_KEY analyze GOOGL
python main.py --api-key YOUR_KEY analyze META
python main.py --api-key YOUR_KEY analyze NVDA

# Screen for new opportunities
python main.py screen --min-discount 15 --top 20
```

### Weekly Deep Dive
```bash
# Analyze sector or exchange
python main.py --api-key YOUR_KEY batch NASDAQ --limit 100 --delay 1.5

# Find best opportunities
python main.py screen --min-discount 20 --top 30

# Export results
python main.py export --output weekly_$(date +%Y%m%d).json --min-discount 15
```

### Monthly Review
```bash
# Check trends for your holdings
python main.py trending AAPL --periods 10
python main.py trending MSFT --periods 10
python main.py trending GOOGL --periods 10
```

---

## 💾 Saving Your API Key (Advanced)

Instead of typing your API key every time:

### Windows (PowerShell):
```powershell
# Save key to file once
echo "YOUR_ACTUAL_API_KEY" > api_key.txt

# Then use it like this:
python main.py --api-key $(Get-Content api_key.txt) analyze AAPL
```

### Mac/Linux:
```bash
# Save key to file once
echo "YOUR_ACTUAL_API_KEY" > api_key.txt

# Then use it like this:
python3 main.py --api-key $(cat api_key.txt) analyze AAPL
```

### Or Create an Alias:
```bash
# Add to ~/.bashrc or ~/.zshrc (Mac/Linux):
alias dcf="python3 /path/to/dcf_analyzer/main.py --api-key YOUR_KEY"

# Then use it:
dcf analyze AAPL
dcf screen --min-discount 20
```

---

## 📊 Understanding Output

### Analysis Output Example:
```
Company: Apple Inc.
Current Price: $180.50
Intrinsic Value: $225.30
Discount/Premium: +24.8%
*** UNDERVALUED ***
```

**What It Means:**
- **Positive Discount** = Undervalued (potential buy)
- **Negative Discount** = Overvalued (potential sell/avoid)
- **-10% to +10%** = Fairly valued
- **20%+ discount** = Strong undervaluation
- **40%+ discount** = Very undervalued (verify assumptions!)

### Screening Output Example:
```
Ticker     Current    Intrinsic    Discount   
AAPL       $180.50    $225.30      +24.8%
MSFT       $374.50    $420.20      +12.2%
```

**Sorted by discount** (highest discount = biggest opportunity)

---

## 🐛 Quick Troubleshooting

| Error | What It Means | Fix |
|-------|---------------|-----|
| `python is not recognized` | Python not in PATH | Reinstall Python, check "Add to PATH" |
| `No such file` | Wrong folder | `cd` to dcf_analyzer folder |
| `No module named 'requests'` | Libraries not installed | Run `pip install -r requirements.txt` |
| `Could not fetch data` | API key wrong or rate limit | Check API key or wait (250/day limit) |
| `No stocks analyzed yet` | Empty database | Run `analyze` or `batch` first |

---

## 📈 Rate Limits & Best Practices

**Free Tier Limits:**
- 250 API requests per day
- Each stock analysis = ~5-7 requests
- Can analyze ~40 stocks per day

**Best Practices:**
1. **Start with watchlist** - Analyze 10-20 stocks you know
2. **Use delays** - Add `--delay 2.0` for batch processing
3. **Run regularly** - Weekly/monthly for trend tracking
4. **Be conservative** - Use higher WACC for margin of safety
5. **Verify assumptions** - Check if growth rates are realistic

---

## 🎓 Parameter Presets (Code)

For advanced users, use presets in Python:

```python
from main import DCFAnalyzer
from config import get_dcf_preset

analyzer = DCFAnalyzer(api_key="YOUR_KEY")

# Use conservative preset
params = get_dcf_preset('conservative')
analyzer.analyze_stock('AAPL', params=params)

# Available presets:
# - conservative (WACC 12%, low growth, 15% margin of safety)
# - moderate (WACC 10%, balanced)
# - aggressive (WACC 8%, high growth)
# - high_growth (10-year, 20% growth)
# - value (low growth, mature businesses)
```

---

## 📁 Important Files

| File | What It Does |
|------|--------------|
| `main.py` | Main program - run this |
| `database.py` | Stores all your analyses |
| `dcf_calculator.py` | Does the DCF math |
| `screener.py` | Finds opportunities |
| `config.py` | Parameter presets |
| `requirements.txt` | Required libraries |
| `dcf_analysis.db` | Your data (created automatically) |

---

## 🔗 Quick Links

- **Get API Key**: https://financialmodelingprep.com/developer/docs/
- **Python Download**: https://www.python.org/downloads/

---

## 📞 Getting Help

```bash
# Show all commands
python main.py --help

# Show help for specific command
python main.py analyze --help
python main.py batch --help
python main.py screen --help

# Run interactive demo
python examples.py

# Test installation
python test_installation.py
```

---

## ⚡ Power User Tips

### 1. Batch Multiple Tickers
Create a file `tickers.txt`:
```
AAPL
MSFT
GOOGL
META
NVDA
```

Then run:
```bash
for ticker in $(cat tickers.txt); do
  python main.py --api-key YOUR_KEY analyze $ticker
  sleep 1
done
```

### 2. Find Improving Stocks (Python)
```python
from main import DCFAnalyzer

analyzer = DCFAnalyzer(api_key="YOUR_KEY")
improving = analyzer.screener.get_improving_stocks(min_avg_change=5.0)

for stock in improving[:10]:
    print(f"{stock['ticker']}: {stock['discount_pct']:.1f}% discount")
```

### 3. Custom Screening (Python)
```python
from main import DCFAnalyzer

analyzer = DCFAnalyzer(api_key="YOUR_KEY")

# Custom filter function
def my_screen(calc):
    return (
        calc['discount_pct'] > 20 and      # 20%+ discount
        calc['intrinsic_value'] > 50 and   # $50+ intrinsic value
        calc['wacc'] < 0.11                # Lower risk
    )

results = analyzer.screener.custom_screen(my_screen)
```

---

## 🎯 Daily Command Template

Copy this and customize:

```bash
# Replace YOUR_KEY with your actual API key

# Morning: Update watchlist
python main.py --api-key YOUR_KEY analyze AAPL
python main.py --api-key YOUR_KEY analyze MSFT
python main.py --api-key YOUR_KEY analyze GOOGL

# Afternoon: Screen for opportunities  
python main.py screen --min-discount 15 --top 20

# Evening: Export results
python main.py export --output daily_$(date +%Y%m%d).json
```

---

**Print this page and keep it next to your computer!** 🖨️
