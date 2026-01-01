"""
DCF Stock Analyzer - Streamlit Web App
Google Flights-inspired UI with horizontal tabs and filter bar
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
    initial_sidebar_state="collapsed"  # Collapse sidebar by default for cleaner look
)

# Custom CSS for Google Flights-inspired styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a73e8;
        margin-bottom: 0.5rem;
    }

    /* Tab styling - Google Flights inspired */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #f8f9fa;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0 24px;
        background-color: transparent;
        border-radius: 20px;
        color: #5f6368;
        font-weight: 500;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background-color: #e8f0fe;
        color: #1a73e8;
    }

    /* Filter bar styling */
    .filter-bar {
        background-color: #f8f9fa;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    /* Filter dropdown button styling */
    .stSelectbox > div > div {
        border-radius: 20px;
    }

    /* Metric cards */
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1a73e8;
    }

    .undervalued {
        color: #137333;
        font-weight: bold;
    }

    .overvalued {
        color: #c5221f;
        font-weight: bold;
    }

    /* Hide default streamlit hamburger menu for cleaner look */
    #MainMenu {visibility: hidden;}

    /* Compact filter popover */
    .filter-section {
        background: white;
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 12px;
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'batch_running' not in st.session_state:
    st.session_state.batch_running = False

# Filter state initialization
if 'filter_sectors' not in st.session_state:
    st.session_state.filter_sectors = []
if 'filter_exchanges' not in st.session_state:
    st.session_state.filter_exchanges = []
if 'filter_market_caps' not in st.session_state:
    st.session_state.filter_market_caps = []

# Try to load API key from Streamlit secrets
def get_saved_api_key():
    try:
        return st.secrets.get("ROIC_API_KEY", "")
    except:
        return ""

if not st.session_state.api_key:
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
    st.session_state.analysis_history = [
        r for r in st.session_state.analysis_history
        if r['ticker'] != result['ticker']
    ]
    st.session_state.analysis_history.insert(0, result)
    st.session_state.analysis_history = st.session_state.analysis_history[:100]

# ==================== HEADER ====================
st.markdown('<p class="main-header">📊 DCF Stock Analyzer</p>', unsafe_allow_html=True)

# ==================== MAIN TABS (Google Flights Style) ====================
tab_analyze, tab_batch, tab_history, tab_settings = st.tabs([
    "🔍 Analyze Stock",
    "📊 Batch Screener",
    "📋 Analysis History",
    "⚙️ Settings"
])

# ==================== TAB: SETTINGS ====================
with tab_settings:
    st.markdown("### Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Data Source")
        data_source = st.radio(
            "Select Data Source",
            ["Roic.ai (30+ years)", "Yahoo Finance (4-5 years)"],
            help="Roic.ai requires API key but provides 30+ years of data",
            label_visibility="collapsed"
        )

        if "Roic" in data_source:
            api_key = st.text_input(
                "Roic.ai API Key",
                value=st.session_state.api_key,
                type="password",
                help="Get your API key from roic.ai"
            )
            st.session_state.api_key = api_key
            if api_key:
                st.success("✓ API key provided")
            else:
                st.warning("⚠ API key required for Roic.ai")
        else:
            api_key = "not_needed"

    with col2:
        st.markdown("#### DCF Parameters")
        preset_name = st.selectbox(
            "Parameter Preset",
            list(PRESET_CONFIGS.keys()),
            help="Choose a preset configuration"
        )
        preset = PRESET_CONFIGS[preset_name]
        st.info(f"**{preset['name']}:** {preset['description']}")

    # Advanced parameters
    with st.expander("🔧 Customize Parameters"):
        col1, col2, col3 = st.columns(3)

        with col1:
            wacc = st.number_input(
                "WACC %", min_value=1.0, max_value=50.0,
                value=preset['wacc'] * 100, step=0.5
            ) / 100

            terminal_growth = st.number_input(
                "Terminal Growth %", min_value=0.0, max_value=10.0,
                value=preset['terminal_growth_rate'] * 100, step=0.25
            ) / 100

        with col2:
            fcf_growth = st.number_input(
                "FCF Growth %", min_value=-50.0, max_value=100.0,
                value=preset['fcf_growth_rate'] * 100, step=1.0
            ) / 100

            projection_years = st.number_input(
                "Projection Years", min_value=1, max_value=30,
                value=preset['projection_years'], step=1
            )

        with col3:
            margin_of_safety = st.number_input(
                "Margin of Safety %", min_value=0.0, max_value=50.0,
                value=preset['conservative_adjustment'] * 100, step=5.0
            ) / 100

            input_type = st.radio(
                "DCF Input Type",
                ["fcf", "eps_cont_ops"],
                format_func=lambda x: "Free Cash Flow" if x == "fcf" else "EPS Cont Ops"
            )

        # Store customized params
        st.session_state.custom_params = {
            'wacc': wacc,
            'terminal_growth_rate': terminal_growth,
            'fcf_growth_rate': fcf_growth,
            'projection_years': projection_years,
            'conservative_adjustment': margin_of_safety,
            'dcf_input_type': input_type,
            'normalize_starting_value': preset['normalize_starting_value'],
            'normalization_years': preset['normalization_years']
        }

    # Store default params if not customized
    if 'custom_params' not in st.session_state:
        st.session_state.custom_params = preset.copy()

    # Store data source
    st.session_state.data_source = data_source

# Get current settings
data_source = st.session_state.get('data_source', "Roic.ai (30+ years)")
api_key = st.session_state.get('api_key', '')
params = st.session_state.get('custom_params', PRESET_CONFIGS['Conservative'])

# ==================== TAB: ANALYZE STOCK ====================
with tab_analyze:
    # Ticker input row
    col1, col2, col3 = st.columns([2, 1, 3])

    with col1:
        ticker = st.text_input(
            "Stock Ticker",
            value="AAPL",
            max_chars=10,
            help="Enter stock ticker symbol",
            label_visibility="collapsed",
            placeholder="Enter ticker (e.g., AAPL)"
        ).upper()

    with col2:
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

    # Analysis execution
    if analyze_button:
        if not ticker:
            st.error("Please enter a stock ticker")
        elif "Roic" in data_source and not api_key:
            st.error("Please enter your Roic.ai API key in Settings tab")
        else:
            with st.spinner(f"Analyzing {ticker}..."):
                try:
                    source = "roic" if "Roic" in data_source else "yahoo"
                    analyzer = DCFAnalyzer(api_key=api_key, data_source=source)
                    result = analyzer.analyze_stock(ticker, params=params)
                    st.session_state.analysis_result = result
                    add_to_history(result)
                except Exception as e:
                    st.error(f"Error analyzing {ticker}: {str(e)}")
                    st.session_state.analysis_result = None

    # Display results
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        st.markdown("---")

        market_cap = result.get('market_cap', 0)
        universe = get_market_cap_universe(market_cap)
        dcf = result['dcf_result']
        shares = dcf.get('shares_outstanding', 1)
        discount = result['discount']

        # Header row
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])

        with c1:
            st.markdown(f"### {result['ticker']}")
            st.caption(f"{result.get('company_name', '')} • {result.get('sector', 'N/A')}")

        with c2:
            st.metric("Current Price", f"${result['current_price']:.2f}")

        with c3:
            st.metric("Intrinsic Value", f"${result['intrinsic_value']:.2f}")

        with c4:
            if discount > 0:
                st.metric("Discount", f"{discount:.1f}%", delta="Undervalued", delta_color="normal")
            else:
                st.metric("Premium", f"{abs(discount):.1f}%", delta="Overvalued", delta_color="inverse")

        # Details
        with st.expander("📊 Valuation Details", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Market Cap", format_market_cap(market_cap), universe)
                st.metric("Shares Outstanding", f"{shares/1e9:.2f}B" if shares >= 1e9 else f"{shares/1e6:.0f}M")

            with col2:
                pv_fcf = dcf.get('pv_fcf', 0) * shares
                pv_terminal = dcf.get('pv_terminal', 0) * shares
                st.metric("PV of Cash Flows", format_value(pv_fcf))
                st.metric("PV of Terminal Value", format_value(pv_terminal))

            with col3:
                hist_growth = dcf.get('historical_fcf_growth', 0) * 100
                proj_growth = dcf['params']['fcf_growth_rate'] * 100
                st.metric("Historical Growth", f"{hist_growth:.1f}%")
                st.metric("Projected Growth", f"{proj_growth:.1f}%")

    else:
        st.info("👆 Enter a stock ticker and click 'Analyze' to begin")

# ==================== TAB: BATCH SCREENER ====================
with tab_batch:
    # ===== HORIZONTAL FILTER BAR (Google Flights Style) =====
    st.markdown("### Filter Stocks")

    # Filter bar - horizontal layout
    filter_cols = st.columns([1, 1, 1, 1, 0.5])

    with filter_cols[0]:
        # Exchange filter with "All" option
        all_exchanges = get_all_exchanges()
        exchange_options = ["All Exchanges"] + all_exchanges
        selected_exchanges = st.multiselect(
            "Exchange",
            options=all_exchanges,
            default=[],
            help="Leave empty for all exchanges",
            placeholder="All Exchanges"
        )

    with filter_cols[1]:
        # Sector filter
        all_sectors = get_all_sectors()
        selected_sectors = st.multiselect(
            "Sector",
            options=all_sectors,
            default=[],
            help="Leave empty for all sectors",
            placeholder="All Sectors"
        )

    with filter_cols[2]:
        # Market Cap filter
        all_caps = get_all_market_cap_universes()
        selected_caps = st.multiselect(
            "Market Cap",
            options=all_caps,
            default=[],
            help="Leave empty for all market caps",
            placeholder="All Market Caps"
        )

    with filter_cols[3]:
        # Max stocks
        max_stocks = st.number_input(
            "Max Stocks",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            help="Maximum stocks to analyze"
        )

    with filter_cols[4]:
        st.markdown("<br>", unsafe_allow_html=True)
        reset_filters = st.button("🔄 Reset", use_container_width=True)

    if reset_filters:
        st.rerun()

    # Additional filters (collapsible)
    with st.expander("📊 Advanced Filters"):
        adv_cols = st.columns(4)

        with adv_cols[0]:
            fcf_last_year = st.selectbox(
                "Positive FCF (Last Year)",
                ["Any", "Yes", "No"],
                index=0
            )

        with adv_cols[1]:
            fcf_years_3 = st.number_input(
                "Min FCF Years (3yr)", min_value=0, max_value=3, value=0
            )

        with adv_cols[2]:
            fcf_years_5 = st.number_input(
                "Min FCF Years (5yr)", min_value=0, max_value=5, value=0
            )

        with adv_cols[3]:
            min_gross_margin = st.number_input(
                "Min Gross Margin %", min_value=0.0, max_value=100.0, value=0.0, step=5.0
            )

    # Build filters dict
    batch_filters = {
        'sector': selected_sectors,
        'exchange': selected_exchanges,
        'market_cap_universe': selected_caps,
        'positive_fcf_last_year': fcf_last_year,
        'positive_fcf_years_3': fcf_years_3,
        'positive_fcf_years_5': fcf_years_5,
        'min_gross_margin': min_gross_margin,
    }

    # Show active filters summary
    active_filters = []
    if selected_exchanges:
        active_filters.append(f"Exchanges: {', '.join(selected_exchanges)}")
    if selected_sectors:
        active_filters.append(f"Sectors: {', '.join(selected_sectors)}")
    if selected_caps:
        active_filters.append(f"Market Cap: {', '.join(selected_caps)}")

    if active_filters:
        st.info("**Active Filters:** " + " | ".join(active_filters))
    else:
        st.info("**No filters active** - Will screen all available stocks")

    st.markdown("---")

    # Run button
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        run_batch = st.button("🚀 Run Batch Analysis", type="primary", use_container_width=True)

    with col2:
        stop_batch = st.button("⏹ Stop", use_container_width=True)

    # Batch execution
    if run_batch:
        if "Roic" in data_source and not api_key:
            st.error("Please enter your Roic.ai API key in Settings tab")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            matched_display = st.empty()

            matched_tickers = []

            try:
                source = "roic" if "Roic" in data_source else "yahoo"
                screener = BatchScreener(data_source=source, api_key=api_key)
                analyzer = DCFAnalyzer(api_key=api_key, data_source=source)

                def update_progress(current, total, message, is_filtering=True):
                    pct = int((current / total) * 100) if total > 0 else 0
                    progress_bar.progress(pct / 100)
                    status_text.text(message)

                def on_match(stock):
                    matched_tickers.append(stock['ticker'])
                    matched_display.success(f"**Matched ({len(matched_tickers)}):** {', '.join(matched_tickers)}")

                # Screen stocks
                status_text.text("Screening stocks...")
                filtered_stocks = list(screener.screen_stocks_streaming(
                    filters=batch_filters,
                    progress_callback=update_progress,
                    match_callback=on_match,
                    max_stocks=max_stocks
                ))

                # Analyze matched stocks
                if filtered_stocks:
                    status_text.text(f"Analyzing {len(filtered_stocks)} stocks...")

                    for i, stock in enumerate(filtered_stocks):
                        ticker_batch = stock['ticker']
                        pct = (i + 1) / len(filtered_stocks)
                        progress_bar.progress(pct)
                        status_text.text(f"Analyzing {ticker_batch}... ({i+1}/{len(filtered_stocks)})")

                        try:
                            result = analyzer.analyze_stock(ticker_batch, params=params)
                            if result:
                                add_to_history(result)
                        except Exception as e:
                            print(f"Error analyzing {ticker_batch}: {e}")

                        time.sleep(0.3)

                    progress_bar.progress(1.0)
                    status_text.success(f"✅ Done! Analyzed {len(filtered_stocks)} stocks. Check 'Analysis History' tab.")
                    st.balloons()
                else:
                    status_text.warning("⚠️ No stocks matched the filter criteria.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== TAB: ANALYSIS HISTORY ====================
with tab_history:
    if not st.session_state.analysis_history:
        st.info("No analyses yet. Analyze stocks to see them here.")
    else:
        # Build history table
        history_data = []
        for r in st.session_state.analysis_history:
            dcf_r = r.get('dcf_result', {})
            shares_r = dcf_r.get('shares_outstanding', 1)

            history_data.append({
                'Ticker': r.get('ticker', ''),
                'Company': r.get('company_name', '')[:30],
                'Price': f"${r.get('current_price', 0):.2f}",
                'Intrinsic': f"${r.get('intrinsic_value', 0):.2f}",
                'Discount': f"{r.get('discount', 0):+.1f}%",
                'Market Cap': format_market_cap(r.get('market_cap', 0)),
            })

        history_df = pd.DataFrame(history_data)

        # Selection
        ticker_options = [r['ticker'] for r in st.session_state.analysis_history]
        selected_ticker = st.selectbox("Select Ticker for Details", ticker_options, index=0)

        # Highlight selected
        def highlight_selected(row):
            if row['Ticker'] == selected_ticker:
                return ['background-color: #e8f0fe'] * len(row)
            return [''] * len(row)

        styled_df = history_df.style.apply(highlight_selected, axis=1)
        st.dataframe(styled_df, hide_index=True, use_container_width=True, height=350)

        st.markdown("---")

        # Show details for selected ticker
        if selected_ticker:
            selected_result = next((r for r in st.session_state.analysis_history if r['ticker'] == selected_ticker), None)

            if selected_result:
                dcf_selected = selected_result.get('dcf_result', {})
                input_type_sel = dcf_selected.get('input_type', 'fcf')
                input_label = "EPS" if input_type_sel == 'eps_cont_ops' else "FCF/Share"

                historical_data = dcf_selected.get('historical_data', [])
                fcf_projections = dcf_selected.get('fcf_projections', [])

                if historical_data:
                    last_year = max(h[0] for h in historical_data)
                else:
                    last_year = datetime.now().year - 1

                years = []
                values = []
                types = []

                for year, value in sorted(historical_data, key=lambda x: x[0]):
                    years.append(str(year))
                    values.append(value)
                    types.append('Historical')

                for i, proj_value in enumerate(fcf_projections):
                    years.append(str(last_year + i + 1))
                    values.append(proj_value)
                    types.append('Projected')

                if years:
                    st.markdown(f"### {selected_ticker} - {input_label} by Year")

                    # Chart
                    import altair as alt
                    chart_df = pd.DataFrame({'Year': years, input_label: values, 'Type': types})

                    chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X('Year:N', sort=None),
                        y=alt.Y(f'{input_label}:Q'),
                        color=alt.Color('Type:N', scale=alt.Scale(
                            domain=['Historical', 'Projected'],
                            range=['#1a73e8', '#fbbc04']
                        ))
                    ).properties(height=300)

                    st.altair_chart(chart, use_container_width=True)

# Footer
st.markdown("---")
st.caption("DCF Stock Analyzer | Built with Streamlit | [GitHub](https://github.com/mcemkarahan-dev/DCF)")
