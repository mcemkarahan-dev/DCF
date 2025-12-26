"""
DCF Stock Analyzer - Streamlit Web App
Professional DCF valuation tool with 30+ years of historical data
"""

import streamlit as st
import pandas as pd

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

# Sidebar - Configuration
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
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
            help="Get your API key from https://roic.ai"
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
        
        wacc = st.slider(
            "WACC (Discount Rate)",
            min_value=0.05,
            max_value=0.20,
            value=preset['wacc'],
            step=0.01,
            format="%.1f%%",
            help="Weighted Average Cost of Capital"
        ) 
        
        terminal_growth = st.slider(
            "Terminal Growth Rate",
            min_value=0.0,
            max_value=0.05,
            value=preset['terminal_growth_rate'],
            step=0.005,
            format="%.1f%%",
            help="Perpetual growth rate"
        )
        
        fcf_growth = st.slider(
            "FCF/EPS Growth Rate",
            min_value=0.0,
            max_value=0.30,
            value=preset['fcf_growth_rate'],
            step=0.01,
            format="%.1f%%",
            help="Projected growth rate"
        )
        
        projection_years = st.slider(
            "Projection Years",
            min_value=3,
            max_value=15,
            value=preset['projection_years'],
            help="Number of years to project"
        )
        
        margin_of_safety = st.slider(
            "Margin of Safety",
            min_value=0.0,
            max_value=0.30,
            value=preset['conservative_adjustment'],
            step=0.05,
            format="%.0f%%",
            help="Safety haircut to intrinsic value"
        )
        
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
            years_back = st.slider(
                "Years of History",
                min_value=5,
                max_value=30,
                value=10,
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
    analyze_button = st.button("🔍 Analyze Stock", type="primary", use_container_width=True)

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
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### {result.get('company_name', ticker)}")
        st.markdown(f"**Sector:** {result.get('sector', 'N/A')}")
    
    with col2:
        st.metric("Current Price", f"${result['current_price']:.2f}")
    
    with col3:
        st.metric("Intrinsic Value", f"${result['intrinsic_value_per_share']:.2f}")
    
    # Valuation assessment
    discount = result['discount_percentage']
    
    if discount > 0:
        st.markdown(f'<div class="metric-card undervalued">✅ UNDERVALUED by {discount:.1f}%</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="metric-card overvalued">⚠️ OVERVALUED by {abs(discount):.1f}%</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    input_type = result.get('input_type', 'fcf')
    input_label = "EPS from Cont Ops" if input_type == 'eps_cont_ops' else "FCF per Share"
    
    with col1:
        st.metric(
            "Input Type",
            input_label,
            help="What metric is being projected"
        )
    
    with col2:
        historical_growth = result.get('historical_fcf_growth', 0) * 100
        st.metric(
            f"Historical Growth (5yr)",
            f"{historical_growth:.1f}%",
            help="Historical CAGR"
        )
    
    with col3:
        projected_growth = result['params']['fcf_growth_rate'] * 100
        st.metric(
            "Projected Growth",
            f"{projected_growth:.1f}%",
            help="Growth rate used in DCF"
        )
    
    with col4:
        wacc = result['params']['wacc'] * 100
        st.metric(
            "WACC",
            f"{wacc:.1f}%",
            help="Discount rate"
        )
    
    # Valuation breakdown
    st.markdown("### 📈 Valuation Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Present Value Components:**")
        
        # Format large numbers
        def format_value(val):
            if val >= 1e12:
                return f"${val/1e12:.2f}T"
            elif val >= 1e9:
                return f"${val/1e9:.2f}B"
            elif val >= 1e6:
                return f"${val/1e6:.2f}M"
            else:
                return f"${val:,.0f}"
        
        pv_fcf = result.get('pv_fcf', 0)
        pv_terminal = result.get('pv_terminal', 0)
        
        st.metric("PV of Projected Cash Flows", format_value(pv_fcf))
        st.metric("PV of Terminal Value", format_value(pv_terminal))
        st.metric("Total Enterprise Value", format_value(result.get('enterprise_value', 0)))
    
    with col2:
        st.markdown("**Per Share Values:**")
        
        equity_value_per_share = result['equity_value'] / result['shares_outstanding']
        
        st.metric("Enterprise Value per Share", f"${result.get('enterprise_value', 0) / result['shares_outstanding']:.2f}")
        st.metric("Equity Value per Share", f"${equity_value_per_share:.2f}")
        st.metric("Intrinsic Value per Share", f"${result['intrinsic_value_per_share']:.2f}")
    
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
                f"{result['params']['wacc']*100:.1f}%",
                f"{result['params']['terminal_growth_rate']*100:.1f}%",
                f"{result['params']['fcf_growth_rate']*100:.1f}%",
                f"{result['params']['projection_years']}",
                f"{result['params']['conservative_adjustment']*100:.1f}%"
            ]
        })
        st.dataframe(params_df, hide_index=True, use_container_width=True)

else:
    # Welcome message
    st.info("👆 Enter a stock ticker and click 'Analyze Stock' to begin")
    
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
