"""
Batch Stock Screener Module
Provides filtering and batch analysis capabilities for stock universes
Designed for extensibility - easy to add new filter types
"""

import yfinance as yf
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class FilterCategory(Enum):
    """Categories for organizing filters in the UI"""
    BASIC = "Basic Filters"
    MARKET = "Market Filters"
    PROFITABILITY = "Profitability Filters"
    GROWTH = "Growth Filters"
    QUALITY = "Quality Filters"


@dataclass
class FilterDefinition:
    """Definition of a filter parameter"""
    key: str
    label: str
    category: FilterCategory
    filter_type: str  # 'select', 'multiselect', 'range', 'number'
    options: List[Any] = field(default_factory=list)  # For select/multiselect
    min_value: float = None  # For range/number
    max_value: float = None  # For range/number
    default: Any = None
    help_text: str = ""
    requires_financial_data: bool = False  # If True, needs data fetch to apply


# ==================== FILTER DEFINITIONS ====================
# Add new filters here - they will automatically appear in the UI

FILTER_DEFINITIONS = [
    # Basic Filters
    FilterDefinition(
        key="sector",
        label="Sector",
        category=FilterCategory.BASIC,
        filter_type="multiselect",
        options=[
            "Technology", "Healthcare", "Financial Services", "Consumer Cyclical",
            "Consumer Defensive", "Industrials", "Energy", "Utilities",
            "Real Estate", "Basic Materials", "Communication Services"
        ],
        default=[],
        help_text="Filter by company sector"
    ),
    FilterDefinition(
        key="exchange",
        label="Exchange",
        category=FilterCategory.BASIC,
        filter_type="multiselect",
        options=["NASDAQ", "NYSE", "AMEX"],
        default=[],
        help_text="Filter by stock exchange"
    ),

    # Market Filters
    FilterDefinition(
        key="market_cap_universe",
        label="Market Cap Universe",
        category=FilterCategory.MARKET,
        filter_type="multiselect",
        options=["Mega Cap", "Large Cap", "Mid Cap", "Small Cap", "Micro Cap"],
        default=[],
        help_text="Filter by market capitalization tier"
    ),

    # Profitability Filters
    FilterDefinition(
        key="positive_fcf_last_year",
        label="Positive FCF (Last Year)",
        category=FilterCategory.PROFITABILITY,
        filter_type="select",
        options=["Any", "Yes", "No"],
        default="Any",
        help_text="Require positive FCF in the most recent year",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_3",
        label="Positive FCF Years (Last 3)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=3,
        default=0,
        help_text="Minimum years with positive FCF in last 3 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_5",
        label="Positive FCF Years (Last 5)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=5,
        default=0,
        help_text="Minimum years with positive FCF in last 5 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_10",
        label="Positive FCF Years (Last 10)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=10,
        default=0,
        help_text="Minimum years with positive FCF in last 10 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="min_gross_margin",
        label="Minimum Gross Margin %",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=100,
        default=0,
        help_text="Minimum gross margin percentage",
        requires_financial_data=True
    ),

    # Growth Filters
    FilterDefinition(
        key="revenue_growth_years_5",
        label="Revenue Growth Years (Last 5)",
        category=FilterCategory.GROWTH,
        filter_type="number",
        min_value=0,
        max_value=5,
        default=0,
        help_text="Minimum years with revenue growth in last 5 years",
        requires_financial_data=True
    ),
]


def get_filters_by_category() -> Dict[FilterCategory, List[FilterDefinition]]:
    """Group filters by category for UI organization"""
    result = {}
    for filter_def in FILTER_DEFINITIONS:
        if filter_def.category not in result:
            result[filter_def.category] = []
        result[filter_def.category].append(filter_def)
    return result


def get_market_cap_universe(market_cap: float) -> str:
    """Classify market cap into universe tier"""
    if market_cap >= 200e9:
        return "Mega Cap"
    elif market_cap >= 10e9:
        return "Large Cap"
    elif market_cap >= 2e9:
        return "Mid Cap"
    elif market_cap >= 300e6:
        return "Small Cap"
    elif market_cap >= 50e6:
        return "Micro Cap"
    else:
        return "Nano Cap"


