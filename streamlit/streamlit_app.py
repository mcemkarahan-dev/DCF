"""
DCF Stock Analyzer - Streamlit Web App
Google Flights-inspired UI with horizontal tabs and filter bar
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
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
import db_storage  # Persistent database storage

# Page configuration
st.set_page_config(
    page_title="DCF Stock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default for cleaner look
)

# Custom CSS for Google Flights-inspired styling (Desktop + Mobile)
st.markdown("""
<style>
    /* Import Google's Roboto font */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    /* Apply Roboto font globally */
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }

    /* White background throughout */
    .stApp {
        background-color: #ffffff;
    }

    .main .block-container {
        background-color: #ffffff;
        padding-top: 1rem;
    }

    /* Main header styling - clean, no emoji */
    .main-header {
        font-family: 'Roboto', sans-serif;
        font-size: 1.5rem;
        font-weight: 500;
        color: #202124;
        margin-bottom: 1rem;
    }

    /* Tab styling - Google Flights style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        padding: 0;
        border-bottom: 1px solid #dadce0;
        overflow-x: auto;
        flex-wrap: nowrap;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        padding: 0 16px;
        background-color: transparent;
        border-radius: 0;
        color: #5f6368;
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        font-size: 14px;
        border: none;
        border-bottom: 3px solid transparent;
        white-space: nowrap;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #202124;
        background-color: #f8f9fa;
    }

    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #1a73e8;
        border-bottom: 3px solid #1a73e8;
    }

    /* Google Flights style filter buttons */
    .stMultiSelect > div > div {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 20px;
        min-height: 36px;
    }

    .stMultiSelect > div > div:hover {
        background-color: #f8f9fa;
    }

    .stMultiSelect label {
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        font-weight: 500;
        color: #3c4043;
    }

    .stSelectbox > div > div {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 20px;
        min-height: 36px;
    }

    .stSelectbox > div > div:hover {
        background-color: #f8f9fa;
    }

    /* Number input styling */
    .stNumberInput > div > div > input {
        border: 1px solid #dadce0;
        border-radius: 20px;
    }

    /* Button styling - Google style */
    .stButton > button {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        border-radius: 20px;
        border: 1px solid #dadce0;
        background-color: #ffffff;
        color: #3c4043;
        min-height: 44px;
    }

    .stButton > button:hover {
        background-color: #f8f9fa;
        border-color: #dadce0;
    }

    .stButton > button[kind="primary"] {
        background-color: #1a73e8;
        border-color: #1a73e8;
        color: #ffffff;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #1557b0;
        border-color: #1557b0;
    }

    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
    }

    .undervalued {
        color: #137333;
        font-weight: 500;
    }

    .overvalued {
        color: #c5221f;
        font-weight: 500;
    }

    /* Hide hamburger menu */
    #MainMenu {visibility: hidden;}

    /* Expander styling */
    .streamlit-expanderHeader {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        color: #3c4043;
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 8px;
    }

    /* Info/warning boxes */
    .stAlert {
        border-radius: 8px;
        border: none;
    }

    /* Clean divider */
    hr {
        border: none;
        border-top: 1px solid #dadce0;
        margin: 1rem 0;
    }

    /* ==================== MOBILE RESPONSIVE STYLES ==================== */
    @media (max-width: 768px) {
        /* Reduce padding on mobile */
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 0.5rem;
        }

        /* Smaller header on mobile */
        .main-header {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }

        /* Scrollable tabs on mobile */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }

        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;
        }

        .stTabs [data-baseweb="tab"] {
            height: 44px;
            padding: 0 12px;
            font-size: 13px;
            min-width: fit-content;
        }

        /* Larger touch targets for checkboxes */
        .stCheckbox label {
            min-height: 44px;
            display: flex;
            align-items: center;
            font-size: 16px;
        }

        .stCheckbox > div {
            min-height: 44px;
        }

        /* Larger buttons on mobile */
        .stButton > button {
            min-height: 48px;
            font-size: 16px;
            width: 100%;
        }

        /* Full-width inputs on mobile */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            min-height: 48px;
            font-size: 16px;
        }

        /* Stack columns on mobile - Streamlit handles this but we ensure it */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* Expanders full width and larger touch target */
        .streamlit-expanderHeader {
            min-height: 48px;
            font-size: 16px;
        }

        /* Metrics stack better */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.875rem;
        }

        /* Data tables scroll horizontally */
        .stDataFrame {
            overflow-x: auto;
        }
    }

    /* Extra small screens (phones in portrait) */
    @media (max-width: 480px) {
        .main-header {
            font-size: 1.1rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0 8px;
            font-size: 12px;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.25rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_history' not in st.session_state:
    # Load from persistent database on first run
    st.session_state.analysis_history = db_storage.load_all_history(limit=100)
if 'batch_running' not in st.session_state:
    st.session_state.batch_running = False

# Filter state initialization
if 'filter_sectors' not in st.session_state:
    st.session_state.filter_sectors = []
if 'filter_exchanges' not in st.session_state:
    st.session_state.filter_exchanges = []
if 'filter_market_caps' not in st.session_state:
    st.session_state.filter_market_caps = []

# Default ROIC API key (hardcoded for single-user convenience)
DEFAULT_ROIC_API_KEY = "1e702063f1534ee1b0485da8f461bda9"

def get_saved_api_key():
    """Get API key - first try secrets, then use default"""
    try:
        key = st.secrets.get("ROIC_API_KEY", "")
        if key:
            return key
    except:
        pass
    return DEFAULT_ROIC_API_KEY

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

def get_params_hash(params):
    """Create a hash of DCF parameters for comparison"""
    key_params = (
        params.get('wacc'),
        params.get('terminal_growth_rate'),
        params.get('fcf_growth_rate'),
        params.get('projection_years'),
        params.get('conservative_adjustment'),
        params.get('dcf_input_type'),
    )
    return hash(key_params)

def add_to_history(result, params=None):
    """Add analysis result to history (newest first, max 100)"""
    if result is None:
        return

    # Add run metadata
    result['run_date'] = datetime.now().isoformat()
    params_hash = None
    if params:
        params_hash = get_params_hash(params)
        result['params_hash'] = params_hash

    # Remove previous entry for same ticker (in session)
    st.session_state.analysis_history = [
        r for r in st.session_state.analysis_history
        if r['ticker'] != result['ticker']
    ]
    st.session_state.analysis_history.insert(0, result)
    st.session_state.analysis_history = st.session_state.analysis_history[:100]

    # Persist to database
    db_storage.save_analysis(result, params_hash)

def was_recently_analyzed(ticker, params, days=10):
    """Check if ticker was analyzed with same params within last N days"""
    if not st.session_state.analysis_history:
        return False, None

    current_hash = get_params_hash(params)
    cutoff_date = datetime.now() - timedelta(days=days)

    for r in st.session_state.analysis_history:
        if r['ticker'] == ticker:
            run_date_str = r.get('run_date')
            if run_date_str:
                try:
                    run_date = datetime.fromisoformat(run_date_str)
                    if run_date > cutoff_date:
                        # Check if params match
                        if r.get('params_hash') == current_hash:
                            return True, run_date
                except:
                    pass
    return False, None

# ==================== HEADER ====================
st.markdown('<p class="main-header">DCF Stock Analyzer</p>', unsafe_allow_html=True)

# ==================== MAIN TABS (Google Flights Style) ====================
tab_analyze, tab_batch, tab_history, tab_settings = st.tabs([
    "Analyze Stock",
    "Batch Screener",
    "Analysis History",
    "Settings"
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
                st.success("API key provided")
            else:
                st.warning("API key required for Roic.ai")
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
    with st.expander("Customize Parameters"):
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
params = st.session_state.get('custom_params', PRESET_CONFIGS['conservative'])

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
        analyze_button = st.button("Analyze", type="primary", use_container_width=True)

    # Analysis execution
    if analyze_button:
        if not ticker:
            st.error("Please enter a stock ticker")
        elif "Roic" in data_source and not api_key:
            st.error("Please enter your Roic.ai API key in Settings tab")
        else:
            # Check if recently analyzed with same params
            recently_run, last_run_date = was_recently_analyzed(ticker, params)
            if recently_run:
                st.warning(f"{ticker} was already analyzed with these parameters on {last_run_date.strftime('%Y-%m-%d %H:%M')}. Showing cached result.")
                # Show existing result from history
                existing = next((r for r in st.session_state.analysis_history if r['ticker'] == ticker), None)
                if existing:
                    st.session_state.analysis_result = existing
            else:
                with st.spinner(f"Analyzing {ticker}..."):
                    try:
                        source = "roic" if "Roic" in data_source else "yahoo"
                        analyzer = DCFAnalyzer(api_key=api_key, data_source=source)
                        result = analyzer.analyze_stock(ticker, params=params)
                        st.session_state.analysis_result = result
                        add_to_history(result, params)
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
        with st.expander("Valuation Details", expanded=True):
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
        st.info("Enter a stock ticker and click 'Analyze' to begin")

# ==================== TAB: BATCH SCREENER ====================
with tab_batch:
    # Get all filter options
    all_exchanges = get_all_exchanges()
    all_sectors = get_all_sectors()
    all_caps = get_all_market_cap_universes()

    # Initialize filter states in session
    if 'sel_exchanges' not in st.session_state:
        st.session_state.sel_exchanges = []
    if 'sel_sectors' not in st.session_state:
        st.session_state.sel_sectors = []
    if 'sel_caps' not in st.session_state:
        st.session_state.sel_caps = []

    # ===== HORIZONTAL FILTER BAR (Google Flights Style) =====

    # Callbacks to handle Select All toggling
    def on_select_all_exchanges():
        if st.session_state.select_all_exchanges:
            # Check all individual checkboxes
            for ex in all_exchanges:
                st.session_state[f"ex_{ex}"] = True
        else:
            # Uncheck all individual checkboxes
            for ex in all_exchanges:
                st.session_state[f"ex_{ex}"] = False

    def on_select_all_sectors():
        if st.session_state.select_all_sectors:
            for sec in all_sectors:
                st.session_state[f"sec_{sec}"] = True
        else:
            for sec in all_sectors:
                st.session_state[f"sec_{sec}"] = False

    def on_select_all_caps():
        if st.session_state.select_all_caps:
            for cap in all_caps:
                st.session_state[f"cap_{cap}"] = True
        else:
            for cap in all_caps:
                st.session_state[f"cap_{cap}"] = False

    # Filter buttons row
    filter_cols = st.columns([1, 1, 1, 1, 0.8])

    # Exchange Filter
    with filter_cols[0]:
        ex_count = len(st.session_state.sel_exchanges)
        if ex_count == 0 or ex_count == len(all_exchanges):
            exchange_label = "Exchange"
        else:
            exchange_label = f"Exchange ({ex_count})"

        with st.expander(f"{exchange_label} ▾", expanded=False):
            # Select All checkbox with callback
            st.checkbox(
                "Select all exchanges",
                value=len(st.session_state.sel_exchanges) == len(all_exchanges),
                key="select_all_exchanges",
                on_change=on_select_all_exchanges
            )

            st.markdown("---")

            # Individual checkboxes
            new_exchanges = []
            for ex in all_exchanges:
                default_checked = ex in st.session_state.sel_exchanges
                if st.checkbox(ex, value=default_checked, key=f"ex_{ex}"):
                    new_exchanges.append(ex)

            # Update session state
            st.session_state.sel_exchanges = new_exchanges

    # Sector Filter
    with filter_cols[1]:
        sec_count = len(st.session_state.sel_sectors)
        if sec_count == 0 or sec_count == len(all_sectors):
            sector_label = "Sector"
        else:
            sector_label = f"Sector ({sec_count})"

        with st.expander(f"{sector_label} ▾", expanded=False):
            st.checkbox(
                "Select all sectors",
                value=len(st.session_state.sel_sectors) == len(all_sectors),
                key="select_all_sectors",
                on_change=on_select_all_sectors
            )

            st.markdown("---")

            new_sectors = []
            for sec in all_sectors:
                default_checked = sec in st.session_state.sel_sectors
                if st.checkbox(sec, value=default_checked, key=f"sec_{sec}"):
                    new_sectors.append(sec)

            st.session_state.sel_sectors = new_sectors

    # Market Cap Filter
    with filter_cols[2]:
        cap_count = len(st.session_state.sel_caps)
        if cap_count == 0 or cap_count == len(all_caps):
            cap_label = "Market Cap"
        else:
            cap_label = f"Market Cap ({cap_count})"

        with st.expander(f"{cap_label} ▾", expanded=False):
            st.checkbox(
                "Select all market caps",
                value=len(st.session_state.sel_caps) == len(all_caps),
                key="select_all_caps",
                on_change=on_select_all_caps
            )

            st.markdown("---")

            new_caps = []
            for cap in all_caps:
                default_checked = cap in st.session_state.sel_caps
                if st.checkbox(cap, value=default_checked, key=f"cap_{cap}"):
                    new_caps.append(cap)

            st.session_state.sel_caps = new_caps

    # Max Stocks
    with filter_cols[3]:
        max_stocks = st.number_input(
            "Max Stocks",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            label_visibility="visible"
        )

    # Reset button
    with filter_cols[4]:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        if st.button("Reset", use_container_width=True):
            st.session_state.sel_exchanges = []
            st.session_state.sel_sectors = []
            st.session_state.sel_caps = []
            st.rerun()

    # Advanced filters
    with st.expander("Advanced Filters ▾"):
        adv_cols = st.columns(5)

        with adv_cols[0]:
            fcf_last_year = st.selectbox(
                "Positive FCF (Last Year)",
                ["Any", "Yes", "No"],
                index=0
            )

        with adv_cols[1]:
            fcf_years_3 = st.number_input(
                "Min +FCF Years (3yr)", min_value=0, max_value=3, value=0,
                help="Min years with positive FCF in last 3 years"
            )

        with adv_cols[2]:
            fcf_years_5 = st.number_input(
                "Min +FCF Years (5yr)", min_value=0, max_value=5, value=0,
                help="Min years with positive FCF in last 5 years"
            )

        with adv_cols[3]:
            fcf_years_10 = st.number_input(
                "Min +FCF Years (10yr)", min_value=0, max_value=10, value=0,
                help="Min years with positive FCF in last 10 years"
            )

        with adv_cols[4]:
            min_gross_margin = st.number_input(
                "Min Gross Margin %", min_value=0.0, max_value=100.0, value=0.0, step=5.0
            )

    # Build filters dict (empty list = all)
    batch_filters = {
        'sector': st.session_state.sel_sectors,
        'exchange': st.session_state.sel_exchanges,
        'market_cap_universe': st.session_state.sel_caps,
        'positive_fcf_last_year': fcf_last_year,
        'positive_fcf_years_3': fcf_years_3,
        'positive_fcf_years_5': fcf_years_5,
        'positive_fcf_years_10': fcf_years_10,
        'min_gross_margin': min_gross_margin,
    }

    # Show active filters summary
    active_filters = []
    if st.session_state.sel_exchanges:
        active_filters.append(f"Exchanges: {', '.join(st.session_state.sel_exchanges)}")
    if st.session_state.sel_sectors:
        active_filters.append(f"Sectors: {', '.join(st.session_state.sel_sectors)}")
    if st.session_state.sel_caps:
        active_filters.append(f"Market Cap: {', '.join(st.session_state.sel_caps)}")

    if active_filters:
        st.caption("Active: " + " | ".join(active_filters))
    else:
        st.caption("No filters - screening all stocks")

    st.markdown("---")

    # Run button
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        run_batch = st.button("Run Batch Analysis", type="primary", use_container_width=True)

    with col2:
        stop_batch = st.button("Stop", use_container_width=True)

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

                    analyzed_count = 0
                    skipped_count = 0

                    for i, stock in enumerate(filtered_stocks):
                        ticker_batch = stock['ticker']
                        pct = (i + 1) / len(filtered_stocks)
                        progress_bar.progress(pct)

                        # Check if recently analyzed with same params
                        recently_run, _ = was_recently_analyzed(ticker_batch, params)
                        if recently_run:
                            status_text.text(f"Skipping {ticker_batch} (recently analyzed)... ({i+1}/{len(filtered_stocks)})")
                            skipped_count += 1
                            time.sleep(0.1)
                            continue

                        status_text.text(f"Analyzing {ticker_batch}... ({i+1}/{len(filtered_stocks)})")

                        try:
                            result = analyzer.analyze_stock(ticker_batch, params=params)
                            if result:
                                add_to_history(result, params)
                                analyzed_count += 1
                        except Exception as e:
                            print(f"Error analyzing {ticker_batch}: {e}")

                        time.sleep(0.3)

                    progress_bar.progress(1.0)
                    if analyzed_count > 0 or skipped_count > 0:
                        msg = f"Done! Analyzed {analyzed_count} stocks"
                        if skipped_count > 0:
                            msg += f", skipped {skipped_count} (recently analyzed)"
                        msg += ". Check 'Analysis History' tab."
                        status_text.success(msg)
                    else:
                        status_text.warning("No new stocks to analyze.")
                else:
                    status_text.warning("No stocks matched the filter criteria.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== TAB: ANALYSIS HISTORY ====================
with tab_history:
    if not st.session_state.analysis_history:
        st.info("No analyses yet. Analyze stocks to see them here.")
    else:
        # Build history table with Universe and Sector
        history_data = []
        for r in st.session_state.analysis_history:
            dcf_r = r.get('dcf_result', {})
            mkt_cap = r.get('market_cap', 0)

            # Parse run_date
            run_date_str = r.get('run_date')
            if run_date_str:
                try:
                    run_date = datetime.fromisoformat(run_date_str)
                except:
                    run_date = None
            else:
                run_date = None

            history_data.append({
                'Ticker': r.get('ticker', ''),
                'Universe': get_market_cap_universe(mkt_cap),
                'Sector': r.get('sector', 'N/A'),
                'Company': r.get('company_name', '')[:25],
                'Price': r.get('current_price', 0),
                'Intrinsic': r.get('intrinsic_value', 0),
                'Discount': r.get('discount', 0),
                'Market Cap': mkt_cap,
                'Last Run': run_date,
            })

        history_df = pd.DataFrame(history_data)

        # Format Market Cap with M/B/T notation
        def format_mkt_cap(val):
            if val >= 1e12:
                return f"${val/1e12:.1f}T"
            elif val >= 1e9:
                return f"${val/1e9:.1f}B"
            elif val >= 1e6:
                return f"${val/1e6:.1f}M"
            else:
                return f"${val:,.0f}"

        history_df['Mkt Cap'] = history_df['Market Cap'].apply(format_mkt_cap)

        # Table width matches charts (2/3 of display)
        table_col, table_spacer = st.columns([2, 1])

        with table_col:
            # ===== FILTERS FOR TABLE =====
            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:
                # Universe filter
                universe_options = sorted(history_df['Universe'].unique().tolist())
                selected_universe = st.multiselect(
                    "Filter by Universe",
                    options=universe_options,
                    default=[],
                    placeholder="All Universes"
                )

            with filter_col2:
                # Sector filter
                sector_options = sorted(history_df['Sector'].unique().tolist())
                selected_sector_filter = st.multiselect(
                    "Filter by Sector",
                    options=sector_options,
                    default=[],
                    placeholder="All Sectors"
                )

            # Apply filters
            filtered_df = history_df.copy()
            if selected_universe:
                filtered_df = filtered_df[filtered_df['Universe'].isin(selected_universe)]
            if selected_sector_filter:
                filtered_df = filtered_df[filtered_df['Sector'].isin(selected_sector_filter)]

            # Show count
            st.caption(f"Showing {len(filtered_df)} of {len(history_df)} stocks")

            # Selection for details
            if len(filtered_df) > 0:
                ticker_options = filtered_df['Ticker'].tolist()
                selected_ticker = st.selectbox("Select Ticker for Details", ticker_options, index=0)
            else:
                selected_ticker = None

            # Drop raw Market Cap column, keep formatted Mkt Cap
            display_df = filtered_df.drop(columns=['Market Cap'])

            # Display table with sorting enabled via column_config
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                height=350,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Universe": st.column_config.TextColumn("Universe", width="small"),
                    "Sector": st.column_config.TextColumn("Sector", width="small"),
                    "Company": st.column_config.TextColumn("Company", width="medium"),
                    "Price": st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
                    "Intrinsic": st.column_config.NumberColumn("Intrinsic", format="$%.2f", width="small"),
                    "Discount": st.column_config.NumberColumn("Discount", format="%.1f%%", width="small"),
                    "Mkt Cap": st.column_config.TextColumn("Mkt Cap", width="small"),
                    "Last Run": st.column_config.DatetimeColumn("Last Run", format="MM/DD/YY HH:mm", width="small"),
                }
            )

        with table_spacer:
            pass  # Reserved space

        st.markdown("---")

        # Show details for selected ticker
        if selected_ticker:
            selected_result = next((r for r in st.session_state.analysis_history if r['ticker'] == selected_ticker), None)

            if selected_result:
                import altair as alt
                dcf_selected = selected_result.get('dcf_result', {})
                input_type_sel = dcf_selected.get('input_type', 'fcf')
                input_label = "EPS" if input_type_sel == 'eps_cont_ops' else "FCF/Share"

                st.markdown(f"### {selected_ticker} - Financial History")

                # Helper function to create compact charts with trendline
                def create_mini_chart(data, value_col, title, color='#1a73e8', is_currency=True, is_percent=False, show_projection=False, projections=None, last_year=None):
                    if not data:
                        return None

                    years = []
                    values = []
                    types = []
                    year_nums = []  # Numeric year for trendline calculation

                    for year, value in data:
                        # Skip entries with invalid years
                        if year is None or not isinstance(year, (int, float)):
                            continue
                        years.append(str(int(year)))
                        values.append(value)
                        types.append('Historical')
                        year_nums.append(int(year))

                    # Add projections if provided
                    if show_projection and projections and last_year and isinstance(last_year, (int, float)):
                        for i, proj_value in enumerate(projections):
                            proj_year = int(last_year) + i + 1
                            years.append(str(proj_year))
                            values.append(proj_value)
                            types.append('Projected')
                            year_nums.append(proj_year)

                    # Return None if no valid data after filtering
                    if not years:
                        return None

                    chart_df = pd.DataFrame({
                        'Year': years,
                        value_col: values,
                        'Type': types,
                        'YearNum': year_nums
                    })

                    # Y-axis format: $M/B/T for currency, % for percent, plain for others
                    if is_currency:
                        # Custom JavaScript expression for $M/B/T format
                        y_axis = alt.Axis(
                            labelFontSize=10,
                            labelExpr="abs(datum.value) >= 1e12 ? '$' + format(datum.value/1e12, '.1f') + 'T' : abs(datum.value) >= 1e9 ? '$' + format(datum.value/1e9, '.1f') + 'B' : abs(datum.value) >= 1e6 ? '$' + format(datum.value/1e6, '.1f') + 'M' : '$' + format(datum.value, ',.0f')"
                        )
                    elif is_percent:
                        y_axis = alt.Axis(labelFontSize=10, format='.1f')
                    else:
                        # For shares - use B/M notation without $
                        y_axis = alt.Axis(
                            labelFontSize=10,
                            labelExpr="datum.value >= 1e9 ? format(datum.value/1e9, '.1f') + 'B' : datum.value >= 1e6 ? format(datum.value/1e6, '.1f') + 'M' : format(datum.value, ',.0f')"
                        )

                    # Bar chart
                    if show_projection:
                        bars = alt.Chart(chart_df).mark_bar().encode(
                            x=alt.X('Year:N', sort=None, axis=alt.Axis(labelAngle=-45, labelFontSize=9), title=None),
                            y=alt.Y(f'{value_col}:Q', axis=y_axis, title=None),
                            color=alt.Color('Type:N', scale=alt.Scale(
                                domain=['Historical', 'Projected'],
                                range=[color, '#fbbc04']
                            ), legend=None)
                        )
                    else:
                        bars = alt.Chart(chart_df).mark_bar(color=color).encode(
                            x=alt.X('Year:N', sort=None, axis=alt.Axis(labelAngle=-45, labelFontSize=9), title=None),
                            y=alt.Y(f'{value_col}:Q', axis=y_axis, title=None)
                        )

                    # Trendline (regression on historical data only)
                    hist_df = chart_df[chart_df['Type'] == 'Historical'].copy()
                    if len(hist_df) >= 2:
                        trendline = alt.Chart(hist_df).transform_regression(
                            'YearNum', value_col
                        ).mark_line(
                            color='#333333',
                            strokeDash=[4, 4],
                            strokeWidth=2
                        ).encode(
                            x=alt.X('Year:N', sort=None),
                            y=alt.Y(f'{value_col}:Q')
                        )
                        chart = (bars + trendline).properties(
                            height=200,
                            title=alt.TitleParams(text=title, fontSize=13, fontWeight='bold')
                        )
                    else:
                        chart = bars.properties(
                            height=200,
                            title=alt.TitleParams(text=title, fontSize=13, fontWeight='bold')
                        )

                    return chart

                # Get data from dcf_result
                historical_data = dcf_selected.get('historical_data', [])
                fcf_projections = dcf_selected.get('fcf_projections', [])
                revenue_history = dcf_selected.get('revenue_history', [])
                gross_margin_history = dcf_selected.get('gross_margin_history', [])
                debt_history = dcf_selected.get('debt_history', [])
                capex_history = dcf_selected.get('capex_history', [])
                shares_history = dcf_selected.get('shares_history', [])

                if historical_data:
                    last_year = max(h[0] for h in historical_data)
                else:
                    last_year = datetime.now().year - 1

                # Layout: 2/3 for charts (2 cols x 3 rows), 1/3 reserved for future use
                charts_col, future_col = st.columns([2, 1])

                with charts_col:
                    # Row 1: FCF, Revenue
                    r1c1, r1c2 = st.columns(2)
                    with r1c1:
                        fcf_chart = create_mini_chart(
                            historical_data, input_label, f'{input_label} (w/ Proj)',
                            color='#1a73e8', is_currency=True, show_projection=True,
                            projections=fcf_projections, last_year=last_year
                        )
                        if fcf_chart:
                            st.altair_chart(fcf_chart, use_container_width=True)

                    with r1c2:
                        rev_chart = create_mini_chart(
                            revenue_history, 'Revenue', 'Revenue',
                            color='#34a853', is_currency=True
                        )
                        if rev_chart:
                            st.altair_chart(rev_chart, use_container_width=True)
                        elif not revenue_history:
                            st.caption("Revenue: No data")

                    # Row 2: Gross Margin, Debt
                    r2c1, r2c2 = st.columns(2)
                    with r2c1:
                        gm_chart = create_mini_chart(
                            gross_margin_history, 'Margin %', 'Gross Margin %',
                            color='#673ab7', is_currency=False, is_percent=True
                        )
                        if gm_chart:
                            st.altair_chart(gm_chart, use_container_width=True)
                        elif not gross_margin_history:
                            st.caption("Gross Margin: No data")

                    with r2c2:
                        debt_chart = create_mini_chart(
                            debt_history, 'Debt', 'Total Debt',
                            color='#ea4335', is_currency=True
                        )
                        if debt_chart:
                            st.altair_chart(debt_chart, use_container_width=True)
                        elif not debt_history:
                            st.caption("Debt: No data")

                    # Row 3: Capex, Shares Outstanding
                    r3c1, r3c2 = st.columns(2)
                    with r3c1:
                        capex_chart = create_mini_chart(
                            capex_history, 'Capex', 'Capex',
                            color='#ff9800', is_currency=True
                        )
                        if capex_chart:
                            st.altair_chart(capex_chart, use_container_width=True)
                        elif not capex_history:
                            st.caption("Capex: No data")

                    with r3c2:
                        shares_chart = create_mini_chart(
                            shares_history, 'Shares', 'Shares Outstanding',
                            color='#00bcd4', is_currency=False, is_percent=False
                        )
                        if shares_chart:
                            st.altair_chart(shares_chart, use_container_width=True)
                        elif not shares_history:
                            st.caption("Shares: No data")

                with future_col:
                    # Reserved for future use
                    pass

# Footer
st.markdown("---")
st.caption("DCF Stock Analyzer | Built with Streamlit | [GitHub](https://github.com/mcemkarahan-dev/DCF)")
