"""
Alternative Data Fetcher using Yahoo Finance (yfinance)
No API key required - completely free!
"""

import yfinance as yf
from typing import List, Dict, Optional
import time


class YahooFinanceFetcher:
    def __init__(self, api_key: str = None):
        """
        Initialize Yahoo Finance fetcher
        api_key parameter ignored - kept for compatibility
        """
        self.api_key = api_key  # Not used, but keeps interface consistent
    
    def get_company_profile(self, ticker: str) -> Optional[Dict]:
        """Get company profile information"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'symbol': ticker,
                'companyName': info.get('longName', ticker),
                'exchangeShortName': info.get('exchange', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'mktCap': info.get('marketCap', 0)
            }
        except Exception as e:
            print(f"Error fetching profile for {ticker}: {e}")
            return None
    
    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get income statement data"""
        try:
            stock = yf.Ticker(ticker)
            
            if period == "annual":
                financials = stock.financials
            else:
                financials = stock.quarterly_financials
            
            if financials is None or financials.empty:
                return []
            
            # Get shares outstanding for EPS calculation
            info = stock.info
            shares_outstanding = info.get('sharesOutstanding', 0)
            
            # Convert to list of dicts
            results = []
            for date in financials.columns[:limit]:
                data = financials[date]
                
                # Calculate EPS from net income and shares
                net_income = data.get('Net Income', 0) or 0
                eps_cont_ops = 0
                if shares_outstanding > 0 and net_income != 0:
                    eps_cont_ops = net_income / shares_outstanding
                
                results.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'revenue': data.get('Total Revenue', 0),
                    'operatingIncome': data.get('Operating Income', 0),
                    'netIncome': net_income,
                    'eps_cont_ops': eps_cont_ops,
                    'period': period
                })
            
            return results
        except Exception as e:
            print(f"Error fetching income statement for {ticker}: {e}")
            return []
    
    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get balance sheet data"""
        try:
            stock = yf.Ticker(ticker)
            
            if period == "annual":
                balance_sheet = stock.balance_sheet
            else:
                balance_sheet = stock.quarterly_balance_sheet
            
            if balance_sheet is None or balance_sheet.empty:
                return []
            
            results = []
            for date in balance_sheet.columns[:limit]:
                data = balance_sheet[date]
                results.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'cashAndCashEquivalents': data.get('Cash And Cash Equivalents', 0),
                    'totalDebt': data.get('Total Debt', 0),
                    'commonStock': data.get('Common Stock', 0),
                    'period': period
                })
            
            return results
        except Exception as e:
            print(f"Error fetching balance sheet for {ticker}: {e}")
            return []
    
    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get cash flow statement data"""
        try:
            stock = yf.Ticker(ticker)
            
            if period == "annual":
                cashflow = stock.cashflow
            else:
                cashflow = stock.quarterly_cashflow
            
            if cashflow is None or cashflow.empty:
                return []
            
            results = []
            for date in cashflow.columns[:limit]:
                data = cashflow[date]
                
                # Calculate free cash flow
                operating_cf = data.get('Operating Cash Flow', 0) or 0
                capex = data.get('Capital Expenditure', 0) or 0
                
                # CapEx is usually negative in yfinance
                if capex > 0:
                    capex = -capex
                
                fcf = operating_cf + capex
                
                results.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'operatingCashFlow': operating_cf,
                    'capitalExpenditure': capex,
                    'freeCashFlow': fcf,
                    'period': period
                })
            
            return results
        except Exception as e:
            print(f"Error fetching cash flow for {ticker}: {e}")
            return []
    
    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 5) -> List[Dict]:
        """Get key financial metrics"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get shares outstanding
            shares = info.get('sharesOutstanding', 0)
            
            # Return dummy data for compatibility
            results = []
            for i in range(limit):
                results.append({
                    'numberOfShares': shares
                })
            
            return results
        except Exception as e:
            print(f"Error fetching key metrics for {ticker}: {e}")
            return []
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Try different price fields
            price = (info.get('currentPrice') or 
                    info.get('regularMarketPrice') or 
                    info.get('previousClose'))
            
            return float(price) if price else None
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
    
    def get_financial_data_complete(self, ticker: str) -> Dict:
        """
        Get all financial data needed for DCF analysis
        Returns comprehensive dataset
        """
        print(f"Fetching data for {ticker} from Yahoo Finance...")
        
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
            'current_price': current_price,
            'reporting_currency': 'USD',  # Yahoo Finance data is typically in USD
            'stock_currency': 'USD'
        }
    
    def get_exchange_tickers(self, exchange: str, limit: int = None) -> List[str]:
        """Get list of tickers for a specific exchange"""
        # This is harder with yfinance - would need to scrape or use a ticker list
        print("Note: Exchange listing not available with Yahoo Finance")
        print("Please provide specific tickers to analyze")
        return []
    
    def calculate_fcf_from_statements(self, cash_flow: Dict) -> float:
        """
        Calculate Free Cash Flow from cash flow statement
        Already calculated in get_cash_flow, just return it
        """
        return cash_flow.get('freeCashFlow', 0) or 0


# Example usage and testing
if __name__ == "__main__":
    fetcher = YahooFinanceFetcher()
    
    # Test with Apple
    data = fetcher.get_financial_data_complete("AAPL")
    
    print(f"Company: {data['profile'].get('companyName') if data['profile'] else 'N/A'}")
    print(f"Current Price: ${data['current_price']}")
    
    if data['cash_flows']:
        latest_cf = data['cash_flows'][0]
        fcf = latest_cf.get('freeCashFlow', 0)
        print(f"Latest FCF: ${fcf:,.0f}")