class BatchScreener:
    """
    Batch stock screener with two-stage filtering:
    1. Basic filters (sector, exchange, market cap) - fast, no data fetch
    2. Financial filters (FCF, margins, growth) - requires data fetch
    """

    def __init__(self, data_source: str = "yahoo", api_key: str = None):
        self.data_source = data_source
        self.api_key = api_key

        # Initialize appropriate fetcher
        if data_source == "roic":
            from data_fetcher_roic import RoicDataFetcher
            self.fetcher = RoicDataFetcher(api_key)
        else:
            from data_fetcher_yahoo import YahooFinanceFetcher
            self.fetcher = YahooFinanceFetcher(api_key)

    def get_stock_universe(self, exchange: str = None) -> List[Dict]:
        """
        Get the universe of stocks to screen.
        Returns list of dicts with basic info: ticker, name, sector, exchange, market_cap
        """
        if self.data_source == "roic":
            return self._get_roic_universe(exchange)
        else:
            return self._get_yahoo_universe(exchange)

    def _get_yahoo_universe(self, exchange: str = None) -> List[Dict]:
        """
        Get stock universe using Yahoo Finance screener.
        Uses yfinance screener for major indices.
        """
        stocks = []

        # Get stocks from major indices
        indices = {
            'NASDAQ': '^IXIC',
            'NYSE': '^NYA',
        }

        # Use S&P 500 as a reliable universe
        try:
            # Get S&P 500 tickers
            sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            import pandas as pd
            tables = pd.read_html(sp500_url)
            sp500_df = tables[0]

            for _, row in sp500_df.iterrows():
                ticker = row['Symbol'].replace('.', '-')  # Yahoo format
                stock_info = {
                    'ticker': ticker,
                    'name': row.get('Security', ticker),
                    'sector': row.get('GICS Sector', 'N/A'),
                    'industry': row.get('GICS Sub-Industry', 'N/A'),
                    'exchange': 'NYSE' if row.get('Symbol', '').find('.') == -1 else 'NASDAQ',
                    'market_cap': 0  # Will be fetched later if needed
                }

                # Filter by exchange if specified
                if exchange and stock_info['exchange'] != exchange:
                    continue

                stocks.append(stock_info)

        except Exception as e:
            print(f"Error fetching S&P 500 list: {e}")
            # Fallback to a small list of well-known tickers
            fallback_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'JPM',
                'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'VZ', 'NFLX'
            ]
            for ticker in fallback_tickers:
                stocks.append({
                    'ticker': ticker,
                    'name': ticker,
                    'sector': 'N/A',
                    'exchange': 'N/A',
                    'market_cap': 0
                })

        return stocks

    def _get_roic_universe(self, exchange: str = None) -> List[Dict]:
        """Get stock universe from ROIC.ai"""
        try:
            tickers = self.fetcher.get_exchange_tickers(exchange)

            stocks = []
            for ticker in tickers:
                stocks.append({
                    'ticker': ticker,
                    'name': ticker,
                    'sector': 'N/A',  # Will be fetched later
                    'exchange': exchange or 'N/A',
                    'market_cap': 0
                })

            return stocks
        except Exception as e:
            print(f"Error fetching ROIC universe: {e}")
            return []

    def enrich_stock_info(self, stock: Dict) -> Dict:
        """
        Fetch additional info for a stock (sector, market cap, etc.)
        Used for stocks where we don't have complete info
        """
        try:
            ticker = stock['ticker']
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info

            stock['name'] = info.get('longName', stock.get('name', ticker))
            stock['sector'] = info.get('sector', stock.get('sector', 'N/A'))
            stock['industry'] = info.get('industry', stock.get('industry', 'N/A'))
            stock['exchange'] = info.get('exchange', stock.get('exchange', 'N/A'))
            stock['market_cap'] = info.get('marketCap', 0) or 0
            stock['market_cap_universe'] = get_market_cap_universe(stock['market_cap'])

            # Additional quick metrics
            stock['gross_margin'] = (info.get('grossMargins', 0) or 0) * 100

        except Exception as e:
            print(f"Error enriching {stock['ticker']}: {e}")
            stock['market_cap_universe'] = 'Unknown'
            stock['gross_margin'] = 0

        return stock

    def get_financial_metrics(self, ticker: str, years: int = 10) -> Dict:
        """
        Fetch financial metrics needed for filtering.
        Returns metrics like FCF history, revenue growth, margins.
        """
        try:
            if self.data_source == "roic":
                data = self.fetcher.get_financial_data_complete(ticker, years_back=years)
            else:
                data = self.fetcher.get_financial_data_complete(ticker)

            # Extract FCF history
            fcf_history = []
            for cf in data.get('cash_flows', []):
                fcf = cf.get('freeCashFlow', 0)
                date = cf.get('date', '')
                if date:
                    year = int(date[:4])
                    fcf_history.append({'year': year, 'fcf': fcf})

            # Extract revenue history
            revenue_history = []
            for inc in data.get('income_statements', []):
                revenue = inc.get('revenue', 0)
                date = inc.get('date', '')
                if date:
                    year = int(date[:4])
                    revenue_history.append({'year': year, 'revenue': revenue})

            # Sort by year (newest first)
            fcf_history.sort(key=lambda x: x['year'], reverse=True)
            revenue_history.sort(key=lambda x: x['year'], reverse=True)

            # Calculate metrics
            positive_fcf_last_year = fcf_history[0]['fcf'] > 0 if fcf_history else False

            positive_fcf_count_3 = sum(1 for f in fcf_history[:3] if f['fcf'] > 0)
            positive_fcf_count_5 = sum(1 for f in fcf_history[:5] if f['fcf'] > 0)
            positive_fcf_count_10 = sum(1 for f in fcf_history[:10] if f['fcf'] > 0)

            # Revenue growth years
            revenue_growth_years = 0
            for i in range(min(5, len(revenue_history) - 1)):
                if revenue_history[i]['revenue'] > revenue_history[i + 1]['revenue']:
                    revenue_growth_years += 1

            return {
                'positive_fcf_last_year': positive_fcf_last_year,
                'positive_fcf_years_3': positive_fcf_count_3,
                'positive_fcf_years_5': positive_fcf_count_5,
                'positive_fcf_years_10': positive_fcf_count_10,
                'revenue_growth_years_5': revenue_growth_years,
                'fcf_history': fcf_history,
                'revenue_history': revenue_history,
                'full_data': data  # Keep for DCF analysis
            }

        except Exception as e:
            print(f"Error fetching financial metrics for {ticker}: {e}")
            return {
                'positive_fcf_last_year': False,
                'positive_fcf_years_3': 0,
                'positive_fcf_years_5': 0,
                'positive_fcf_years_10': 0,
                'revenue_growth_years_5': 0,
                'fcf_history': [],
                'revenue_history': [],
                'full_data': None
            }

    def apply_basic_filters(self, stocks: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply basic filters that don't require financial data fetch.
        """
        filtered = []

        for stock in stocks:
            # Sector filter
            if filters.get('sector') and len(filters['sector']) > 0:
                if stock.get('sector', 'N/A') not in filters['sector']:
                    continue

            # Exchange filter
            if filters.get('exchange') and len(filters['exchange']) > 0:
                stock_exchange = stock.get('exchange', 'N/A')
                # Normalize exchange names
                if 'NASDAQ' in stock_exchange.upper() or 'NMS' in stock_exchange.upper():
                    stock_exchange = 'NASDAQ'
                elif 'NYSE' in stock_exchange.upper() or 'NYQ' in stock_exchange.upper():
                    stock_exchange = 'NYSE'
                elif 'AMEX' in stock_exchange.upper():
                    stock_exchange = 'AMEX'

                if stock_exchange not in filters['exchange']:
                    continue

            # Market cap universe filter
            if filters.get('market_cap_universe') and len(filters['market_cap_universe']) > 0:
                universe = stock.get('market_cap_universe', 'Unknown')
                if universe not in filters['market_cap_universe']:
                    continue

            filtered.append(stock)

        return filtered

    def apply_financial_filters(self, stock: Dict, metrics: Dict, filters: Dict) -> bool:
        """
        Apply financial filters that require data fetch.
        Returns True if stock passes all filters.
        """
        # Positive FCF last year
        if filters.get('positive_fcf_last_year') == "Yes":
            if not metrics.get('positive_fcf_last_year', False):
                return False
        elif filters.get('positive_fcf_last_year') == "No":
            if metrics.get('positive_fcf_last_year', False):
                return False

        # Positive FCF years (3)
        min_fcf_3 = filters.get('positive_fcf_years_3', 0)
        if min_fcf_3 > 0:
            if metrics.get('positive_fcf_years_3', 0) < min_fcf_3:
                return False

        # Positive FCF years (5)
        min_fcf_5 = filters.get('positive_fcf_years_5', 0)
        if min_fcf_5 > 0:
            if metrics.get('positive_fcf_years_5', 0) < min_fcf_5:
                return False

        # Positive FCF years (10)
        min_fcf_10 = filters.get('positive_fcf_years_10', 0)
        if min_fcf_10 > 0:
            if metrics.get('positive_fcf_years_10', 0) < min_fcf_10:
                return False

        # Revenue growth years
        min_rev_growth = filters.get('revenue_growth_years_5', 0)
        if min_rev_growth > 0:
            if metrics.get('revenue_growth_years_5', 0) < min_rev_growth:
                return False

        # Minimum gross margin
        min_gross_margin = filters.get('min_gross_margin', 0)
        if min_gross_margin > 0:
            if stock.get('gross_margin', 0) < min_gross_margin:
                return False

        return True

    def has_financial_filters(self, filters: Dict) -> bool:
        """Check if any financial filters are active"""
        financial_filter_keys = [
            'positive_fcf_last_year', 'positive_fcf_years_3', 'positive_fcf_years_5',
            'positive_fcf_years_10', 'revenue_growth_years_5', 'min_gross_margin'
        ]

        for key in financial_filter_keys:
            value = filters.get(key)
            if value is not None and value != 0 and value != "Any" and value != []:
                return True

        return False

    def screen_stocks(self, filters: Dict, progress_callback: Callable = None,
                     max_stocks: int = None) -> List[Dict]:
        """
        Main screening method. Returns list of stocks that pass all filters.

        Args:
            filters: Dict of filter values
            progress_callback: Function(current, total, message) for progress updates
            max_stocks: Maximum number of stocks to return

        Returns:
            List of stock dicts that pass all filters, with enriched data
        """
        # Get initial universe
        if progress_callback:
            progress_callback(0, 100, "Fetching stock universe...")

        exchange_filter = filters.get('exchange', [])
        exchange = exchange_filter[0] if len(exchange_filter) == 1 else None

        stocks = self.get_stock_universe(exchange)

        if progress_callback:
            progress_callback(10, 100, f"Found {len(stocks)} stocks, enriching data...")

        # Enrich stocks with basic info (for basic filtering)
        enriched_stocks = []
        for i, stock in enumerate(stocks):
            if progress_callback and i % 10 == 0:
                pct = 10 + int((i / len(stocks)) * 30)
                progress_callback(pct, 100, f"Enriching stock data... ({i}/{len(stocks)})")

            enriched = self.enrich_stock_info(stock)
            enriched_stocks.append(enriched)
            time.sleep(0.1)  # Rate limiting

        # Apply basic filters
        if progress_callback:
            progress_callback(40, 100, "Applying basic filters...")

        basic_filtered = self.apply_basic_filters(enriched_stocks, filters)

        if progress_callback:
            progress_callback(45, 100, f"{len(basic_filtered)} stocks passed basic filters")

        # If no financial filters, we're done
        if not self.has_financial_filters(filters):
            result = basic_filtered[:max_stocks] if max_stocks else basic_filtered
            if progress_callback:
                progress_callback(100, 100, f"Screening complete: {len(result)} stocks")
            return result

        # Apply financial filters (requires data fetch)
        if progress_callback:
            progress_callback(50, 100, "Applying financial filters...")

        final_stocks = []
        for i, stock in enumerate(basic_filtered):
            if max_stocks and len(final_stocks) >= max_stocks:
                break

            if progress_callback:
                pct = 50 + int((i / len(basic_filtered)) * 45)
                progress_callback(pct, 100, f"Checking {stock['ticker']}... ({i}/{len(basic_filtered)})")

            # Fetch financial metrics
            metrics = self.get_financial_metrics(stock['ticker'])

            # Apply financial filters
            if self.apply_financial_filters(stock, metrics, filters):
                stock['metrics'] = metrics
                final_stocks.append(stock)

            time.sleep(0.2)  # Rate limiting

        if progress_callback:
            progress_callback(100, 100, f"Screening complete: {len(final_stocks)} stocks passed all filters")

        return final_stocks


# Get all unique sectors from the filter definition
def get_all_sectors() -> List[str]:
    """Get list of all sectors for the filter dropdown"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'sector':
            return f.options
    return []


def get_all_exchanges() -> List[str]:
    """Get list of all exchanges for the filter dropdown"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'exchange':
            return f.options
    return []


def get_all_market_cap_universes() -> List[str]:
    """Get list of all market cap universes"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'market_cap_universe':
            return f.options
    return []
