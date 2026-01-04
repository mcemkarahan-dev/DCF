"""
DCF Stock Analyzer - Streamlit Web App
Google Flights-inspired UI with horizontal tabs and filter bar
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
import json
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
    page_title="DCF Screener v2.1",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default for cleaner look
)

# Version for deployment verification
APP_VERSION = "v2.8"

# Compact UI via components.html - debounced to prevent loops
import streamlit.components.v1 as components

components.html("""
<script>
(function() {
    const parent = window.parent.document;
    if (parent.compactUIv26) return;
    parent.compactUIv26 = true;

    let timeout = null;

    function compactUI() {
        // Mark elements we've already processed
        parent.querySelectorAll('button:not([data-compacted])').forEach(btn => {
            btn.setAttribute('data-compacted', '1');
            btn.style.height = '32px';
            btn.style.minHeight = '32px';
            btn.style.padding = '0 12px';
            btn.style.fontSize = '13px';
        });

        parent.querySelectorAll('[data-baseweb="select"]:not([data-compacted])').forEach(sel => {
            sel.setAttribute('data-compacted', '1');
            sel.style.minHeight = '32px';
            sel.style.maxHeight = '38px';
        });

        parent.querySelectorAll('input:not([data-compacted])').forEach(inp => {
            inp.setAttribute('data-compacted', '1');
            inp.style.height = '32px';
            inp.style.minHeight = '32px';
            inp.style.padding = '4px 8px';
        });
    }

    function scheduleCompact() {
        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(compactUI, 100);
    }

    // Initial run
    setTimeout(compactUI, 500);

    // Watch for new elements only (not attribute changes)
    const observer = new MutationObserver(scheduleCompact);
    observer.observe(parent.body, { childList: true, subtree: true });

    console.log('UI compact v2.6 ready');
})();
</script>
""", height=0)

# Custom CSS for Google Flights-inspired styling (Desktop + Mobile)
st.markdown("""
<style>
    /* Import Google's Roboto font */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    /* AGGRESSIVE: Target root and force smaller base font */
    :root {
        font-size: 14px !important;
    }

    /* Apply Roboto font globally with smaller base size */
    html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Roboto', sans-serif !important;
        font-size: 14px !important;
    }

    /* AGGRESSIVE: Target ALL buttons */
    button, [data-testid="baseButton-secondary"], [data-testid="baseButton-primary"] {
        min-height: 32px !important;
        height: 32px !important;
        padding: 0 12px !important;
        font-size: 13px !important;
    }

    /* AGGRESSIVE: Target ALL inputs and selects */
    input, select, [data-baseweb="select"], [data-baseweb="input"] {
        min-height: 32px !important;
        height: 32px !important;
        font-size: 13px !important;
    }

    /* AGGRESSIVE: Target selectbox containers */
    [data-testid="stSelectbox"] > div > div {
        min-height: 32px !important;
    }

    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 32px !important;
        padding: 2px 8px !important;
    }

    /* AGGRESSIVE: Number inputs */
    [data-testid="stNumberInput"] input {
        height: 32px !important;
        padding: 4px 8px !important;
    }

    /* AGGRESSIVE: Labels smaller */
    label, [data-testid="stWidgetLabel"] {
        font-size: 12px !important;
        margin-bottom: 2px !important;
    }

    /* White background throughout */
    .stApp {
        background-color: #ffffff;
    }

    /* Constrain max width and reduce padding */
    .main .block-container {
        background-color: #ffffff;
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        max-width: 1200px;
    }

    /* Reduce vertical spacing globally */
    .element-container {
        margin-bottom: 0.25rem !important;
    }

    /* Reduce spacing between elements */
    .stVerticalBlock > div {
        gap: 0.25rem;
    }

    /* Main header styling - smaller */
    .main-header {
        font-family: 'Roboto', sans-serif;
        font-size: 1.25rem;
        font-weight: 500;
        color: #202124;
        margin-bottom: 0.5rem;
    }

    /* Tab styling - Google Flights style - more compact */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        padding: 0;
        border-bottom: 1px solid #dadce0;
        overflow-x: auto;
        flex-wrap: nowrap;
    }

    .stTabs [data-baseweb="tab"] {
        height: 36px;
        padding: 0 12px;
        background-color: transparent;
        border-radius: 0;
        color: #5f6368;
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        font-size: 13px;
        border: none;
        border-bottom: 2px solid transparent;
        white-space: nowrap;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #202124;
        background-color: #f8f9fa;
    }

    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #1a73e8;
        border-bottom: 2px solid #1a73e8;
    }

    /* Compact selectbox/dropdown styling */
    .stSelectbox > div > div {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 4px;
        min-height: 32px !important;
        padding: 0 8px;
    }

    .stSelectbox > div > div > div {
        padding: 4px 0 !important;
        font-size: 13px !important;
    }

    .stSelectbox > div > div:hover {
        background-color: #f8f9fa;
    }

    .stSelectbox label {
        font-size: 12px !important;
        margin-bottom: 2px !important;
    }

    /* Compact multiselect */
    .stMultiSelect > div > div {
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 4px;
        min-height: 32px !important;
    }

    .stMultiSelect > div > div:hover {
        background-color: #f8f9fa;
    }

    .stMultiSelect label {
        font-family: 'Roboto', sans-serif;
        font-size: 12px !important;
        font-weight: 500;
        color: #3c4043;
        margin-bottom: 2px !important;
    }

    /* Compact number input styling */
    .stNumberInput > div > div > input {
        border: 1px solid #dadce0;
        border-radius: 4px;
        height: 32px !important;
        padding: 4px 8px !important;
        font-size: 13px !important;
    }

    .stNumberInput label {
        font-size: 12px !important;
        margin-bottom: 2px !important;
    }

    /* Compact button styling */
    .stButton > button {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        font-size: 13px;
        border-radius: 4px;
        border: 1px solid #dadce0;
        background-color: #ffffff;
        color: #3c4043;
        min-height: 32px !important;
        height: 32px !important;
        padding: 0 12px !important;
        line-height: 30px;
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

    /* Compact checkbox styling */
    .stCheckbox {
        margin-bottom: 0 !important;
    }

    .stCheckbox label {
        font-size: 13px !important;
    }

    .stCheckbox > label > div {
        padding: 2px 0 !important;
    }

    /* Compact expander styling */
    .streamlit-expanderHeader {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        font-size: 13px !important;
        color: #3c4043;
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 4px;
        padding: 6px 12px !important;
    }

    details[data-testid="stExpander"] {
        border: none !important;
    }

    details[data-testid="stExpander"] > summary {
        padding: 6px 12px !important;
    }

    /* Compact slider */
    .stSlider label {
        font-size: 12px !important;
        margin-bottom: 2px !important;
    }

    /* Metric styling - smaller */
    [data-testid="stMetricValue"] {
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
        font-size: 1.1rem !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 12px !important;
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

    /* Reduce caption/label sizes */
    .stCaption, small {
        font-size: 11px !important;
    }

    /* Info/warning boxes - more compact */
    .stAlert {
        border-radius: 4px;
        border: none;
        padding: 8px 12px !important;
        font-size: 13px;
    }

    /* Clean divider - less margin */
    hr {
        border: none;
        border-top: 1px solid #dadce0;
        margin: 0.5rem 0;
    }

    /* Logo and header container - smaller */
    .logo-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.5rem;
    }

    .logo-svg {
        width: 36px;
        height: 22px;
        flex-shrink: 0;
    }

    .logo-header .main-header {
        margin-bottom: 0;
    }

    /* Section headers - smaller */
    h5, .stMarkdown h5 {
        font-size: 14px !important;
        margin-bottom: 8px !important;
        margin-top: 8px !important;
    }

    /* Column gaps - tighter */
    [data-testid="column"] {
        padding: 0 4px !important;
    }

    /* Progress bar - thinner */
    .stProgress > div > div {
        height: 4px !important;
    }

    /* ==================== MOBILE RESPONSIVE STYLES ==================== */
    @media (max-width: 768px) {
        /* Reduce padding on mobile */
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
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

# JavaScript to inject styles after DOM is ready (more reliable than CSS alone)
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Inject compact styles via JavaScript
    var style = document.createElement('style');
    style.textContent = `
        /* JS-injected compact styles v2.1 */
        button { height: 32px !important; min-height: 32px !important; font-size: 13px !important; }
        input { height: 32px !important; font-size: 13px !important; }
        [data-baseweb="select"] > div { min-height: 32px !important; }
        label { font-size: 12px !important; }
        .main .block-container { max-width: 1200px !important; }
    `;
    document.head.appendChild(style);
    console.log('Compact styles injected via JS');
});
</script>
""", unsafe_allow_html=True)

# Show version at bottom right (small, subtle)
st.markdown(f"""
<div style="position: fixed; bottom: 5px; right: 10px; font-size: 10px; color: #999; z-index: 9999;">
    {APP_VERSION}
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_history' not in st.session_state:
    # Load from persistent database on first run
    st.session_state.analysis_history = db_storage.load_all_history(limit=100)
    # Debug: show storage info
    print(f"Storage backend: {db_storage.get_storage_backend()}")
    print(f"Loaded {len(st.session_state.analysis_history)} items from history")
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

