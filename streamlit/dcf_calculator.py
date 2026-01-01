"""
DCF Calculation Engine
Supports multiple DCF models with configurable parameters
"""

from typing import List, Dict, Optional
import statistics
from datetime import datetime


def format_value(value):
    """Format large numbers with T/B/M notation"""
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.1f}T"
    elif abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"


class DCFCalculator:
    def __init__(self):
        self.default_params = {
            'wacc': 0.10,  # 10% weighted average cost of capital
            'terminal_growth_rate': 0.025,  # 2.5% perpetual growth
            'projection_years': 5,
            'fcf_growth_rate': 0.10,  # 10% FCF growth (will be capped by historical)
            'fcf_margin_target': None,  # Will use historical average if None
            'conservative_adjustment': 0.0,  # Margin of safety - haircut to intrinsic value
            'dcf_input_type': 'fcf',  # 'fcf' or 'eps_cont_ops' - what to project
            'normalize_starting_value': True,  # Use average of last N years instead of most recent
            'normalization_years': 5  # Number of years to average (3, 5, or 10)
        }
    
    def calculate_wacc(self, risk_free_rate: float = 0.04, 
                       market_risk_premium: float = 0.08,
                       beta: float = 1.0,
                       debt_to_equity: float = 0.0,
                       tax_rate: float = 0.21) -> float:
        """
        Calculate WACC (Weighted Average Cost of Capital)
        WACC = E/V * Re + D/V * Rd * (1-Tc)
        Using CAPM for cost of equity: Re = Rf + β(Rm - Rf)
        """
        cost_of_equity = risk_free_rate + beta * market_risk_premium
        
        if debt_to_equity > 0:
            # Simplified WACC with debt
            equity_weight = 1 / (1 + debt_to_equity)
            debt_weight = debt_to_equity / (1 + debt_to_equity)
            cost_of_debt = risk_free_rate + 0.02  # Simplified
            
            wacc = (equity_weight * cost_of_equity + 
                   debt_weight * cost_of_debt * (1 - tax_rate))
        else:
            wacc = cost_of_equity
        
        return wacc
    
    def calculate_historical_fcf_growth(self, historical_fcf: List[float], years: int = 5) -> float:
        """
        Calculate compound annual growth rate (CAGR) of historical FCF
        Uses last 'years' periods or all available if fewer
        Returns average growth rate based on actual history
        """
        if not historical_fcf or len(historical_fcf) < 2:
            return 0.0
        
        # Use last N years or all available
        fcf_subset = historical_fcf[:min(years, len(historical_fcf))]
        
        # Remove any zero or negative values for CAGR calculation
        positive_fcf = [fcf for fcf in fcf_subset if fcf > 0]
        
        if len(positive_fcf) < 2:
            return 0.0
        
        # CAGR = (Ending Value / Beginning Value)^(1/years) - 1
        # Note: historical_fcf is ordered newest to oldest
        ending_value = positive_fcf[0]  # Most recent
        beginning_value = positive_fcf[-1]  # Oldest in subset
        num_years = len(positive_fcf) - 1
        
        if beginning_value <= 0 or num_years <= 0:
            return 0.0
        
        cagr = (ending_value / beginning_value) ** (1 / num_years) - 1
        
        # Cap at reasonable limits (-50% to +100%)
        cagr = max(-0.5, min(1.0, cagr))
        
        return cagr
    
    def project_fcf_simple(self, historical_fcf: List[float], 
                          projection_years: int,
                          growth_rate: float,
                          normalize: bool = False,
                          normalization_years: int = 5) -> List[float]:
        """
        Simple FCF projection using constant growth rate
        
        Args:
            normalize: If True, use average of last N years as starting point
            normalization_years: Number of years to average (helps with cyclical businesses)
        """
        if not historical_fcf or len(historical_fcf) == 0:
            return []
        
        # Determine base FCF
        if normalize and len(historical_fcf) >= 2:
            # Use average of last N years (or all available if fewer)
            n = min(normalization_years, len(historical_fcf))
            base_fcf = sum(historical_fcf[:n]) / n
            print(f"  Using {n}-year average as starting point: ${base_fcf:.2f}")
        else:
            # Use most recent FCF as base
            base_fcf = historical_fcf[0]
            print(f"  Using most recent value as starting point: ${base_fcf:.2f}")
        
        projections = []
        for year in range(1, projection_years + 1):
            projected_fcf = base_fcf * ((1 + growth_rate) ** year)
            projections.append(projected_fcf)
        
        return projections
    
    def project_fcf_revenue_based(self, historical_revenue: List[float],
                                 historical_fcf: List[float],
                                 projection_years: int,
                                 revenue_growth_rate: float,
                                 fcf_margin_target: float = None) -> List[float]:
        """
        Project FCF based on revenue growth and FCF margin
        More sophisticated than simple growth
        """
        if not historical_revenue or not historical_fcf:
            return []
        
        # Calculate historical FCF margin
        fcf_margins = []
        for i in range(min(len(historical_revenue), len(historical_fcf))):
            if historical_revenue[i] > 0:
                margin = historical_fcf[i] / historical_revenue[i]
                fcf_margins.append(margin)
        
        # Use target margin or historical average
        if fcf_margin_target is None:
            fcf_margin_target = statistics.mean(fcf_margins) if fcf_margins else 0.15
        
        # Project revenue and apply margin
        base_revenue = historical_revenue[0]
        projections = []
        
        for year in range(1, projection_years + 1):
            projected_revenue = base_revenue * ((1 + revenue_growth_rate) ** year)
            projected_fcf = projected_revenue * fcf_margin_target
            projections.append(projected_fcf)
        
        return projections
    
    def calculate_terminal_value(self, final_fcf: float,
                                terminal_growth_rate: float,
                                wacc: float) -> float:
        """
        Calculate terminal value using Gordon Growth Model
        TV = FCF * (1 + g) / (WACC - g)
        """
        if wacc <= terminal_growth_rate:
            # Invalid: WACC must be greater than terminal growth
            return final_fcf * 20  # Fallback to simple multiple
        
        terminal_value = (final_fcf * (1 + terminal_growth_rate)) / (wacc - terminal_growth_rate)
        return terminal_value
    
    def discount_cash_flows(self, cash_flows: List[float], wacc: float) -> float:
        """
        Discount cash flows to present value
        PV = CF / (1 + WACC)^year
        """
        present_value = 0
        for year, cf in enumerate(cash_flows, start=1):
            pv = cf / ((1 + wacc) ** year)
            present_value += pv
        
        return present_value
    
    def calculate_dcf_simple(self, historical_fcf: List[float],
                           params: Dict = None) -> Dict:
        """
        Simple DCF model using constant FCF growth
        """
        params = {**self.default_params, **(params or {})}
        
        # Project FCF with optional normalization
        fcf_projections = self.project_fcf_simple(
            historical_fcf,
            params['projection_years'],
            params.get('fcf_growth_rate', 0.05),
            normalize=params.get('normalize_starting_value', True),
            normalization_years=params.get('normalization_years', 5)
        )
        
        if not fcf_projections:
            return None
        
        # Calculate terminal value
        terminal_value = self.calculate_terminal_value(
            fcf_projections[-1],
            params['terminal_growth_rate'],
            params['wacc']
        )
        
        # Discount cash flows
        pv_fcf = self.discount_cash_flows(fcf_projections, params['wacc'])
        pv_terminal = terminal_value / ((1 + params['wacc']) ** params['projection_years'])
        
        # Enterprise value
        enterprise_value = pv_fcf + pv_terminal
        
        return {
            'fcf_projections': fcf_projections,
            'pv_fcf': pv_fcf,
            'terminal_value': terminal_value,
            'pv_terminal': pv_terminal,
            'enterprise_value': enterprise_value
        }
    
    def calculate_dcf_revenue_based(self, historical_revenue: List[float],
                                   historical_fcf: List[float],
                                   params: Dict = None) -> Dict:
        """
        Revenue-based DCF model
        Projects revenue growth and applies FCF margin
        """
        params = {**self.default_params, **(params or {})}
        
        # Project FCF based on revenue
        fcf_projections = self.project_fcf_revenue_based(
            historical_revenue,
            historical_fcf,
            params['projection_years'],
            params['revenue_growth_rate'],
            params.get('fcf_margin_target')
        )
        
        if not fcf_projections:
            return None
        
        # Calculate terminal value
        terminal_value = self.calculate_terminal_value(
            fcf_projections[-1],
            params['terminal_growth_rate'],
            params['wacc']
        )
        
        # Discount cash flows
        pv_fcf = self.discount_cash_flows(fcf_projections, params['wacc'])
        pv_terminal = terminal_value / ((1 + params['wacc']) ** params['projection_years'])
        
        # Enterprise value
        enterprise_value = pv_fcf + pv_terminal
        
        return {
            'fcf_projections': fcf_projections,
            'pv_fcf': pv_fcf,
            'terminal_value': terminal_value,
            'pv_terminal': pv_terminal,
            'enterprise_value': enterprise_value
        }
    
    def calculate_intrinsic_value_per_share(self, enterprise_value: float,
                                          cash: float,
                                          debt: float,
                                          shares_outstanding: float) -> float:
        """
        Convert enterprise value to equity value per share
        Equity Value = Enterprise Value + Cash - Debt
        Price per Share = Equity Value / Shares Outstanding
        """
        equity_value = enterprise_value + cash - debt
        
        if shares_outstanding <= 0:
            return 0
        
        intrinsic_value = equity_value / shares_outstanding
        return intrinsic_value
    
    def run_full_dcf(self, financial_data: Dict, 
                    model_type: str = "revenue_based",
                    params: Dict = None) -> Dict:
        """
        Run complete DCF analysis on financial data
        Returns intrinsic value and all intermediate calculations
        """
        params = {**self.default_params, **(params or {})}
        
        # Extract data
        cash_flows = financial_data.get('cash_flows', [])
        income_statements = financial_data.get('income_statements', [])
        balance_sheets = financial_data.get('balance_sheets', [])
        
        if not cash_flows or not balance_sheets:
            print(f"ERROR: Missing data - cash_flows: {len(cash_flows)}, balance_sheets: {len(balance_sheets)}")
            return None
        
        # Get latest balance sheet data FIRST (need shares for EPS calculation)
        latest_bs = balance_sheets[0]
        cash = latest_bs.get('cashAndCashEquivalents', 0) or 0
        debt = latest_bs.get('totalDebt', 0) or 0
        shares = latest_bs.get('commonStock', 0) or 0
        
        # Try to get shares from key metrics
        if financial_data.get('key_metrics') and len(financial_data['key_metrics']) > 0:
            shares_from_metrics = financial_data['key_metrics'][0].get('numberOfShares')
            if shares_from_metrics and shares_from_metrics > 0:
                shares = shares_from_metrics
        
        # If shares still zero or None, try to calculate from market cap and price
        current_price = financial_data.get('current_price')
        if (not shares or shares == 0) and current_price and current_price > 0:
            profile = financial_data.get('profile', {})
            mkt_cap = profile.get('mktCap', 0)
            if mkt_cap and mkt_cap > 0:
                shares = mkt_cap / current_price
        
        print(f"\nShares outstanding: {shares:,.0f}")
        
        # Get historical data based on input type
        input_type = params.get('dcf_input_type', 'fcf')
        
        if input_type == 'eps_cont_ops':
            # Extract EPS from continuing operations (per share)
            historical_values = []
            historical_data = []  # List of (year, value) tuples for charting
            print(f"\nExtracting EPS from Continuing Operations:")
            for i, inc in enumerate(income_statements[:10]):
                eps = inc.get('eps_cont_ops')
                date = inc.get('date')
                if eps and eps != 0:
                    # Store EPS as-is (per share)
                    historical_values.append(eps)
                    # Extract year from date safely
                    year = None
                    if date and date != 'N/A':
                        try:
                            year = int(str(date)[:4])
                        except (ValueError, TypeError):
                            pass
                    if year:
                        historical_data.append((year, eps))
                    print(f"  {date}: EPS = ${eps:.2f}")
                else:
                    print(f"  {date}: EPS = 0 or missing")

            print(f"\nUsing EPS from Continuing Operations as DCF input ({len(historical_values)} periods)")
            print(f"Note: Projecting per-share growth, will multiply by current shares ({shares:,.0f}) for valuation")
        else:
            # Extract FCF per share (more accurate - accounts for buybacks/dilution)
            historical_values = []
            historical_data = []  # List of (year, value) tuples for charting
            print(f"\nExtracting Free Cash Flow per Share:")

            # Get key metrics for historical shares
            key_metrics = financial_data.get('key_metrics', [])

            for i, cf in enumerate(cash_flows[:10]):
                fcf = cf.get('freeCashFlow')
                date = cf.get('date', 'N/A')

                # Get shares outstanding for THIS period by matching date
                period_shares = 0

                # First try to match by date from key_metrics
                if key_metrics:
                    for metric in key_metrics:
                        if metric.get('date') == date:
                            period_shares = metric.get('numberOfShares', 0) or 0
                            break

                # If not found, try balance sheet (less reliable)
                if (not period_shares or period_shares == 0) and i < len(balance_sheets):
                    # Try bs_sh_out if it exists in balance sheet
                    period_shares = balance_sheets[i].get('bs_sh_out', 0) or balance_sheets[i].get('numberOfShares', 0) or 0

                # Fall back to current shares if still not found
                if not period_shares or period_shares == 0:
                    period_shares = shares

                if fcf and fcf != 0 and period_shares > 0:
                    fcf_per_share = fcf / period_shares
                    historical_values.append(fcf_per_share)
                    # Extract year from date safely
                    year = None
                    if date and date != 'N/A':
                        try:
                            year = int(str(date)[:4])
                        except (ValueError, TypeError):
                            pass
                    if year:
                        historical_data.append((year, fcf_per_share))
                    print(f"  {date}: FCF = ${fcf:,.0f}, Shares = {period_shares:,.0f}, FCF/share = ${fcf_per_share:.2f}")
                elif fcf and fcf != 0:
                    print(f"  {date}: FCF = ${fcf:,.0f} (missing shares data - skipping)")
                else:
                    print(f"  {date}: FCF = 0 or missing")

            print(f"\nUsing FCF per Share as DCF input ({len(historical_values)} periods)")
            print(f"Note: Projecting per-share growth, will multiply by current shares ({shares:,.0f}) for valuation")
        
        # Get historical revenue (kept for context, not currently used)
        historical_revenue = []
        for inc in income_statements[:10]:
            revenue = inc.get('revenue')
            if revenue and revenue != 0:
                historical_revenue.append(revenue)

        # ===== EXTRACT ADDITIONAL HISTORICAL SERIES FOR CHARTING =====
        def parse_year(date_str):
            """Safely parse year from date string"""
            if not date_str or date_str == 'N/A':
                return None
            try:
                return int(date_str[:4])
            except (ValueError, TypeError):
                return None

        # Revenue history with years
        revenue_history = []
        for inc in income_statements[:10]:
            year = parse_year(inc.get('date'))
            revenue = inc.get('revenue', 0) or 0
            if year and revenue:
                revenue_history.append((year, revenue))

        # Gross margin history (gross_profit / revenue * 100)
        gross_margin_history = []
        for inc in income_statements[:10]:
            year = parse_year(inc.get('date'))
            revenue = inc.get('revenue', 0) or 0
            gross_profit = inc.get('grossProfit', 0) or 0
            if year and revenue > 0:
                margin = (gross_profit / revenue) * 100
                gross_margin_history.append((year, margin))

        # Debt history
        debt_history = []
        for bs in balance_sheets[:10]:
            year = parse_year(bs.get('date'))
            total_debt = bs.get('totalDebt', 0) or 0
            if year:
                debt_history.append((year, total_debt))

        # Capex history (keep as negative to show below x-axis)
        capex_history = []
        for cf in cash_flows[:10]:
            year = parse_year(cf.get('date'))
            capex = cf.get('capitalExpenditure', 0) or 0
            if year:
                # Keep capex as negative to display below x-axis
                if capex > 0:
                    capex = -capex  # Ensure it's negative (cash outflow)
                capex_history.append((year, capex))

        # Shares outstanding history
        shares_history = []
        key_metrics = financial_data.get('key_metrics', [])
        for metric in key_metrics[:10]:
            year = parse_year(metric.get('date'))
            num_shares = metric.get('numberOfShares', 0) or 0
            if year and num_shares > 0:
                shares_history.append((year, num_shares))
        
        # Run DCF calculation using user-specified growth rate
        # Calculate historical growth rate for informational purposes (5-year or available)
        historical_growth = self.calculate_historical_fcf_growth(historical_values, years=5)
        years_used = min(5, len([val for val in historical_values if val > 0]))
        
        # Use user-specified growth rate directly
        user_growth_rate = params.get('fcf_growth_rate', 0.05)
        
        input_label = "EPS (Cont Ops)" if input_type == 'eps_cont_ops' else "FCF per Share"
        print(f"\nHistorical {input_label} Growth ({years_used}-year CAGR): {historical_growth*100:.1f}%")
        print(f"Projected {input_label} Growth Rate: {user_growth_rate*100:.1f}%")
        
        # Use simple growth model with user-specified rate
        dcf_result = self.calculate_dcf_simple(historical_values, params)
        
        # Add historical growth info to result for display
        if dcf_result:
            dcf_result['historical_fcf_growth'] = historical_growth
            dcf_result['historical_years_used'] = years_used
            dcf_result['input_type'] = input_type
            # Flag to indicate if we used per-share values
            dcf_result['is_per_share'] = (input_type in ['eps_cont_ops', 'fcf'])  # Both are per-share now
            # Add historical data for charting (sorted oldest to newest)
            dcf_result['historical_data'] = sorted(historical_data, key=lambda x: x[0])
            # Add additional historical series for charting
            dcf_result['revenue_history'] = sorted(revenue_history, key=lambda x: x[0])
            dcf_result['gross_margin_history'] = sorted(gross_margin_history, key=lambda x: x[0])
            dcf_result['debt_history'] = sorted(debt_history, key=lambda x: x[0])
            dcf_result['capex_history'] = sorted(capex_history, key=lambda x: x[0])
            dcf_result['shares_history'] = sorted(shares_history, key=lambda x: x[0])
        
        if not dcf_result:
            return None
        
        # Calculate intrinsic value per share
        # Note: For per-share inputs (FCF/share, EPS), enterprise_value is already per-share
        # So we adjust cash and debt to per-share before calculating
        if dcf_result.get('is_per_share'):
            # Enterprise value is already per-share, just adjust for cash and debt per share
            cash_per_share = cash / shares if shares > 0 else 0
            debt_per_share = debt / shares if shares > 0 else 0
            intrinsic_value = dcf_result['enterprise_value'] + cash_per_share - debt_per_share
        else:
            # Old method: enterprise value is total, divide by shares
            intrinsic_value = self.calculate_intrinsic_value_per_share(
                dcf_result['enterprise_value'],
                cash,
                debt,
                shares
            )
        
        # Apply conservative adjustment if specified
        if params['conservative_adjustment'] > 0:
            intrinsic_value *= (1 - params['conservative_adjustment'])
        
        # Calculate total equity value for display
        # For per-share inputs, intrinsic_value is already per-share
        # Multiply by shares to get total equity value
        if dcf_result.get('is_per_share'):
            # Enterprise value from DCF is per-share, convert to total
            enterprise_value_total = dcf_result['enterprise_value'] * shares
            equity_value = enterprise_value_total + cash - debt
        else:
            # Enterprise value is already total
            equity_value = dcf_result['enterprise_value'] + cash - debt
        
        return {
            **dcf_result,
            'intrinsic_value_per_share': intrinsic_value,
            'equity_value': equity_value,
            'cash': cash,
            'debt': debt,
            'shares_outstanding': shares,
            'params': params
        }


