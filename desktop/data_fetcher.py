"""
Data fetcher module for DCF analyzer
Fetches financial data from Financial Modeling Prep API
Free tier allows 250 requests per day
"""

import requests
from typing import List, Dict, Optional
import time


class DataFetcher:
    def __init__(self, api_key: str = None):
        """
        Initialize data fetcher with API key
        Get free API key from: https://financialmodelingprep.com/developer/docs/
        """
        self.api_key = api_key or "demo"  # demo key for testing, limited to few stocks
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            time.sleep(0.3)  # Rate limiting courtesy
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
    
    def get_stock_list(self, exchange: str = None) -> List[Dict]:
        """
        Get list of all stocks, optionally filtered by exchange
        Exchanges: NYSE, NASDAQ, AMEX, etc.
        """
        endpoint = "stock/list"
        data = self._make_request(endpoint)
        
        if not data:
            return []
        
        # Filter by exchange if specified
        if exchange:
            data = [stock for stock in data if stock.get('exchangeShortName') == exchange]
        
        return data
    
    def get_company_profile(self, ticker: str) -> Optional[Dict]:
        """Get company profile information"""
        endpoint = f"profile/{ticker}"
        data = self._make_request(endpoint)
        return data[0] if data else None
    
    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """
        Get income statement data
        period: 'annual' or 'quarter'
        """
        endpoint = f"income-statement/{ticker}"
        params = {'period': period, 'limit': limit}
        data = self._make_request(endpoint, params)
        return data if data else []
    
    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get balance sheet data"""
        endpoint = f"balance-sheet-statement/{ticker}"
        params = {'period': period, 'limit': limit}
        data = self._make_request(endpoint, params)
        return data if data else []
    
    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get cash flow statement data"""
        endpoint = f"cash-flow-statement/{ticker}"
        params = {'period': period, 'limit': limit}
        data = self._make_request(endpoint, params)
        return data if data else []
    
    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get key financial metrics"""
        endpoint = f"key-metrics/{ticker}"
        params = {'period': period, 'limit': limit}
        data = self._make_request(endpoint, params)
        return data if data else []
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        endpoint = f"quote-short/{ticker}"
        data = self._make_request(endpoint)
        if data and len(data) > 0:
            return data[0].get('price')
        return None
    
    def get_financial_data_complete(self, ticker: str) -> Dict:
        """
        Get all financial data needed for DCF analysis
        Returns comprehensive dataset
        """
        print(f"Fetching data for {ticker}...")
        
        profile = self.get_company_profile(ticker)
        income_statements = self.get_income_statement(ticker)
        balance_sheets = self.get_balance_sheet(ticker)
        cash_flows = self.get_cash_flow(ticker)
        key_metrics = self.get_key_metrics(ticker)
        current_price = self.get_current_price(ticker)
        
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
        stocks = self.get_stock_list(exchange)
        tickers = [stock['symbol'] for stock in stocks if stock.get('symbol')]
        
        if limit:
            tickers = tickers[:limit]
        
        return tickers
    
    def calculate_fcf_from_statements(self, cash_flow: Dict) -> float:
        """
        Calculate Free Cash Flow from cash flow statement
        FCF = Operating Cash Flow - Capital Expenditures
        """
        operating_cf = cash_flow.get('operatingCashFlow', 0) or 0
        capex = cash_flow.get('capitalExpenditure', 0) or 0
        
        # CapEx is usually negative, but sometimes reported as positive
        if capex > 0:
            capex = -capex
        
        fcf = operating_cf + capex  # capex is negative
        return fcf


# Example usage and testing
if __name__ == "__main__":
    # For testing - replace with your API key
    fetcher = DataFetcher(api_key="demo")
    
    # Test with Apple (demo key allows AAPL)
    data = fetcher.get_financial_data_complete("AAPL")
    
    print(f"Company: {data['profile'].get('companyName') if data['profile'] else 'N/A'}")
    print(f"Current Price: ${data['current_price']}")
    
    if data['cash_flows']:
        latest_cf = data['cash_flows'][0]
        fcf = fetcher.calculate_fcf_from_statements(latest_cf)
        print(f"Latest FCF: ${fcf:,.0f}")