# Currency symbols for formatting
CURRENCY_SYMBOLS = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CNY': '¥',
    'CHF': 'CHF ', 'CAD': 'C$', 'AUD': 'A$', 'HKD': 'HK$', 'SGD': 'S$',
    'KRW': '₩', 'INR': '₹', 'BRL': 'R$', 'MXN': 'MX$', 'TWD': 'NT$',
    'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr', 'PLN': 'zł', 'THB': '฿',
    'ZAR': 'R', 'RUB': '₽', 'TRY': '₺', 'ILS': '₪', 'IDR': 'Rp',
}

def get_currency_symbol(currency_code):
    """Get currency symbol from code, with fallback to code itself"""
    return CURRENCY_SYMBOLS.get(currency_code, f'{currency_code} ')

def format_price_with_currency(value, currency_code):
    """Format a price with the appropriate currency symbol"""
    symbol = get_currency_symbol(currency_code)
    if currency_code in ['JPY', 'KRW', 'IDR']:  # No decimals for these
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"

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
# Logo and branding in single HTML block for tight positioning
# Oreo cookies logo - sketch style
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap');
</style>
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
    <img src="data:image/jpeg;base64,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" width="56" height="36" style="object-fit: contain;"/>
    <span style="font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.25rem; color: #1a73e8; letter-spacing: -0.5px;">Cem's DCF Screener</span>
