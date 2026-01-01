"""
DCF Stock Analyzer - Streamlit Web App
Professional DCF valuation tool with 30+ years of historical data
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import time

# Add current directory to Python path for Streamlit Cloud compatibility
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct imports - files are in same directory
from dcf_calculator import DCFAnalyzer
from config import PRESET_CONFIGS
from batch_screener import (
    BatchScreener, FilterCategory, FILTER_DEFINITIONS,
    get_filters_by_category, get_all_sectors, get_all_exchanges,
    get_all_market_cap_universes
)

# Page configuration
st.set_page_config(
    page_title="DCF Stock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .undervalued {
        color: #28a745;
        font-weight: bold;
    }
    .overvalued {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []  # List of analysis results (max 100)
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'batch_running' not in st.session_state:
    st.session_state.batch_running = False
if 'batch_progress' not in st.session_state:
    st.session_state.batch_progress = 0
if 'batch_message' not in st.session_state:
    st.session_state.batch_message = ""

# Try to load API key from Streamlit secrets (for persistence)
def get_saved_api_key():
    try:
        return st.secrets.get("ROIC_API_KEY", "")
    except:
        return ""

if 'api_key' not in st.session_state or not st.session_state.api_key:
    st.session_state.api_key = get_saved_api_key()

# Helper functions
def get_market_cap_universe(mkt_cap):
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

def format_market_cap(mkt_cap):
    if mkt_cap >= 1e12:
        return f"${mkt_cap/1e12:.2f}T"
    elif mkt_cap >= 1e9:
        return f"${mkt_cap/1e9:.2f}B"
    elif mkt_cap >= 1e6:
        return f"${mkt_cap/1e6:.2f}M"
    else:
        return f"${mkt_cap:,.0f}"

def format_value(val):
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    elif val >= 1e9:
        return f"${val/1e9:.1f}B"
    elif val >= 1e6:
        return f"${val/1e6:.1f}M"
    else:
        return f"${val:,.0f}"

def add_to_history(result):
    """Add analysis result to history (newest first, max 100)"""
    if result is None:
        return

    # Remove existing entry for same ticker if present
    st.session_state.analysis_history = [
        r for r in st.session_state.analysis_history
        if r['ticker'] != result['ticker']
    ]

    # Insert at beginning (newest first)
    st.session_state.analysis_history.insert(0, result)

    # Keep only last 100
    st.session_state.analysis_history = st.session_state.analysis_history[:100]

# Sidebar - Configuration
with st.sidebar:
    st.markdown("## Configuration")

    # Analysis Mode Toggle
    analysis_mode = st.radio(
        "Analysis Mode",
        ["Single Ticker", "Batch Analysis"],
        help="Single: Analyze one stock. Batch: Screen and analyze multiple stocks."
    )

    st.markdown("---")

    # Data Source
    data_source = st.radio(
        "Data Source",
        ["Roic.ai (30+ years)", "Yahoo Finance (4-5 years)"],
        help="Roic.ai requires API key but provides 30+ years of data"
    )

    # API Key
    if "Roic" in data_source:
        api_key = st.text_input(
            "Roic.ai API Key",
            value=st.session_state.api_key,
            type="password",
            help="Add ROIC_API_KEY to Streamlit secrets for persistence"
        )
        st.session_state.api_key = api_key

        if api_key:
            st.success("✓ API key provided")
        else:
            st.warning("⚠ API key required for Roic.ai")
    else:
        api_key = "not_needed"

    st.markdown("---")

    # Parameter Preset
    st.markdown("## 📋 DCF Parameters")
    preset_name = st.selectbox(
        "Parameter Preset",
        list(PRESET_CONFIGS.keys()),
        help="Choose a preset or customize below"
    )

    preset = PRESET_CONFIGS[preset_name]

    # Show preset description
    st.info(f"**{preset['name']}:** {preset['description']}")

    # Customization option
    customize = st.checkbox("Customize Parameters")

    if customize:
        st.markdown("### Custom Parameters")

        wacc = st.number_input(
            "WACC (Discount Rate) %",
            min_value=1.0,
            max_value=50.0,
            value=preset['wacc'] * 100,
            step=0.5,
            help="Weighted Average Cost of Capital"
        ) / 100

        terminal_growth = st.number_input(
            "Terminal Growth Rate %",
            min_value=0.0,
            max_value=10.0,
            value=preset['terminal_growth_rate'] * 100,
            step=0.25,
            help="Perpetual growth rate"
        ) / 100

        fcf_growth = st.number_input(
            "FCF/EPS Growth Rate %",
            min_value=-50.0,
            max_value=100.0,
            value=preset['fcf_growth_rate'] * 100,
            step=1.0,
            help="Projected growth rate"
        ) / 100

        projection_years = st.number_input(
            "Projection Years",
            min_value=1,
            max_value=30,
            value=preset['projection_years'],
            step=1,
            help="Number of years to project"
        )

        margin_of_safety = st.number_input(
            "Margin of Safety %",
            min_value=0.0,
            max_value=50.0,
            value=preset['conservative_adjustment'] * 100,
            step=5.0,
            help="Safety haircut to intrinsic value"
        ) / 100

        # Update params
        params = {
            'wacc': wacc,
            'terminal_growth_rate': terminal_growth,
            'fcf_growth_rate': fcf_growth,
            'projection_years': projection_years,
            'conservative_adjustment': margin_of_safety,
            'dcf_input_type': preset['dcf_input_type'],
            'normalize_starting_value': preset['normalize_starting_value'],
            'normalization_years': preset['normalization_years']
        }
    else:
        params = preset.copy()

    st.markdown("---")

    # Advanced options
    with st.expander("🔧 Advanced Options"):
        input_type = st.radio(
            "DCF Input Type",
            ["fcf", "eps_cont_ops"],
            index=0 if params['dcf_input_type'] == 'fcf' else 1,
            format_func=lambda x: "Free Cash Flow per Share" if x == "fcf" else "EPS from Continuing Ops"
        )
        params['dcf_input_type'] = input_type

        if "Roic" in data_source:
            years_back = st.number_input(
                "Years of History",
                min_value=5,
                max_value=30,
                value=10,
                step=1,
                help="How many years of historical data to fetch"
            )
        else:
            years_back = 5

    # ==================== BATCH FILTERS (shown only in Batch mode) ====================
    if analysis_mode == "Batch Analysis":
        st.markdown("---")
        st.markdown("## 🔍 Batch Filters")

        # Initialize filter values in session state
        if 'batch_filters' not in st.session_state:
            st.session_state.batch_filters = {}

        batch_filters = {}

        # Group filters by category
        filters_by_category = get_filters_by_category()

        # Basic Filters
        with st.expander("📌 Basic Filters", expanded=True):
            batch_filters['sector'] = st.multiselect(
                "Sector",
                options=get_all_sectors(),
                default=[],
                help="Filter by company sector (leave empty for all)"
            )

            batch_filters['exchange'] = st.multiselect(
                "Exchange",
                options=get_all_exchanges(),
                default=[],
                help="Filter by stock exchange (leave empty for all)"
            )

        # Market Filters
        with st.expander("📊 Market Filters", expanded=False):
            batch_filters['market_cap_universe'] = st.multiselect(
                "Market Cap Universe",
                options=get_all_market_cap_universes(),
                default=[],
                help="Filter by market cap tier (leave empty for all)"
            )

        # Profitability Filters
        with st.expander("💰 Profitability Filters", expanded=False):
            batch_filters['positive_fcf_last_year'] = st.selectbox(
                "Positive FCF (Last Year)",
                options=["Any", "Yes", "No"],
                index=0,
                help="Require positive FCF in the most recent year"
            )

            batch_filters['positive_fcf_years_3'] = st.number_input(
                "Min Positive FCF Years (Last 3)",
                min_value=0,
                max_value=3,
                value=0,
                step=1,
                help="Minimum years with positive FCF in last 3 years"
            )

            batch_filters['positive_fcf_years_5'] = st.number_input(
                "Min Positive FCF Years (Last 5)",
                min_value=0,
                max_value=5,
                value=0,
                step=1,
                help="Minimum years with positive FCF in last 5 years"
            )

            batch_filters['positive_fcf_years_10'] = st.number_input(
                "Min Positive FCF Years (Last 10)",
                min_value=0,
                max_value=10,
                value=0,
                step=1,
                help="Minimum years with positive FCF in last 10 years"
            )

            batch_filters['min_gross_margin'] = st.number_input(
                "Minimum Gross Margin %",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=5.0,
                help="Minimum gross margin percentage"
            )

        # Growth Filters
        with st.expander("📈 Growth Filters", expanded=False):
            batch_filters['revenue_growth_years_5'] = st.number_input(
                "Min Revenue Growth Years (Last 5)",
                min_value=0,
                max_value=5,
                value=0,
                step=1,
                help="Minimum years with revenue growth in last 5 years"
            )

        # Additional Filters (placeholder for future)
        with st.expander("🔮 Additional Filters", expanded=False):
            st.caption("More filters coming soon...")
            st.caption("• Dividend yield range")
            st.caption("• P/E ratio range")
            st.caption("• Debt/Equity ratio")
            st.caption("• ROE/ROIC minimums")

        # Batch options
        st.markdown("---")
        st.markdown("### Batch Options")

        max_stocks = st.number_input(
            "Max Stocks to Analyze",
            min_value=1,
            max_value=100,
            value=20,
            step=5,
            help="Maximum number of stocks to analyze after filtering"
        )

        st.session_state.batch_filters = batch_filters

# Main content - Header
st.markdown('<p class="main-header">📊 DCF Stock Analyzer</p>', unsafe_allow_html=True)
st.markdown("Professional discounted cash flow valuation with 30+ years of historical data")

# Create tabs
tab1, tab2 = st.tabs(["Analyze Stock", "Analysis History"])

# ==================== TAB 1: Analyze Stock ====================
with tab1:
    if analysis_mode == "Single Ticker":
        # ===== SINGLE TICKER MODE =====
        col1, col2 = st.columns([3, 1])

        with col1:
            ticker = st.text_input(
                "Stock Ticker",
                value="AAPL",
                max_chars=10,
                help="Enter stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
            ).upper()

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_button = st.button("Analyze", type="primary", use_container_width=True)

        # Analysis
        if analyze_button:
            if not ticker:
                st.error("Please enter a stock ticker")
            elif "Roic" in data_source and not api_key:
                st.error("Please enter your Roic.ai API key in the sidebar")
            else:
                with st.spinner(f"Analyzing {ticker}..."):
                    try:
                        source = "roic" if "Roic" in data_source else "yahoo"
                        analyzer = DCFAnalyzer(api_key=api_key, data_source=source)

                        result = analyzer.analyze_stock(
                            ticker,
                            params=params,
                            years_back=years_back if "Roic" in data_source else None
                        )

                        st.session_state.analysis_result = result
                        add_to_history(result)

                    except Exception as e:
                        st.error(f"Error analyzing {ticker}: {str(e)}")
                        st.session_state.analysis_result = None

    else:
        # ===== BATCH ANALYSIS MODE =====
        st.markdown("### Batch Analysis")
        st.markdown("Configure filters in the sidebar, then click 'Run Batch Analysis' to screen and analyze stocks.")

        # Show active filters summary
        batch_filters = st.session_state.get('batch_filters', {})
        active_filters = []

        if batch_filters.get('sector'):
            active_filters.append(f"Sectors: {', '.join(batch_filters['sector'])}")
        if batch_filters.get('exchange'):
            active_filters.append(f"Exchanges: {', '.join(batch_filters['exchange'])}")
        if batch_filters.get('market_cap_universe'):
            active_filters.append(f"Market Cap: {', '.join(batch_filters['market_cap_universe'])}")
        if batch_filters.get('positive_fcf_last_year') not in [None, "Any", ""]:
            active_filters.append(f"Positive FCF Last Year: {batch_filters['positive_fcf_last_year']}")
        if batch_filters.get('positive_fcf_years_3', 0) > 0:
            active_filters.append(f"Min FCF Years (3yr): {batch_filters['positive_fcf_years_3']}")
        if batch_filters.get('positive_fcf_years_5', 0) > 0:
            active_filters.append(f"Min FCF Years (5yr): {batch_filters['positive_fcf_years_5']}")
        if batch_filters.get('min_gross_margin', 0) > 0:
            active_filters.append(f"Min Gross Margin: {batch_filters['min_gross_margin']}%")
        if batch_filters.get('revenue_growth_years_5', 0) > 0:
            active_filters.append(f"Min Revenue Growth Years: {batch_filters['revenue_growth_years_5']}")

        if active_filters:
            st.info("**Active Filters:** " + " | ".join(active_filters))
        else:
            st.info("**No filters active** - All S&P 500 stocks will be screened (up to max limit).")

        # Run batch button
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            run_batch = st.button("🚀 Run Batch Analysis", type="primary", use_container_width=True)

        with col2:
            stop_batch = st.button("⏹ Stop", use_container_width=True)

        # Batch execution
        if run_batch:
            if "Roic" in data_source and not api_key:
                st.error("Please enter your Roic.ai API key in the sidebar")
            else:
                st.session_state.batch_running = True

                # Create UI elements for live updates
                progress_bar = st.progress(0)
                status_container = st.container()
                with status_container:
                    status_text = st.empty()
                    filtering_indicator = st.empty()

                # Live matched tickers display
                st.markdown("---")
                matched_header = st.empty()
                matched_tickers_display = st.empty()

                matched_tickers_list = []

                try:
                    source = "roic" if "Roic" in data_source else "yahoo"
                    screener = BatchScreener(data_source=source, api_key=api_key)
                    analyzer = DCFAnalyzer(api_key=api_key, data_source=source)

                    # Progress callback with is_filtering flag
                    def update_progress(current, total, message, is_filtering=True):
                        pct = int((current / total) * 100) if total > 0 else 0
                        progress_bar.progress(pct / 100)
                        status_text.text(message)
                        if is_filtering:
                            filtering_indicator.info("🔄 **Filtering in progress...**")
                        else:
                            filtering_indicator.success("✅ **Filtering complete**")

                    # Match callback - update live display
                    def on_match(stock):
                        matched_tickers_list.append(stock)
                        matched_header.markdown(f"### Matched Tickers ({len(matched_tickers_list)})")
                        ticker_text = ", ".join([s['ticker'] for s in matched_tickers_list])
                        matched_tickers_display.code(ticker_text)

                    # Screen stocks with streaming
                    update_progress(0, 100, "Starting batch screening...", True)
                    matched_header.markdown("### Matched Tickers (0)")
                    matched_tickers_display.code("Scanning...")

                    try:
                        max_stocks_val = max_stocks
                    except:
                        max_stocks_val = 20

                    # Use streaming to show matches live
                    filtered_stocks = []
                    for stock in screener.screen_stocks_streaming(
                        filters=batch_filters,
                        progress_callback=update_progress,
                        match_callback=on_match,
                        max_stocks=max_stocks_val
                    ):
                        filtered_stocks.append(stock)

                    # Run DCF on filtered stocks
                    if filtered_stocks:
                        filtering_indicator.success(f"✅ **Found {len(filtered_stocks)} stocks - Running DCF analysis...**")

                        analyzed_count = 0
                        for i, stock in enumerate(filtered_stocks):
                            ticker_batch = stock['ticker']
                            pct = int(((i + 1) / len(filtered_stocks)) * 100)
                            progress_bar.progress(pct / 100)
                            status_text.text(f"Analyzing {ticker_batch}... ({i+1}/{len(filtered_stocks)})")

                            try:
                                result = analyzer.analyze_stock(
                                    ticker_batch,
                                    params=params,
                                    years_back=years_back if "Roic" in data_source else None
                                )

                                if result:
                                    add_to_history(result)
                                    analyzed_count += 1

                            except Exception as e:
                                print(f"Error analyzing {ticker_batch}: {str(e)}")

                            time.sleep(0.3)  # Rate limiting

                        progress_bar.progress(1.0)
                        status_text.text(f"Batch complete!")
                        filtering_indicator.success(f"✅ **Done! Analyzed {analyzed_count} stocks. Check 'Analysis History' tab.**")
                        st.balloons()
                    else:
                        status_text.text("Screening complete")
                        filtering_indicator.warning("⚠️ **No stocks matched the filter criteria.** Try relaxing the filters.")
                        matched_tickers_display.code("No matches found")

                except Exception as e:
                    st.error(f"Batch analysis error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

                finally:
                    st.session_state.batch_running = False

    # Display results (for single ticker mode)
    if analysis_mode == "Single Ticker" and st.session_state.analysis_result:
        result = st.session_state.analysis_result

        st.markdown("---")

        market_cap = result.get('market_cap', 0)
        universe = get_market_cap_universe(market_cap)
        dcf = result['dcf_result']
        shares = dcf.get('shares_outstanding', 1)

        # === HEADER ROW ===
        c1, c2, c3, c4, _ = st.columns([1.2, 0.7, 0.7, 0.7, 1.5])

        discount = result['discount']

        with c1:
            st.markdown(f"### {result['ticker']}")
            company_name = result.get('company_name', '')
            sector = result.get('sector', 'N/A')
            st.caption(f"{company_name}  •  {sector}")

        with c2:
            st.metric("Market Cap", format_market_cap(market_cap), universe, delta_color="off")

        with c3:
            st.metric("Current Price", f"${result['current_price']:.2f}")
            if discount > 0:
                st.caption(f":green[Undervalued {discount:.1f}%]")
            else:
                st.caption(f":red[Overvalued {abs(discount):.1f}%]")

        with c4:
            st.metric("Intrinsic Value", f"${result['intrinsic_value']:.2f}")

        st.markdown("---")

        # === KEY METRICS ROW ===
        input_type_display = result.get('input_type', 'fcf')
        input_label = "EPS from Cont Ops" if input_type_display == 'eps_cont_ops' else "FCF per Share"

        c1, c2, c3, c4, _ = st.columns([1.2, 0.7, 0.7, 0.7, 1.5])

        with c1:
            st.metric("Input Type", input_label, help="What metric is being projected")

        with c2:
            historical_growth = dcf.get('historical_fcf_growth', 0) * 100
            years_used = dcf.get('historical_years_used', 5)
            st.metric(f"Historical Growth ({years_used}yr)", f"{historical_growth:.1f}%", help="Historical CAGR")

        with c3:
            projected_growth = dcf['params']['fcf_growth_rate'] * 100
            st.metric("Projected Growth", f"{projected_growth:.1f}%", help="Growth rate used in DCF")

        with c4:
            wacc_display = dcf['params']['wacc'] * 100
            st.metric("WACC", f"{wacc_display:.1f}%", help="Discount rate")

        st.markdown("---")

        # === VALUATION BREAKDOWN ===
        pv_fcf_ps = dcf.get('pv_fcf', 0)
        pv_terminal_ps = dcf.get('pv_terminal', 0)
        enterprise_ps = dcf.get('enterprise_value', 0)

        pv_fcf_total = pv_fcf_ps * shares
        pv_terminal_total = pv_terminal_ps * shares
        enterprise_total = enterprise_ps * shares
        equity_total = dcf.get('equity_value', 0)
        equity_ps = equity_total / shares if shares else 0
        intrinsic_ps = result['intrinsic_value']
        intrinsic_total = intrinsic_ps * shares

        c1, c2, c3, c4, _ = st.columns([1.2, 0.7, 0.7, 0.7, 1.5])

        with c1:
            st.markdown("**Valuation Breakdown**")
            st.metric("PV of Projected Cash Flows", format_value(pv_fcf_total), f"${pv_fcf_ps:.1f}/sh")
            st.metric("PV of Terminal Value", format_value(pv_terminal_total), f"${pv_terminal_ps:.1f}/sh")
            st.metric("Enterprise Value", format_value(enterprise_total), f"${enterprise_ps:.1f}/sh")

        with c2:
            st.markdown("&nbsp;")
            st.metric("Equity Value", format_value(equity_total), f"${equity_ps:.1f}/sh")
            st.metric("Intrinsic Value", format_value(intrinsic_total), f"${intrinsic_ps:.1f}/sh")
            st.metric("Shares Outstanding", f"{shares/1e9:.1f}B" if shares >= 1e9 else f"{shares/1e6:.0f}M")

        # DCF Parameters used
        with st.expander("📋 DCF Parameters Used"):
            params_df = pd.DataFrame({
                'Parameter': [
                    'WACC (Discount Rate)',
                    'Terminal Growth Rate',
                    f'{input_label} Growth Rate',
                    'Projection Years',
                    'Margin of Safety'
                ],
                'Value': [
                    f"{result['dcf_result']['params']['wacc']*100:.1f}%",
                    f"{result['dcf_result']['params']['terminal_growth_rate']*100:.1f}%",
                    f"{result['dcf_result']['params']['fcf_growth_rate']*100:.1f}%",
                    f"{result['dcf_result']['params']['projection_years']}",
                    f"{result['dcf_result']['params']['conservative_adjustment']*100:.1f}%"
                ]
            })
            st.dataframe(params_df, hide_index=True, use_container_width=True)

    elif analysis_mode == "Single Ticker" and not st.session_state.analysis_result:
        # Welcome message
        st.info("👆 Enter a stock ticker and click 'Analyze' to begin")

        # Feature highlights
        st.markdown("### ✨ Features")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **📊 Accurate DCF Model**
            - Per-share FCF/EPS projections
            - Accounts for buybacks
            - 2-stage growth model
            - Gordon Growth terminal value
            """)

        with col2:
            st.markdown("""
            **📈 30+ Years of Data**
            - Roic.ai integration
            - Historical FCF/EPS tracking
            - Free Yahoo Finance option
            - Automated data fetching
            """)

        with col3:
            st.markdown("""
            **⚙️ Fully Customizable**
            - 5 built-in presets
            - Custom parameters
            - Multiple DCF inputs
            - Margin of safety
            """)

