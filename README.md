# DCF Stock Analyzer 📊

Professional discounted cash flow (DCF) valuation tool with 30+ years of historical data support. Available as both a desktop application and web app.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)

## 🌟 Features

- **Accurate DCF Valuation**: 2-stage DCF model with Gordon Growth terminal value
- **Per-Share Metrics**: Properly accounts for share buybacks and dilution
- **30+ Years of Data**: Integration with Roic.ai for comprehensive historical data
- **Multiple Presets**: 5 built-in parameter presets (Conservative, Moderate, Aggressive, High Growth, Value)
- **Flexible Inputs**: Choose between FCF per share or EPS from continuing operations
- **Normalization**: Smooth out cyclical volatility with multi-year averages
- **Two Interfaces**: Desktop GUI (Tkinter) or Web App (Streamlit)

## 📦 What's Included

### Desktop Application (`/desktop`)
Full-featured Python desktop app with:
- Tkinter GUI interface
- Single stock analysis
- Batch analysis
- Stock screening
- Historical tracking
- SQLite database
- Export to Excel/CSV

### Web Application (`/streamlit`)
Modern browser-based interface with:
- Clean, professional UI
- Real-time analysis
- Mobile responsive
- Easy sharing via URL
- No installation required

### Shared Core (`/shared`)
Common modules used by both applications:
- DCF calculation engine
- Data fetchers (Roic.ai, Yahoo Finance)
- Parameter presets
- Database management

## 🚀 Quick Start

### Option 1: Web App (Easiest)

1. **Install dependencies:**
```bash
cd streamlit
pip install -r requirements.txt
```

2. **Run the app:**
```bash
streamlit run streamlit_app.py
```

3. **Open browser:**
The app will automatically open at `http://localhost:8501`

### Option 2: Desktop App

1. **Install dependencies:**
```bash
cd desktop
pip install -r requirements.txt
```

2. **Run the GUI:**
```bash
python gui_launcher.py
```

Or use the launcher scripts:
- **Windows:** `launch_gui_windows.bat`
- **Mac/Linux:** `./launch_gui_mac_linux.sh`

## 🔑 API Keys

### Roic.ai (Recommended - 30+ years of data)
1. Sign up at [roic.ai](https://roic.ai)
2. Get your API key from Settings
3. Enter in the app (stored securely)

### Yahoo Finance (Free - 4-5 years of data)
No API key required, works out of the box!

## 📊 DCF Methodology

This tool implements a **2-Stage DCF Model**:

1. **Explicit Forecast Period** (5-10 years)
   - Projects FCF/EPS using constant growth rate
   - Uses per-share metrics to account for buybacks
   - Optional normalization for cyclical companies

2. **Terminal Value** (Gordon Growth Model)
   ```
   Terminal Value = FCF_final × (1 + g) / (WACC - g)
   ```

3. **Intrinsic Value Calculation**
   ```
   Enterprise Value = PV(Projected FCF) + PV(Terminal Value)
   Equity Value = Enterprise Value + Cash - Debt
   Intrinsic Value per Share = Equity Value / Shares Outstanding
   ```

4. **Margin of Safety** (optional)
   - Applies final haircut to intrinsic value
   - Benjamin Graham-style conservatism

## ⚙️ Parameter Presets

| Preset | WACC | Growth | Terminal | Years | Best For |
|--------|------|--------|----------|-------|----------|
| **Conservative** | 12% | 5% | 2% | 5 | Risk-averse investors |
| **Moderate** | 10% | 8% | 2.5% | 5 | Balanced approach |
| **Aggressive** | 8% | 15% | 3% | 7 | Growth stocks |
| **High Growth** | 9% | 20% | 3% | 10 | Tech companies |
| **Value** | 9% | 3% | 2% | 5 | Mature businesses |

All presets are fully customizable!

## 📁 Project Structure

```
DCF/
├── README.md
├── LICENSE
├── .gitignore
│
├── desktop/                 # Desktop application
│   ├── main.py             # CLI entry point
│   ├── gui_launcher.py     # Tkinter GUI
│   ├── requirements.txt
│   └── ...
│
├── streamlit/              # Web application
│   ├── streamlit_app.py    # Streamlit app
│   ├── requirements.txt
│   └── ...
│
└── shared/                 # Shared core modules
    ├── dcf_calculator.py   # DCF engine
    ├── data_fetcher_roic.py
    ├── data_fetcher_yahoo.py
    ├── config.py           # Presets
    ├── database.py
    └── screener.py
```

## 🎯 Usage Examples

### Web App
Simply enter a ticker and click "Analyze Stock"!

### Desktop CLI
```bash
# Basic analysis
python main.py analyze AAPL

# With custom parameters
python main.py analyze AAPL --wacc 0.11 --growth 0.08 --terminal 0.025

# Use a preset
python main.py analyze AAPL --preset conservative

# Roic.ai with API key
python main.py --api-key YOUR_KEY --data-source roic analyze AAPL --years-back 20

# Batch analysis
python main.py batch NYSE --limit 10

# Screen for undervalued stocks
python main.py screen --min-discount 20 --max-price 100
```

## 🔧 Advanced Features

### Custom Presets
Create your own parameter presets:
1. Click "Customize" in the GUI
2. Adjust parameters
3. Click "Save As Preset"
4. Reuse anytime!

### Normalization
For cyclical companies (oil, commodities), enable normalization:
- Uses 3-5 year average instead of most recent year
- Smooths out volatility
- More conservative for unpredictable industries

### Per-Share Analysis
The tool automatically:
- Fetches historical shares outstanding for each period
- Calculates per-share FCF/EPS
- Accounts for buybacks (value increase) and dilution (value decrease)
- More accurate than using total FCF

## 📈 Comparison to Other Tools

| Feature | This Tool | Gurufocus | Yahoo Finance |
|---------|-----------|-----------|---------------|
| Historical Data | 30+ years | 30+ years | 5 years |
| Per-Share FCF | ✅ | ✅ | ❌ |
| Buyback Adjustment | ✅ | ✅ | ❌ |
| Custom Parameters | ✅ | ❌ | ❌ |
| Batch Analysis | ✅ | ❌ | ❌ |
| Free Tier | ✅ | Limited | ✅ |
| Offline Mode | ✅ | ❌ | ❌ |

## 🐛 Troubleshooting

### "403 Error" with Roic.ai
- Check your API key is correct
- Verify your subscription is active
- Try Yahoo Finance as alternative

### "Module not found" error
```bash
pip install -r requirements.txt
```

### GUI doesn't open
Make sure you have tkinter installed:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Mac
brew install python-tk
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use for personal or commercial projects!

## 🙏 Acknowledgments

- **Roic.ai** - Comprehensive financial data API
- **Yahoo Finance** - Free market data
- **Streamlit** - Amazing web framework

## 📞 Contact

- **GitHub**: [@mcemkarahan-dev](https://github.com/mcemkarahan-dev)
- **Issues**: [GitHub Issues](https://github.com/mcemkarahan-dev/DCF/issues)

## 🚀 Deployment

### Deploy Streamlit App to Streamlit Cloud (Free!)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Select `streamlit/streamlit_app.py`
5. Add secrets (API key) in Settings
6. Deploy!

Your app will be live at: `https://[your-app-name].streamlit.app`

---

**Made with ❤️ for value investors**
