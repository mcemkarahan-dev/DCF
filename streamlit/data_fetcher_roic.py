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
            'companyName': profile.get('name') or ticker,
            'exchangeShortName': profile.get('exchange_name') or 'N/A',
            'sector': profile.get('sector') or 'N/A',
            'industry': profile.get('industry') or 'N/A',
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
            
            # Debug: uncomment to see field names
            # if len(results) == 0:
            #     print(f"DEBUG - Income statement fields: {list(item.keys())[:10]}")
            
            # Roic.ai uses different field names
            revenue = to_float(
                item.get('is_sales_revenue_turnover') or 
                item.get('is_sales_and_services_revenues') or
                item.get('revenue') or 
                item.get('totalRevenue')
            )
            
            operating_income = to_float(
                item.get('is_operating_income') or
                item.get('operatingIncome')
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
            
            results.append({
                'date': item.get('date'),
                'revenue': revenue,
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
            
            results.append({
                'date': item.get('date'),
                'cashAndCashEquivalents': to_float(item.get('cashAndCashEquivalents')),
                'totalDebt': to_float(item.get('totalDebt')),
                'commonStock': to_float(item.get('commonStock') or item.get('totalStockholdersEquity')),
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
            
            # Debug: uncomment to see field names
            # if len(results) == 0:
            #     print(f"DEBUG - Cash flow fields: {list(item.keys())[:10]}")
            
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
            
            results.append({
                'date': item.get('date'),
                'operatingCashFlow': operating_cf,
                'capitalExpenditure': capex if capex < 0 else -capex,
                'freeCashFlow': fcf,
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
        
        # Update profile with actual company name if available
        if income_statements and len(income_statements) > 0:
            profile['companyName'] = ticker  # Roic returns ticker, not full name
        
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