# ==================== TAB 2: Analysis History ====================
with tab2:
    if not st.session_state.analysis_history:
        st.info("No analyses yet. Analyze some stocks in the 'Analyze Stock' tab to see them here.")
    else:
        # Build Table 1 data
        history_data = []
        for r in st.session_state.analysis_history:
            dcf_r = r.get('dcf_result', {})
            params_r = dcf_r.get('params', {})
            shares_r = dcf_r.get('shares_outstanding', 1)

            history_data.append({
                'Ticker': r.get('ticker', ''),
                'WACC %': f"{params_r.get('wacc', 0) * 100:.1f}",
                'Terminal Growth %': f"{params_r.get('terminal_growth_rate', 0) * 100:.1f}",
                'FCF Growth %': f"{params_r.get('fcf_growth_rate', 0) * 100:.1f}",
                'Proj Years': params_r.get('projection_years', 0),
                'Margin of Safety %': f"{params_r.get('conservative_adjustment', 0) * 100:.1f}",
                'Intrinsic/Share': f"${r.get('intrinsic_value', 0):.2f}",
                'Total Intrinsic': format_value(r.get('intrinsic_value', 0) * shares_r),
                'Price/Share': f"${r.get('current_price', 0):.2f}",
                'Market Cap': format_market_cap(r.get('market_cap', 0)),
                'Discount %': f"{r.get('discount', 0):+.1f}%"
            })

        # Pad to 100 rows
        while len(history_data) < 100:
            history_data.append({
                'Ticker': '',
                'WACC %': '',
                'Terminal Growth %': '',
                'FCF Growth %': '',
                'Proj Years': '',
                'Margin of Safety %': '',
                'Intrinsic/Share': '',
                'Total Intrinsic': '',
                'Price/Share': '',
                'Market Cap': '',
                'Discount %': ''
            })

        history_df = pd.DataFrame(history_data)

        # ===== TOP HALF: Table 1 with selection =====
        st.markdown("### Analysis History")
        st.caption("Select a ticker to view detailed historical and projected data below")

        # Get list of tickers for selection
        ticker_options = [r['ticker'] for r in st.session_state.analysis_history]

        # Selection mechanism
        selected_ticker = st.selectbox(
            "Select Ticker for Details",
            options=ticker_options,
            index=0 if ticker_options else None,
            key="history_ticker_select"
        )

        # Style the dataframe to highlight selected row
        def highlight_selected(row):
            if row['Ticker'] == selected_ticker:
                return ['background-color: #ffff99'] * len(row)
            return [''] * len(row)

        styled_df = history_df.style.apply(highlight_selected, axis=1)

        # Display Table 1 (fixed height for ~50% of screen)
        st.dataframe(
            styled_df,
            hide_index=True,
            use_container_width=True,
            height=400
        )

        st.markdown("---")

        # ===== BOTTOM HALF: Table 2 and Chart 1 =====
        if selected_ticker:
            # Find the selected result
            selected_result = None
            for r in st.session_state.analysis_history:
                if r['ticker'] == selected_ticker:
                    selected_result = r
                    break

            if selected_result:
                dcf_selected = selected_result.get('dcf_result', {})
                input_type_sel = dcf_selected.get('input_type', 'fcf')
                input_label_sel = "EPS" if input_type_sel == 'eps_cont_ops' else "FCF/Share"

                # Get historical data
                historical_data = dcf_selected.get('historical_data', [])

                # Get projected data
                fcf_projections = dcf_selected.get('fcf_projections', [])

                # Determine years
                if historical_data:
                    last_historical_year = max(h[0] for h in historical_data)
                else:
                    last_historical_year = datetime.now().year - 1

                # Build combined data for Table 2 and Chart 1
                years = []
                values = []
                types = []  # 'Historical' or 'Projected'

                # Add historical data (sorted by year)
                for year, value in sorted(historical_data, key=lambda x: x[0]):
                    years.append(str(year))
                    values.append(value)
                    types.append('Historical')

                # Add projected data
                for i, proj_value in enumerate(fcf_projections):
                    proj_year = last_historical_year + i + 1
                    years.append(str(proj_year))
                    values.append(proj_value)
                    types.append('Projected')

                # Table 2: Historical + Projected by year
                st.markdown(f"### {selected_ticker} - {input_label_sel} by Year")

                if years:
                    # Create Table 2 data (1 header row + 1 data row)
                    table2_data = {year: f"${val:.2f}" for year, val in zip(years, values)}
                    table2_df = pd.DataFrame([table2_data])

                    st.dataframe(
                        table2_df,
                        hide_index=True,
                        use_container_width=True
                    )

                    # Chart 1: Visual representation
                    st.markdown(f"### {input_label_sel} Trend")

                    # Create chart data
                    chart_df = pd.DataFrame({
                        'Year': years,
                        input_label_sel: values,
                        'Type': types
                    })

                    # Use different colors for historical vs projected
                    import altair as alt

                    chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X('Year:N', sort=None, title='Year'),
                        y=alt.Y(f'{input_label_sel}:Q', title=f'{input_label_sel} ($)'),
                        color=alt.Color('Type:N',
                                       scale=alt.Scale(domain=['Historical', 'Projected'],
                                                      range=['#1f77b4', '#ff7f0e']),
                                       legend=alt.Legend(title='Data Type'))
                    ).properties(
                        height=300
                    )

                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.warning("No historical or projected data available for this ticker.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    DCF Stock Analyzer | Built with Streamlit |
    <a href='https://github.com/mcemkarahan-dev/DCF'>GitHub</a>
</div>
""", unsafe_allow_html=True)
