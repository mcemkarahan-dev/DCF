"""
DCF Stock Analyzer - Streamlit Web App
Professional DCF valuation tool with 30+ years of historical data
"""

import streamlit as st
import pandas as pd
import sys
import os

# Add current directory to Python path for Streamlit Cloud compatibility
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct imports - files are in same directory
from dcf_calculator import DCFAnalyzer
from config import PRESET_CONFIGS

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

# Try to load API key from Streamlit secrets (for persistence)
def get_saved_api_key():
    try:
        return st.secrets.get("ROIC_API_KEY", "")
    except:
        return ""

if 'api_key' not in st.session_state or not st.session_state.api_key:
    st.session_state.api_key = get_saved_api_key()

# Sidebar - Configuration
with st.sidebar:
    st.markdown("## Configuration")

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

# Main content
st.markdown('<p class="main-header">📊 DCF Stock Analyzer</p>', unsafe_allow_html=True)
st.markdown("Professional discounted cash flow valuation with 30+ years of historical data")

# Stock input
col1, col2 = st.columns([3, 1])

with col1:
    ticker = st.text_input(
        "Stock Ticker",
        value="AAPL",
        max_chars=10,
        help="Enter stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
    ).upper()

with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
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
                # Initialize analyzer
                source = "roic" if "Roic" in data_source else "yahoo"
                analyzer = DCFAnalyzer(api_key=api_key, data_source=source)
                
                # Run analysis
                result = analyzer.analyze_stock(
                    ticker,
                    params=params,
                    years_back=years_back if "Roic" in data_source else None
                )
                
                st.session_state.analysis_result = result
                
            except Exception as e:
                st.error(f"Error analyzing {ticker}: {str(e)}")
                st.session_state.analysis_result = None

# Display results
if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    # Company header
    st.markdown("---")

    # Helper function for market cap universe
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

    market_cap = result.get('market_cap', 0)
    universe = get_market_cap_universe(market_cap)
    dcf = result['dcf_result']
    shares = dcf.get('shares_outstanding', 1)

    # Format large numbers helper (1 decimal place)
    def format_value(val):
        if val >= 1e12:
            return f"${val/1e12:.1f}T"
        elif val >= 1e9:
            return f"${val/1e9:.1f}B"
        elif val >= 1e6:
            return f"${val/1e6:.1f}M"
        else:
            return f"${val:,.0f}"

    # === HEADER ROW ===
    # Columns: Company | Market Cap | Current Price | Intrinsic Value | [reserved]
    c1, c2, c3, c4, _ = st.columns([1.2, 0.7, 0.7, 0.7, 1.5])

    discount = result['discount']

    with c1:
        st.markdown(f"### {ticker}")
        company_name = result.get('company_name', '')
        sector = result.get('sector', 'N/A')
        # Company name and sector on same line or tight spacing
        st.caption(f"{company_name}  •  {sector}")

    with c2:
        st.metric("Market Cap", format_market_cap(market_cap), universe, delta_color="off")

    with c3:
        st.metric("Current Price", f"${result['current_price']:.2f}")
        # Valuation status under price (tight spacing)
        if discount > 0:
            st.caption(f":green[Undervalued {discount:.1f}%]")
        else:
            st.caption(f":red[Overvalued {abs(discount):.1f}%]")

    with c4:
        st.metric("Intrinsic Value", f"${result['intrinsic_value']:.2f}")

    st.markdown("---")

    # === KEY METRICS ROW ===
    # Columns aligned with header: Input Type | Historical Growth | Projected Growth | WACC | [reserved]
    input_type = result.get('input_type', 'fcf')
    input_label = "EPS from Cont Ops" if input_type == 'eps_cont_ops' else "FCF per Share"

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
        wacc = dcf['params']['wacc'] * 100
        st.metric("WACC", f"{wacc:.1f}%", help="Discount rate")

    st.markdown("---")

    # === VALUATION BREAKDOWN ===
    # Per-share values from DCF
    pv_fcf_ps = dcf.get('pv_fcf', 0)
    pv_terminal_ps = dcf.get('pv_terminal', 0)
    enterprise_ps = dcf.get('enterprise_value', 0)

    # Calculate totals
    pv_fcf_total = pv_fcf_ps * shares
    pv_terminal_total = pv_terminal_ps * shares
    enterprise_total = enterprise_ps * shares
    equity_total = dcf.get('equity_value', 0)
    equity_ps = equity_total / shares if shares else 0
    intrinsic_ps = result['intrinsic_value']
    intrinsic_total = intrinsic_ps * shares

    # Columns aligned with rows above: [1.2] | [0.7] | [0.7] | [0.7] | [reserved]
    c1, c2, c3, c4, _ = st.columns([1.2, 0.7, 0.7, 0.7, 1.5])

    with c1:
        st.markdown("**Valuation Breakdown**")
        st.metric("PV of Projected Cash Flows", format_value(pv_fcf_total), f"${pv_fcf_ps:.1f}/sh")
        st.metric("PV of Terminal Value", format_value(pv_terminal_total), f"${pv_terminal_ps:.1f}/sh")
        st.metric("Enterprise Value", format_value(enterprise_total), f"${enterprise_ps:.1f}/sh")

    with c2:
        st.markdown("&nbsp;")  # Spacer to align with header
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

else:
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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    DCF Stock Analyzer | Built with Streamlit | 
    <a href='https://github.com/mcemkarahan-dev/DCF'>GitHub</a>
</div>
""", unsafe_allow_html=True)