</div>
''', unsafe_allow_html=True)

# ==================== MAIN TABS (Google Flights Style) ====================
tab_screen, tab_analyze, tab_history = st.tabs([
    "Screen & Analyze",
    "Single Stock",
    "History"
])

# ==================== INITIALIZE DEFAULT SETTINGS ====================
# Initialize data source and API key
if 'data_source' not in st.session_state:
    st.session_state.data_source = "Roic.ai (30+ years)"
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'custom_params' not in st.session_state:
    st.session_state.custom_params = PRESET_CONFIGS['conservative'].copy()

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
            st.error("Please enter your Roic.ai API key in DCF Parameters (Screen & Analyze tab)")
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
        reporting_currency = result.get('reporting_currency', 'USD')
        stock_currency = result.get('stock_currency', 'USD')

        # Header row
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])

        with c1:
            st.markdown(f"### {result['ticker']}")
            country = result.get('country', '')
            country_display = f" • {country}" if country and country not in ['N/A', 'United States', 'United States of America'] else ""
            st.caption(f"{result.get('company_name', '')} • {result.get('sector', 'N/A')} • {result.get('industry', 'N/A')}{country_display}")
            description = result.get('description', '')
            if description:
                # Truncate to ~200 chars for header display
                short_desc = description[:200] + "..." if len(description) > 200 else description
                st.markdown(f"<p style='font-size: 0.85em; color: #64748b; margin-top: -10px;'>{short_desc}</p>", unsafe_allow_html=True)

        with c2:
            price_display = format_price_with_currency(result['current_price'], stock_currency)
            st.metric(f"Price ({stock_currency})", price_display)

        with c3:
            iv_display = format_price_with_currency(result['intrinsic_value'], reporting_currency)
            st.metric(f"IV ({reporting_currency})", iv_display)

        with c4:
            if discount > 0:
                st.metric("Discount", f"{discount:.1f}%", delta="Undervalued", delta_color="normal")
            else:
                st.metric("Premium", f"{abs(discount):.1f}%", delta="Overvalued", delta_color="inverse")

        # Currency mismatch warning for ADRs
        if reporting_currency != stock_currency:
            st.warning(f"**Currency Note:** Stock trades in {stock_currency}, financials reported in {reporting_currency}. Intrinsic value and discount % are calculated in {reporting_currency}.")

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

# ==================== TAB: SCREEN & ANALYZE ====================
with tab_screen:
    # Get all filter options
    all_exchanges = get_all_exchanges()
    all_sectors = get_all_sectors()
    all_caps = get_all_market_cap_universes()

    # Initialize filter states FIRST (before config loading can reference them)
    for ex in all_exchanges:
        if f"ex_{ex}" not in st.session_state:
            st.session_state[f"ex_{ex}"] = False
    for sec in all_sectors:
        if f"sec_{sec}" not in st.session_state:
            st.session_state[f"sec_{sec}"] = False
    for cap in all_caps:
        if f"cap_{cap}" not in st.session_state:
            st.session_state[f"cap_{cap}"] = False
    if "exclude_market_cap_filter" not in st.session_state:
        st.session_state["exclude_market_cap_filter"] = True  # Default to excluded

    # ===== UNIFIED CONFIGURATION PANEL =====
    st.markdown("##### Configuration")

    # Helper to sync DCF params to widget keys
    def sync_params_to_widgets(params):
        """Update widget session state keys from params dict"""
        st.session_state['param_wacc'] = float(params.get('wacc', 0.10) * 100)
        st.session_state['param_terminal'] = float(params.get('terminal_growth_rate', 0.02) * 100)
        st.session_state['param_fcf_growth'] = float(params.get('fcf_growth_rate', 0.05) * 100)
        st.session_state['param_proj_years'] = int(params.get('projection_years', 5))
        st.session_state['param_mos'] = float(params.get('conservative_adjustment', 0.0) * 100)
        st.session_state['param_normalize'] = params.get('normalize_starting_value', True)
        st.session_state['param_norm_years'] = int(params.get('normalization_years', 5))

    # Config management - label row then controls row for alignment
    st.caption("Load / Save Configuration")
    config_col1, config_col2, config_col3 = st.columns([1, 1, 1])

    with config_col1:
        saved_configs = db_storage.list_user_configs()
        config_names = [""] + [c['config_name'] for c in saved_configs]
        selected_config = st.selectbox(
            "config_select",
            options=config_names,
            index=0,
            placeholder="Select saved config...",
            key="config_selector",
            label_visibility="collapsed"
        )

        # Load the selected config
        if selected_config and selected_config != st.session_state.get('last_loaded_config', ''):
            loaded = db_storage.load_user_config(selected_config)
            if loaded:
                # Update DCF params AND widget keys
                if 'dcf_params' in loaded:
                    st.session_state.custom_params = loaded['dcf_params']
                    sync_params_to_widgets(loaded['dcf_params'])
                # Update filter checkboxes
                if 'filters' in loaded:
                    filters = loaded['filters']
                    # Clear all first
                    for ex in all_exchanges:
                        st.session_state[f"ex_{ex}"] = False
                    for sec in all_sectors:
                        st.session_state[f"sec_{sec}"] = False
                    for cap in all_caps:
                        st.session_state[f"cap_{cap}"] = False
                    # Set selected ones
                    for ex in filters.get('exchanges', []):
                        st.session_state[f"ex_{ex}"] = True
                    for sec in filters.get('sectors', []):
                        st.session_state[f"sec_{sec}"] = True
                    for cap in filters.get('market_caps', []):
                        st.session_state[f"cap_{cap}"] = True
                st.session_state['last_loaded_config'] = selected_config
                st.rerun()

    with config_col2:
        # Save button with popover for config name
        with st.popover("Save Config", use_container_width=True):
            save_name = st.text_input("Configuration name:", placeholder="My Config", key="save_config_name")
            if st.button("Save", type="primary", use_container_width=True):
                if save_name:
                    # Get current filter selections
                    current_exchanges = [ex for ex in all_exchanges if st.session_state.get(f"ex_{ex}", False)]
                    current_sectors = [sec for sec in all_sectors if st.session_state.get(f"sec_{sec}", False)]
                    current_caps = [cap for cap in all_caps if st.session_state.get(f"cap_{cap}", False)]

                    config_data = {
                        'dcf_params': st.session_state.get('custom_params', PRESET_CONFIGS['conservative']),
                        'filters': {
                            'exchanges': current_exchanges,
                            'sectors': current_sectors,
                            'market_caps': current_caps
                        }
                    }

                    if db_storage.save_user_config(save_name, config_data):
                        st.success(f"Saved!")
                        st.session_state['last_loaded_config'] = ''
                        st.rerun()
                    else:
                        st.error("Failed to save")
                else:
                    st.warning("Enter a name")

    with config_col3:
        if st.button("Delete", use_container_width=True):
            if selected_config:
                if db_storage.delete_user_config(selected_config):
                    st.success(f"Deleted: {selected_config}")
                    st.session_state['last_loaded_config'] = ''
                    st.rerun()
                else:
                    st.error("Failed to delete")
            else:
                st.warning("Select a config first")

    # DCF Parameters in expander
    with st.expander("DCF Parameters", expanded=False):
        # Preset selector row
        preset_col, api_col = st.columns([1, 1])

        with preset_col:
            preset_options = list(PRESET_CONFIGS.keys())
            current_preset = st.selectbox(
                "Preset",
                options=preset_options,
                index=0,
                format_func=lambda x: PRESET_CONFIGS[x]['name'],
                key="dcf_preset"
            )

            # Apply preset button
            if st.button("Apply Preset"):
                preset_params = PRESET_CONFIGS[current_preset].copy()
                st.session_state.custom_params = preset_params
                sync_params_to_widgets(preset_params)
                st.rerun()

        with api_col:
            # API Key - show current status
            current_key = st.session_state.get('api_key', '')
            masked_key = f"{current_key[:8]}..." if len(current_key) > 8 else current_key
            new_api_key = st.text_input(
                "ROIC API Key",
                value=current_key,
                type="password",
                help=f"Current: {masked_key}" if current_key else "Enter your ROIC.AI API key"
            )
            if new_api_key != current_key:
                st.session_state.api_key = new_api_key

        st.markdown("---")

        # Current params
        current_params = st.session_state.get('custom_params', PRESET_CONFIGS['conservative'])

        # Parameter inputs in columns
        param_col1, param_col2, param_col3, param_col4 = st.columns(4)

        with param_col1:
            wacc = st.number_input(
                "WACC (%)",
                min_value=1.0,
                max_value=30.0,
                value=float(current_params.get('wacc', 0.10) * 100),
                step=0.5,
                key="param_wacc"
            )
            st.session_state.custom_params['wacc'] = wacc / 100

        with param_col2:
            terminal_growth = st.number_input(
                "Terminal Growth (%)",
                min_value=0.0,
                max_value=10.0,
                value=float(current_params.get('terminal_growth_rate', 0.02) * 100),
                step=0.25,
                key="param_terminal"
            )
            st.session_state.custom_params['terminal_growth_rate'] = terminal_growth / 100

        with param_col3:
            fcf_growth = st.number_input(
                "FCF Growth (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(current_params.get('fcf_growth_rate', 0.05) * 100),
                step=1.0,
                key="param_fcf_growth"
            )
            st.session_state.custom_params['fcf_growth_rate'] = fcf_growth / 100

        with param_col4:
            projection_years = st.number_input(
                "Projection Years",
                min_value=3,
                max_value=15,
                value=int(current_params.get('projection_years', 5)),
                step=1,
                key="param_proj_years"
            )
            st.session_state.custom_params['projection_years'] = projection_years

        # Second row of params
        param_col5, param_col6, param_col7, param_col8 = st.columns(4)

        with param_col5:
            conservative_adj = st.number_input(
                "Margin of Safety (%)",
                min_value=0.0,
                max_value=50.0,
                value=float(current_params.get('conservative_adjustment', 0.0) * 100),
                step=5.0,
                key="param_mos"
            )
            st.session_state.custom_params['conservative_adjustment'] = conservative_adj / 100

        with param_col6:
            normalize = st.checkbox(
                "Normalize Starting FCF",
                value=current_params.get('normalize_starting_value', True),
                key="param_normalize"
            )
            st.session_state.custom_params['normalize_starting_value'] = normalize

        with param_col7:
            if normalize:
                norm_years = st.number_input(
                    "Normalization Years",
                    min_value=2,
                    max_value=10,
                    value=int(current_params.get('normalization_years', 5)),
                    step=1,
                    key="param_norm_years"
                )
                st.session_state.custom_params['normalization_years'] = norm_years

        with param_col8:
            input_type = st.selectbox(
                "DCF Input",
                options=['fcf', 'eps_cont_ops'],
                index=0 if current_params.get('dcf_input_type', 'fcf') == 'fcf' else 1,
                format_func=lambda x: "Free Cash Flow" if x == 'fcf' else "EPS (Cont. Ops)",
                key="param_input_type"
            )
            st.session_state.custom_params['dcf_input_type'] = input_type

    st.markdown("---")

    # Filter states already initialized at top of tab_screen

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

    # Screening Filters section
    st.markdown("##### Screening Filters")

    # Filter row - all elements aligned (no labels above individual elements)
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.2, 1.2, 1.2, 0.7, 0.5])
    filter_cols = [filter_col1, filter_col2, filter_col3, filter_col4, filter_col5]

    # Exchange Filter
    with filter_cols[0]:
        # Count selected exchanges from individual checkbox states
        sel_exchanges = [ex for ex in all_exchanges if st.session_state.get(f"ex_{ex}", False)]
        ex_count = len(sel_exchanges)
        if ex_count == 0 or ex_count == len(all_exchanges):
            exchange_label = "Exchange"
        else:
            exchange_label = f"Exchange ({ex_count})"

        with st.expander(f"{exchange_label} ▾", expanded=False):
            # Select All checkbox with callback
            all_selected = ex_count == len(all_exchanges)
            st.checkbox(
                "Select all exchanges",
                value=all_selected,
                key="select_all_exchanges",
                on_change=on_select_all_exchanges
            )

            st.markdown("---")

            # Individual checkboxes - no value param, let session state control
            for ex in all_exchanges:
                st.checkbox(ex, key=f"ex_{ex}")

    # Sector Filter
    with filter_cols[1]:
        # Count selected sectors from individual checkbox states
        sel_sectors = [sec for sec in all_sectors if st.session_state.get(f"sec_{sec}", False)]
        sec_count = len(sel_sectors)
        if sec_count == 0 or sec_count == len(all_sectors):
            sector_label = "Sector"
        else:
            sector_label = f"Sector ({sec_count})"

        with st.expander(f"{sector_label} ▾", expanded=False):
            all_selected = sec_count == len(all_sectors)
            st.checkbox(
                "Select all sectors",
                value=all_selected,
                key="select_all_sectors",
                on_change=on_select_all_sectors
            )

            st.markdown("---")

            # Individual checkboxes - no value param, let session state control
            for sec in all_sectors:
                st.checkbox(sec, key=f"sec_{sec}")

    # Market Cap Filter
    with filter_cols[2]:
        # Check if market cap filter is excluded
        exclude_mkt_cap = st.session_state.get("exclude_market_cap_filter", True)

        # Count selected caps from individual checkbox states
        sel_caps_raw = [cap for cap in all_caps if st.session_state.get(f"cap_{cap}", False)]
        cap_count = len(sel_caps_raw) if not exclude_mkt_cap else 0

        if exclude_mkt_cap:
            cap_label = "Market Cap (off)"
        elif cap_count == 0 or cap_count == len(all_caps):
            cap_label = "Market Cap"
        else:
            cap_label = f"Market Cap ({cap_count})"

        with st.expander(f"{cap_label} ▾", expanded=False):
            # Exclude option at top
            st.checkbox(
                "Exclude Market Cap Screener",
                key="exclude_market_cap_filter",
                help="Check to disable market cap filtering (recommended - data is limited)"
            )

            st.markdown("---")

            all_selected = cap_count == len(all_caps)
            st.checkbox(
                "Select all market caps",
                value=all_selected,
                key="select_all_caps",
                on_change=on_select_all_caps,
                disabled=exclude_mkt_cap
            )

            # Individual checkboxes - disabled when excluded
            for cap in all_caps:
                st.checkbox(cap, key=f"cap_{cap}", disabled=exclude_mkt_cap)

    # Max Stocks - label collapsed for alignment
    with filter_cols[3]:
        max_stocks = st.number_input(
            "Max",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            label_visibility="collapsed",
            help="Max stocks to screen"
        )

    # Reset button callback
    def reset_all_filters():
        for ex in all_exchanges:
            st.session_state[f"ex_{ex}"] = False
        for sec in all_sectors:
            st.session_state[f"sec_{sec}"] = False
        for cap in all_caps:
            st.session_state[f"cap_{cap}"] = False
        st.session_state["exclude_market_cap_filter"] = True

    with filter_cols[4]:
        st.button("Reset", on_click=reset_all_filters)

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

    # Compute selected filters from checkbox states
    sel_exchanges = [ex for ex in all_exchanges if st.session_state.get(f"ex_{ex}", False)]
    sel_sectors = [sec for sec in all_sectors if st.session_state.get(f"sec_{sec}", False)]
    # Market cap filter is empty if excluded
    if st.session_state.get("exclude_market_cap_filter", True):
        sel_caps = []
    else:
        sel_caps = [cap for cap in all_caps if st.session_state.get(f"cap_{cap}", False)]

    # Build filters dict (empty list = all)
    batch_filters = {
        'sector': sel_sectors,
        'exchange': sel_exchanges,
        'market_cap_universe': sel_caps,
        'positive_fcf_last_year': fcf_last_year,
        'positive_fcf_years_3': fcf_years_3,
        'positive_fcf_years_5': fcf_years_5,
        'positive_fcf_years_10': fcf_years_10,
        'min_gross_margin': min_gross_margin,
    }

    # Show active filters summary
    active_filters = []
    if sel_exchanges:
        active_filters.append(f"Exchanges: {', '.join(sel_exchanges)}")
    if sel_sectors:
        active_filters.append(f"Sectors: {', '.join(sel_sectors)}")
    if sel_caps:
        active_filters.append(f"Market Cap: {', '.join(sel_caps)}")

    if active_filters:
        st.caption("Active: " + " | ".join(active_filters))
    else:
        st.caption("No filters - screening all stocks")

    st.markdown("---")

    # Storage status for cache
    backend = db_storage.get_storage_backend()
    total_checked = db_storage.get_checked_tickers_count(batch_filters)
    if "SQLite" in backend:
        st.warning(f"⚠️ Cache: {backend} - **NOT shared** across devices. Total cached: {total_checked}")
    else:
        st.caption(f"Cache: {backend} (shared) | Total cached for these filters: {total_checked}")

    # Run button and controls - left-aligned, equal size, tight spacing
    btn_col1, btn_col2, btn_col3, btn_spacer = st.columns([1, 1, 1, 4])

    with btn_col1:
        run_batch = st.button("Run Batch", type="primary", use_container_width=True)

    with btn_col2:
        stop_batch = st.button("Stop", use_container_width=True)

    with btn_col3:
        if st.button("Clear Cache", use_container_width=True):
            db_storage.clear_all_checked_tickers()
            st.success("Cache cleared!")
            st.rerun()

    # Batch execution
    if run_batch:
        if "Roic" in data_source and not api_key:
            st.error("Please enter your Roic.ai API key in DCF Parameters (Screen & Analyze tab)")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            stats_display = st.empty()
            matched_display = st.empty()

            matched_tickers = []
            checked_count = [0]  # Use list to allow mutation in nested function
            total_count = [0]  # Track total for display
            skipped_recently_checked = [0]  # Track skipped due to recent check

            # Get set of tickers already in history to skip
            existing_tickers = set(r['ticker'] for r in st.session_state.analysis_history)

            # Get tickers recently checked with same filters (last 7 days)
            recently_checked = db_storage.get_recently_checked_tickers(batch_filters, days=7)
            if recently_checked:
                skipped_recently_checked[0] = len(recently_checked)

            # Show debug info in UI
            import hashlib
            filter_str = json.dumps(batch_filters, sort_keys=True)
            hash_bytes = hashlib.md5(filter_str.encode()).digest()[:8]
            filter_hash = int.from_bytes(hash_bytes, byteorder='big', signed=True)

            debug_expander = st.expander(f"🔍 Debug: Cache Status (hash: {filter_hash})", expanded=True)
            with debug_expander:
                st.code(f"Filter hash: {filter_hash}\nFilters: {filter_str[:200]}...")
                st.write(f"**Recently checked tickers in DB:** {len(recently_checked)}")
                if recently_checked:
                    sample = sorted(list(recently_checked))[:20]
                    st.write(f"**First 20 cached:** {', '.join(sample)}")
                    # Show LAST cached ticker (where we should resume from)
                    last_cached = sorted(list(recently_checked))[-1]
                    st.write(f"**Last cached ticker:** {last_cached}")
                st.write(f"**Tickers in history:** {len(existing_tickers)}")
                st.write(f"**Total to skip:** {len(recently_checked | existing_tickers)}")

            try:
                source = "roic" if "Roic" in data_source else "yahoo"
                screener = BatchScreener(data_source=source, api_key=api_key)
                analyzer = DCFAnalyzer(api_key=api_key, data_source=source)

                def update_progress(current, total, message, is_filtering=True):
                    pct = current / total if total > 0 else 0
                    progress_bar.progress(pct)
                    status_text.text(message)
                    # Update counts during filtering phase
                    if is_filtering:
                        checked_count[0] = current
                        total_count[0] = total
                        match_pct = (len(matched_tickers) / current * 100) if current > 0 else 0
                        skip_text = ""
                        if skipped_recently_checked[0] > 0:
                            skip_text = f" | **Cached:** {skipped_recently_checked[0]}"
                        stats_display.markdown(
                            f"**Checked:** {current:,} / {total:,} | **Matched:** {len(matched_tickers)}{skip_text} | **Match Rate:** {match_pct:.1f}%"
                        )

                def on_match(stock):
                    ticker = stock['ticker']
                    matched_tickers.append(ticker)
                    match_pct = (len(matched_tickers) / checked_count[0] * 100) if checked_count[0] > 0 else 0
                    skip_text = ""
                    if skipped_recently_checked[0] > 0:
                        skip_text += f" | **Cached:** {skipped_recently_checked[0]}"
                    stats_display.markdown(
                        f"**Checked:** {checked_count[0]:,} / {total_count[0]:,} | **Matched:** {len(matched_tickers)}{skip_text} | **Match Rate:** {match_pct:.1f}%"
                    )
                    matched_display.success(f"**Matched Tickers:** {', '.join(matched_tickers)}")

                saved_count = [0]  # Track successful saves

                def on_checked(ticker: str, matched: bool):
                    """Save each checked ticker to avoid re-checking"""
                    db_storage.save_checked_ticker(ticker, batch_filters, matched)
                    saved_count[0] += 1

                # Combine all tickers to skip: recently checked + already in history
                all_skip_tickers = recently_checked | existing_tickers

                # Screen stocks
                status_text.text("Screening stocks...")
                first_processed = [None]  # Track first ticker processed

                def on_checked_with_tracking(ticker: str, matched: bool):
                    """Save each checked ticker and track first one"""
                    if first_processed[0] is None:
                        first_processed[0] = ticker
                        # Update debug display with first ticker
                        with debug_expander:
                            st.write(f"**🚀 STARTING FROM:** {ticker}")
                    db_storage.save_checked_ticker(ticker, batch_filters, matched)
                    saved_count[0] += 1

                all_matched = list(screener.screen_stocks_streaming(
                    filters=batch_filters,
                    progress_callback=update_progress,
                    match_callback=on_match,
                    checked_callback=on_checked_with_tracking,
                    exclude_tickers=all_skip_tickers,
                    max_stocks=max_stocks
                ))

                # filtered_stocks is same as all_matched since we excluded at screener level
                filtered_stocks = all_matched

                # Analyze matched stocks
                if filtered_stocks:
                    status_text.text(f"Analyzing {len(filtered_stocks)} new stocks...")

                    analyzed_count = 0

                    for i, stock in enumerate(filtered_stocks):
                        ticker_batch = stock['ticker']
                        pct = (i + 1) / len(filtered_stocks)
                        progress_bar.progress(pct)

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
                    # Show final cache status
                    final_cache_count = db_storage.get_checked_tickers_count(batch_filters)
                    msg = f"Done! Analyzed {analyzed_count} new stocks. Cached: {saved_count[0]} new, {final_cache_count} total. Check 'Analysis History' tab."
                    status_text.success(msg)
                else:
                    # Still show cache update even if no matches
                    final_cache_count = db_storage.get_checked_tickers_count(batch_filters)
                    status_text.warning(f"No stocks matched. Cached: {saved_count[0]} new tickers, {final_cache_count} total for these filters.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== TAB: ANALYSIS HISTORY ====================
with tab_history:
    # Storage status line
    backend = db_storage.get_storage_backend()
    history_count = len(st.session_state.analysis_history)
    st.caption(f"Storage: {backend} | Items: {history_count}")

    # Initialize filter states
    if 'show_positive_iv_only' not in st.session_state:
        st.session_state.show_positive_iv_only = False
    if 'show_undervalued_only' not in st.session_state:
        st.session_state.show_undervalued_only = False

    # All 5 buttons on one line (2 filters + 3 actions)
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5, btn_spacer = st.columns([1, 1, 1, 1, 1, 1])

    with btn_col1:
        # Toggle for positive IV filter
        if st.button(
            "✓ +IV Only" if st.session_state.show_positive_iv_only else "+IV Only",
            type="primary" if st.session_state.show_positive_iv_only else "secondary",
            use_container_width=True
        ):
            st.session_state.show_positive_iv_only = not st.session_state.show_positive_iv_only
            st.rerun()

    with btn_col2:
        # Toggle for undervalued (positive discount) filter
        if st.button(
            "✓ Undervalued" if st.session_state.show_undervalued_only else "Undervalued",
            type="primary" if st.session_state.show_undervalued_only else "secondary",
            use_container_width=True
        ):
            st.session_state.show_undervalued_only = not st.session_state.show_undervalued_only
            st.rerun()

    with btn_col3:
        if st.button("Test DB", type="secondary", use_container_width=True):
            try:
                st.info(f"Backend: {db_storage.get_storage_backend()}")
                test_result = {
                    'ticker': 'TEST',
                    'company_name': 'Test Company',
                    'run_date': datetime.now().isoformat(),
                    'intrinsic_value': 100.0,
                    'current_price': 50.0,
                    'discount_pct': 50.0,
                }
                db_storage.save_analysis(test_result)
                last_error = db_storage.get_last_db_error()
                if last_error:
                    st.error(f"Save failed: {last_error}")
                else:
                    loaded = db_storage.get_analysis('TEST')
                    if loaded:
                        st.success(f"DB works!")
                        db_storage.delete_analysis('TEST')
                    else:
                        st.error("Read failed - check RLS")
            except Exception as e:
                st.error(f"Test error: {str(e)}")

    with btn_col4:
        if st.button("Clear History", type="secondary", use_container_width=True):
            db_storage.clear_all_history()
            st.session_state.analysis_history = []
            st.rerun()

    with btn_col5:
        if st.button("Refresh", type="secondary", use_container_width=True):
            st.session_state.analysis_history = db_storage.load_all_history(limit=100)
            st.rerun()

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
                'Company': r.get('company_name', '')[:25],
                'Universe': get_market_cap_universe(mkt_cap),
                'Sector': r.get('sector', 'N/A'),
                'Ccy': r.get('reporting_currency', 'USD'),
                'Price': r.get('current_price', 0),
                'IV': r.get('intrinsic_value', 0),
                'Discount': r.get('discount', 0),
                'Market Cap': mkt_cap,
                'Last Run': run_date.date() if run_date else None,
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

            # Apply positive IV filter (from button toggle)
            if st.session_state.show_positive_iv_only:
                filtered_df = filtered_df[filtered_df['IV'] > 0]

            # Apply undervalued filter (positive discount = trading below IV)
            if st.session_state.show_undervalued_only:
                filtered_df = filtered_df[filtered_df['Discount'] > 0]

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

                # Show company description when ticker is selected
                if selected_ticker:
                    selected_info = next((r for r in st.session_state.analysis_history if r['ticker'] == selected_ticker), None)
                    if selected_info:
                        company_name = selected_info.get('company_name', '')
                        description = selected_info.get('description', '')
                        if description:
                            short_desc = description[:150] + "..." if len(description) > 150 else description
                            st.markdown(f"<p style='font-size: 0.85em; color: #64748b; margin: 4px 0 8px 0;'><b>{company_name}</b>: {short_desc}</p>", unsafe_allow_html=True)
            else:
                selected_ticker = None

            # Drop raw Market Cap column, keep formatted Mkt Cap, reorder columns
            display_df = filtered_df.drop(columns=['Market Cap'])
            display_df = display_df[['Ticker', 'Company', 'Universe', 'Sector', 'Price', 'IV', 'Discount', 'Mkt Cap', 'Last Run']]

            # Highlight selected row with understated light blue
            def highlight_selected(row):
                if row['Ticker'] == selected_ticker:
                    return ['background-color: #e0f2fe'] * len(row)  # Light blue (sky-100)
                return [''] * len(row)

            styled_df = display_df.style.apply(highlight_selected, axis=1)

            # Display table with sorting enabled via column_config
            st.dataframe(
                styled_df,
                hide_index=True,
                use_container_width=True,
                height=350,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Company": st.column_config.TextColumn("Company", width="medium"),
                    "Universe": st.column_config.TextColumn("Universe", width="small"),
                    "Sector": st.column_config.TextColumn("Sector", width="small"),
                    "Price": st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
                    "IV": st.column_config.NumberColumn("IV", format="$%.2f", width="small"),
                    "Discount": st.column_config.NumberColumn("Discount", format="%.1f%%", width="small"),
                    "Mkt Cap": st.column_config.TextColumn("Mkt Cap", width="small"),
                    "Last Run": st.column_config.DateColumn("Last Run", format="MM/DD/YY", width="small"),
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

                # Header with Re-Analyze button
                header_col, btn_col = st.columns([3, 1])
                with header_col:
                    st.markdown(f"### {selected_ticker} - Financial History")
                with btn_col:
                    if st.button("🔄 Re-Analyze", key="reanalyze_btn", use_container_width=True):
                        # Get current settings
                        reanalyze_data_source = st.session_state.get('data_source', "Roic.ai (30+ years)")
                        reanalyze_api_key = st.session_state.get('api_key', '')
                        reanalyze_params = st.session_state.get('custom_params', PRESET_CONFIGS['conservative'])

                        with st.spinner(f"Re-analyzing {selected_ticker}..."):
                            try:
                                source = "roic" if "Roic" in reanalyze_data_source else "yahoo"
                                analyzer = DCFAnalyzer(api_key=reanalyze_api_key, data_source=source)
                                new_result = analyzer.analyze_stock(selected_ticker, params=reanalyze_params)
                                if new_result:
                                    add_to_history(new_result, reanalyze_params)
                                    st.success(f"✓ {selected_ticker} re-analyzed successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to re-analyze {selected_ticker}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                # Modern, understated color palette
                COLOR_HISTORICAL = '#64748b'      # Slate gray for historical bars
                COLOR_PROJECTED = '#94a3b8'       # Lighter slate for projections
                COLOR_TREND_HIST = '#3b82f6'      # Modern blue for historical trendline
                COLOR_TREND_PROJ = '#f97316'      # Modern orange for projection trendline
                COLOR_LABEL = '#475569'           # Slate for data labels

                # Helper function to create compact charts with trendline
                def create_mini_chart(data, value_col, title, is_currency=True, is_percent=False, show_projection=False, projections=None, last_year=None, vertical_labels=False):
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

                    # Format labels based on value type
                    def format_label(val):
                        if is_percent:
                            return f'{val:.0f}%'
                        elif is_currency:
                            if abs(val) >= 1e12:
                                return f'${val/1e12:.1f}T'
                            elif abs(val) >= 1e9:
                                return f'${val/1e9:.1f}B'
                            elif abs(val) >= 1e6:
                                return f'${val/1e6:.1f}M'
                            elif abs(val) >= 1000:
                                return f'${val/1000:.0f}K'
                            else:
                                return f'${val:.1f}'
                        else:
                            if abs(val) >= 1e9:
                                return f'{val/1e9:.1f}B'
                            elif abs(val) >= 1e6:
                                return f'{val/1e6:.1f}M'
                            else:
                                return f'{val:,.0f}'

                    labels = [format_label(v) for v in values]

                    chart_df = pd.DataFrame({
                        'Year': years,
                        value_col: values,
                        'Type': types,
                        'YearNum': year_nums,
                        'Label': labels
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

                    # Calculate trendline for historical data
                    hist_df = chart_df[chart_df['Type'] == 'Historical'].copy()
                    if len(hist_df) >= 2:
                        x_vals = hist_df['YearNum'].values
                        y_vals = hist_df[value_col].values
                        slope, intercept = np.polyfit(x_vals, y_vals, 1)
                        hist_df['Trend'] = [intercept + slope * yn for yn in hist_df['YearNum']]

                    # Calculate trendline for projected data (if applicable)
                    proj_df = chart_df[chart_df['Type'] == 'Projected'].copy()
                    if show_projection and len(proj_df) >= 2:
                        x_vals_proj = proj_df['YearNum'].values
                        y_vals_proj = proj_df[value_col].values
                        slope_proj, intercept_proj = np.polyfit(x_vals_proj, y_vals_proj, 1)
                        proj_df['TrendProj'] = [intercept_proj + slope_proj * yn for yn in proj_df['YearNum']]

                    # Bar chart with uniform colors
                    if show_projection:
                        bars = alt.Chart(chart_df).mark_bar().encode(
                            x=alt.X('Year:N', sort=None, axis=alt.Axis(labelAngle=-45, labelFontSize=9), title=None),
                            y=alt.Y(f'{value_col}:Q', axis=y_axis, title=None),
                            color=alt.Color('Type:N', scale=alt.Scale(
                                domain=['Historical', 'Projected'],
                                range=[COLOR_HISTORICAL, COLOR_PROJECTED]
                            ), legend=None)
                        )
                    else:
                        bars = alt.Chart(chart_df).mark_bar(color=COLOR_HISTORICAL).encode(
                            x=alt.X('Year:N', sort=None, axis=alt.Axis(labelAngle=-45, labelFontSize=9), title=None),
                            y=alt.Y(f'{value_col}:Q', axis=y_axis, title=None)
                        )

                    # Data labels centered inside bars
                    label_angle = 270 if vertical_labels else 0

                    # Calculate midpoint for label positioning (half of bar height)
                    chart_df['LabelY'] = chart_df[value_col] / 2

                    data_labels = alt.Chart(chart_df).mark_text(
                        align='center',
                        baseline='middle',
                        angle=label_angle,
                        fontSize=8,
                        color='white',
                        fontWeight='bold'
                    ).encode(
                        x=alt.X('Year:N', sort=None),
                        y=alt.Y('LabelY:Q'),
                        text='Label:N'
                    )

                    # Build chart with trendlines
                    layers = [bars, data_labels]

                    # Historical trendline
                    if len(hist_df) >= 2 and 'Trend' in hist_df.columns:
                        trend_hist = alt.Chart(hist_df).mark_line(
                            color=COLOR_TREND_HIST,
                            strokeDash=[4, 4],
                            strokeWidth=2
                        ).encode(
                            x=alt.X('Year:N', sort=None),
                            y=alt.Y('Trend:Q')
                        )
                        layers.append(trend_hist)

                    # Projection trendline (only for FCF chart with projections)
                    if show_projection and len(proj_df) >= 2 and 'TrendProj' in proj_df.columns:
                        trend_proj = alt.Chart(proj_df).mark_line(
                            color=COLOR_TREND_PROJ,
                            strokeDash=[2, 2],
                            strokeWidth=2
                        ).encode(
                            x=alt.X('Year:N', sort=None),
                            y=alt.Y('TrendProj:Q')
                        )
                        layers.append(trend_proj)

                    chart = alt.layer(*layers).properties(
                        height=200,
                        title=alt.TitleParams(text=title, fontSize=13, fontWeight='bold')
                    )

                    return chart

                # Get data from dcf_result
                historical_data = dcf_selected.get('historical_data', [])
                fcf_projections_per_share = dcf_selected.get('fcf_projections', [])
                shares_outstanding = dcf_selected.get('shares_outstanding', 1)

                # Convert per-share projections to total FCF
                fcf_projections = [proj * shares_outstanding for proj in fcf_projections_per_share] if fcf_projections_per_share else []

                total_fcf_history = dcf_selected.get('total_fcf_history', [])
                revenue_history = dcf_selected.get('revenue_history', [])
                ebit_history = dcf_selected.get('ebit_history', [])
                gross_margin_history = dcf_selected.get('gross_margin_history', [])
                operating_margin_history = dcf_selected.get('operating_margin_history', [])
                capex_history = dcf_selected.get('capex_history', [])
                debt_history = dcf_selected.get('debt_history', [])
                dividend_history = dcf_selected.get('dividend_history', [])
                shares_history = dcf_selected.get('shares_history', [])

                if total_fcf_history:
                    last_year = max(h[0] for h in total_fcf_history)
                elif historical_data:
                    last_year = max(h[0] for h in historical_data)
                else:
                    last_year = datetime.now().year - 1

                # Layout: charts on left (narrower, 33% less), spacer, company info on right
                # Charts take ~1.2 (was 1.8), info takes ~1.0 (was 0.6)
                charts_col, spacer_col, info_col = st.columns([1.2, 0.1, 1.0])

                with charts_col:
                    # Two-column chart layout
                    # Col1: FCF, Revenue, EBIT, Total Debt, Capex
                    # Col2: Gross Margin %, Operating Margin %, Dividends, Shares
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        # FCF (with projections)
                        fcf_chart = create_mini_chart(
                            total_fcf_history, 'Total FCF', 'Total FCF (w/ Proj)',
                            is_currency=True, show_projection=True,
                            projections=fcf_projections, last_year=last_year,
                            vertical_labels=True
                        )
                        if fcf_chart:
                            st.altair_chart(fcf_chart, use_container_width=True)
                        elif not total_fcf_history:
                            st.caption("Total FCF: No data")

                        # Revenue
                        rev_chart = create_mini_chart(
                            revenue_history, 'Revenue', 'Revenue',
                            is_currency=True
                        )
                        if rev_chart:
                            st.altair_chart(rev_chart, use_container_width=True)
                        elif not revenue_history:
                            st.caption("Revenue: No data")

                        # EBIT
                        ebit_chart = create_mini_chart(
                            ebit_history, 'EBIT', 'EBIT (Operating Income)',
                            is_currency=True
                        )
                        if ebit_chart:
                            st.altair_chart(ebit_chart, use_container_width=True)
                        elif not ebit_history:
                            st.caption("EBIT: No data")

                        # Total Debt
                        debt_chart = create_mini_chart(
                            debt_history, 'Debt', 'Total Debt',
                            is_currency=True
                        )
                        if debt_chart:
                            st.altair_chart(debt_chart, use_container_width=True)
                        elif not debt_history:
                            st.caption("Debt: No data")

                        # Capex
                        capex_chart = create_mini_chart(
                            capex_history, 'Capex', 'Capex',
                            is_currency=True
                        )
                        if capex_chart:
                            st.altair_chart(capex_chart, use_container_width=True)
                        elif not capex_history:
                            st.caption("Capex: No data")

                    with chart_col2:
                        # Gross Margin %
                        gm_chart = create_mini_chart(
                            gross_margin_history, 'Margin %', 'Gross Margin %',
                            is_currency=False, is_percent=True
                        )
                        if gm_chart:
                            st.altair_chart(gm_chart, use_container_width=True)
                        elif not gross_margin_history:
                            st.caption("Gross Margin: No data")

                        # Operating Margin %
                        op_margin_chart = create_mini_chart(
                            operating_margin_history, 'Op Margin %', 'Operating Margin %',
                            is_currency=False, is_percent=True
                        )
                        if op_margin_chart:
                            st.altair_chart(op_margin_chart, use_container_width=True)
                        elif not operating_margin_history:
                            st.caption("Operating Margin: No data")

                        # Dividends Paid
                        dividend_chart = create_mini_chart(
                            dividend_history, 'Dividends', 'Dividends Paid',
                            is_currency=True
                        )
                        if dividend_chart:
                            st.altair_chart(dividend_chart, use_container_width=True)
                        elif not dividend_history:
                            st.caption("Dividends: No data")

                        # Shares Outstanding
                        shares_chart = create_mini_chart(
                            shares_history, 'Shares', 'Shares Outstanding',
                            is_currency=False, is_percent=False
                        )
                        if shares_chart:
                            st.altair_chart(shares_chart, use_container_width=True)
                        elif not shares_history:
                            st.caption("Shares: No data")

                with spacer_col:
                    pass  # Spacer for visual separation

                with info_col:
                    # Company info panel with gray border
                    company_name = selected_result.get('company_name', selected_ticker)
                    sector = selected_result.get('sector', 'N/A')
                    industry = selected_result.get('industry', 'N/A')
                    description = selected_result.get('description', '')
                    curr_price = selected_result.get('current_price', 0)
                    intrinsic_val = selected_result.get('intrinsic_value', 0)
                    discount = selected_result.get('discount', 0)
                    mkt_cap = selected_result.get('market_cap', 0)
                    country = selected_result.get('country', 'N/A')
                    reporting_currency = selected_result.get('reporting_currency', 'USD')
                    stock_currency = selected_result.get('stock_currency', 'USD')

                    # Format prices with correct currencies
                    price_formatted = format_price_with_currency(curr_price, stock_currency)
                    iv_formatted = format_price_with_currency(intrinsic_val, reporting_currency)

                    # Build the info box with border
                    about_html = ""
                    if description:
                        short_desc = description[:300] + "..." if len(description) > 300 else description
                        about_html = f"<p style='font-size: 0.8em; color: #64748b; margin-top: 8px;'>{short_desc}</p>"

                    # Currency mismatch warning for ADRs
                    currency_warning = ""
                    if reporting_currency != stock_currency:
                        currency_warning = f"""
                        <div style="background: #fef7e0; border: 1px solid #f9ab00; border-radius: 4px; padding: 8px; margin-bottom: 12px; font-size: 0.8em;">
                            <strong>⚠️ Currency Note:</strong> Stock trades in {stock_currency}, financials reported in {reporting_currency}.
                            Intrinsic value shown in {reporting_currency}.
                        </div>
                        """

                    discount_text = f"{discount:.1f}%" if discount > 0 else f"{abs(discount):.1f}%"
                    discount_label = "Discount" if discount > 0 else "Premium"
                    discount_color = "#137333" if discount > 0 else "#c5221f"
                    valuation_text = "Undervalued" if discount > 0 else "Overvalued"

                    # Show country if not US
                    country_display = f" • {country}" if country and country not in ['N/A', 'United States', 'United States of America'] else ""

                    info_box_html = f"""
                    <div style="border: 1px solid #dadce0; border-radius: 8px; padding: 16px; background: #fff;">
                        <div style="font-weight: 600; font-size: 1.1em; color: #202124;">{company_name}</div>
                        <div style="font-size: 0.85em; color: #5f6368; margin-bottom: 12px;">{sector} • {industry}{country_display}</div>
                        {about_html}
                        {currency_warning}
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 12px 0;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <div>
                                <div style="font-size: 0.75em; color: #5f6368;">Current Price ({stock_currency})</div>
                                <div style="font-size: 1.1em; font-weight: 500;">{price_formatted}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75em; color: #5f6368;">Intrinsic Value ({reporting_currency})</div>
                                <div style="font-size: 1.1em; font-weight: 500;">{iv_formatted}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75em; color: #5f6368;">{discount_label}</div>
                                <div style="font-size: 1.1em; font-weight: 500; color: {discount_color};">{discount_text}</div>
                                <div style="font-size: 0.7em; color: {discount_color};">↑ {valuation_text}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75em; color: #5f6368;">Market Cap</div>
                                <div style="font-size: 1.1em; font-weight: 500;">{format_market_cap(mkt_cap)}</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(info_box_html, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("DCF Stock Analyzer | Built with Streamlit | [GitHub](https://github.com/mcemkarahan-dev/DCF)")
