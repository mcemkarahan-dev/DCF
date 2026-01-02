"""
Roic.ai Data Fetcher
Provides 30+ years of financial data from SEC filings
"""

import requests
from typing import List, Dict, Optional
import time


class RoicDataFetcher:
    def __init__(self, api_key: str):
        """
        Initialize Roic.ai fetcher with API key
        """
        self.api_key = api_key
        self.base_url = "https://api.roic.ai/v2"
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[List]:
        """Make API request with error handling"""
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            time.sleep(0.1)  # Rate limiting courtesy
            
            data = response.json()
            # Debug output disabled - uncomment if needed
            # print(f"DEBUG - {endpoint}: {type(data)}, Length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
    
    def get_company_profile(self, ticker: str) -> Optional[Dict]:
        """Get company profile information"""
        endpoint = f"company/profile/{ticker}"
        
        data = self._make_request(endpoint)
        
        if not data or len(data) == 0:
            return {
                'symbol': ticker,
                'companyName': ticker,
                'exchangeShortName': 'N/A',
                'sector': 'N/A',
                'industry': 'N/A',
                'mktCap': 0
            }
        
        profile = data[0]

        return {
            'symbol': profile.get('ticker') or ticker,
            'companyName': profile.get('company_name') or ticker,
            'exchangeShortName': profile.get('exchange_short_name') or profile.get('exchange') or 'N/A',
            'sector': profile.get('sector') or 'N/A',
            'industry': profile.get('industry') or 'N/A',
            'description': profile.get('description') or '',
            'mktCap': 0  # Will calculate from price * shares if needed
        }
    
    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict]:
        """
        Get income statement data
        period: 'annual' or 'quarterly'
        limit: number of periods to fetch (roic supports 30+ years)
        """
        endpoint = f"fundamental/income-statement/{ticker}"
        params = {'limit': limit}
        
        if period == "quarterly":
            params['period'] = 'quarterly'
        
        data = self._make_request(endpoint, params)
        
        if not data:
            return []
        
        # Convert roic.ai format to our standard format
        results = []
        for item in data:
            # Helper function to safely convert to float
            def to_float(val):
                if val is None:
                    return 0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0
            
            # Debug: show field names for first record
            if len(results) == 0:
                print(f"DEBUG - Income statement fields: {list(item.keys())}")

            # Roic.ai uses different field names
            revenue = to_float(
                item.get('is_sales_revenue_turnover') or
                item.get('is_sales_and_services_revenues') or
                item.get('revenue') or
                item.get('totalRevenue')
            )

            # Operating income / EBIT - roic.ai uses is_oper_income
            operating_income = to_float(
                item.get('is_oper_income') or
                item.get('is_operating_income') or
                item.get('operatingIncome') or
                item.get('ebit')
            )
            
            net_income = to_float(
                item.get('is_net_inc') or
                item.get('netIncome')
            )
            
            # EPS from continuing operations (excluding non-recurring items)
            eps_cont_ops = to_float(
                item.get('is_diluted_eps_from_cont_ops') or
                item.get('is_basic_eps_from_cont_ops') or
                item.get('diluted_eps') or
                item.get('eps')
            )

            # Gross profit for margin calculation
            gross_profit = to_float(
                item.get('is_gross_profit') or
                item.get('grossProfit') or
                item.get('is_gross_inc')
            )

            results.append({
                'date': item.get('date'),
                'revenue': revenue,
                'grossProfit': gross_profit,
                'operatingIncome': operating_income,
                'netIncome': net_income,
                'eps_cont_ops': eps_cont_ops,
                'period': period
            })
        
        return results
    
    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict]:
        """Get balance sheet data"""
        endpoint = f"fundamental/balance-sheet/{ticker}"
        params = {'limit': limit}
        
        if period == "quarterly":
            params['period'] = 'quarterly'
        
        data = self._make_request(endpoint, params)
        
        if not data:
            return []
        
        results = []
        for item in data:
            # Helper function to safely convert to float
            def to_float(val):
                if val is None:
                    return 0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0
            
            # Debug: uncomment to see field names
            # if len(results) == 0:
            #     print(f"DEBUG - Balance sheet fields: {list(item.keys())[:15]}")
            
            # Calculate total debt from short-term + long-term borrowings
            short_term_debt = to_float(
                item.get('bs_st_borrow') or
                item.get('bs_short_term_debt_detailed') or
                item.get('shortTermDebt') or 0
            )
            long_term_debt = to_float(
                item.get('bs_lt_borrow') or
                item.get('bs_long_term_borrowings_detailed') or
                item.get('longTermDebt') or 0
            )
            total_debt = short_term_debt + long_term_debt

            # If still 0, try totalDebt field as fallback
            if total_debt == 0:
                total_debt = to_float(item.get('totalDebt') or item.get('bs_tot_liab') or 0)

            results.append({
                'date': item.get('date'),
                'cashAndCashEquivalents': to_float(
                    item.get('bs_cash_and_equiv') or
                    item.get('cashAndCashEquivalents') or 0
                ),
                'totalDebt': total_debt,
                'commonStock': to_float(
                    item.get('bs_sh_out') or
                    item.get('commonStock') or
                    item.get('totalStockholdersEquity') or 0
                ),
                'period': period
            })
        
        return results
    
    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict]:
        """Get cash flow statement data"""
        endpoint = f"fundamental/cash-flow/{ticker}"
        params = {'limit': limit}
        
        if period == "quarterly":
            params['period'] = 'quarterly'
        
        data = self._make_request(endpoint, params)
        
        if not data:
            return []
        
        results = []
        for item in data:
            # Helper function to safely convert to float
            def to_float(val):
                if val is None:
                    return 0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0
            
            # Debug: show field names for first record
            if len(results) == 0:
                print(f"DEBUG - Cash flow fields: {list(item.keys())}")

            # Roic.ai uses different field names
            operating_cf = to_float(
                item.get('cf_cash_from_operating_activities') or
                item.get('cf_cash_from_oper') or
                item.get('operatingCashFlow') or
                item.get('cashFlowFromOperatingActivities')
            )
            
            capex = to_float(
                item.get('cf_cap_expenditures') or
                item.get('capitalExpenditure') or
                item.get('capitalExpenditures')
            )
            
            # Check if roic already provides FCF
            fcf = to_float(item.get('cf_free_cash_flow'))

            # If not, calculate it
            if fcf == 0 and (operating_cf != 0 or capex != 0):
                # Ensure capex is negative
                if capex > 0:
                    capex = -capex
                fcf = operating_cf + capex

            # Dividends paid - roic.ai uses cf_dvd_paid
            dividends = to_float(
                item.get('cf_dvd_paid') or
                item.get('cf_dividends_paid') or
                item.get('cf_div_paid') or
                item.get('dividendsPaid') or 0
            )

            results.append({
                'date': item.get('date'),
                'operatingCashFlow': operating_cf,
                'capitalExpenditure': capex if capex < 0 else -capex,
                'freeCashFlow': fcf,
                'dividendsPaid': abs(dividends),  # Store as positive for display
                'period': period
            })
        
        return results
    
    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict]:
        """Get key financial metrics including shares outstanding for each period"""
        # Roic.ai has a dedicated per-share endpoint with bs_sh_out field
        endpoint = f"fundamental/per-share/{ticker}"
        params = {'limit': limit}  # Get historical shares for all periods
        
        data = self._make_request(endpoint, params)
        
        # Helper function to safely convert to float
        def to_float(val):
            if val is None:
                return 0
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0
        
        results = []
        if data and len(data) > 0:
            # Return shares for each period
            for item in data:
                shares = to_float(item.get('bs_sh_out'))
                date = item.get('date')
                results.append({
                    'date': date,
                    'numberOfShares': shares
                })
        
        # If we got no data, return empty list
        if not results:
            # Fallback: try to get just current shares
            bs_endpoint = f"fundamental/balance-sheet/{ticker}"
            bs_data = self._make_request(bs_endpoint, {'limit': 1})
            if bs_data and len(bs_data) > 0:
                shares = to_float(bs_data[0].get('bs_sh_out'))
                results.append({'numberOfShares': shares, 'date': None})
        
        return results
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        endpoint = f"stock-prices/latest/{ticker}"
        
        data = self._make_request(endpoint)
        
        if not data:
            return None
        
        # Handle different response formats
        # Could be a list or a dict
        if isinstance(data, list):
            if len(data) > 0:
                item = data[0]
            else:
                return None
        elif isinstance(data, dict):
            item = data
        else:
            return None
        
        # Try different possible field names and convert to float
        price = (item.get('close') or 
                item.get('price') or 
                item.get('lastPrice') or
                item.get('last_price') or
                item.get('adjusted_close') or
                item.get('adj_close'))
        
        # Convert to float if it's a string
        if price is not None:
            try:
                return float(price)
            except (ValueError, TypeError):
                return None
        
        return None
    
    def get_financial_data_complete(self, ticker: str, years_back: int = 10) -> Dict:
        """
        Get all financial data needed for DCF analysis
        years_back: How many years of history to fetch (roic supports 30+)
        """
        print(f"Fetching {years_back} years of data for {ticker} from Roic.ai...")
        
        profile = self.get_company_profile(ticker)
        income_statements = self.get_income_statement(ticker, limit=years_back)
        balance_sheets = self.get_balance_sheet(ticker, limit=years_back)
        cash_flows = self.get_cash_flow(ticker, limit=years_back)
        key_metrics = self.get_key_metrics(ticker, limit=years_back)
        
        # Try to get current price, but don't fail if it doesn't work
        try:
            current_price = self.get_current_price(ticker)
        except Exception as e:
            print(f"Warning: Could not fetch current price: {e}")
            current_price = None
        
        # Keep profile company name from API (don't override with ticker)
        
        return {
            'ticker': ticker,
            'profile': profile,
            'income_statements': income_statements,
            'balance_sheets': balance_sheets,
            'cash_flows': cash_flows,
            'key_metrics': key_metrics,
            'current_price': current_price
        }
    
    def get_exchange_tickers(self, exchange: str, limit: int = None) -> List[str]:
        """Get list of tickers for a specific exchange"""
        # Roic has a tickers endpoint
        endpoint = "tickers"

        data = self._make_request(endpoint)

        if not data:
            return []

        # Filter by exchange if needed
        tickers = []
        for item in data:
            if exchange and item.get('exchange') != exchange:
                continue
            tickers.append(item.get('symbol'))

        if limit:
            tickers = tickers[:limit]

        return tickers

    def get_all_tickers(self) -> List[Dict]:
        """
        Get all available tickers from ROIC.ai with full metadata.
        Returns list of dicts with: symbol, name, sector, exchange, marketCap
        Used for dynamic batch screening.
        """
        endpoint = "tickers"

        data = self._make_request(endpoint)

        if not data:
            print("Warning: ROIC.ai /tickers endpoint returned no data")
            return []

        # Return full ticker data with all available fields
        results = []
        for item in data:
            if isinstance(item, dict):
                ticker_info = {
                    'symbol': item.get('symbol') or item.get('ticker'),
                    'name': item.get('name') or item.get('companyName') or item.get('symbol', ''),
                    'sector': item.get('sector') or 'N/A',
                    'exchange': item.get('exchange') or item.get('exchangeShortName') or 'N/A',
                    'marketCap': item.get('marketCap') or item.get('mktCap') or 0,
                }
                if ticker_info['symbol']:
                    results.append(ticker_info)
            elif isinstance(item, str):
                # If API returns just strings, create minimal dict
                results.append({
                    'symbol': item,
                    'name': item,
                    'sector': 'N/A',
                    'exchange': 'N/A',
                    'marketCap': 0,
                })

        print(f"ROIC.ai returned {len(results)} tickers")
        return results

    def get_filtered_tickers(self, sectors: List[str] = None, exchanges: List[str] = None,
                             market_cap_universes: List[str] = None) -> List[Dict]:
        """
        Get tickers from ROIC.ai with SERVER-SIDE filtering.
        Filters are applied at data fetch time to minimize client processing.

        Args:
            sectors: List of sectors to include (empty = all)
            exchanges: List of exchanges to include (empty = all)
            market_cap_universes: List of market cap tiers (empty = all)
                Options: "Mega Cap", "Large Cap", "Mid Cap", "Small Cap", "Micro Cap"

        Returns:
            List of ticker dicts matching the filters
        """
        endpoint = "tickers"
        data = self._make_request(endpoint)

        if not data:
            print("Warning: ROIC.ai /tickers endpoint returned no data")
            return []

        # Market cap thresholds for universe classification
        def get_market_cap_universe(mkt_cap):
            if not mkt_cap or mkt_cap == 0:
                return "Unknown"
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

        # Normalize exchange names
        def normalize_exchange(exch):
            if not exch:
                return 'N/A'
            exch_upper = exch.upper()
            if 'NASDAQ' in exch_upper or 'NMS' in exch_upper or 'NGM' in exch_upper:
                return 'NASDAQ'
            elif 'NYSE' in exch_upper or 'NYQ' in exch_upper:
                return 'NYSE'
            elif 'AMEX' in exch_upper:
                return 'AMEX'
            return exch

        results = []
        filtered_out = {'sector': 0, 'exchange': 0, 'market_cap': 0}

        for item in data:
            if not isinstance(item, dict):
                continue

            symbol = item.get('symbol') or item.get('ticker')
            if not symbol:
                continue

            # Extract metadata
            raw_sector = item.get('sector') or 'N/A'
            raw_exchange = item.get('exchange') or item.get('exchangeShortName') or 'N/A'
            market_cap = item.get('marketCap') or item.get('mktCap') or 0

            # Normalize values
            exchange = normalize_exchange(raw_exchange)
            universe = get_market_cap_universe(market_cap)

            # Apply filters (empty list = include all)
            # Sector filter
            if sectors and len(sectors) > 0:
                if raw_sector == 'N/A' or raw_sector not in sectors:
                    filtered_out['sector'] += 1
                    continue

            # Exchange filter
            if exchanges and len(exchanges) > 0:
                if exchange == 'N/A' or exchange not in exchanges:
                    filtered_out['exchange'] += 1
                    continue

            # Market cap universe filter
            if market_cap_universes and len(market_cap_universes) > 0:
                if universe == 'Unknown' or universe not in market_cap_universes:
                    filtered_out['market_cap'] += 1
                    continue

            # Passed all filters
            results.append({
                'symbol': symbol,
                'ticker': symbol,  # Alias for compatibility
                'name': item.get('name') or item.get('companyName') or symbol,
                'sector': raw_sector,
                'exchange': exchange,
                'marketCap': market_cap,
                'market_cap': market_cap,  # Alias for compatibility
                'market_cap_universe': universe,
            })

        print(f"ROIC.ai: {len(data)} total → {len(results)} after filters "
              f"(filtered: sector={filtered_out['sector']}, exchange={filtered_out['exchange']}, "
              f"market_cap={filtered_out['market_cap']})")

        # Sort alphabetically by ticker for consistent ordering
        results.sort(key=lambda x: x['ticker'])

        return results
    
    def calculate_fcf_from_statements(self, cash_flow: Dict) -> float:
        """
        Calculate Free Cash Flow from cash flow statement
        Already calculated in get_cash_flow, just return it
        """
        return cash_flow.get('freeCashFlow', 0) or 0


# Test the API
if __name__ == "__main__":
    import sys
    
    api_key = "1e702063f1534ee1b0485da8f461bda9"
    fetcher = RoicDataFetcher(api_key=api_key)
    
    # Test with Apple
    print("Testing Roic.ai API with AAPL...")
    data = fetcher.get_financial_data_complete("AAPL", years_back=10)
    
    print(f"\nCompany: {data['profile'].get('companyName')}")
    print(f"Current Price: ${data['current_price']}")
    
    print(f"\nIncome Statements: {len(data['income_statements'])} periods")
    if data['income_statements']:
        latest = data['income_statements'][0]
        print(f"  Latest period: {latest['date']}")
        print(f"  Revenue: ${latest['revenue']:,.0f}")
    
    print(f"\nCash Flows: {len(data['cash_flows'])} periods")
    if data['cash_flows']:
        latest_cf = data['cash_flows'][0]
        print(f"  Latest period: {latest_cf['date']}")
        print(f"  Free Cash Flow: ${latest_cf['freeCashFlow']:,.0f}")
    
    print(f"\nBalance Sheets: {len(data['balance_sheets'])} periods")
    
    print(f"\n✓ Successfully fetched {len(data['cash_flows'])} years of data!")