class DCFAnalyzer:
    def __init__(self, api_key: str = None, db_path: str = "dcf_analysis.db", data_source: str = "yahoo"):
        """
        Initialize DCF Analyzer

        data_source options:
        - "yahoo": Yahoo Finance (free, 4-5 years of data, no API key needed)
        - "roic": Roic.ai (paid, 30+ years of data, requires API key)
        """
        from database import DCFDatabase
        from screener import StockScreener

        self.db = DCFDatabase(db_path)
        self.data_source = data_source

        # Initialize appropriate data fetcher
        if data_source == "roic":
            from data_fetcher_roic import RoicDataFetcher
            self.fetcher = RoicDataFetcher(api_key)
            print("Using Roic.ai data source (30+ years of history)")
        else:  # yahoo (default)
            from data_fetcher_yahoo import YahooFinanceFetcher
            self.fetcher = YahooFinanceFetcher(api_key)
            print("Using Yahoo Finance data source (4-5 years of history)")

        self.calculator = DCFCalculator()
        self.screener = StockScreener(self.db)

    def analyze_stock(self, ticker: str, params: Dict = None, save: bool = True, years_back: int = None) -> Dict:
        """
        Analyze a single stock with DCF
        years_back: Number of years of historical data to fetch (only used with roic.ai)
        """
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker}")
        print(f"{'='*60}")

        # Determine years_back based on data source and parameters
        if years_back is None:
            if self.data_source == "roic":
                years_back = params.get('projection_years', 10) if params else 10
            else:
                years_back = 5

        # Fetch data
        if hasattr(self.fetcher, 'get_financial_data_complete'):
            if self.data_source == "roic":
                financial_data = self.fetcher.get_financial_data_complete(ticker, years_back=years_back)
            else:
                financial_data = self.fetcher.get_financial_data_complete(ticker)
        else:
            financial_data = self.fetcher.get_financial_data_complete(ticker)

        if not financial_data['profile']:
            print(f"Error: Could not fetch data for {ticker}")
            return None

        # Save company info
        profile = financial_data['profile']
        self.db.add_stock(
            ticker=ticker,
            company_name=profile.get('companyName'),
            exchange=profile.get('exchangeShortName'),
            sector=profile.get('sector'),
            industry=profile.get('industry')
        )

        # Save financial data
        if financial_data['cash_flows']:
            for cf in financial_data['cash_flows'][:5]:
                period_date = cf.get('date')

                income = next((i for i in financial_data['income_statements']
                             if i.get('date') == period_date), {})
                balance = next((b for b in financial_data['balance_sheets']
                              if b.get('date') == period_date), {})

                fcf = self.fetcher.calculate_fcf_from_statements(cf)

                self.db.add_financial_data(
                    ticker=ticker,
                    period_date=period_date,
                    period_type=cf.get('period', 'annual'),
                    revenue=income.get('revenue', 0) or 0,
                    operating_income=income.get('operatingIncome', 0) or 0,
                    net_income=income.get('netIncome', 0) or 0,
                    free_cash_flow=fcf,
                    total_debt=balance.get('totalDebt', 0) or 0,
                    cash_and_equivalents=balance.get('cashAndCashEquivalents', 0) or 0,
                    shares_outstanding=balance.get('commonStock', 0) or 0
                )

        # Run DCF
        dcf_result = self.calculator.run_full_dcf(financial_data, params=params)

        if not dcf_result:
            print(f"Error: Could not calculate DCF for {ticker}")
            return None

        # Extract results
        intrinsic_value = dcf_result['intrinsic_value_per_share']
        current_price = financial_data['current_price']

        # Print results
        print(f"\nCompany: {profile.get('companyName')}")
        print(f"Sector: {profile.get('sector')}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Intrinsic Value: ${intrinsic_value:.2f}")

        discount = ((intrinsic_value - current_price) / current_price * 100) if current_price else 0
        print(f"Discount/Premium: {discount:+.2f}%")

        if discount > 20:
            print(f"*** UNDERVALUED - Trading {abs(discount):.1f}% below intrinsic value ***")
        elif discount < -20:
            print(f"*** OVERVALUED - Trading {abs(discount):.1f}% above intrinsic value ***")
        else:
            print(f"*** FAIRLY VALUED ***")

        # Save DCF calculation
        if save:
            self.db.save_dcf_calculation(
                ticker=ticker,
                model_type=params.get('model_type', 'revenue_based') if params else 'revenue_based',
                parameters=dcf_result['params'],
                intrinsic_value=intrinsic_value,
                current_price=current_price,
                wacc=dcf_result['params']['wacc'],
                terminal_growth_rate=dcf_result['params']['terminal_growth_rate'],
                projection_years=dcf_result['params']['projection_years'],
                fcf_projections=dcf_result['fcf_projections'],
                terminal_value=dcf_result['terminal_value'],
                enterprise_value=dcf_result['enterprise_value'],
                equity_value=dcf_result['equity_value'],
                shares_outstanding=dcf_result['shares_outstanding']
            )

        # Get market cap for universe classification
        market_cap = current_price * dcf_result.get('shares_outstanding', 0) if current_price else 0

        return {
            'ticker': ticker,
            'company_name': profile.get('companyName', ticker),
            'sector': profile.get('sector', 'N/A'),
            'industry': profile.get('industry', 'N/A'),
            'market_cap': market_cap,
            'intrinsic_value': intrinsic_value,
            'current_price': current_price,
            'discount': discount,
            'dcf_result': dcf_result
        }


# Example usage
if __name__ == "__main__":
    calculator = DCFCalculator()
    
    # Example with dummy data
    historical_fcf = [5000000000, 4500000000, 4000000000, 3500000000, 3000000000]
    historical_revenue = [50000000000, 48000000000, 45000000000, 42000000000, 40000000000]
    
    params = {
        'wacc': 0.09,
        'terminal_growth_rate': 0.025,
        'projection_years': 5,
        'revenue_growth_rate': 0.08
    }
    
    result = calculator.calculate_dcf_revenue_based(historical_revenue, historical_fcf, params)
    
    print("DCF Calculation Results:")
    print(f"Projected FCF: {result['fcf_projections']}")
    print(f"PV of FCF: ${result['pv_fcf']:,.0f}")
    print(f"Terminal Value: ${result['terminal_value']:,.0f}")
    print(f"Enterprise Value: ${result['enterprise_value']:,.0f}")
